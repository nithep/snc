# -*- coding: utf-8 -*-
"""tests/test_export_traces.py — ทดสอบ ops/export_traces.py (ADR 0013 · Phase 3)"""
import json
import pathlib
import sqlite3
import sys
from datetime import datetime, timezone

import pytest

REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from ops.export_traces import build_record, export  # noqa: E402

# ตาม schema จริงของ api/storage.py
SCHEMA = """
CREATE TABLE nurse_call_events (
    id TEXT PRIMARY KEY,
    room_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    status TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    fhir_payload TEXT NOT NULL,
    acknowledged_at TEXT,
    resolved_at TEXT,
    ack_time_seconds INTEGER,
    resolution_time_seconds INTEGER,
    sla_breached BOOLEAN DEFAULT FALSE,
    source TEXT DEFAULT 'real'
)
"""


def make_db(tmp_path: pathlib.Path, rows) -> pathlib.Path:
    tmp_path.mkdir(parents=True, exist_ok=True)
    db = tmp_path / "nurse_call_events.db"
    conn = sqlite3.connect(db)
    conn.execute(SCHEMA)
    for r in rows:
        conn.execute(
            """INSERT INTO nurse_call_events
               (id, room_id, event_type, status, timestamp, fhir_payload,
                acknowledged_at, resolved_at, ack_time_seconds,
                resolution_time_seconds, sla_breached, source)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            r,
        )
    conn.commit()
    conn.close()
    return db


ROW_OK = (
    "e1", "401", "CALL_BEDSIDE", "resolved", "2026-09-03T08:15:03+00:00",
    '{"resourceType":"Encounter","subject":{"display":"ผู้ป่วย"},"meta":{}}',
    "2026-09-03T08:15:15+00:00", "2026-09-03T08:16:31+00:00", 12, 88, False, "real",
)

ROW_BREACH = (
    "e2", "400", "CALL_BATHROOM_EMERGENCY", "acknowledged", "2026-09-03T10:22:48+00:00",
    '{"resourceType":"Encounter","subject":{"display":"ผู้ป่วย"},"meta":{}}',
    "2026-09-03T10:23:40+00:00", None, 52, None, True, "synthetic",
)


def test_export_whitelist_only_no_phi(tmp_path):
    """export แล้วต้องมีเฉพาะ field whitelist — ห้ามมี fhir_payload/ข้อมูลผู้ป่วย"""
    db = make_db(tmp_path, [ROW_OK, ROW_BREACH])
    records, out_path = export(db, since=None, stdout=True,
                               out_dir=tmp_path / "out")
    assert out_path is None  # stdout mode ไม่เขียนไฟล์
    assert len(records) == 2

    rec = records[0]
    # ห้ามมี field ต้องห้าม
    assert "fhir_payload" not in rec
    assert "acknowledged_at" not in rec
    assert "resolved_at" not in rec
    # มี field whitelist ครบ
    assert set(rec.keys()) == {
        "ts", "event_type", "room_id", "status",
        "ack_seconds", "resolution_seconds", "sla_breached", "source",
    }
    # room_id ปัดเป็น 4 หลัก
    assert rec["room_id"] == "0401"
    assert records[1]["room_id"] == "0400"
    # ข้อมูลไทย/UTF-8 (json ผ่าน ensure_ascii=False)
    line = json.dumps(rec, ensure_ascii=False)
    assert line.count("\u0e40") >= 0  # sanity: ไม่ crash กับ Unicode
    assert rec["source"] == "real"
    # sla_breached เป็น JSON true/false (ไม่ใช่ 0/1)
    assert records[1]["sla_breached"] is True
    assert rec["sla_breached"] is False


def test_export_naive_timestamp_assumed_utc(tmp_path):
    """timestamp แบบไม่มี timezone (db จริง) ต้องไม่ crash เมื่อ filter ตามเวลา"""
    naive = (
        "e3", "405", "CALL_BEDSIDE", "resolved", "2026-09-03T08:15:03.123456",
        "{}", None, None, 10, 60, False, "real",
    )
    db = make_db(tmp_path, [naive])
    since = datetime(2026, 9, 1, tzinfo=timezone.utc)
    records, _ = export(db, since=since, stdout=True, out_dir=tmp_path / "out")
    assert len(records) == 1
    assert records[0]["ts"] == "2026-09-03T08:15:03.123456"


def test_export_writes_file_named_by_date(tmp_path):
    db = make_db(tmp_path, [ROW_OK])
    records, out_path = export(db, since=None, stdout=False,
                               out_dir=tmp_path / "raw")
    assert out_path is not None
    assert out_path.parent == tmp_path / "raw"
    name = out_path.name
    assert name.startswith("traces-") and name.endswith(".jsonl")
    lines = out_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    parsed = json.loads(lines[0])
    assert parsed["event_type"] == "CALL_BEDSIDE"
    assert parsed["ack_seconds"] == 12


def test_export_days_filter_excludes_old(tmp_path):
    old = (
        "e0", "100", "CALL_BEDSIDE", "resolved", "2026-08-01T00:00:00+00:00",
        "{}", None, None, 10, 60, False, "real",
    )
    db = make_db(tmp_path, [old, ROW_OK])
    since = datetime(2026, 9, 1, tzinfo=timezone.utc)
    records, _ = export(db, since=since, stdout=True, out_dir=tmp_path / "out")
    assert len(records) == 1
    assert records[0]["ts"] == ROW_OK[4]


def test_export_empty_db_returns_no_records(tmp_path):
    db = make_db(tmp_path, [])
    records, out_path = export(db, since=None, stdout=False,
                               out_dir=tmp_path / "raw")
    assert records == []
    assert out_path is None  # ไม่สร้างไฟล์เปล่า


def test_export_main_exit_codes(tmp_path, capsys):
    from ops.export_traces import main
    # ใช้ subdir คนละตัว เพื่อให้ db แต่ละตัวเป็นไฟล์คนละไฟล์
    db = make_db(tmp_path / "empty", [])
    # empty → exit 2
    assert main(["--db", str(db), "--stdout"]) == 2
    db2 = make_db(tmp_path / "full", [ROW_OK])
    # มีข้อมูล → exit 0
    assert main(["--db", str(db2), "--stdout"]) == 0
    # db ไม่มี → exit 1
    assert main(["--db", str(tmp_path / "nope.db"), "--stdout"]) == 1