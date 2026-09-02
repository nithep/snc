"""Rule-based Ops Self-Healing Agent for SNC Phase 1.

The agent is intentionally small and deterministic.  It performs read-only
health checks and can request a PBX reconnect through a hand-off file that the
listener owns.  It never restarts services, changes alerts, or sends patient
data to an external service.
"""

from __future__ import annotations

import asyncio
import importlib.util
import json
import logging
import os
import shutil
import socket
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Mapping, Optional

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class OpsThresholds:
    """Thresholds for warnings and bounded reconnect requests."""

    pbx_timeout_seconds: float = 2.0
    backend_timeout_seconds: float = 5.0
    wal_warning_bytes: int = 64 * 1024 * 1024
    disk_warning_percent: float = 85.0
    reconnect_cooldown_seconds: float = 300.0
    max_reconnect_requests: int = 3


@dataclass
class OpsAgentConfig:
    """Runtime configuration loaded from environment variables."""

    pbx_host: str = "192.168.1.91"
    pbx_port: int = 23
    proxy_host: str = "127.0.0.1"
    proxy_port: int = 2323
    backend_url: str = "http://127.0.0.1:8000"
    db_path: str = "nurse_call_events.db"
    reconnect_request_file: str = ""
    poll_interval_seconds: float = 30.0
    auto_reconnect: bool = False
    alert_enabled: bool = False
    thresholds: OpsThresholds = field(default_factory=OpsThresholds)

    @classmethod
    def from_env(cls) -> "OpsAgentConfig":
        """Build config from SNC-specific env vars without reading secrets."""
        root = Path(__file__).resolve().parents[3]
        db_path = os.getenv("SNC_SQLITE_PATH", str(root / "api" / "nurse_call_events.db"))
        request_file = os.getenv(
            "SNC_RECONNECT_REQUEST_FILE",
            str(root / "api" / ".snc-reconnect-request.json"),
        )
        thresholds = OpsThresholds(
            pbx_timeout_seconds=_env_float("SNC_OPS_PBX_TIMEOUT", 2.0),
            backend_timeout_seconds=_env_float("SNC_OPS_BACKEND_TIMEOUT", 5.0),
            wal_warning_bytes=_env_int("SNC_OPS_WAL_WARNING_BYTES", 64 * 1024 * 1024),
            disk_warning_percent=_env_float("SNC_OPS_DISK_WARNING_PERCENT", 85.0),
            reconnect_cooldown_seconds=_env_float("SNC_OPS_RECONNECT_COOLDOWN", 300.0),
            max_reconnect_requests=_env_int("SNC_OPS_MAX_RECONNECT_REQUESTS", 3),
        )
        return cls(
            pbx_host=os.getenv("PBX_IP", "192.168.1.91"),
            pbx_port=_env_int("PBX_PORT", 23),
            proxy_host=os.getenv("SNC_OPS_PROXY_HOST", "127.0.0.1"),
            proxy_port=_env_int("PROXY_PORT", 2323),
            backend_url=os.getenv("BACKEND_API_URL", "http://127.0.0.1:8000").rstrip("/"),
            db_path=db_path,
            reconnect_request_file=request_file,
            poll_interval_seconds=_env_float("SNC_OPS_POLL_INTERVAL", 30.0),
            auto_reconnect=_env_bool("SNC_OPS_AUTO_RECONNECT", False),
            alert_enabled=_env_bool("SNC_OPS_ALERT_ENABLED", False),
            thresholds=thresholds,
        )


class OpsSelfHealingAgent:
    """Collect SNC health and perform only explicitly allowed recovery actions."""

    def __init__(
        self,
        config: Optional[OpsAgentConfig] = None,
        *,
        clock: Callable[[], float] = time.monotonic,
        tcp_checker: Optional[Callable[[str, int, float], bool]] = None,
        http_checker: Optional[Callable[[str, float], Mapping[str, Any]]] = None,
    ):
        self.config = config or OpsAgentConfig.from_env()
        self._clock = clock
        self._tcp_checker = tcp_checker or self._check_tcp
        self._http_checker = http_checker or self._check_http
        self._last_reconnect_at = float("-inf")
        self._reconnect_requests = 0
        self._stop_event = asyncio.Event()

    @staticmethod
    def _check_tcp(host: str, port: int, timeout: float) -> bool:
        try:
            with socket.create_connection((host, port), timeout=timeout):
                return True
        except (OSError, ValueError):
            return False

    @staticmethod
    def _check_http(url: str, timeout: float) -> Mapping[str, Any]:
        request = urllib.request.Request(
            url,
            headers={"User-Agent": "SNC-Ops-Agent/1.0"},
        )
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = response.read().decode("utf-8")
        data = json.loads(payload)
        if not isinstance(data, dict):
            raise ValueError("health response must be a JSON object")
        return data

    def _database_report(self) -> Dict[str, Any]:
        path = Path(self.config.db_path)
        report: Dict[str, Any] = {
            "path": str(path),
            "exists": path.is_file(),
            "bytes": path.stat().st_size if path.is_file() else 0,
            "wal_bytes": 0,
            "shm_bytes": 0,
        }
        for suffix, key in (("-wal", "wal_bytes"), ("-shm", "shm_bytes")):
            sidecar = Path(str(path) + suffix)
            if sidecar.is_file():
                report[key] = sidecar.stat().st_size
        report["status"] = "missing" if not report["exists"] else "healthy"
        if report["wal_bytes"] >= self.config.thresholds.wal_warning_bytes:
            report["status"] = "warning"
        return report

    def _disk_report(self) -> Dict[str, Any]:
        target = Path(self.config.db_path).resolve().parent
        usage = shutil.disk_usage(target)
        used_percent = ((usage.total - usage.free) / usage.total * 100) if usage.total else 0.0
        return {
            "path": str(target),
            "used_percent": round(used_percent, 2),
            "free_bytes": usage.free,
            "status": "warning" if used_percent >= self.config.thresholds.disk_warning_percent else "healthy",
        }

    def collect_health(self) -> Dict[str, Any]:
        """Return an operator-safe report with no patient event payloads."""
        checks: Dict[str, Any] = {}
        for name, host, port in (
            ("pbx", self.config.pbx_host, self.config.pbx_port),
            ("proxy", self.config.proxy_host, self.config.proxy_port),
        ):
            started = self._clock()
            try:
                ok = bool(self._tcp_checker(host, port, self.config.thresholds.pbx_timeout_seconds))
                checks[name] = {
                    "status": "healthy" if ok else "down",
                    "target": f"{host}:{port}",
                    "latency_ms": round((self._clock() - started) * 1000, 2),
                }
            except Exception as exc:  # diagnostics must not crash the worker
                checks[name] = {
                    "status": "unknown",
                    "target": f"{host}:{port}",
                    "error": type(exc).__name__,
                }

        try:
            backend = dict(self._http_checker(
                f"{self.config.backend_url}/health",
                self.config.thresholds.backend_timeout_seconds,
            ))
            checks["backend"] = {
                "status": str(backend.get("status", "unknown")),
                "backend": backend.get("service", "snc-backend"),
            }
        except (OSError, ValueError, urllib.error.URLError) as exc:
            checks["backend"] = {"status": "down", "error": type(exc).__name__}
        except Exception as exc:
            checks["backend"] = {"status": "unknown", "error": type(exc).__name__}

        checks["database"] = self._database_report()
        checks["disk"] = self._disk_report()
        statuses = [str(item.get("status", "unknown")) for item in checks.values()]
        overall = "down" if "down" in statuses else (
            "degraded" if any(s in {"warning", "unknown", "missing"} for s in statuses) else "healthy"
        )
        return {
            "agent": "ops-self-healing",
            "mode": "rule-based",
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "status": overall,
            "checks": checks,
            "safe_execution": {
                "auto_reconnect_enabled": self.config.auto_reconnect,
                "restart_services": False,
                "modify_alerts": False,
                "export_patient_data": False,
            },
        }

    def request_pbx_reconnect(self, reason: str) -> Dict[str, Any]:
        """Request listener-owned reconnect, bounded by cooldown and count."""
        if not self.config.auto_reconnect:
            return {"status": "disabled", "reason": "SNC_OPS_AUTO_RECONNECT is disabled"}
        now = self._clock()
        if self._reconnect_requests >= self.config.thresholds.max_reconnect_requests:
            return {"status": "blocked", "reason": "reconnect request limit reached"}
        if now - self._last_reconnect_at < self.config.thresholds.reconnect_cooldown_seconds:
            return {"status": "cooldown", "reason": "reconnect cooldown is active"}
        request_path = Path(self.config.reconnect_request_file)
        request_path.parent.mkdir(parents=True, exist_ok=True)
        request_path.write_text(
            json.dumps({
                "requested_at": datetime.now(timezone.utc).isoformat(),
                "reason": str(reason)[:500],
                "source": "ops-self-healing-agent",
            }, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        self._last_reconnect_at = now
        self._reconnect_requests += 1
        return {"status": "requested", "path": str(request_path)}

    def remediate(self, report: Mapping[str, Any]) -> Dict[str, Any]:
        """Apply Phase 1 remediation rules; never restart or mutate clinical data."""
        pbx_status = ((report.get("checks") or {}).get("pbx") or {}).get("status")
        action = {"status": "none", "reason": "no bounded remediation required"}
        if pbx_status == "down":
            action = self.request_pbx_reconnect("PBX TCP health check is down")
        return {"report_status": report.get("status", "unknown"), "action": action}

    def _emit_alert_if_enabled(self, report: Mapping[str, Any]) -> None:
        """Optionally send a non-clinical alert through the existing ledger path."""
        if not self.config.alert_enabled or report.get("status") == "healthy":
            return
        try:
            alert_path = Path(__file__).resolve().parents[3] / "ops" / "alerting.py"
            spec = importlib.util.spec_from_file_location("snc_ops_alerting", alert_path)
            if not spec or not spec.loader:
                return
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            failed = [
                name for name, check in (report.get("checks") or {}).items()
                if check.get("status") not in {"healthy", "active", "ready"}
            ]
            module.send_alert(
                "CRITICAL" if report.get("status") == "down" else "WARNING",
                "OPS_AGENT",
                "SNC Ops health requires attention",
                details="Checks: " + ", ".join(failed),
                verify="Run SNC Ops health report and inspect the relevant service logs.",
                dedupe_minutes=10,
            )
        except Exception:
            logger.exception("SNC Ops alert hook failed")

    async def run_once(self) -> Dict[str, Any]:
        report = await asyncio.to_thread(self.collect_health)
        report["remediation"] = await asyncio.to_thread(self.remediate, report)
        return report

    async def run(self) -> None:
        """Run the non-critical polling loop until stopped."""
        self._stop_event.clear()
        while not self._stop_event.is_set():
            try:
                report = await self.run_once()
                self._emit_alert_if_enabled(report)
                logger.info("SNC Ops health: status=%s", report["status"])
            except Exception:
                logger.exception("SNC Ops health cycle failed")
            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=self.config.poll_interval_seconds)
            except asyncio.TimeoutError:
                continue

    def stop(self) -> None:
        self._stop_event.set()


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except ValueError:
        return default


async def _main() -> None:
    logging.basicConfig(level=os.getenv("SNC_OPS_LOG_LEVEL", "INFO"))
    agent = OpsSelfHealingAgent()
    try:
        await agent.run()
    finally:
        agent.stop()


if __name__ == "__main__":
    try:
        asyncio.run(_main())
    except KeyboardInterrupt:
        pass
