import asyncio
import os
import pathlib
import json
import logging
import time
import urllib.request
from collections import defaultdict
from datetime import datetime
from typing import List
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
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

# Event Store — abstraction เหนือ SQLite (Pi4) / Firestore (Cloud Run)
# เลือก backend ผ่าน env SNC_DB_BACKEND (ดู api/storage.py)
from storage import get_store

# Setup Logging
logging.basicConfig(level=logging.INFO)

gemini_service = GeminiDirectService()
store = get_store()
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

    # Webhook จาก GCP Monitoring (uptime alert) — auth ผ่าน ?token= ของตัวเอง (GCP ส่ง X-API-Key ไม่ได้)
    if request.url.path.startswith("/api/webhooks/"):
        return await call_next(request)

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
# รองรับ 2 layout:
#   1) Repo/5-Core (Pi4):      api/server.py  +  app/  →  ../app
#   2) Container (Cloud Run):  /app/server.py + /app/app/ → app  (dirname(__file__) = /app)
_server_dir = os.path.dirname(os.path.abspath(__file__))
_static_candidates = [
    os.path.join(_server_dir, "..", "app"),
    os.path.join(_server_dir, "app"),
]
static_dir = None
for _candidate in _static_candidates:
    if os.path.isfile(os.path.join(_candidate, "index.html")):
        static_dir = _candidate
        break
if static_dir is None:
    # fallback: ใช้ตัวแรก (คงพฤติกรรมเดิม) + แจ้งเตือนชัดเจน แทนการ mkdir แบบเงียบๆ
    static_dir = _static_candidates[0]
    logging.warning(f"Dashboard not found in {_static_candidates} — serving from {static_dir}")
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

@app.get("/api/events")
def get_recent_events():
    # Fetch more records internally to allow frontend filtering, but limit is also applied in frontend
    return {"events": store.get_recent_events(200)}

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
    store.save_event(event_payload)
    logging.info(f"✅ Event saved successfully: {unique_id}")

    await manager.broadcast(event_payload)
    return {"status": "success", "event": event_payload}

@app.post("/api/events/acknowledge/{room_id}")
async def acknowledge_call(room_id: str):
    """Nurse acknowledges the call from Dashboard."""
    now_iso = datetime.now().isoformat()
    formatted_room = room_id.zfill(4)

    created_at, sla_metrics = store.acknowledge_room(formatted_room, now_iso)

    ack_event = {
        "resourceType": "CommunicationRequest",
        "id": f"ack-{formatted_room}-{int(datetime.now().timestamp())}",
        "status": "acknowledged",
        "payload": [{"contentString": "ACKNOWLEDGED"}],
        "extension": {"roomId": formatted_room, "timestamp": now_iso}
    }
    await manager.broadcast(ack_event)
    return {"status": "acknowledged", "room_id": formatted_room, "sla_metrics": sla_metrics if created_at else None}

@app.post("/api/events/clear/{room_id}")
async def clear_call(room_id: str):
    """Clear the call event when issue is resolved."""
    now_iso = datetime.now().isoformat()
    formatted_room = room_id.zfill(4)

    created_at, sla_metrics = store.clear_room(formatted_room, now_iso)

    clear_event = {
        "resourceType": "CommunicationRequest",
        "id": f"clear-{formatted_room}-{int(datetime.now().timestamp())}",
        "status": "resolved",
        "payload": [{"contentString": "CALL_CLEARED"}],
        "extension": {"roomId": formatted_room, "timestamp": now_iso}
    }
    await manager.broadcast(clear_event)
    return {"status": "cleared", "room_id": formatted_room, "sla_metrics": sla_metrics if created_at else None}

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
    return store.get_kpi_summary()

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
    room_events = store.get_room_events(formatted_room, 20)

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

@app.post("/api/admin/reset-kpi")
def reset_kpi_stats(request: Request):
    """Admin endpoint to reset KPI statistics (clears event history for calculation)."""
    if SNC_API_KEY and request.headers.get("X-API-Key", "") != SNC_API_KEY:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)

    store.reset()
    logging.warning("KPI Statistics have been reset by admin command.")
    return {"status": "success", "message": "KPI stats cleared."}

@app.post("/api/admin/reset-db")
def reset_database(request: Request):
    """Admin endpoint to clear all event history (Use with caution)."""
    # ตรวจสอบ API Key เพื่อความปลอดภัย (ถ้ามีการตั้งค่าไว้)
    if SNC_API_KEY and request.headers.get("X-API-Key", "") != SNC_API_KEY:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)

    store.reset()
    logging.warning("Database has been reset by admin command.")
    return {"status": "success", "message": "All events cleared."}

@app.get("/health")
def health_check():
    """Health check endpoint for monitoring."""
    return {
        "status": "healthy",
        "service": "snc-backend",
        "db": store.backend_name,
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

# ── GCP Monitoring webhook bridge (uptime alert → Telegram) ────────────────
# Cloud Run รับ webhook จาก Cloud Monitoring เมื่อ uptime check พบปัญหา แล้วส่ง Telegram
# (ไม่พึ่ง Pi — เช็คเองแม้ Pi ตาย) ตั้ง env: TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID / MONITOR_WEBHOOK_TOKEN
MONITOR_WEBHOOK_TOKEN = os.getenv("MONITOR_WEBHOOK_TOKEN", "")


def _tg_send_sync(text: str) -> bool:
    """ส่งข้อความ Telegram (sync — ใช้ urllib เหมือน services อื่น ไม่มี dependency เพิ่ม)"""
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "")
    if not bot_token or not chat_id:
        logging.warning("TELEGRAM_BOT_TOKEN/TELEGRAM_CHAT_ID ไม่ได้ตั้ง — ข้ามส่ง Telegram")
        return False
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    data = json.dumps({"chat_id": chat_id, "text": text, "parse_mode": "HTML"}).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status == 200
    except Exception as e:
        logging.error(f"Telegram send failed: {e}")
        return False


@app.post("/api/webhooks/gcp-alert")
async def gcp_alert_webhook(request: Request):
    """รับ webhook จาก GCP Cloud Monitoring (uptime check fail) → ส่ง Telegram
    - auth ผ่าน ?token= (MONITOR_WEBHOOK_TOKEN) — GCP webhook ส่ง X-API-Key ไม่ได้
    - ถูก exempt จาก API-key middleware (ดู guard_write_endpoints)"""
    if MONITOR_WEBHOOK_TOKEN and request.query_params.get("token", "") != MONITOR_WEBHOOK_TOKEN:
        return JSONResponse({"error": "forbidden"}, status_code=403)
    try:
        body = await request.json()
    except Exception:
        body = {}
    incident = body.get("incident", {}) if isinstance(body, dict) else {}
    state = incident.get("state", "OPEN")
    summary = incident.get("summary", "") or "Cloud Run uptime check failed"
    condition = incident.get("condition_name", "")
    incident_url = incident.get("incident_url", "")
    lines = [
        "🚨 <b>GCP Monitoring: Cloud Run ผิดปกติ</b>",
        f"สถานะ: {state}",
        f"เงื่อนไข: {condition}" if condition else "",
        f"รายละเอียด: {summary}",
        f"ลิงก์: {incident_url}" if incident_url else "",
    ]
    text = "\n".join(line for line in lines if line)
    ok = await asyncio.get_running_loop().run_in_executor(None, _tg_send_sync, text)
    return {"status": "sent" if ok else "skipped", "state": state}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
