# api/storage.py
# ============================================================================
# SNC Event Store — abstraction เหนือ SQLite (Pi4) และ Firestore (Cloud Run)
# ----------------------------------------------------------------------------
# เลือก backend ผ่าน env SNC_DB_BACKEND:
#   sqlite    (default) — ใช้บน Pi4 (ไฟล์ nurse_call_events.db ในเครื่อง)
#   firestore (Cloud Run) — persistent: event ไม่หายตอน instance scale-to-zero
#
# ทั้งสอง class มี interface เดียวกัน:
#   save_event(event_data)                    เก็บ event ใหม่
#   get_recent_events(limit)                  ดึง event ล่าสุด (dashboard)
#   acknowledge_room(room_id, now_iso)        รับเรื่อง → (created_at, sla_metrics|None)
#   clear_room(room_id, now_iso)              เคลียร์สาย → (created_at, sla_metrics|None)
#   get_kpi_summary()                         สถิติ KPI
#   get_room_events(room_id, limit)           ประวัติห้อง (AI anomaly analysis)
#   reset()                                   ล้างข้อมูลทั้งหมด (admin)
#
# หมายเหตุ Firestore: ใช้ single-field index อัตโนมัติเท่านั้น (หลีกเลี่ยง
# composite index ที่ต้องสร้างเอง) — การ query ห้องใช้ room_state collection
# แทนการ filter ซ้อน order เพื่อไม่ต้องจัดการ index ด้วยมือ
# ============================================================================
import json
import logging
import os
import sqlite3
from collections import Counter
from datetime import datetime
from typing import Dict, List, Optional, Tuple

# override ได้ผ่าน env (ใช้ในการ test บนเครื่องอื่นโดยไม่แตะ production DB)
DB_PATH = os.getenv("SNC_SQLITE_PATH", "nurse_call_events.db")
FIRESTORE_EVENTS = "nurse_call_events"
FIRESTORE_ROOM_STATE = "room_state"


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
        conn.commit()
        conn.close()

    def save_event(self, event_data: dict):
        conn = self._connect()
        cursor = conn.cursor()
        ext = event_data.get("extension", {})
        room_id = ext["roomId"]
        event_type = ext.get("sourceEventType") or event_data["payload"][0]["contentString"]
        cursor.execute("""
            INSERT OR REPLACE INTO nurse_call_events (id, room_id, event_type, status, timestamp, fhir_payload)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            event_data["id"],
            room_id,
            event_type,
            event_data["status"],
            ext["timestamp"],
            json.dumps(event_data, ensure_ascii=False)
        ))
        conn.commit()
        conn.close()

    def get_recent_events(self, limit: int = 200) -> List[dict]:
        conn = self._connect()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, room_id, event_type, status, timestamp, acknowledged_at, resolved_at,
                   ack_time_seconds, resolution_time_seconds, sla_breached
            FROM nurse_call_events ORDER BY timestamp DESC LIMIT ?
        """, (limit,))
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
                "sla_breached": row[9]
            })
        return events

    def acknowledge_room(self, room_id: str, now_iso: str) -> Tuple[Optional[str], Optional[dict]]:
        conn = self._connect()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT timestamp FROM nurse_call_events
            WHERE room_id = ? AND status = 'active' ORDER BY timestamp DESC LIMIT 1
        """, (room_id,))
        row = cursor.fetchone()
        if not row:
            conn.close()
            return None, None
        created_at = row[0]
        sla_metrics = calculate_sla_metrics(created_at, acknowledged_at=now_iso)
        cursor.execute("""
            UPDATE nurse_call_events SET status = 'acknowledged', acknowledged_at = ?,
            ack_time_seconds = ?, sla_breached = ?
            WHERE room_id = ? AND status = 'active'
        """, (now_iso, sla_metrics["ack_time_seconds"], sla_metrics["sla_breached"], room_id))
        conn.commit()
        conn.close()
        return created_at, sla_metrics

    def clear_room(self, room_id: str, now_iso: str) -> Tuple[Optional[str], Optional[dict]]:
        conn = self._connect()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT timestamp FROM nurse_call_events
            WHERE room_id = ? AND status IN ('active', 'acknowledged')
            ORDER BY timestamp DESC LIMIT 1
        """, (room_id,))
        row = cursor.fetchone()
        if not row:
            conn.close()
            return None, None
        created_at = row[0]
        sla_metrics = calculate_sla_metrics(created_at, resolved_at=now_iso)
        cursor.execute("""
            UPDATE nurse_call_events SET status = 'resolved', resolved_at = ?,
            resolution_time_seconds = ?, sla_breached = ?
            WHERE room_id = ? AND status IN ('active', 'acknowledged')
        """, (now_iso, sla_metrics["resolution_time_seconds"], sla_metrics["sla_breached"], room_id))
        conn.commit()
        conn.close()
        return created_at, sla_metrics

    def get_kpi_summary(self) -> dict:
        conn = self._connect()
        cursor = conn.cursor()
        cursor.execute("SELECT AVG(ack_time_seconds) FROM nurse_call_events WHERE ack_time_seconds IS NOT NULL")
        avg_ack_time = cursor.fetchone()[0] or 0
        cursor.execute("SELECT AVG(resolution_time_seconds) FROM nurse_call_events WHERE resolution_time_seconds IS NOT NULL")
        avg_resolution_time = cursor.fetchone()[0] or 0
        cursor.execute("SELECT event_type, COUNT(*) FROM nurse_call_events GROUP BY event_type")
        events_by_type = dict(cursor.fetchall())
        cursor.execute("SELECT COUNT(*) FROM nurse_call_events")
        total_events = cursor.fetchone()[0] or 0
        cursor.execute("SELECT COUNT(*) FROM nurse_call_events WHERE sla_breached = 0 OR sla_breached IS NULL")
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
# Firestore backend (Cloud Run) — persistent, ไม่หายตอน scale-to-zero
# ═══════════════════════════════════════════════════════════════════════════
class FirestoreStore:
    backend_name = "firestore"

    def __init__(self):
        # lazy import — Pi4 (ไม่มีแพ็กเกจ) จะไม่แตะโค้ดนี้ถ้าไม่ตั้ง SNC_DB_BACKEND=firestore
        from google.cloud import firestore
        self._fs = firestore
        self._db = firestore.Client()
        self._events = self._db.collection(FIRESTORE_EVENTS)
        self._room_state = self._db.collection(FIRESTORE_ROOM_STATE)
        logging.info("FirestoreStore ready (collection=%s, room_state=%s)", FIRESTORE_EVENTS, FIRESTORE_ROOM_STATE)

    # ── helpers ────────────────────────────────────────────────────────────
    def _event_doc(self, event_data: dict) -> dict:
        ext = event_data.get("extension", {})
        room_id = ext["roomId"]
        event_type = ext.get("sourceEventType") or event_data["payload"][0]["contentString"]
        return {
            "id": event_data["id"],
            "room_id": room_id,
            "event_type": event_type,
            "status": event_data["status"],
            "timestamp": ext["timestamp"],
            "fhir_payload": json.dumps(event_data, ensure_ascii=False),
            "acknowledged_at": None,
            "resolved_at": None,
            "ack_time_seconds": None,
            "resolution_time_seconds": None,
            "sla_breached": False,
        }

    @staticmethod
    def _snap_to_event(snap) -> dict:
        d = snap.to_dict()
        return {
            "id": d.get("id"),
            "room_id": d.get("room_id"),
            "event_type": d.get("event_type"),
            "status": d.get("status"),
            "timestamp": d.get("timestamp"),
            "acknowledged_at": d.get("acknowledged_at"),
            "resolved_at": d.get("resolved_at"),
            "ack_time_seconds": d.get("ack_time_seconds"),
            "resolution_time_seconds": d.get("resolution_time_seconds"),
            "sla_breached": d.get("sla_breached", False),
        }

    # ── interface ──────────────────────────────────────────────────────────
    def save_event(self, event_data: dict):
        doc = self._event_doc(event_data)
        self._events.document(event_data["id"]).set(doc)
        # room_state: ชี้ event ล่าสุดของห้อง — ใช้สำหรับ ack/clear (ไม่ต้อง composite index)
        self._room_state.document(doc["room_id"]).set({
            "room_id": doc["room_id"],
            "status": doc["status"],
            "event_id": doc["id"],
            "timestamp": doc["timestamp"],
        })

    def get_recent_events(self, limit: int = 200) -> List[dict]:
        query = self._events.order_by("timestamp", direction=self._fs.Query.DESCENDING).limit(limit)
        return [self._snap_to_event(snap) for snap in query.stream()]

    def acknowledge_room(self, room_id: str, now_iso: str) -> Tuple[Optional[str], Optional[dict]]:
        ref = self._room_state.document(room_id)
        snap = ref.get()
        if not snap.exists or snap.get("status") != "active":
            return None, None
        created_at = snap.get("timestamp")
        event_id = snap.get("event_id")
        sla_metrics = calculate_sla_metrics(created_at, acknowledged_at=now_iso)
        self._events.document(event_id).update({
            "status": "acknowledged",
            "acknowledged_at": now_iso,
            "ack_time_seconds": sla_metrics["ack_time_seconds"],
            "sla_breached": sla_metrics["sla_breached"],
        })
        ref.update({"status": "acknowledged"})
        return created_at, sla_metrics

    def clear_room(self, room_id: str, now_iso: str) -> Tuple[Optional[str], Optional[dict]]:
        ref = self._room_state.document(room_id)
        snap = ref.get()
        if not snap.exists or snap.get("status") not in ("active", "acknowledged"):
            return None, None
        created_at = snap.get("timestamp")
        event_id = snap.get("event_id")
        sla_metrics = calculate_sla_metrics(created_at, resolved_at=now_iso)
        self._events.document(event_id).update({
            "status": "resolved",
            "resolved_at": now_iso,
            "resolution_time_seconds": sla_metrics["resolution_time_seconds"],
            "sla_breached": sla_metrics["sla_breached"],
        })
        ref.update({"status": "resolved"})
        return created_at, sla_metrics

    def get_kpi_summary(self) -> dict:
        total_events = 0
        sum_ack = 0.0
        cnt_ack = 0
        sum_res = 0.0
        cnt_res = 0
        compliant = 0
        by_type = Counter()
        for snap in self._events.stream():
            d = snap.to_dict()
            total_events += 1
            by_type[d.get("event_type", "UNKNOWN")] += 1
            a = d.get("ack_time_seconds")
            if a is not None:
                sum_ack += a
                cnt_ack += 1
            r = d.get("resolution_time_seconds")
            if r is not None:
                sum_res += r
                cnt_res += 1
            if not d.get("sla_breached"):
                compliant += 1
        avg_ack = round(sum_ack / cnt_ack, 2) if cnt_ack else 0
        avg_res = round(sum_res / cnt_res, 2) if cnt_res else 0
        rate = 100.0 if total_events == 0 else round((compliant / total_events) * 100, 2)
        return {
            "avg_ack_time_seconds": avg_ack,
            "avg_resolution_time_seconds": avg_res,
            "total_events": total_events,
            "events_by_type": dict(by_type),
            "sla_compliance_rate": rate,
        }

    def get_room_events(self, room_id: str, limit: int = 20) -> List[dict]:
        # ดึง 200 ล่าสุดแล้วกรองห้องใน Python — หลีกเลี่ยง composite index (room_id + timestamp)
        out = []
        query = self._events.order_by("timestamp", direction=self._fs.Query.DESCENDING).limit(200)
        for snap in query.stream():
            ev = self._snap_to_event(snap)
            if ev["room_id"] == room_id:
                out.append(ev)
                if len(out) >= limit:
                    break
        return out

    def reset(self):
        # Firestore ไม่มี delete-all — ลบทีละ batch (500 ต่อรอบ)
        for coll in (self._events, self._room_state):
            while True:
                snaps = list(coll.limit(500).stream())
                if not snaps:
                    break
                batch = self._db.batch()
                for snap in snaps:
                    batch.delete(snap.reference)
                batch.commit()


# ═══════════════════════════════════════════════════════════════════════════
# Factory — เลือก backend จาก env SNC_DB_BACKEND (sqlite | firestore)
# ═══════════════════════════════════════════════════════════════════════════
_store = None


def get_store():
    global _store
    if _store is None:
        backend = os.getenv("SNC_DB_BACKEND", "sqlite").strip().lower()
        if backend == "firestore":
            _store = FirestoreStore()
            logging.info("Event store: Firestore (persistent — Cloud Run)")
        else:
            _store = SqliteStore()
            logging.info(f"Event store: SQLite ({_store.db_path})")
    return _store
