# api/storage.py
# ============================================================================
# SNC Event Store — SQLite backend (Pi4 / local)
# ----------------------------------------------------------------------------
# interface ของ SqliteStore:
#   save_event(event_data)                    เก็บ event ใหม่
#   get_recent_events(limit)                  ดึง event ล่าสุด (dashboard)
#   acknowledge_room(room_id, now_iso)        รับเรื่อง → (created_at, sla_metrics|None)
#   clear_room(room_id, now_iso)              เคลียร์สาย → (created_at, sla_metrics|None)
#   get_kpi_summary()                         สถิติ KPI
#   get_room_events(room_id, limit)           ประวัติห้อง (AI anomaly analysis)
#   reset()                                   ล้างข้อมูลทั้งหมด (admin)
# ============================================================================
import json
import logging
import os
import sqlite3
from datetime import datetime, timedelta
from typing import List, Optional, Tuple

# override ได้ผ่าน env (ใช้ในการ test บนเครื่องอื่นโดยไม่แตะ production DB)
DB_PATH = os.getenv("SNC_SQLITE_PATH", "nurse_call_events.db")


def calculate_sla_metrics(created_at: str, acknowledged_at: str = None, resolved_at: str = None):
    """Calculate SLA metrics for nurse call events."""
    created_dt = datetime.fromisoformat(created_at)
    metrics = {
        "ack_time_seconds": None,
        "resolution_time_seconds": None,
        "sla_breached": False
    }

    if acknowledged_at:
        ack_dt = datetime.fromisoformat(acknowledged_at)
        ack_diff = (ack_dt - created_dt).total_seconds()
        metrics["ack_time_seconds"] = int(ack_diff)
        # SLA breach if ack time > 30 seconds
        if ack_diff > 30:
            metrics["sla_breached"] = True

    if resolved_at:
        res_dt = datetime.fromisoformat(resolved_at)
        res_diff = (res_dt - created_dt).total_seconds()
        metrics["resolution_time_seconds"] = int(res_diff)
        # SLA breach if resolution time > 180 seconds (3 minutes)
        if res_diff > 180:
            metrics["sla_breached"] = True

    return metrics


# ═══════════════════════════════════════════════════════════════════════════
# SQLite backend (Pi4 / local) — logic เดิมจาก server.py
# ═══════════════════════════════════════════════════════════════════════════
class SqliteStore:
    backend_name = "sqlite"

    def __init__(self):
        self.db_path = DB_PATH
        self._init_db()

    def _connect(self):
        return sqlite3.connect(self.db_path, timeout=15.0)

    def _init_db(self):
        conn = self._connect()
        cursor = conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL;")
        cursor.execute("PRAGMA synchronous=NORMAL;")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS nurse_call_events (
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
                sla_breached BOOLEAN DEFAULT FALSE
            )
        """)

        # One-time migration: DB เก่าที่สร้างก่อน schema ใหม่จะไม่มีคอลัมน์ SLA
        def ensure_column(table: str, column: str, ddl: str):
            cursor.execute(f"PRAGMA table_info({table})")
            cols = [row[1] for row in cursor.fetchall()]
            if column not in cols:
                cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}")
                logging.info(f"Migrated: added {table}.{column}")

        ensure_column("nurse_call_events", "ack_time_seconds", "INTEGER")
        ensure_column("nurse_call_events", "resolution_time_seconds", "INTEGER")
        ensure_column("nurse_call_events", "sla_breached", "BOOLEAN DEFAULT FALSE")
        ensure_column("nurse_call_events", "source", "TEXT DEFAULT 'real'")
        conn.commit()
        conn.close()

    def save_event(self, event_data: dict):
        conn = self._connect()
        cursor = conn.cursor()
        ext = event_data.get("extension", {})
        room_id = ext["roomId"]
        event_type = ext.get("sourceEventType") or event_data["payload"][0]["contentString"]
        source = ext.get("source", "real")
        # INSERT OR IGNORE: idempotent ตาม id — ถ้า event id มีอยู่แล้ว (ส่งซ้ำ) ไม่ทับ
        # (เดิมใช้ REPLACE ซึ่งจะทับทำลาย ack/clear — เปลี่ยนเพื่อความถูกต้องของ SLA)
        cursor.execute("""
            INSERT OR IGNORE INTO nurse_call_events (id, room_id, event_type, status, timestamp, fhir_payload, source)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            event_data["id"],
            room_id,
            event_type,
            event_data["status"],
            ext["timestamp"],
            json.dumps(event_data, ensure_ascii=False),
            source
        ))
        conn.commit()
        conn.close()

    def event_exists(self, event_id: str) -> bool:
        conn = self._connect()
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM nurse_call_events WHERE id = ?", (event_id,))
        row = cursor.fetchone()
        conn.close()
        return row is not None

    def get_recent_events(self, limit: int = 200, source: str = None) -> List[dict]:
        conn = self._connect()
        cursor = conn.cursor()
        where, params = "", []
        if source:
            where = "WHERE source = ?"
            params.append(source)
        params.append(limit)
        cursor.execute(f"""
            SELECT id, room_id, event_type, status, timestamp, acknowledged_at, resolved_at,
                   ack_time_seconds, resolution_time_seconds, sla_breached, source
            FROM nurse_call_events {where} ORDER BY timestamp DESC LIMIT ?
        """, params)
        rows = cursor.fetchall()
        conn.close()
        return self._rows_to_events(rows)

    @staticmethod
    def _rows_to_events(rows) -> List[dict]:
        events = []
        for row in rows:
            events.append({
                "id": row[0],
                "room_id": row[1],
                "event_type": row[2],
                "status": row[3],
                "timestamp": row[4],
                "acknowledged_at": row[5],
                "resolved_at": row[6],
                "ack_time_seconds": row[7],
                "resolution_time_seconds": row[8],
                "sla_breached": row[9],
                "source": row[10] if len(row) > 10 else "real"
            })
        return events

    def acknowledge_room(self, room_id: str, now_iso: str) -> Tuple[Optional[str], Optional[dict], Optional[str]]:
        conn = self._connect()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT timestamp, source FROM nurse_call_events
            WHERE room_id = ? AND status = 'active' ORDER BY timestamp DESC LIMIT 1
        """, (room_id,))
        row = cursor.fetchone()
        if not row:
            conn.close()
            return None, None, None
        created_at = row[0]
        source = row[1] if len(row) > 1 and row[1] else "real"
        sla_metrics = calculate_sla_metrics(created_at, acknowledged_at=now_iso)
        cursor.execute("""
            UPDATE nurse_call_events SET status = 'acknowledged', acknowledged_at = ?,
            ack_time_seconds = ?, sla_breached = ?
            WHERE room_id = ? AND status = 'active'
        """, (now_iso, sla_metrics["ack_time_seconds"], sla_metrics["sla_breached"], room_id))
        conn.commit()
        conn.close()
        return created_at, sla_metrics, source

    def clear_room(self, room_id: str, now_iso: str) -> Tuple[Optional[str], Optional[dict], Optional[str]]:
        conn = self._connect()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT timestamp, source FROM nurse_call_events
            WHERE room_id = ? AND status IN ('active', 'acknowledged')
            ORDER BY timestamp DESC LIMIT 1
        """, (room_id,))
        row = cursor.fetchone()
        if not row:
            conn.close()
            return None, None, None
        created_at = row[0]
        source = row[1] if len(row) > 1 and row[1] else "real"
        sla_metrics = calculate_sla_metrics(created_at, resolved_at=now_iso)
        cursor.execute("""
            UPDATE nurse_call_events SET status = 'resolved', resolved_at = ?,
            resolution_time_seconds = ?, sla_breached = ?
            WHERE room_id = ? AND status IN ('active', 'acknowledged')
        """, (now_iso, sla_metrics["resolution_time_seconds"], sla_metrics["sla_breached"], room_id))
        conn.commit()
        conn.close()
        return created_at, sla_metrics, source

    def get_kpi_summary(self, source: str = None) -> dict:
        conn = self._connect()
        cursor = conn.cursor()
        and_src, src_params = ("AND source = ?", [source]) if source else ("", [])
        cursor.execute(f"SELECT AVG(ack_time_seconds) FROM nurse_call_events WHERE ack_time_seconds IS NOT NULL {and_src}", src_params)
        avg_ack_time = cursor.fetchone()[0] or 0
        cursor.execute(f"SELECT AVG(resolution_time_seconds) FROM nurse_call_events WHERE resolution_time_seconds IS NOT NULL {and_src}", src_params)
        avg_resolution_time = cursor.fetchone()[0] or 0
        cursor.execute(f"SELECT event_type, COUNT(*) FROM nurse_call_events WHERE 1=1 {and_src} GROUP BY event_type", src_params)
        events_by_type = dict(cursor.fetchall())
        cursor.execute(f"SELECT COUNT(*) FROM nurse_call_events WHERE 1=1 {and_src}", src_params)
        total_events = cursor.fetchone()[0] or 0
        cursor.execute(f"SELECT COUNT(*) FROM nurse_call_events WHERE (sla_breached = 0 OR sla_breached IS NULL) {and_src}", src_params)
        compliant_events = cursor.fetchone()[0]
        conn.close()
        if total_events == 0:
            sla_compliance_rate = 100.0
        else:
            sla_compliance_rate = (compliant_events / total_events) * 100
        return {
            "avg_ack_time_seconds": round(avg_ack_time, 2),
            "avg_resolution_time_seconds": round(avg_resolution_time, 2),
            "total_events": total_events,
            "events_by_type": events_by_type,
            "sla_compliance_rate": round(sla_compliance_rate, 2)
        }

    def get_trend(self, source: str = "real", bucket: str = "day") -> List[dict]:
        """ค่าเฉลี่ย SLA แบ่งตามช่วงเวลา — bucket: day (24 ชม. แบ่งชั่วโมง) | month (30 วัน แบ่งวัน) | year (12 เดือน แบ่งเดือน)"""
        if bucket == "day":
            cutoff = (datetime.now() - timedelta(hours=24)).isoformat()
            group_expr = "substr(timestamp, 1, 13)"
        elif bucket == "month":
            cutoff = (datetime.now() - timedelta(days=30)).isoformat()
            group_expr = "substr(timestamp, 1, 10)"
        else:
            cutoff = (datetime.now() - timedelta(days=365)).isoformat()
            group_expr = "substr(timestamp, 1, 7)"
        where, params = "WHERE timestamp >= ?", [cutoff]
        if source:
            where += " AND source = ?"
            params.append(source)
        conn = self._connect()
        cursor = conn.cursor()
        cursor.execute(f"""
            SELECT {group_expr} AS bucket, COUNT(*),
                   AVG(ack_time_seconds), AVG(resolution_time_seconds),
                   SUM(CASE WHEN sla_breached THEN 1 ELSE 0 END)
            FROM nurse_call_events
            {where}
            GROUP BY bucket ORDER BY bucket
        """, params)
        rows = cursor.fetchall()
        conn.close()
        return [
            {
                "bucket": r[0],
                "total": r[1],
                "avg_ack": round(r[2], 1) if r[2] is not None else None,
                "avg_res": round(r[3], 1) if r[3] is not None else None,
                "breached": r[4] or 0
            }
            for r in rows
        ]

    def get_room_events(self, room_id: str, limit: int = 20) -> List[dict]:
        conn = self._connect()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, room_id, event_type, status, timestamp, acknowledged_at, resolved_at,
                   ack_time_seconds, resolution_time_seconds, sla_breached
            FROM nurse_call_events WHERE room_id = ? ORDER BY timestamp DESC LIMIT ?
        """, (room_id, limit))
        rows = cursor.fetchall()
        conn.close()
        return self._rows_to_events(rows)

    def reset(self):
        conn = self._connect()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM nurse_call_events")
        conn.commit()
        conn.close()


# ═══════════════════════════════════════════════════════════════════════════
# Factory — returns SqliteStore
# ═══════════════════════════════════════════════════════════════════════════
_store = None


def get_store():
    global _store
    if _store is None:
        _store = SqliteStore()
        logging.info(f"Event store: SQLite ({_store.db_path})")
    return _store
