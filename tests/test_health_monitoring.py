#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tests/test_health_monitoring.py — ทดสอบระบบ monitoring ใหม่ของ SNC

ครอบคลุม:
  1. api/server._systemd_service_status — mapping สถานะ systemd → /health
     (บนเครื่องไม่มี systemd เช่น Cloud Run/Windows → skipped ไม่นับเป็นปัญหา)
  2. ops/snc_telegram_agent.health_reply/logs_reply — ฟอร์แมตสถานะ+สาเหตุ+เมนูถัดไป
  3. ops/alerting.format_alert — template 4 ส่วนมาตรฐาน

รัน (ไม่ต้องมี pytest):
  python -m unittest tests/test_health_monitoring.py -v
"""
import datetime
import json
import os
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "ops"))

# กัน Windows console encoding ตอน assert ข้อความไทย
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def _fake_completed(stdout: str):
    completed = subprocess.CompletedProcess(args=[], returncode=0)
    completed.stdout = stdout
    completed.stderr = ""
    return completed


class SystemdServiceStatusTest(unittest.TestCase):
    """mapping systemctl is-active → (status, message)"""

    @classmethod
    def setUpClass(cls):
        # server.py import แบบ WorkingDirectory=api (systemd) — ต้องมี api/ ใน sys.path
        api_dir = os.path.join(ROOT, "api")
        if api_dir not in sys.path:
            sys.path.insert(0, api_dir)
        from api import server

        # staticmethod — กัน function กลายเป็น bound method เมื่อเรียกผ่าน self
        cls.status_of = staticmethod(server._systemd_service_status)

    def test_active(self):
        with mock.patch.object(subprocess, "run",
                               return_value=_fake_completed("active\n")):
            status, msg = self.status_of("snc-pbx-listener.service")
        self.assertEqual(status, "active")
        self.assertIn("active", msg)

    def test_activating_maps_to_degraded(self):
        with mock.patch.object(subprocess, "run",
                               return_value=_fake_completed("activating\n")):
            status, msg = self.status_of("snc-pbx-listener.service")
        self.assertEqual(status, "degraded")
        self.assertIn("activating", msg)

    def test_failed_maps_to_down(self):
        with mock.patch.object(subprocess, "run",
                               return_value=_fake_completed("failed\n")):
            status, msg = self.status_of("snc-pbx-listener.service")
        self.assertEqual(status, "down")
        self.assertIn("failed", msg)

    def test_no_systemd_is_skipped_not_failure(self):
        """Cloud Run / Windows ไม่มี systemctl — ต้อง skipped ไม่ใช่ down (กัน false alarm)"""
        with mock.patch.object(subprocess, "run",
                               side_effect=FileNotFoundError()):
            status, msg = self.status_of("snc-pbx-listener.service")
        self.assertEqual(status, "skipped")
        self.assertNotIn("systemd active", msg)


class AgentHealthReplyTest(unittest.TestCase):
    """ฟอร์แมตข้อความ /health ของ Telegram agent"""

    @classmethod
    def setUpClass(cls):
        import snc_telegram_agent as agent

        cls.agent = agent

    def _reply_with(self, payload):
        with mock.patch.object(self.agent, "http_json", return_value=payload):
            return self.agent.health_reply()

    def test_healthy_message_structure(self):
        text = self._reply_with({
            "status": "healthy",
            "timestamp": "2026-09-02T01:00:00",
            "reason": "ไม่พบความผิดปกติจาก Backend health check",
            "checks": {
                "backend": {"status": "healthy", "message": "ตอบสนองปกติ"},
                "pbx_listener": {"status": "active", "message": "systemd active"},
            },
        })
        self.assertIn("HEALTHY", text)
        self.assertIn("Backend API", text)
        self.assertIn("PBX Listener", text)
        self.assertIn("systemd active", text)
        self.assertIn("สาเหตุที่ตรวจพบ", text)
        self.assertIn("เมนูถัดไป", text)

    def test_no_more_unnamed_services(self):
        """ห้ามกลับไปเป็น 'services: active, active' แบบไม่ระบุชื่อ"""
        text = self._reply_with({
            "status": "healthy", "checks": {
                "pbx_listener": {"status": "active", "message": "ok"}}})
        self.assertNotIn("services: active, active", text)
        self.assertIn("PBX Listener", text)

    def test_backend_down_message(self):
        with mock.patch.object(self.agent, "http_json",
                               side_effect=Exception("connection refused")):
            text = self.agent.health_reply()
        self.assertIn("DOWN", text)
        self.assertIn("ไม่สามารถเรียก /health ได้", text)
        self.assertIn("/logs", text)

    def test_html_escaped_cause(self):
        """สาเหตุที่มีอักขระ HTML ต้องถูก escape กัน Telegram parse พัง"""
        with mock.patch.object(self.agent, "http_json",
                               side_effect=Exception("<b>&broken")):
            text = self.agent.health_reply()
        self.assertIn("&lt;b&gt;&amp;broken", text)

    def test_logs_reply_graceful_without_journalctl(self):
        with mock.patch.object(self.agent.subprocess, "run",
                               side_effect=FileNotFoundError()):
            text = self.agent.logs_reply()
        self.assertIn("journalctl", text)
        self.assertIn("เมนูถัดไป", text)


class AlertFormatTest(unittest.TestCase):
    """template alert มาตรฐาน 4 ส่วน"""

    @classmethod
    def setUpClass(cls):
        import alerting

        cls.alerting = alerting

    def _format(self):
        return self.alerting.format_alert(
            "CRITICAL", "SNC-AL-CLOUD-20260902-010947",
            "Cloud Run uptime check /health failed",
            details="Uptime check ล้มเหลว 120 วินาที",
            verify="curl https://example.com/health")

    def test_four_sections_present(self):
        text = self._format()
        self.assertIn("สถานะรวม", text)
        self.assertIn("รายการตรวจสอบ", text)
        self.assertIn("สาเหตุที่ตรวจพบ", text)
        self.assertIn("เมนูถัดไป", text)

    def test_reference_code_and_verify(self):
        text = self._format()
        self.assertIn("SNC-AL-CLOUD-20260902-010947", text)
        self.assertIn("curl https://example.com/health", text)

    def test_make_code_shape(self):
        code = self.alerting.make_code("cloud")
        self.assertTrue(code.startswith("SNC-AL-CLOUD-"))


class RecoveryAndDedupeTest(unittest.TestCase):
    """send_recovery / pending_incidents / dedupe — ใช้ temp ledger ไม่กระทบของจริง"""

    def setUp(self):
        import alerting

        self.alerting = alerting
        self._old_ledger = alerting.LEDGER
        fd, path = tempfile.mkstemp(suffix=".log")
        os.close(fd)
        alerting.LEDGER = path
        self.tmp_ledger = path

    def tearDown(self):
        self.alerting.LEDGER = self._old_ledger
        os.unlink(self.tmp_ledger)

    def _ts(self, minutes_ago: int) -> str:
        ts = datetime.datetime.now() - datetime.timedelta(minutes=minutes_ago)
        return ts.strftime("%Y-%m-%d %H:%M:%S")

    def _write(self, entry):
        with open(self.tmp_ledger, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def test_format_recovery_sections(self):
        text = self.alerting.format_recovery(
            "SNC-AL-RECOVERY-20260902-021000", "TUNNEL",
            recovered_from="SNC-AL-TUNNEL-20260902-010000", downtime="~60 นาที")
        self.assertIn("กลับมาปกติแล้ว", text)
        self.assertIn("HEALTHY", text)
        self.assertIn("SNC-AL-TUNNEL-20260902-010000", text)
        self.assertIn("~60 นาที", text)
        self.assertIn("เมนูถัดไป", text)

    def test_pending_incidents_open_and_closed(self):
        self._write({"code": "SNC-AL-TUNNEL-1", "type": "TUNNEL",
                     "ts": self._ts(120), "sent": True})
        self.assertEqual(list(self.alerting.pending_incidents()), ["TUNNEL"])

        self._write({"code": "SNC-AL-RECOVERY-1", "type": "RECOVERY",
                     "ts": self._ts(60), "recovered_type": "TUNNEL",
                     "recovered_from": "SNC-AL-TUNNEL-1", "sent": True})
        self.assertEqual(self.alerting.pending_incidents(), {})

    def test_pending_incidents_ignores_recovery_without_target(self):
        self._write({"code": "SNC-AL-RECOVERY-X", "type": "RECOVERY",
                     "ts": self._ts(10), "sent": True})
        self.assertEqual(self.alerting.pending_incidents(), {})

    def test_recent_same_type_dedupe_window(self):
        self._write({"code": "SNC-AL-CLOUD-1", "type": "CLOUD",
                     "ts": self._ts(5), "sent": True})
        self.assertTrue(self.alerting.recent_same_type("CLOUD", 10))
        self.assertFalse(self.alerting.recent_same_type("CLOUD", 1))
        self.assertFalse(self.alerting.recent_same_type("TUNNEL", 60))

    def test_deduped_entries_do_not_extend_window(self):
        self._write({"code": "SNC-AL-CLOUD-1", "type": "CLOUD",
                     "ts": self._ts(5), "sent": False, "deduped": True})
        self.assertFalse(self.alerting.recent_same_type("CLOUD", 60))

    def test_send_alert_dedupe_skips_telegram_but_logs(self):
        with mock.patch.object(self.alerting, "send_telegram",
                               return_value=True) as tg_mock:
            self.alerting.send_alert("CRITICAL", "CLOUD", "ครั้งแรก",
                                     dedupe_minutes=10)
            self.assertEqual(tg_mock.call_count, 1)
            self.alerting.send_alert("CRITICAL", "CLOUD", "ซ้ำใน 10 นาที",
                                     dedupe_minutes=10)
            self.assertEqual(tg_mock.call_count, 1)  # ไม่ส่งซ้ำ

        with open(self.tmp_ledger, encoding="utf-8") as f:
            entries = [json.loads(l) for l in f if l.strip()]
        self.assertEqual(len(entries), 2)
        self.assertFalse(entries[0]["deduped"])
        self.assertTrue(entries[1]["deduped"])

    def test_send_recovery_logs_ledger(self):
        with mock.patch.object(self.alerting, "send_telegram",
                               return_value=True) as tg_mock:
            code = self.alerting.send_recovery(
                "TUNNEL", recovered_from="SNC-AL-TUNNEL-1", downtime="~30 นาที")
        self.assertTrue(code.startswith("SNC-AL-RECOVERY-"))
        tg_mock.assert_called_once()
        with open(self.tmp_ledger, encoding="utf-8") as f:
            entries = [json.loads(l) for l in f if l.strip()]
        self.assertEqual(entries[0]["type"], "RECOVERY")
        self.assertEqual(entries[0]["recovered_type"], "TUNNEL")
        self.assertTrue(entries[0]["sent"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
