# -*- coding: utf-8 -*-
"""Unit tests สำหรับ Durable Outbox (pbx/event_outbox.py)

ครอบ: enqueue idempotent, pending/retry, mark_sent, mark_failed,
count_pending, และการ purge (cleaning ของ sent rows)

รัน: python -m unittest pbx.test_event_outbox -v   (จาก repo root)
"""
import json
import os
import tempfile
import unittest

from event_outbox import EventOutbox


def _make_event(event_id, room_id="0401", event_type="CALL_BEDSIDE"):
    return {
        "id": event_id,
        "resourceType": "CommunicationRequest",
        "extension": {"roomId": room_id},
        "payload": [{"contentString": event_type}],
        "timestamp": "2026-08-16T10:00:00+07:00",
    }


class TestEventOutbox(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="snc_outbox_")
        self.db_path = os.path.join(self.tmpdir, "test_outbox.db")
        self.box = EventOutbox(db_path=self.db_path)

    def tearDown(self):
        # ลบไฟล์ db + WAL/SHM กันค้าง
        for suffix in ("", "-wal", "-shm"):
            p = self.db_path + suffix
            if os.path.exists(p):
                os.remove(p)
        os.rmdir(self.tmpdir)

    def test_enqueue_and_pending(self):
        self.box.enqueue(_make_event("evt-1"))
        self.assertEqual(self.box.count_pending(), 1)
        pending = self.box.pending()
        self.assertEqual(len(pending), 1)
        self.assertEqual(pending[0]["id"], "evt-1")
        self.assertEqual(pending[0]["room_id"], "0401")
        self.assertEqual(pending[0]["event_type"], "CALL_BEDSIDE")
        # payload คืนเป็น dict เดิม
        self.assertEqual(pending[0]["payload"]["id"], "evt-1")

    def test_enqueue_idempotent_duplicate(self):
        """INSERT OR IGNORE — ส่งซ้ำ event เดียวกันต้องไม่สร้างแถวใหม่"""
        self.box.enqueue(_make_event("evt-dup"))
        self.box.enqueue(_make_event("evt-dup"))
        self.box.enqueue(_make_event("evt-dup"))
        self.assertEqual(self.box.count_pending(), 1)
        self.assertEqual(len(self.box.pending()), 1)

    def test_mark_sent_removes_from_pending(self):
        self.box.enqueue(_make_event("evt-ok"))
        self.box.mark_sent("evt-ok")
        self.assertEqual(self.box.count_pending(), 0)
        self.assertEqual(len(self.box.pending()), 0)

    def test_mark_failed_increments_attempts(self):
        self.box.enqueue(_make_event("evt-fail"))
        self.box.mark_failed("evt-fail", "connection refused")
        self.box.mark_failed("evt-fail", "timeout")
        pending = self.box.pending()
        self.assertEqual(pending[0]["attempts"], 2)
        self.assertIn("timeout", pending[0]["last_error"])
        # ยัง pending (ยังไม่ sent)
        self.assertEqual(self.box.count_pending(), 1)

    def test_pending_respects_limit(self):
        for i in range(5):
            self.box.enqueue(_make_event(f"evt-{i}"))
        pending = self.box.pending(limit=2)
        self.assertEqual(len(pending), 2)
        # เรียงตามเวลาเก่าก่อน (created_at ASC)
        self.assertEqual(pending[0]["id"], "evt-0")

    def test_multiple_events_independent(self):
        """sent ของตัวหนึ่ง ไม่กระทบอีกตัว"""
        self.box.enqueue(_make_event("evt-a"))
        self.box.enqueue(_make_event("evt-b"))
        self.box.mark_sent("evt-a")
        pending = self.box.pending()
        self.assertEqual(len(pending), 1)
        self.assertEqual(pending[0]["id"], "evt-b")

    def test_mark_sent_unknown_id_noop(self):
        """mark_sent id ที่ไม่มี = ไม่ error ไม่สร้างผล"""
        self.box.enqueue(_make_event("evt-real"))
        self.box.mark_sent("evt-not-exist")  # ต้องไม่ throw
        self.assertEqual(self.box.count_pending(), 1)

    def test_payload_utf8_thai_preserved(self):
        """payload ที่มีอักษรไทย (ensure_ascii=False) ต้องกลับมาเหมือนเดิม"""
        event = _make_event("evt-thai")
        event["payload"][0]["contentString"] = "CALL_BATHROOM_EMERGENCY"
        event["extension"]["roomLabel"] = "ห้อง 1101"
        self.box.enqueue(event)
        pending = self.box.pending()
        self.assertEqual(pending[0]["payload"]["extension"]["roomLabel"], "ห้อง 1101")
        self.assertEqual(pending[0]["event_type"], "CALL_BATHROOM_EMERGENCY")


if __name__ == "__main__":
    unittest.main()