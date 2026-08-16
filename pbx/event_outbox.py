# -*- coding: utf-8 -*-
"""
pbx/event_outbox.py — Durable Outbox สำหรับ event จาก PBX Listener

ปัญหาที่แก้ (ADR 0004):
- เดิม listener ส่ง HTTP POST ตรงไป backend → backend down = event หาย (data loss)
- เดิม backend สร้าง id ใหม่ทุก POST → ส่งซ้ำได้ event ซ้ำ (SLA นับผิด)

วิธีแก้: ก่อนส่งให้เก็บ event ลง SQLite เป็น pending (durable) แล้วค่อยส่งพร้อม retry
แบบ backoff; ส่งสำเร็จ (backend รับ) แล้ว mark sent. Idempotent ตาม id (INSERT OR IGNORE)
ดังนั้น retry ของ event เดียวกันจะไม่สร้าง duplicate

ตาราง: snc_event_outbox
  id           TEXT PK        — event id (idempotency key)
  room_id      TEXT
  event_type   TEXT
  payload      TEXT           — JSON ของ event เต็ม (dict)
  status       TEXT           — pending | sent
  attempts     INTEGER        — จำนวนครั้งที่พยายามส่ง
  last_error   TEXT           — ข้อผิดพลาดล่าสุด
  created_at   TEXT           — ISO
  sent_at      TEXT           — ISO (เมื่อส่งสำเร็จ)

ใช้ได้ทั้ง Pi (ไฟล์ db ในเครื่อง) — deterministic, ไม่มี external dependency
"""
import json
import logging
import os
import pathlib
import sqlite3
from datetime import datetime
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# ไฟล์ outbox อยู่ข้าง listener (pbx/) — override ได้ผ่าน env (ใช้ใน test)
OUTBOX_PATH = os.getenv("SNC_OUTBOX_PATH", str(pathlib.Path(__file__).resolve().parent / "snc_event_outbox.db"))

# retry: เจอ 200 (หรือ duplicate) = สำเร็จ ถ้าไม่ใช่ = ลองใหม่
RETRYABLE_STATUS = {200}


class EventOutbox:
    def __init__(self, db_path: str = OUTBOX_PATH):
        self.db_path = db_path
        self._init_db()

    def _connect(self):
        return sqlite3.connect(self.db_path, timeout=15.0)

    def _init_db(self):
        conn = self._connect()
        cur = conn.cursor()
        cur.execute("PRAGMA journal_mode=WAL;")
        cur.execute("PRAGMA synchronous=NORMAL;")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS snc_event_outbox (
                id         TEXT PRIMARY KEY,
                room_id    TEXT NOT NULL,
                event_type TEXT NOT NULL,
                payload    TEXT NOT NULL,
                status     TEXT NOT NULL DEFAULT 'pending',
                attempts   INTEGER NOT NULL DEFAULT 0,
                last_error TEXT,
                created_at TEXT NOT NULL,
                sent_at    TEXT
            )
        """)
        conn.commit()
        conn.close()
        logger.info("Outbox ready: %s", self.db_path)

    def enqueue(self, event_data: dict) -> None:
        """เก็บ event ลง outbox เป็น pending — idempotent ตาม id (INSERT OR IGNORE)"""
        ext = event_data.get("extension", {})
        room_id = ext.get("roomId", "")
        event_type = event_data.get("payload", [{}])[0].get("contentString", "")
        conn = self._connect()
        cur = conn.cursor()
        cur.execute("""
            INSERT OR IGNORE INTO snc_event_outbox
                (id, room_id, event_type, payload, status, created_at)
            VALUES (?, ?, ?, ?, 'pending', ?)
        """, (
            event_data.get("id", ""),
            room_id,
            event_type,
            json.dumps(event_data, ensure_ascii=False),
            datetime.now().isoformat(),
        ))
        conn.commit()
        conn.close()

    def pending(self, limit: int = 200) -> List[Dict]:
        """ดึง event ที่ยังไม่ส่ง (status != sent) เรียงตามเวลา เพื่อ retry"""
        conn = self._connect()
        cur = conn.cursor()
        cur.execute("""
            SELECT id, room_id, event_type, payload, attempts, last_error
            FROM snc_event_outbox WHERE status != 'sent'
            ORDER BY created_at ASC LIMIT ?
        """, (limit,))
        rows = cur.fetchall()
        conn.close()
        out = []
        for row in rows:
            try:
                payload = json.loads(row[3])
            except Exception:
                payload = {}
            out.append({
                "id": row[0],
                "room_id": row[1],
                "event_type": row[2],
                "payload": payload,
                "attempts": row[4],
                "last_error": row[5],
            })
        return out

    def mark_sent(self, event_id: str) -> None:
        conn = self._connect()
        cur = conn.cursor()
        cur.execute("""
            UPDATE snc_event_outbox
            SET status='sent', sent_at=?, attempts=attempts+1, last_error=NULL
            WHERE id=?
        """, (datetime.now().isoformat(), event_id))
        conn.commit()
        conn.close()

    def mark_failed(self, event_id: str, error: str) -> None:
        conn = self._connect()
        cur = conn.cursor()
        cur.execute("""
            UPDATE snc_event_outbox
            SET attempts=attempts+1, last_error=?
            WHERE id=?
        """, (error[:500], event_id))
        conn.commit()
        conn.close()

    def count_pending(self) -> int:
        conn = self._connect()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM snc_event_outbox WHERE status != 'sent'")
        n = cur.fetchone()[0]
        conn.close()
        return n