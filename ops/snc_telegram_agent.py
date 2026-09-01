#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
snc_telegram_agent.py — ตอบคำถามเกี่ยวกับ SNC ผ่าน Telegram bot @snc2569_bot (โหมด 2 ทาง)

- Zero dependency (urllib) — ฟรี 100% ไม่เรียก AI ภายนอก ไม่ต้องเปิดพอร์ตสาธารณะ
- Poll getUpdates (long-polling) อ่านข้อความเข้ามา → ตอบสถานะจริงจาก backend / burnin.log
- ปลอดภัย: ตอบเฉพาะ chat_id ใน SNC_TG_ALLOWED_CHAT (ถ้าตั้ง) — ค่าอื่นตอบปฏิเสธ

วิธีรัน (ง่ายสุด, ไม่ต้อง sudo):
  cd /home/ecs-agent/snc
  nohup python3 ops/snc_telegram_agent.py >> tg_agent.log 2>&1 &

วิธีถาวร (systemd — service snc-tg-agent, รอด reboot):
  sudo cp ops/snc-tg-agent.service /etc/systemd/system/
  sudo systemctl daemon-reload && sudo systemctl enable --now snc-tg-agent

คำสั่งที่ถามได้: /help /kpi /rooms /burn /status หรือพิมพ์ภาษาไทย เช่น "ห้องไหนค้าง", "burn ถึงไหนแล้ว"
"""
import os
import sys
import json
import time
import subprocess
import datetime
import importlib.util
import urllib.request
import urllib.parse

try:
    from html import escape as html_escape
except ImportError:  # pragma: no cover
    html_escape = lambda value: str(value)

BASE = os.path.dirname(os.path.abspath(__file__))
PARENT = os.path.dirname(BASE)  # root ของโปรเจกต์ (ถ้าสคริปต์อยู่ใน ops/)


def load_env(path):
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip())
    except OSError:
        pass


# 5-Core: .env อยู่ที่ <root>/api/.env, <root>/pbx/.env (ลอง parent ก่อน)
# Legacy: .env อยู่ข้างสคริปต์ (backend/, pbx-connector/, root)
for base in (PARENT, BASE):
    for p in ("api/.env", ".env", "backend/.env", "pbx-connector/.env", "pbx/.env"):
        load_env(os.path.join(base, p))

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
ALLOWED = {c.strip() for c in os.getenv("SNC_TG_ALLOWED_CHAT", "").split(",") if c.strip()}
BACKEND = os.getenv("BACKEND_API_URL", "http://localhost:8000")
BURNIN_LOG = os.getenv("BURNIN_LOG", os.path.join(BASE, "burnin.log"))


def tg(method, **params):
    data = urllib.parse.urlencode(params).encode()
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{TOKEN}/{method}", data=data, method="POST")
    with urllib.request.urlopen(req, timeout=40) as r:
        return json.loads(r.read().decode("utf-8"))


def send(chat_id, text):
    return tg("sendMessage", chat_id=chat_id, text=text, parse_mode="HTML")


def http_json(path):
    # UA เฉพาะของเรา — Cloudflare WAF บล็อก UA default ของ python-urllib (403)
    req = urllib.request.Request(
        f"{BACKEND}{path}", headers={"User-Agent": "SNC-Telegram-Agent/1.0"})
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read().decode("utf-8"))


HELP = (
    "🤖 <b>SNC Agent</b> — เมนูตรวจสอบระบบ\n\n"
    "<b>สถานะระบบ</b>\n"
    "/health — ตรวจ Backend, Database, PBX Listener, WebSocket และ Cloud Run\n"
    "/status — สรุปสถานะระบบแบบสั้น\n"
    "/cloudrun — ตรวจ Cloud Run และ endpoint /health\n"
    "/uptime — ตรวจ Uptime Check /health\n\n"
    "<b>การปฏิบัติงาน</b>\n"
    "/logs — ดู Logs ล่าสุด\n"
    "/kpi — ตัวชี้วัด SLA ล่าสุด\n"
    "/rooms — สายเรียกค้าง / เหตุการณ์ล่าสุด\n"
    "/burn — สถานะ Burn-in 48 ชม.\n"
    "/alerts — แจ้งเตือนล่าสุด 10 รายการ\n"
    "/alerts TUNNEL — ค้นตามรหัส/ประเภท/คีย์เวิร์ด\n\n"
    "/help — แสดงเมนูนี้\n\n"
    "กดคำสั่งตามลำดับแนะนำ: /health → /cloudrun หรือ /logs"
)


ABOUT = (
    "🤖 <b>SNC Agent — Smart Nurse Call</b>\n\n"
    "📍 <b>ทำงานที่ไหน</b>\n"
    "• Edge Pi <b>192.168.1.94</b> → /home/ecs-agent/snc\n"
    "• 2 services (systemd): snc-backend (API :8000) + snc-pbx-listener\n"
    "• ฟัง SMDR จากตู้ Phonik PBX <b>192.168.1.91:23</b>\n"
    "• proxy mirror พอร์ต <b>2323</b> ให้ PC Room Manager\n\n"
    "🏢 <b>สังกัด</b>: โครงการ Smart Nurse Call PoC ของ Hotel-ECS\n\n"
    "🎯 <b>ขอบเขต (ทำ)</b>\n"
    "• ดักจับสัญญาณ nurse call → event: CALL_BEDSIDE / CALL_BATHROOM_EMERGENCY / CALL_CLEARED\n"
    "• จับเวลา SLA: Ack ≤30s · Resolution ≤180s · compliance ≥98%\n"
    "• แสดงแดชบอร์ด nurse station สด (WebSocket) + แจ้งเตือน/ตอบคำถาม Telegram\n\n"
    "🚫 <b>ไม่ทำ</b>: คุมไฟห้องพัก (CCH2 ..ROOM) — เป็นอีก repo (Hotel power)\n\n"
    "💡 <b>คำแนะนำ</b>: พิมพ์ /kpi /rooms /burn /status /help หรือภาษาไทย เช่น \"ห้องไหนค้าง\""
)


def kpi_reply():
    k = http_json("/api/analytics/kpi")
    comp = k.get("sla_compliance_rate", 0)
    ok = "✅" if comp >= 98 else ("⚠️" if comp >= 90 else "🚨")
    by = ", ".join(f"{x}:{n}" for x, n in (k.get("events_by_type") or {}).items())
    return (f"📊 <b>KPI ล่าสุด</b>\n"
            f"• Ack เฉลี่ย: <b>{k.get('avg_ack_time_seconds')}s</b> (เป้า ≤30s)\n"
            f"• Resolution เฉลี่ย: <b>{k.get('avg_resolution_time_seconds')}s</b> (เป้า ≤180s)\n"
            f"• SLA compliance: <b>{comp}%</b> {ok} (เป้า ≥98%)\n"
            f"• เหตุการณ์ทั้งหมด: <b>{k.get('total_events')}</b>\n"
            f"• แยกตามประเภท: {by or '-'}")


def rooms_reply():
    evs = http_json("/api/events")["events"]
    open_ = [e for e in evs if e["status"] in ("active", "acknowledged")]
    if not open_:
        return "✅ ไม่มีสายค้าง — ทุกห้องปกติ"
    lines = ["🚨 <b>สายค้างอยู่</b>:"]
    for e in open_:
        lines.append(f"• ห้อง {e['room_id']} — {e['event_type']} ({e['status']})")
    return "\n".join(lines)


def burn_reply():
    try:
        with open(BURNIN_LOG, encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
        if len(lines) < 2:
            return "🔥 ยังไม่มีข้อมูล burnin.log เพียงพอ"
        t0 = datetime.datetime.strptime(lines[0][:19], "%Y-%m-%d %H:%M:%S")
        t1 = datetime.datetime.strptime(lines[-1][:19], "%Y-%m-%d %H:%M:%S")
        el = (t1 - t0).total_seconds() / 3600
        rem = max(0.0, 48 - el)
        return (f"🔥 <b>Burn-in</b>\n"
                f"• เริ่ม: {lines[0][:19]}\n"
                f"• ผ่านไป: <b>{el:.1f}</b>/48 ชม. (เหลือ ~{rem:.1f} ชม.)\n"
                f"• ล่าสุด: {lines[-1].strip()}")
    except Exception as e:
        return f"อ่าน burnin.log ไม่ได้: {e}"


def alerts_reply(text):
    """ดู/ค้นประวัติการแจ้งเตือนจาก ledger (logs/alerts.log) — มีรหัสอ้างอิง SNC-AL-..."""
    try:
        spec = importlib.util.spec_from_file_location(
            "alerting", os.path.join(BASE, "alerting.py"))
        a = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(a)
    except Exception as e:
        return f"อ่าน alerting.py ไม่ได้: {e} — ดู logs/alerts.log ตรง ๆ"

    # ตัดคำฟุ่มเฟือย: "alert ล่าสุด" / "แจ้งเตือนรายการ" → โหมดรายการ
    q = text.replace("/alerts", "").replace("alert", "").lower()
    for w in ("ล่าสุด", "รายการ", "ประวัติ", "ดู", "โชว์", "แจ้งเตือน", "แจ้ง"):
        q = q.replace(w, "")
    q = q.strip()
    if not q:
        items = a.list_alerts(limit=10)
        if not items:
            return "📭 ยังไม่มี alert ใน ledger (logs/alerts.log)"
        lines = ["🗂️ <b>Alert ล่าสุด 10 รายการ</b> (รหัส/เวลา/เรื่อง):"]
        for e in items:
            icon = a.SEVERITY_ICON.get(e.get("severity"), "🔔")
            sent = "" if e.get("sent") else " ⏭️(ยังไม่ส่ง)"
            lines.append(f"{icon} <code>{e['code']}</code> {e['ts']}{sent}\n   {e['summary']}")
        return "\n".join(lines)

    items = a.list_alerts(q, limit=5)
    if not items:
        return f"🔍 ไม่พบ alert ที่ตรงกับ '{q}' — ลอง /alerts เพื่อดูรายการทั้งหมด"
    if len(items) == 1 and items[0]["code"].lower() == q.lower():
        e = items[0]
        return (
            f"📋 <b>รายละเอียด alert</b>\n"
            f"รหัส: <code>{e['code']}</code>\n"
            f"ระดับ: {e['severity']} | เวลา: {e['ts']}\n"
            f"เรื่อง: {e['summary']}\n"
            f"รายละเอียด: {e.get('details') or '-'}\n"
            f"ตรวจสอบ: {e.get('verify') or '-'}\n"
            f"ส่ง Telegram แล้ว: {'✅' if e.get('sent') else '⏭️ (ข้าม — ดู ledger)'}"
        )
    lines = [f"🔍 <b>ค้น '{q}' พบ {len(items)} รายการ:</b>"]
    for e in items:
        icon = a.SEVERITY_ICON.get(e.get("severity"), "🔔")
        lines.append(f"{icon} <code>{e['code']}</code> {e['ts']} — {e['summary']}")
    return "\n".join(lines)


def _icon(status):
    return {"healthy": "✅", "active": "✅", "connected": "✅", "ready": "✅",
            "degraded": "⚠️", "reconnecting": "⚠️", "down": "❌", "failed": "❌"}.get(
                str(status).lower(), "ℹ️")


def health_reply():
    try:
        h = http_json("/health")
    except Exception as exc:
        return ("🚨 <b>ระบบ SNC พบความผิดปกติ</b>\n\n"
                "สถานะรวม: <b>DOWN</b>\n\n"
                "รายการตรวจสอบ:\n❌ Backend API: ไม่สามารถเรียก /health ได้\n\n"
                f"สาเหตุที่ตรวจพบ: {html_escape(str(exc))}\n\n"
                "เมนูถัดไป: /logs หรือ /cloudrun")

    checks = h.get("checks") or {}
    lines = [
        f"{_icon(h.get('status'))} <b>ผลตรวจสุขภาพระบบ SNC</b>",
        f"เวลา: {h.get('timestamp', datetime.datetime.now().isoformat())}",
        f"สถานะรวม: <b>{str(h.get('status', 'unknown')).upper()}</b>",
        "",
        "รายการตรวจสอบ:"
    ]
    if checks:
        labels = {
            "backend": "Backend API", "database": "Database", "pbx_listener": "PBX Listener",
            "websocket": "WebSocket", "cloud_run": "Cloud Run"
        }
        for key, value in checks.items():
            item = value if isinstance(value, dict) else {"status": value}
            lines.append(f"{_icon(item.get('status'))} {labels.get(key, key)}: {item.get('message', item.get('status', '-'))}")
    else:
        lines.extend([
            f"{_icon(h.get('status'))} Backend API: {h.get('status', 'unknown')}",
            f"✅ Database: {h.get('db', 'unknown')}",
        ])

    lines.extend(["", "สาเหตุที่ตรวจพบ: " + (h.get("reason") or "ไม่พบความผิดปกติ"), "",
                  "เมนูถัดไป: /cloudrun | /logs | /uptime"])
    return "\n".join(lines)


def cloudrun_reply():
    try:
        h = http_json("/health")
        return ("☁️ <b>Cloud Run</b>\n"
                f"• Service: {h.get('service', 'snc-backend')}\n"
                f"• /health: {_icon(h.get('status'))} {h.get('status', 'unknown')}\n"
                f"• Database: {h.get('db', 'unknown')}\n"
                f"• เวลา: {h.get('timestamp', '-')}\n\n"
                "เมนูถัดไป: /logs หรือ /uptime")
    except Exception as exc:
        return f"🚨 <b>Cloud Run ตรวจสอบไม่ได้</b>\nสาเหตุ: {html_escape(str(exc))}\n\nเมนูถัดไป: /logs"


def uptime_reply():
    return ("⏱️ <b>Uptime Check</b>\n"
            "• Endpoint ที่ตรวจ: /health\n"
            "• สถานะ: ตรวจผ่าน Backend health endpoint\n"
            "• หากพบ Alert: ตรวจ /cloudrun และ /logs ต่อ\n\n"
            "เมนูถัดไป: /health | /cloudrun | /logs")


def logs_reply():
    try:
        result = subprocess.run(
            ["journalctl", "-u", "snc-backend", "-u", "snc-pbx-listener", "-n", "20", "--no-pager"],
            capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return (f"📜 <b>Logs ล่าสุด</b>\nอ่าน journalctl ไม่ได้ ({html_escape(type(exc).__name__)})\n"
                "ใช้ได้เฉพาะบน Pi (systemd)\n\nเมนูถัดไป: /health")
    output = (result.stdout or result.stderr).strip()
    if not output:
        return "📜 <b>Logs ล่าสุด</b>\nไม่พบข้อมูลจาก systemd\n\nเมนูถัดไป: /health"
    return "📜 <b>Logs ล่าสุด 20 รายการ</b>\n<pre>" + html_escape(output[-3500:]) + "</pre>"


def status_reply():
    return health_reply()


def answer(text):
    t = text.lower()
    if any(k in t for k in ("help", "ช่วย", "คำสั่ง", "command", "/start")):
        return HELP
    if any(k in t for k in ("alerts", "alert", "แจ้งเตือน", "แจ้ง")):
        return alerts_reply(text)
    if any(k in t for k in ("cloudrun", "cloud run", "คลาวด์รัน")):
        return cloudrun_reply()
    if any(k in t for k in ("uptime", "อัปไทม์", "ตรวจ uptime")):
        return uptime_reply()
    if any(k in t for k in ("logs", "log", "ล็อก", "บันทึก")):
        return logs_reply()
    if any(k in t for k in ("kpi", "sla", "เป้า", "เกณฑ์")):
        return kpi_reply()
    if any(k in t for k in ("ห้อง", "room", "สาย", "ค้าง", "active")):
        return rooms_reply()
    if any(k in t for k in ("burn", "เบิร์น", "burnin")):
        return burn_reply()
    if any(k in t for k in ("สถานะ", "status", "health", "สุขภาพ")):
        return health_reply()
    if any(k in t for k in ("skill", "agent", "อธิบาย", "เกี่ยวกับ", "ขอบเขต", "สังกัด", "ทำงาน", "คืออะไร")):
        return ABOUT
    return "🤔 ไม่เข้าใจครับ — ลอง /help เพื่อดูเมนูคำสั่งทั้งหมด"


def main():
    if not TOKEN:
        print("TELEGRAM_BOT_TOKEN ไม่ได้ตั้งค่า", file=sys.stderr)
        sys.exit(1)
    print(f"SNC Agent started. allowed_chat={ALLOWED or 'ANY (เปิดหมด)'}")
    offset = 0
    while True:
        try:
            upd = tg("getUpdates", offset=offset, timeout=25)
            for u in upd.get("result", []):
                offset = u["update_id"] + 1
                m = u.get("message") or {}
                txt = (m.get("text") or "").strip()
                cid = m.get("chat", {}).get("id")
                if not txt or cid is None:
                    continue
                if ALLOWED and str(cid) not in ALLOWED:
                    send(cid, "⛔ บอทนี้จำกัดการใช้งาน (ไม่อยู่ใน allow-list)")
                    continue
                try:
                    send(cid, answer(txt))
                except Exception as e:
                    print("reply error:", e, file=sys.stderr)
        except Exception as e:
            print("poll error:", e, file=sys.stderr)
            time.sleep(5)


if __name__ == "__main__":
    main()
