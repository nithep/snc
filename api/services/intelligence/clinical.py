"""Deterministic clinical operations analytics for SNC.

This module produces read-only operational insights from already persisted SNC
records. It does not make clinical decisions, call an LLM, or modify events.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta
from statistics import mean
from typing import Any, Dict, Iterable, List, Mapping, Optional


CALL_TYPES = {"CALL_BEDSIDE", "CALL_BATHROOM_EMERGENCY", "CALL_TRIGGERED"}


def parse_timestamp(value: Any) -> Optional[datetime]:
    """Parse SNC ISO timestamps and normalize aware timestamps to local-naive time."""
    if not value:
        return None
    try:
        text = str(value).replace("Z", "+00:00")
        parsed = datetime.fromisoformat(text)
        if parsed.tzinfo is not None:
            parsed = parsed.astimezone().replace(tzinfo=None)
        return parsed
    except (TypeError, ValueError):
        return None


def _is_call_event(event: Mapping[str, Any]) -> bool:
    return str(event.get("event_type", "")) in CALL_TYPES


def _numeric_metric(event: Mapping[str, Any], field: str, end_field: str) -> Optional[float]:
    value = event.get(field)
    if value is not None:
        try:
            return float(value)
        except (TypeError, ValueError):
            return None
    start = parse_timestamp(event.get("timestamp"))
    end = parse_timestamp(event.get(end_field))
    if start is None or end is None:
        return None
    return max(0.0, (end - start).total_seconds())


def _metric_values(events: Iterable[Mapping[str, Any]], field: str, end_field: str) -> List[float]:
    return [
        metric
        for event in events
        for metric in [_numeric_metric(event, field, end_field)]
        if metric is not None
    ]


class ClinicalAnalyticsAgent:
    """Generate frequent-caller and SLA-drift insights without side effects."""

    def __init__(self, *, frequent_window_hours: float = 4.0, frequent_min_calls: int = 3,
                 baseline_days: int = 7):
        self.frequent_window_hours = max(1.0, float(frequent_window_hours))
        self.frequent_min_calls = max(2, int(frequent_min_calls))
        self.baseline_days = max(1, int(baseline_days))

    def analyze(
        self,
        events: Iterable[Mapping[str, Any]],
        *,
        now: Optional[datetime] = None,
        window_hours: float = 24.0,
    ) -> Dict[str, Any]:
        """Return read-only insights for the requested recent window."""
        now = now or datetime.now()
        window_hours = min(max(float(window_hours), 1.0), 24.0 * self.baseline_days)
        recent_start = now - timedelta(hours=window_hours)
        baseline_start = recent_start - timedelta(days=self.baseline_days)
        normalized = [event for event in events if _is_call_event(event)]
        recent = [
            event for event in normalized
            if (timestamp := parse_timestamp(event.get("timestamp"))) is not None
            and recent_start <= timestamp <= now
        ]
        baseline = [
            event for event in normalized
            if (timestamp := parse_timestamp(event.get("timestamp"))) is not None
            and baseline_start <= timestamp < recent_start
        ]

        return {
            "agent": "clinical-analytics",
            "mode": "rule-based",
            "generated_at": now.isoformat(),
            "source": "persisted-snc-events",
            "window": {
                "hours": window_hours,
                "recent_start": recent_start.isoformat(),
                "end": now.isoformat(),
                "baseline_days": self.baseline_days,
            },
            "frequent_callers": self._frequent_callers(recent, now),
            "sla_drift": self._sla_drift(recent, baseline),
            "summary": self._summary(recent),
            "safety": {
                "read_only": True,
                "clinical_decision": False,
                "requires_human_review": True,
            },
        }

    def _frequent_callers(self, events: Iterable[Mapping[str, Any]], now: datetime) -> List[Dict[str, Any]]:
        grouped: Dict[str, List[Mapping[str, Any]]] = defaultdict(list)
        frequent_start = now - timedelta(hours=self.frequent_window_hours)
        for event in events:
            timestamp = parse_timestamp(event.get("timestamp"))
            if timestamp is None or timestamp < frequent_start or timestamp > now:
                continue
            room_id = str(event.get("room_id", "")).zfill(4)
            if room_id:
                grouped[room_id].append(event)

        callers = []
        for room_id, room_events in grouped.items():
            if len(room_events) < self.frequent_min_calls:
                continue
            timestamps = sorted(
                timestamp for event in room_events
                for timestamp in [parse_timestamp(event.get("timestamp"))]
                if timestamp is not None
            )
            emergency_count = sum(
                1 for event in room_events if event.get("event_type") == "CALL_BATHROOM_EMERGENCY"
            )
            callers.append({
                "room_id": room_id,
                "call_count": len(room_events),
                "emergency_count": emergency_count,
                "first_call_at": timestamps[0].isoformat() if timestamps else None,
                "last_call_at": timestamps[-1].isoformat() if timestamps else None,
                "window_hours": self.frequent_window_hours,
                "threshold_calls": self.frequent_min_calls,
                "severity": "high" if emergency_count else "attention",
                "requires_human_review": True,
            })
        return sorted(callers, key=lambda item: (-item["call_count"], item["room_id"]))

    @staticmethod
    def _sla_drift(recent: List[Mapping[str, Any]], baseline: List[Mapping[str, Any]]) -> Dict[str, Any]:
        current_ack = _metric_values(recent, "ack_time_seconds", "acknowledged_at")
        previous_ack = _metric_values(baseline, "ack_time_seconds", "acknowledged_at")
        current_resolution = _metric_values(recent, "resolution_time_seconds", "resolved_at")
        previous_resolution = _metric_values(baseline, "resolution_time_seconds", "resolved_at")
        completed = [event for event in recent if event.get("status") == "resolved"]
        breached = sum(1 for event in completed if bool(event.get("sla_breached")))

        ack_avg = mean(current_ack) if current_ack else None
        previous_ack_avg = mean(previous_ack) if previous_ack else None
        resolution_avg = mean(current_resolution) if current_resolution else None
        previous_resolution_avg = mean(previous_resolution) if previous_resolution else None
        ack_drift = ack_avg - previous_ack_avg if ack_avg is not None and previous_ack_avg is not None else None
        resolution_drift = (
            resolution_avg - previous_resolution_avg
            if resolution_avg is not None and previous_resolution_avg is not None else None
        )
        drift_values = [value for value in (ack_drift, resolution_drift) if value is not None]
        status = "insufficient_baseline"
        if drift_values:
            status = "degraded" if any(value > 5 for value in drift_values) else (
                "improved" if all(value < -5 for value in drift_values) else "stable"
            )

        return {
            "status": status,
            "current": {
                "sample_size": len(recent),
                "ack_sample_size": len(current_ack),
                "resolution_sample_size": len(current_resolution),
                "avg_ack_time_seconds": round(ack_avg, 2) if ack_avg is not None else None,
                "avg_resolution_time_seconds": round(resolution_avg, 2) if resolution_avg is not None else None,
                "completed_cases": len(completed),
                "sla_breached_cases": breached,
                "sla_breach_rate": round(breached / len(completed) * 100, 2) if completed else None,
            },
            "baseline": {
                "ack_sample_size": len(previous_ack),
                "resolution_sample_size": len(previous_resolution),
                "avg_ack_time_seconds": round(previous_ack_avg, 2) if previous_ack_avg is not None else None,
                "avg_resolution_time_seconds": round(previous_resolution_avg, 2)
                if previous_resolution_avg is not None else None,
            },
            "drift_seconds": {
                "ack": round(ack_drift, 2) if ack_drift is not None else None,
                "resolution": round(resolution_drift, 2) if resolution_drift is not None else None,
            },
        }

    @staticmethod
    def _summary(events: List[Mapping[str, Any]]) -> Dict[str, Any]:
        return {
            "call_events": len(events),
            "rooms_seen": len({str(event.get("room_id", "")).zfill(4) for event in events}),
            "emergency_events": sum(
                1 for event in events if event.get("event_type") == "CALL_BATHROOM_EMERGENCY"
            ),
        }
