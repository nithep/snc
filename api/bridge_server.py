"""SNC Alert Bridge — standalone Cloud Run service (แยกจาก snc-cloud-backend)

รับ webhook จาก GCP Cloud Monitoring เมื่อ uptime check พบปัญหา แล้วส่ง Telegram
จุดประสงค์หลัก: อยู่คนละ service กับ backend หลัก → alert ส่งถึงแม้ backend หลัก down
(เป็น service จิ๋ว ไม่ import storage/server เลย — ไม่มีจุดพังร่วมกับ service หลัก)

Env (ตั้งโดย ops/deploy_bridge_cloudshell.sh):
  TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID — ปลายทาง Telegram
  MONITOR_WEBHOOK_TOKEN — token กันปลอม (fail-closed: ไม่ตั้ง = ปฏิเสธทั้งหมด)

Deploy: ops/deploy_bridge_cloudshell.sh
"""

import json
import logging
import os
import urllib.request

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="SNC Alert Bridge", version="1.0.0")

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
MONITOR_WEBHOOK_TOKEN = os.getenv("MONITOR_WEBHOOK_TOKEN", "")


def _authorized(request: Request) -> bool:
    """fail-closed: ไม่ตั้ง MONITOR_WEBHOOK_TOKEN = ปฏิเสธทุก request"""
    if not MONITOR_WEBHOOK_TOKEN:
        return False
    if request.query_params.get("token") == MONITOR_WEBHOOK_TOKEN:
        return True
    return request.headers.get("X-SNC-Token", "") == MONITOR_WEBHOOK_TOKEN


def _send_telegram(text: str) -> bool:
    """ส่งข้อความ Telegram (urllib — ไม่มี dependency เพิ่ม)"""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        logging.warning("TELEGRAM env ไม่ครบ — ข้ามส่ง")
        return False
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = json.dumps(
        {"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "HTML"}
    ).encode("utf-8")
    req = urllib.request.Request(
        url, data=payload, headers={"Content-Type": "application/json"}, method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status == 200
    except Exception as e:  # noqa: BLE001 — อย่าให้ webhook ตายเพราะ Telegram หลุด
        logging.error(f"Telegram send failed: {e}")
        return False


@app.get("/health")
def health():
    """uptime check ของ bridge เอง (ใช้เช็คว่า bridge ยังมีชีวิต)"""
    return {"status": "healthy", "service": "snc-alert-bridge"}


@app.post("/webhook")
async def webhook(request: Request):
    """รับ webhook จาก GCP Cloud Monitoring (uptime check fail) → ส่ง Telegram

    - auth ผ่าน ?token= หรือ header X-SNC-Token (GCP webhook ส่ง X-API-Key ไม่ได้)
    - payload รูปแบบ GCP alerting notification: {"incident": {...}}
    """
    if not _authorized(request):
        return JSONResponse({"error": "forbidden"}, status_code=403)
    try:
        body = await request.json()
    except Exception:  # noqa: BLE001
        body = {}
    incident = body.get("incident", {}) if isinstance(body, dict) else {}
    state = incident.get("state", "OPEN")
    summary = incident.get("summary", "") or "uptime check failed"
    condition = incident.get("condition_name", "") or "Uptime check /health failed"
    incident_url = incident.get("incident_url", "")
    # ระบุเป้าหมายที่ตรวจ (เช่น snc.nithep.com = Pi / run.app = Cloud Run) — ใช้รหัสอ้างอิงจาก GCP
    host = ""
    res = incident.get("resource", {}) if isinstance(incident, dict) else {}
    if isinstance(res, dict):
        labels = res.get("labels", {}) if isinstance(res.get("labels"), dict) else {}
        host = str(labels.get("host") or labels.get("url") or "")

    host_label = host.strip() or "SNC endpoint"
    if ".run.app" in host_label or "run.app" in host_label:
        target_type = "Cloud Run service"
        title = "GCP Monitoring: Cloud Run health check failed"
    elif "snc.nithep.com" in host_label or "nithep.com" in host_label:
        target_type = "Pi tunnel / public health endpoint"
        title = "GCP Monitoring: Pi health check failed"
    else:
        target_type = "SNC endpoint"
        title = "GCP Monitoring: SNC health check failed"

    lines = [
        f"🚨 <b>{title}</b>",
        "━━━━━━━━━━━━━━━━",
        f"สถานะ incident: {state}",
        f"เป้าหมาย: {host_label}",
        f"ประเภท: {target_type}",
        f"เงื่อนไข: {condition}",
        f"สรุป: {summary}",
        f"รหัสเหตุการณ์: <code>{incident.get('incident_id', '-')}</code>",
        f"ลิงก์: {incident_url}" if incident_url else "",
    ]
    text = "\n".join(line for line in lines if line)
    ok = _send_telegram(text)
    return {"status": "sent" if ok else "skipped", "state": state}


if __name__ == "__main__":
    import uvicorn

    # Cloud Run injects PORT env (default 8080) — ฟังตามนั้น กัน port mismatch
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)
