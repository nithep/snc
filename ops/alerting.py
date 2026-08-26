#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ops/alerting.py — ระบบแจ้งเตือนกลางของ SNC (zero-dependency, ใช้ urllib เท่านั้น)

แก้ปัญหา:
  - รูปแบบไม่สม่ำเสมอ      → ทุก alert ใช้ฟอร์แมตมาตรฐานเดียวกัน (severity/รหัส/เวลา/วิธีตรวจสอบ)
  - ไม่มีรหัสอ้างอิง        → สร้างรหัส SNC-AL-<TYPE>-<YYYYMMDD>-<HHMMSS> ให้ทุก alert (ค้น/อ้างอิงได้)
  - ไม่มีหลักฐานยืนยัน     → ทุก alert เขียน ledger logs/alerts.log (JSON ต่อท้าย) ค้นด้วย grep หรือ list_alerts()

วิธีใช้จากสคริปต์ shell:
  python3 ops/alerting.py --severity CRITICAL --type TUNNEL \
      --summary "WS Tunnel ตาย 2 ครั้งติด" \
      --details "wss://snc.nithep.com/ws/nurse-station ล้มเหลว 2 ครั้ง" \
      --verify "ssh pi4 tail -20 logs/ws-tunnel-check.log"
  → print รหัส alert (เช่น SNC-AL-TUNNEL-20260826-211500) + exit 0

วิธีใช้จาก Python (เช่น snc_telegram_agent.py):
  import importlib.util ...
  a.send_alert("CRITICAL", "POWER", "ไฟดับ — Pi อยู่นอกเวลา", details=..., verify=...)
  a.list_alerts(query="TUNNEL", limit=10)

severity: CRITICAL 🚨 | WARNING ⚠️ | INFO ℹ️
อ่าน TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID จาก env หรือ .env (api/.env, .env, ...)
อ่าน ledger จาก ALERT_LOG (default: <repo-root>/logs/alerts.log)
"""
import argparse
import json
import os
import sys
import datetime

# Windows console (cp874) พิมพ์ภาษาไทยไม่ได้ — บังคับ UTF-8 (กฎ Strict UTF-8)
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

BASE = os.path.dirname(os.path.abspath(__file__))
PARENT = os.path.dirname(BASE)  # root ของโปรเจกต์ (สคริปต์อยู่ใน ops/)
DEFAULT_LEDGER = os.path.join(PARENT, "logs", "alerts.log")

SEVERITY_ICON = {"CRITICAL": "🚨", "WARNING": "⚠️", "INFO": "ℹ️", "TEST": "🧪"}

# ขั้นตอนกู้คืนอัตโนมัติตามประเภท alert — แนบท้ายข้อความเสมอ (กู้ได้ทันทีจากมือถือ)
CHECKLISTS = {
    "POWER": [
        "1) ตรวจไฟ/เบรกเกอร์/ปลั๊กของ Pi และตู้ PBX",
        "2) ไฟกลับมา → รอ Pi บูต ~2 นาที (systemd ปลุก service เอง)",
        "3) ssh pi4 → systemctl is-active snc-backend snc-pbx-listener snc-cloudflared",
        "4) curl https://snc.nithep.com/health (tunnel กลับมาเมื่อ cloudflared ต่อได้)",
        "5) มี UPS → เช็คสถานะแบต กันไฟดับซ้ำ",
    ],
    "TUNNEL": [
        "1) ssh pi4 → systemctl status snc-cloudflared",
        "2) cloudflared tunnel list (0 connections → tunnel-self-heal ต่ออายุ secret เอง)",
        "3) curl https://snc.nithep.com/health",
        "4) ดู logs/ws-tunnel-check.log + logs/tunnel-self-heal.log",
    ],
    "BACKEND": [
        "1) ssh pi4 → systemctl status snc-backend",
        "2) sudo journalctl -u snc-backend -n 50",
        "3) curl http://localhost:8000/health",
    ],
    "CLOUD": [
        "1) GCP console → Cloud Run → snc-cloud-backend → Logs",
        "2) curl https://snc-cloud-backend-59781590359.asia-southeast1.run.app/health",
    ],
}


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


# 5-Core: .env อยู่ที่ <root>/api/.env — ลองหลายตำแหน่งเหมือน snc_telegram_agent.py
for base in (PARENT, BASE):
    for p in ("api/.env", ".env", "backend/.env", "pbx-connector/.env", "pbx/.env"):
        load_env(os.path.join(base, p))

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()
LEDGER = os.getenv("ALERT_LOG", DEFAULT_LEDGER)


def _tg(method, **params):
    import urllib.parse
    import urllib.request

    data = urllib.parse.urlencode(params).encode()
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{TOKEN}/{method}", data=data, method="POST")
    with urllib.request.urlopen(req, timeout=40) as r:
        return json.loads(r.read().decode("utf-8"))


def send_telegram(text: str) -> bool:
    """ส่งข้อความ Telegram — ถ้าไม่ตั้ง token/chat_id → SKIP เงียบ ๆ (exit 0)"""
    if not TOKEN or not CHAT_ID:
        print(f"[alerting] SKIP: ยังไม่ตั้ง TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID "
              f"(ledger ยังบันทึกหลักฐานไว้ที่ {LEDGER})", file=sys.stderr)
        return False
    try:
        _tg("sendMessage", chat_id=CHAT_ID, text=text, parse_mode="HTML",
            disable_web_page_preview="true")
        return True
    except Exception as e:
        print(f"[alerting] ส่ง Telegram FAILED: {e}", file=sys.stderr)
        return False


def make_code(alert_type: str, now=None) -> str:
    """รหัสอ้างอิง: SNC-AL-<TYPE>-<YYYYMMDD>-<HHMMSS> — อ้างอิง/ค้นใน ledger ได้"""
    now = now or datetime.datetime.now()
    t = (alert_type or "ALERT").upper().replace(" ", "-")
    return f"SNC-AL-{t}-{now:%Y%m%d-%H%M%S}"


def format_alert(severity: str, code: str, summary: str,
                 details: str = "", verify: str = "") -> str:
    """ฟอร์แมตมาตรฐาน — ทุก alert เหมือนกัน ต่างแค่เนื้อหา"""
    sev = severity.upper()
    icon = SEVERITY_ICON.get(sev, "🔔")
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = [
        f"{icon} <b>[{sev}] {summary}</b>",
        "━━━━━━━━━━━━━━━━",
        f"รหัส: <code>{code}</code>",
        f"เวลา: {now}",
    ]
    if details:
        lines.append(f"รายละเอียด: {details}")
    if verify:
        lines.append(f"ตรวจสอบ: {verify}")
    return "\n".join(lines)


def append_ledger(entry: dict) -> None:
    """เขียนหลักฐานการแจ้ง (JSON 1 บรรทัด/alert) — ค้นด้วย grep / list_alerts()"""
    try:
        os.makedirs(os.path.dirname(LEDGER), exist_ok=True)
        with open(LEDGER, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except OSError as e:
        print(f"[alerting] เขียน ledger ล้มเหลว: {e}", file=sys.stderr)


def send_alert(severity: str, alert_type: str, summary: str,
               details: str = "", verify: str = "") -> str:
    """ส่ง alert มาตรฐาน + บันทึก ledger → คืนรหัสอ้างอิง (SNC-AL-...)"""
    code = make_code(alert_type)
    atype = (alert_type or "ALERT").upper()
    steps = CHECKLISTS.get(atype)
    text = format_alert(severity, code, summary, details, verify)
    if steps:
        text += "\n\n📋 <b>ขั้นตอนกู้คืน:</b>\n" + "\n".join(steps)
    ok = send_telegram(text)
    append_ledger({
        "code": code, "severity": severity.upper(),
        "type": atype,
        "ts": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "summary": summary, "details": details, "verify": verify,
        "checklist": steps,
        "sent": ok,
    })
    print(f"[alerting] {code} severity={severity.upper()} type={(alert_type or 'ALERT').upper()} "
          f"telegram={'OK' if ok else 'SKIP'} ledger={LEDGER}")
    return code


def list_alerts(query: str = "", limit: int = 10):
    """อ่าน ledger (ล่าสุดก่อน) — ค้นตามรหัส/type/severity/คีย์เวิร์ด ใช้ใน bot /alerts"""
    if not os.path.isfile(LEDGER):
        return []
    q = (query or "").strip().lower()
    out = []
    try:
        with open(LEDGER, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    e = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if q and not any(
                    q in str(e.get(k, "")).lower()
                    for k in ("code", "type", "severity", "summary", "details")
                ):
                    continue
                out.append(e)
    except OSError:
        pass
    # ledger เขียนต่อท้าย → หลังสุดคือล่าสุด; คืนใหม่สุดก่อน
    return out[::-1][:limit]


def cli():
    p = argparse.ArgumentParser(description="SNC Alert — ส่ง + บันทึก ledger")
    p.add_argument("--severity", default="INFO", choices=["CRITICAL", "WARNING", "INFO", "TEST"])
    p.add_argument("--type", default="ALERT", help="เช่น TUNNEL, POWER, BACKEND")
    p.add_argument("--summary", default="", help="(ไม่ต้องใส่เมื่อใช้ --list)")
    p.add_argument("--details", default="")
    p.add_argument("--verify", default="", help="วิธีตรวจสอบ/หลักฐาน (เช่น path log)")
    p.add_argument("--list", nargs="?", const="", default=None,
                   help="แสดงรายการล่าสุด (optional: คำค้น)")
    p.add_argument("--dry-run", action="store_true",
                   help="แสดงฟอร์แมตโดยไม่ส่งจริง/ไม่เขียน ledger")
    p.add_argument("--limit", type=int, default=10)
    args = p.parse_args()
    if args.list is not None:
        for e in list_alerts(args.list, args.limit):
            print(f"{e['code']} [{e['severity']}] {e['ts']} {e['summary']}"
                  + (f" — ยังไม่ส่ง (ledger only)" if not e.get("sent") else ""))
        return 0
    if not args.summary:
        p.error("--summary จำเป็น (หรือใช้ --list เพื่อดูรายการ)")
    if args.dry_run:
        code = make_code(args.type)
        steps = CHECKLISTS.get(args.type.upper())
        text = format_alert(args.severity, code, args.summary, args.details, args.verify)
        if steps:
            text += "\n\n📋 <b>ขั้นตอนกู้คืน:</b>\n" + "\n".join(steps)
        print(text)
        print(f"\n[alerting] DRY-RUN (ไม่ส่ง ไม่เขียน ledger) — รหัสตัวอย่าง: {code}")
        return 0
    send_alert(args.severity, args.type, args.summary, args.details, args.verify)
    return 0


if __name__ == "__main__":
    sys.exit(cli())
