#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ops/export_traces.py — Export Non-PHI Traces (ADR 0013 · Phase 3)

อ่าน nurse_call_events.db (SQLite WAL ของ backend) แล้ว export เฉพาะ field ที่เป็น
**Non-PHI** ลง `ops/raw/traces-YYYYMMDD.jsonl` เป็นวัตถุดิบให้ Fabric Patterns
(`snc-trace-summary` → `snc-wiki-distill` → `snc-playbook-draft`) ใน Nightly Loop

หลัก Non-PHI (บังคับ ตาม ADR 0013):
- **Whitelist field** เท่านั้น: ts, event_type, room_id, status, ack_seconds,
  resolution_seconds, sla_breached, source
- **ไม่ export `fhir_payload` ดิบ** (อาจมีข้อมูลผู้ป่วย/PDPA-sensitive) — ตัดทิ้งเสมอ
- room_id ปัดเป็น 4 หลัก (เช่น 400 → "0400") ตามมาตรฐาน SNC

Usage:
  python ops/export_traces.py                    # ข้อมูลทั้งหมด (หรือ --days/--since)
  python ops/export_traces.py --days 1           # เฉพาะ 1 วันที่ผ่านมา (ใช้ใน nightly)
  python ops/export_traces.py --since 2026-09-01 # ตั้งแต่วันที่กำหนด (UTC)
  python ops/export_traces.py --stdout           # พิมพ์ไป stdout แทนการเขียนไฟล์
  python ops/export_traces.py --db path/to.db    # ชี้ db อื่น (override)

Exit codes:
  0 = สำเร็จ (มีข้อมูล) · 1 = error · 2 = ไม่มีข้อมูลในช่วง (nightly loop จะข้าม)
"""
import argparse
import json
import pathlib
import sqlite3
import sys
from datetime import datetime, timedelta, timezone

# repo root = parent ของ ops/ (5-Core layout)
REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
DEFAULT_DB = REPO_ROOT / "api" / "nurse_call_events.db"
DEFAULT_OUT_DIR = REPO_ROOT / "ops" / "raw"

# Whitelist field ที่ Non-PHI เท่านั้น — ถ้าจะเพิ่ม field ต้องผ่าน review (ADR 0013)
FIELD_MAP = {
    "timestamp": "ts",
    "event_type": "event_type",
    "room_id": "room_id",
    "status": "status",
    "ack_time_seconds": "ack_seconds",
    "resolution_time_seconds": "resolution_seconds",
    "sla_breached": "sla_breached",
    "source": "source",
}

SELECT_SQL = f"""
    SELECT {", ".join(FIELD_MAP.keys())}
    FROM nurse_call_events
    ORDER BY timestamp ASC
"""


def parse_ts(value: str) -> datetime:
    """แปลง timestamp ISO (รองรับ +00:00 / Z / ไม่มี timezone) เป็น datetime aware (UTC)
    db จริงอาจเก็บ timestamp แบบ naive — ถือว่าเป็น UTC เสมอ (กัน TypeError เปรียบเทียบ)"""
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def build_record(row: tuple) -> dict:
    """สร้าง record Non-PHI จากแถว db — ใช้ FIELD_MAP (whitelist) เท่านั้น"""
    rec = {}
    for idx, (src_col, out_col) in enumerate(FIELD_MAP.items()):
        val = row[idx]
        if src_col == "room_id" and val is not None:
            val = str(val).zfill(4)  # ปัดเป็น 4 หลักตามมาตรฐาน SNC
        elif src_col == "sla_breached":
            val = bool(val)  # SQLite BOOLEAN = 0/1 → JSON true/false ตาม spec pattern
        rec[out_col] = val
    return rec


def compute_stats(records: list) -> dict:
    """คำนวณสถิติแบบ deterministic จาก records — ใช้เป็นหลักอ้างอิงให้ LLM
    (Phase 5 พบว่า LLM นับ traces ดิบผิดพลาด — ตัวเลขต้องมาจากเครื่อง)"""
    from collections import Counter

    by_type = Counter(r.get("event_type") for r in records)
    breaches = [r for r in records if r.get("sla_breached")]
    breach_by_room = Counter(r.get("room_id") for r in breaches)

    def pct(seq, p):
        if not seq:
            return None
        s = sorted(seq)
        return s[min(len(s) - 1, int(len(s) * p))]

    acks = [r["ack_seconds"] for r in records if r.get("ack_seconds") is not None]
    res = [r["resolution_seconds"] for r in records if r.get("resolution_seconds") is not None]

    period = None
    if records:
        period = {"first": records[0]["ts"], "last": records[-1]["ts"]}

    return {
        "period": period,
        "total_events": len(records),
        "events_by_type": dict(by_type),
        "sla_breach_count": len(breaches),
        "breach_by_room_top": breach_by_room.most_common(5),
        "ack_seconds": {"mean": round(sum(acks) / len(acks), 1) if acks else None,
                        "p95": pct(acks, 0.95), "max": max(acks) if acks else None},
        "resolution_seconds": {"mean": round(sum(res) / len(res), 1) if res else None,
                               "p95": pct(res, 0.95), "max": max(res) if res else None},
    }


def export(db_path: pathlib.Path, since: datetime | None,
           stdout: bool, out_dir: pathlib.Path, quiet: bool = False):
    """อ่าน db แล้ว return (records, out_path | None)"""
    # อ่านแบบ read-only (ไม่ล็อก WAL ของ backend ที่รันอยู่)
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, timeout=15.0)
    try:
        rows = conn.execute(SELECT_SQL).fetchall()
    finally:
        conn.close()

    records = []
    skipped = 0
    for row in rows:
        try:
            ts = parse_ts(row[0]) if row[0] else None
        except (TypeError, ValueError):
            skipped += 1
            continue
        if since is not None and (ts is None or ts < since):
            continue
        records.append(build_record(row))

    if not records:
        if not quiet:
            print(f"[export_traces] ไม่มีข้อมูลในช่วง (db={db_path})", file=sys.stderr)
        return records, None

    if stdout:
        for rec in records:
            print(json.dumps(rec, ensure_ascii=False))
        return records, None

    out_dir.mkdir(parents=True, exist_ok=True)
    date_stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
    out_path = out_dir / f"traces-{date_stamp}.jsonl"
    with open(out_path, "w", encoding="utf-8") as fh:
        for rec in records:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")

    if not quiet:
        n = len(records)
        first = records[0]["ts"]
        last = records[-1]["ts"]
        print(f"[export_traces] export {n} records ({first} -> {last}) -> {out_path}")
    return records, out_path


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Export Non-PHI traces (ADR 0013)")
    parser.add_argument("--db", default=str(DEFAULT_DB), help="path ไป nurse_call_events.db")
    parser.add_argument("--days", type=int, default=None,
                        help="export ข้อมูล N วันที่ผ่านมา (นับจาก now UTC)")
    parser.add_argument("--since", default=None,
                        help="export ข้อมูลตั้งแต่วันที่ ISO (เช่น 2026-09-01)")
    parser.add_argument("--stdout", action="store_true", help="พิมพ์ไป stdout แทนการเขียนไฟล์")
    parser.add_argument("--stats", action="store_true",
                        help="พิมพ์สถิติ deterministic (คำนวณโดยเครื่อง) แทน traces")
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR), help="โฟลเดอร์ปลายทาง")
    args = parser.parse_args(argv)

    db_path = pathlib.Path(args.db)
    if not db_path.exists():
        print(f"[export_traces] ERROR: ไม่พบ db: {db_path}", file=sys.stderr)
        return 1

    since = None
    if args.days is not None:
        since = datetime.now(timezone.utc) - timedelta(days=args.days)
    elif args.since:
        since = parse_ts(args.since)

    if args.stats:
        # พิมพ์สถิติ deterministic เป็น JSON (LLM ห้ามนับเอง — ใช้ค่านี้เป็นหลัก)
        records, _ = export(db_path, since, stdout=False,
                            out_dir=pathlib.Path(args.out_dir), quiet=True)
        if not records:
            return 2
        print(json.dumps(compute_stats(records), ensure_ascii=False, indent=2))
        return 0

    records, out_path = export(db_path, since, args.stdout, pathlib.Path(args.out_dir))
    if not records:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())