import asyncio
import os
import pathlib
import sqlite3
import json
import logging
import time
from collections import defaultdict
from datetime import datetime
from typing import List
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from pydantic import BaseModel

# โหลด .env เอง (ไม่มี python-dotenv) — ต้องรันก่อน import services ที่อ่าน GEMINI_API_KEY
_env_file = pathlib.Path(__file__).resolve().parent / ".env"
if _env_file.exists():
    for _line in _env_file.read_text(encoding="utf-8").splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _v = _line.split("=", 1)
            os.environ.setdefault(_k.strip(), _v.strip())

from services.gemini_direct_service import GeminiDirectService

# Setup Logging
logging.basicConfig(level=logging.INFO)

gemini_service = GeminiDirectService()
app = FastAPI(title="Smart Nurse Call (SNC) Backend API", version="1.0.0")

# API Auth: กัน POST /api/events/trigger จากใครก็ได้ใน LAN (เปิดใช้เมื่อตั้ง SNC_API_KEY ใน .env)
SNC_API_KEY = os.getenv("SNC_API_KEY", "")

# Rate limiting: กัน poll ถี่เกิน / brute-force key — ต่อ IP ต่อนาที ปรับได้ผ่าน env
RATE_LIMIT_GET_PER_MIN = int(os.getenv("SNC_RATE_LIMIT_GET", "120"))
RATE_LIMIT_WRITE_PER_MIN = int(os.getenv("SNC_RATE_LIMIT_WRITE", "20"))
RATE_WINDOW_SECONDS = 60.0
_rate_buckets = defaultdict(list)  # (ip, kind) -> [timestamps]


def _rate_allowed(key: str, limit: int, now: float) -> bool:
    window_start = now - RATE_WINDOW_SECONDS
    stamps = _rate_buckets[key]
    # ตัด timestamp เก่านอกหน้าต่างออก
    while stamps and stamps[0] < window_start:
        stamps.pop(0)
    if len(stamps) >= limit:
        return False
    stamps.append(now)
    return True


@app.middleware("http")
async def guard_write_endpoints(request, call_next):
    # Rate limit ก่อน auth: ทุก request กิน quota ต่อ IP — กัน brute-force key และ poll ถี่เกิน
    ip = (request.headers.get("x-forwarded-for") or request.client.host or "unknown").split(",")[0].strip()
    kind = "write" if request.method in ("POST", "PUT", "DELETE") else "get"
    limit = RATE_LIMIT_WRITE_PER_MIN if kind == "write" else RATE_LIMIT_GET_PER_MIN
    if not _rate_allowed((ip, kind), limit, time.monotonic()):
        return JSONResponse(
            {"error": "rate limit exceeded, slow down"},
            status_code=429,
            headers={"Retry-After": str(int(RATE_WINDOW_SECONDS))},
        )

    # กันการเขียน (trigger/ack/clear/AI) จากใครก็ได้ใน LAN — GET (dashboard/poll) ยังเปิด
    if request.method in ("POST", "PUT", "DELETE") and SNC_API_KEY:
        if request.headers.get("X-API-Key", "") != SNC_API_KEY:
            return JSONResponse({"error": "invalid or missing X-API-Key"}, status_code=401)
    return await call_next(request)

# Enable CORS for Frontend Development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static files (dashboard, frontend) — ชี้ไปที่ app/ (UI Dashboard) ตามโครงสร้าง 5-Core ใหม่
static_dir = os.path.join(os.path.dirname(__file__), "..", "app")
if not os.path.exists(static_dir):
    os.makedirs(static_dir)
app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/")
async def serve_root():
    """Serve the original main nurse call dashboard (index.html)."""
    index_path = os.path.join(static_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    else:
        return RedirectResponse(url="/dashboard-status.html")

@app.get("/dashboard-status.html")
async def serve_dashboard():
    """Serve the status dashboard HTML file."""
    dashboard_path = os.path.join(static_dir, "dashboard-status.html")
    if os.path.exists(dashboard_path):
        return FileResponse(dashboard_path)
    else:
        return {"error": "Dashboard not found. Please deploy dashboard-status.html to app/"}

DB_PATH = "nurse_call_events.db"

# Initialize SQLite Database
def init_db():
    conn = sqlite3.connect(DB_PATH, timeout=15.0)
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
    # CREATE TABLE IF NOT EXISTS ไม่ได้เพิ่มคอลัมน์ให้ตารางที่มีอยู่แล้ว
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

init_db()

# WebSocket Manager for Real-time Nurse Station Broadcast
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logging.info(f"Client connected. Active clients: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logging.info(f"Client disconnected. Active clients: {len(self.active_connections)}")

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logging.error(f"Error broadcasting to WebSocket: {e}")

manager = ConnectionManager()

# Data Model for Manual Triggering/Testing
class CallEventRequest(BaseModel):
    room_id: str
    event_type: str

class DemoScenarioRequest(BaseModel):
    room_id: str = "400"
    ack_after: float = 5.0      # วินาทีจาก trigger จนถึงรับเรื่อง (Ack)
    clear_after: float = 12.0   # วินาทีจาก trigger จนถึงเคลียร์สาย
    include_emergency: bool = False  # ต่อด้วยสถานการณ์ฉุกเฉินห้องน้ำอีก 1 รอบ

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

def save_event_to_db(event_data: dict):
    conn = sqlite3.connect(DB_PATH, timeout=15.0)
    cursor = conn.cursor()
    ext = event_data.get("extension", {})
    room_id = ext["roomId"]
    # เก็บ event_type ต้นทาง (เช่น CALL_BEDSIDE / CALL_BATHROOM_EMERGENCY) ไม่ใช่ค่าที่ map แล้ว
    # (CALL_TRIGGERED) เพื่อให้ KPI และ Dashboard แยกเหตุการณ์ได้ถูกต้อง — backward compatible
    event_type = ext.get("sourceEventType") or event_data["payload"][0]["contentString"]
    
    cursor.execute("""
        INSERT OR REPLACE INTO nurse_call_events (id, room_id, event_type, status, timestamp, fhir_payload)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        event_data["id"],
        room_id,
        event_type,
        event_data["status"],
        event_data["extension"]["timestamp"],
        json.dumps(event_data, ensure_ascii=False)
    ))
    conn.commit()
    conn.close()

@app.get("/api/events")
def get_recent_events():
    conn = sqlite3.connect(DB_PATH, timeout=15.0)
    cursor = conn.cursor()
    # Fetch more records internally to allow frontend filtering, but limit is also applied in frontend
    cursor.execute("SELECT id, room_id, event_type, status, timestamp, acknowledged_at, resolved_at, ack_time_seconds, resolution_time_seconds, sla_breached FROM nurse_call_events ORDER BY timestamp DESC LIMIT 200")
    rows = cursor.fetchall()
    conn.close()
    
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
    return {"events": events}

@app.post("/api/events/trigger")
async def trigger_event(req: CallEventRequest):
    """Simulate or trigger an event manually for testing or from PBX Listener."""
    logging.info(f"📨 Received event trigger request: room_id={req.room_id}, event_type={req.event_type}")
    
    formatted_room = req.room_id.zfill(4)
    now_iso = datetime.now().isoformat()
    
    # Handle Hardware PBX Event Logic directly for SLA tracking
    if req.event_type == "NURSE_TALKING":
        logging.info(f"Processing NURSE_TALKING for room {formatted_room}")
        return await acknowledge_call(formatted_room)
    elif req.event_type == "CALL_CLEARED":
        logging.info(f"Processing CALL_CLEARED for room {formatted_room}")
        return await clear_call(formatted_room)
    
    # Map event types from PBX listener to dashboard-compatible types
    event_type_mapping = {
        "CALL_BEDSIDE": "CALL_TRIGGERED",
        "CALL_BATHROOM_EMERGENCY": "CALL_TRIGGERED",
    }
    
    mapped_event_type = event_type_mapping.get(req.event_type, req.event_type)
    logging.info(f"Mapped event type: {req.event_type} -> {mapped_event_type}")
    
    # Use microseconds to ensure unique IDs even for events in the same second
    import time
    unique_id = f"snc-event-{formatted_room}-{int(time.time() * 1000000)}"
    
    event_payload = {
        "resourceType": "CommunicationRequest",
        "id": unique_id,
        "status": "active" if mapped_event_type == "CALL_TRIGGERED" else "completed",
        "occurrenceDateTimeField": now_iso,
        "payload": [{"contentString": mapped_event_type}],
        "extension": {
            "roomId": formatted_room,
            "timestamp": now_iso,
            "sourceEventType": req.event_type  # เก็บชนิดต้นทางไว้แสดงผล/KPI (เช่น CALL_BATHROOM_EMERGENCY)
        }
    }
    
    logging.info(f"Saving event to database: ID={unique_id}, Room={formatted_room}, Type={mapped_event_type}")
    save_event_to_db(event_payload)
    logging.info(f"✅ Event saved successfully: {unique_id}")
    
    await manager.broadcast(event_payload)
    return {"status": "success", "event": event_payload}

@app.post("/api/events/acknowledge/{room_id}")
async def acknowledge_call(room_id: str):
    """Nurse acknowledges the call from Dashboard."""
    conn = sqlite3.connect(DB_PATH, timeout=15.0)
    cursor = conn.cursor()
    now_iso = datetime.now().isoformat()
    formatted_room = room_id.zfill(4)
    
    # Get the original timestamp to calculate ack time
    cursor.execute("SELECT timestamp FROM nurse_call_events WHERE room_id = ? AND status = 'active' ORDER BY timestamp DESC LIMIT 1", (formatted_room,))
    row = cursor.fetchone()
    sla_metrics = None
    
    if row:
        created_at = row[0]
        sla_metrics = calculate_sla_metrics(created_at, acknowledged_at=now_iso)
        
        cursor.execute("""
            UPDATE nurse_call_events SET status = 'acknowledged', acknowledged_at = ?, 
            ack_time_seconds = ?, sla_breached = ?
            WHERE room_id = ? AND status = 'active'
        """, (now_iso, sla_metrics["ack_time_seconds"], sla_metrics["sla_breached"], formatted_room))
        conn.commit()
    
    conn.close()
    
    ack_event = {
        "resourceType": "CommunicationRequest",
        "id": f"ack-{formatted_room}-{int(datetime.now().timestamp())}",
        "status": "acknowledged",
        "payload": [{"contentString": "ACKNOWLEDGED"}],
        "extension": {"roomId": formatted_room, "timestamp": now_iso}
    }
    await manager.broadcast(ack_event)
    return {"status": "acknowledged", "room_id": formatted_room, "sla_metrics": sla_metrics if row else None}

@app.post("/api/events/clear/{room_id}")
async def clear_call(room_id: str):
    """Clear the call event when issue is resolved."""
    conn = sqlite3.connect(DB_PATH, timeout=15.0)
    cursor = conn.cursor()
    now_iso = datetime.now().isoformat()
    formatted_room = room_id.zfill(4)
    
    # Get the original timestamp to calculate resolution time
    cursor.execute("SELECT timestamp FROM nurse_call_events WHERE room_id = ? AND status IN ('active', 'acknowledged') ORDER BY timestamp DESC LIMIT 1", (formatted_room,))
    row = cursor.fetchone()
    sla_metrics = None
    
    if row:
        created_at = row[0]
        sla_metrics = calculate_sla_metrics(created_at, resolved_at=now_iso)
        
        cursor.execute("""
            UPDATE nurse_call_events SET status = 'resolved', resolved_at = ?, 
            resolution_time_seconds = ?, sla_breached = ?
            WHERE room_id = ? AND status IN ('active', 'acknowledged')
        """, (now_iso, sla_metrics["resolution_time_seconds"], sla_metrics["sla_breached"], formatted_room))
        conn.commit()
    
    conn.close()
    
    clear_event = {
        "resourceType": "CommunicationRequest",
        "id": f"clear-{formatted_room}-{int(datetime.now().timestamp())}",
        "status": "resolved",
        "payload": [{"contentString": "CALL_CLEARED"}],
        "extension": {"roomId": formatted_room, "timestamp": now_iso}
    }
    await manager.broadcast(clear_event)
    return {"status": "cleared", "room_id": formatted_room, "sla_metrics": sla_metrics if row else None}

@app.post("/api/demo/scenario")
async def run_demo_scenario(req: DemoScenarioRequest):
    """
    API ทดสอบจริง (Deterministic SLA Demo) — จำลองครบวงจรโดยไม่ต้องพึ่งตู้ PBX:
    CALL_BEDSIDE → รอ ack_after วิ → Acknowledge → รอถึง clear_after วิ → Clear
    (ถ้า include_emergency=True จะต่อด้วย CALL_BATHROOM_EMERGENCY อีก 1 รอบ)

    ทุก transition จะ broadcast ผ่าน WebSocket ทันที → Dashboard อัปเดตสดระหว่างรัน
    เรียกง่าย ๆ: curl -X POST http://localhost:8000/api/demo/scenario
    """
    room = req.room_id.zfill(4)
    steps = []

    async def run_step(name, fn):
        res = await fn()
        steps.append({"step": name, **res})
        return res

    # ระยะที่ 1: สายเรียกข้างเตียง
    await run_step("trigger_bedside",
        lambda: trigger_event(CallEventRequest(room_id=room, event_type="CALL_BEDSIDE")))
    await asyncio.sleep(max(0.0, req.ack_after))
    await run_step("acknowledge", lambda: acknowledge_call(room))
    await asyncio.sleep(max(0.0, req.clear_after - req.ack_after))
    await run_step("clear", lambda: clear_call(room))

    # ระยะที่ 2 (ไม่บังคับ): ฉุกเฉินห้องน้ำ
    if req.include_emergency:
        await run_step("trigger_bathroom_emergency",
            lambda: trigger_event(CallEventRequest(room_id=room, event_type="CALL_BATHROOM_EMERGENCY")))
        await asyncio.sleep(max(0.0, req.ack_after))
        await run_step("acknowledge_emergency", lambda: acknowledge_call(room))
        await asyncio.sleep(max(0.0, req.clear_after - req.ack_after))
        await run_step("clear_emergency", lambda: clear_call(room))

    return {
        "status": "success",
        "room_id": room,
        "steps": steps,
        "kpi": get_kpi_summary()
    }

@app.get("/api/analytics/kpi")
def get_kpi_summary():
    """Get KPI analytics for nurse call performance."""
    conn = sqlite3.connect(DB_PATH, timeout=15.0)
    cursor = conn.cursor()
    
    # Get average ack time
    cursor.execute("SELECT AVG(ack_time_seconds) FROM nurse_call_events WHERE ack_time_seconds IS NOT NULL")
    avg_ack_time = cursor.fetchone()[0] or 0
    
    # Get average resolution time
    cursor.execute("SELECT AVG(resolution_time_seconds) FROM nurse_call_events WHERE resolution_time_seconds IS NOT NULL")
    avg_resolution_time = cursor.fetchone()[0] or 0
    
    # Get total events by type
    cursor.execute("SELECT event_type, COUNT(*) FROM nurse_call_events GROUP BY event_type")
    events_by_type = dict(cursor.fetchall())
    
    # Get SLA compliance rate (DB ว่าง = ไม่มี phantom event/breach)
    cursor.execute("SELECT COUNT(*) FROM nurse_call_events")
    total_events = cursor.fetchone()[0] or 0
    
    cursor.execute("SELECT COUNT(*) FROM nurse_call_events WHERE sla_breached = 0 OR sla_breached IS NULL")
    compliant_events = cursor.fetchone()[0]
    
    if total_events == 0:
        sla_compliance_rate = 100.0
    else:
        sla_compliance_rate = (compliant_events / total_events) * 100
    
    conn.close()
    
    return {
        "avg_ack_time_seconds": round(avg_ack_time, 2),
        "avg_resolution_time_seconds": round(avg_resolution_time, 2),
        "total_events": total_events,
        "events_by_type": events_by_type,
        "sla_compliance_rate": round(sla_compliance_rate, 2)
    }

@app.get("/api/ai/daily-summary")
async def get_daily_ai_summary():
    """Generate daily executive AI summary using Gemini Direct REST API (฿0/month)."""
    kpi_summary = get_kpi_summary()
    recent_events_res = get_recent_events()
    recent_events = recent_events_res.get("events", [])
    
    summary_text = await gemini_service.generate_daily_executive_summary(kpi_summary, recent_events)
    return {
        "status": "success",
        "timestamp": datetime.now().isoformat(),
        "kpi_metrics": kpi_summary,
        "ai_summary": summary_text
    }

@app.post("/api/ai/analyze-anomaly/{room_id}")
async def analyze_room_anomaly(room_id: str):
    """Analyze room emergency call patterns for anomalies using Gemini Direct REST API."""
    formatted_room = room_id.zfill(4)
    conn = sqlite3.connect(DB_PATH, timeout=15.0)
    cursor = conn.cursor()
    cursor.execute("SELECT id, room_id, event_type, status, timestamp, ack_time_seconds, resolution_time_seconds, sla_breached FROM nurse_call_events WHERE room_id = ? ORDER BY timestamp DESC LIMIT 20", (formatted_room,))
    rows = cursor.fetchall()
    conn.close()
    
    room_events = []
    for row in rows:
        room_events.append({
            "id": row[0], "room_id": row[1], "event_type": row[2], "status": row[3],
            "timestamp": row[4], "ack_time_seconds": row[5], "resolution_time_seconds": row[6], "sla_breached": row[7]
        })
        
    analysis = await gemini_service.analyze_emergency_anomaly(formatted_room, room_events)
    return {
        "status": "success",
        "room_id": formatted_room,
        "event_count": len(room_events),
        "ai_analysis": analysis
    }

@app.post("/api/ai/send-daily-summary")
async def send_daily_summary_to_chat(webhook_url: str = None):
    """Generate and send daily AI executive summary card to Google Chat."""
    kpi_summary = get_kpi_summary()
    recent_events_res = get_recent_events()
    recent_events = recent_events_res.get("events", [])
    
    summary_text = await gemini_service.generate_daily_executive_summary(kpi_summary, recent_events)
    sent_success = await gemini_service.send_google_chat_summary(webhook_url, summary_text, kpi_summary)
    
    return {
        "status": "sent" if sent_success else "failed",
        "chat_webhook_delivered": sent_success,
        "ai_summary": summary_text
    }

@app.get("/health")
def health_check():
    """Health check endpoint for monitoring."""
    return {
        "status": "healthy",
        "service": "snc-backend",
        "timestamp": datetime.now().isoformat()
    }

@app.websocket("/ws/nurse-station")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            logging.info(f"Received WS message: {data}")
    except WebSocketDisconnect:
        manager.disconnect(websocket)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
