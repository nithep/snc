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

SEVERITY_ICON = {"CRITICAL": "🚨", "WARNING": "⚠️", "INFO": "ℹ️", "TEST": "🧪",
                "RECOVERY": "💚"}

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
    """Format every alert as status, checks/cause, and next menu."""
    sev = severity.upper()
    icon = SEVERITY_ICON.get(sev, "🔔")
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = [
        f"{icon} <b>ระบบ SNC พบความผิดปกติ</b>",
        f"สถานะรวม: <b>{sev}</b>",
        f"เวลา: {now}",
        f"รหัส: <code>{code}</code>",
        "",
        "รายการตรวจสอบ:",
        f"❌ Service ที่เกี่ยวข้อง: {summary}",
    ]
    if details:
        lines.append(f"\nสาเหตุที่ตรวจพบ:\n{details}")
    if verify:
        lines.append(f"\nหลักฐาน/วิธีตรวจสอบ:\n{verify}")
    lines.append("\nเมนูถัดไป: /health | /cloudrun | /logs | /uptime")
    return "\n".join(lines)


def format_recovery(code: str, alert_type: str = "", recovered_from: str = "",
                    details: str = "", verify: str = "", downtime: str = "") -> str:
    """ข้อความ RECOVERY — แยกชัดเจนจาก alert ว่าระบบกลับมาปกติแล้ว"""
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = [
        "💚 <b>ระบบ SNC กลับมาปกติแล้ว</b>",
        "สถานะรวม: <b>HEALTHY</b>",
        f"เวลา: {now}",
        f"รหัส: <code>{code}</code>",
        "",
    ]
    if recovered_from:
        src = f"กู้คืนจาก: <code>{recovered_from}</code>"
        if alert_type:
            src += f" ({alert_type})"
        lines.append(src)
    if downtime:
        lines.append(f"ระยะเวลาผิดปกติ: {downtime}")
    if details:
        lines.append(f"\nรายละเอียด: {details}")
    if verify:
        lines.append(f"\nตรวจสอบ: {verify}")
    lines.append("\nเมนูถัดไป: /health | /status")
    return "\n".join(lines)


def append_ledger(entry: dict) -> None:
    """เขียนหลักฐานการแจ้ง (JSON 1 บรรทัด/alert) — ค้นด้วย grep / list_alerts()"""
    try:
        os.makedirs(os.path.dirname(LEDGER), exist_ok=True)
        with open(LEDGER, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except OSError as e:
        print(f"[alerting] เขียน ledger ล้มเหลว: {e}", file=sys.stderr)


def recent_same_type(alert_type: str, minutes: int) -> bool:
    """มี alert type เดียวกันใน ledger ภายใน N นาทีล่าสุดหรือไม่ (ใช้ทำ dedupe)"""
    if not os.path.isfile(LEDGER) or minutes <= 0:
        return False
    cutoff = datetime.datetime.now() - datetime.timedelta(minutes=minutes)
    atype = (alert_type or "").upper()
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
                if e.get("type", "").upper() != atype or e.get("deduped"):
                    continue
                try:
                    ts = datetime.datetime.strptime(e.get("ts", ""), "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    continue
                if ts >= cutoff:
                    return True
    except OSError:
        pass
    return False


def send_recovery(alert_type: str = "", recovered_from: str = "",
                  details: str = "", verify: str = "", downtime: str = "") -> str:
    """ส่งข้อความ RECOVERY (ระบบกลับมาปกติ) + บันทึก ledger → คืนรหัส SNC-AL-RECOVERY-..."""
    code = make_code("RECOVERY")
    atype = (alert_type or "ALERT").upper()
    text = format_recovery(code, atype, recovered_from, details, verify, downtime)
    ok = send_telegram(text)
    append_ledger({
        "code": code, "severity": "INFO", "type": "RECOVERY",
        "ts": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "summary": f"ระบบกลับมาปกติ ({atype})",
        "recovered_type": atype, "recovered_from": recovered_from,
        "downtime": downtime, "details": details, "verify": verify,
        "sent": ok,
    })
    print(f"[alerting] {code} type=RECOVERY recovered={atype} "
          f"telegram={'OK' if ok else 'SKIP'} ledger={LEDGER}")
    return code


def pending_incidents() -> dict:
    """เหตุการณ์ที่ยังไม่มี RECOVERY ตามหลัง — dict {type: alert_entry ล่าสุด}

    state มาจาก ledger ทั้งหมด (ไม่ต้องมีไฟล์ state แยก):
    type ใดถือว่ายังไม่ปิด ถ้า alert ล่าสุดของ type นั้นใหม่กว่า RECOVERY ล่าสุด
    """
    if not os.path.isfile(LEDGER):
        return {}
    last_alert = {}
    last_recovery = {}
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
                atype = (e.get("type") or "").upper()
                if atype == "RECOVERY":
                    rf = (e.get("recovered_type") or "").upper()
                    if rf:
                        last_recovery[rf] = e
                elif atype:
                    last_alert[atype] = e
    except OSError:
        return {}
    return {
        t: e for t, e in last_alert.items()
        if t not in last_recovery or e.get("ts", "") > (last_recovery[t].get("ts") or "")
    }


def check_auto_recovery(health_url: str) -> int:
    """cron helper: ถ้า /health กลับมา healthy แต่มี incident ค้าง → ส่ง RECOVERY
    คืนจำนวน recovery ที่ส่ง (cron-safe: exit 0 เสมอ)"""
    import urllib.parse
    import urllib.request

    try:
        req = urllib.request.Request(
            health_url, headers={"User-Agent": "SNC-Recovery-Check/1.0"})
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read().decode("utf-8"))
        healthy = str(data.get("status", "")).lower() in ("healthy", "ok")
    except Exception as e:
        print(f"[alerting] recovery-check: health ไม่พร้อม ({e}) — ไม่ส่ง RECOVERY")
        return 0
    if not healthy:
        print("[alerting] recovery-check: ระบบยังไม่ healthy — ไม่ส่ง RECOVERY")
        return 0

    incidents = pending_incidents()
    if not incidents:
        return 0
    now = datetime.datetime.now()
    sent = 0
    for atype, entry in sorted(incidents.items()):
        downtime = ""
        try:
            t0 = datetime.datetime.strptime(entry.get("ts", ""), "%Y-%m-%d %H:%M:%S")
            mins = int((now - t0).total_seconds() // 60)
            downtime = f"~{mins} นาที" if mins >= 1 else "<1 นาที"
        except ValueError:
            pass
        code = send_recovery(atype, recovered_from=entry.get("code", ""),
                             downtime=downtime, details=entry.get("summary", ""))
        print(f"[alerting] RECOVERY สำหรับ {atype} → {code}")
        sent += 1
    return sent


def send_alert(severity: str, alert_type: str, summary: str,
               details: str = "", verify: str = "",
               dedupe_minutes: int = 0) -> str:
    """ส่ง alert มาตรฐาน + บันทึก ledger → คืนรหัสอ้างอิง (SNC-AL-...)

    dedupe_minutes > 0: ถ้ามี alert type เดียวกันใน N นาทีล่าสุด → ไม่ส่ง Telegram
    ซ้ำ (ยังบันทึก ledger โดยมี deduped: true เพื่อให้ RECOVERY รู้ว่ามีเหตุการณ์)
    """
    code = make_code(alert_type)
    atype = (alert_type or "ALERT").upper()
    steps = CHECKLISTS.get(atype)
    text = format_alert(severity, code, summary, details, verify)
    if steps:
        text += "\n\n📋 <b>ขั้นตอนกู้คืน:</b>\n" + "\n".join(steps)
    deduped = recent_same_type(atype, dedupe_minutes)
    ok = False if deduped else send_telegram(text)
    append_ledger({
        "code": code, "severity": severity.upper(),
        "type": atype,
        "ts": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "summary": summary, "details": details, "verify": verify,
        "checklist": steps,
        "sent": ok, "deduped": deduped,
    })
    print(f"[alerting] {code} severity={severity.upper()} type={atype} "
          f"telegram={'DEDUPED' if deduped else ('OK' if ok else 'SKIP')} ledger={LEDGER}")
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
    p.add_argument("--dedupe-minutes", type=int, default=0,
                   help="ไม่ส่ง Telegram ซ้ำถ้ามี alert type เดียวกันใน N นาทีล่าสุด")
    p.add_argument("--recovery-from", default="",
                   help="ส่งข้อความ RECOVERY โดยอ้างรหัส alert เดิม (เช่น SNC-AL-TUNNEL-...) — ใช้ร่วม --type")
    p.add_argument("--downtime", default="", help="ระยะเวลาผิดปกติ เช่น '~45 นาที' (ใช้กับ --recovery-from)")
    p.add_argument("--recovery-auto", action="store_true",
                   help="cron helper: ถ้า /health healthy และมี incident ค้างใน ledger → ส่ง RECOVERY อัตโนมัติ")
    p.add_argument("--health-url", default="http://localhost:8000/health",
                   help="URL ตรวจสุขภาพสำหรับ --recovery-auto")
    args = p.parse_args()
    if args.recovery_auto:
        sent = check_auto_recovery(args.health_url)
        print(f"[alerting] recovery-auto: ส่ง {sent} ข้อความ")
        return 0
    if args.list is not None:
        for e in list_alerts(args.list, args.limit):
            print(f"{e['code']} [{e['severity']}] {e['ts']} {e['summary']}"
                  + (f" — ยังไม่ส่ง (ledger only)" if not e.get("sent") else ""))
        return 0
    if args.recovery_from:
        code = send_recovery(args.type, recovered_from=args.recovery_from,
                             details=args.details, verify=args.verify,
                             downtime=args.downtime)
        print(f"[alerting] RECOVERY → {code}")
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
    send_alert(args.severity, args.type, args.summary, args.details, args.verify,
               dedupe_minutes=args.dedupe_minutes)
    return 0


if __name__ == "__main__":
    sys.exit(cli())
