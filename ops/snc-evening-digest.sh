#!/usr/bin/env bash
# snc-evening-digest.sh — สรุปสถานะ + ทิปการใช้งานประจำวัน ทุกเย็น → Telegram (@snc2569_bot)
#
# cron (บน Pi):  0 19 * * * /home/ecs-agent/snc/ops/snc-evening-digest.sh
# อ่าน token/chat_id ผ่าน snc_telegram_agent.py (reuse env-loading เดิม) — ถ้าไม่มี key → SKIP เงียบ ๆ
set -uo pipefail

SNC_ROOT="$(cd "$(dirname "$0")" && pwd)"
AGENT="$SNC_ROOT/snc_telegram_agent.py"

if [ ! -f "$AGENT" ]; then
  echo "[snc-evening-digest] ไม่พบ snc_telegram_agent.py" >&2
  exit 1
fi

python3 - "$AGENT" <<'PY'
import importlib.util, sys, os, datetime

spec = importlib.util.spec_from_file_location("agent", sys.argv[1])
a = importlib.util.module_from_spec(spec)
spec.loader.exec_module(a)

chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
if not a.TOKEN or not chat_id:
    print("[snc-evening-digest] SKIP: ยังไม่ตั้ง TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID")
    sys.exit(0)

now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
tips = [
    "PC Room Manager แจ้ง \"Authenticate Failed!!\" → ชี้ไปที่ Pi พอร์ต 2323 ไม่ใช่ตู้ :23",
    "ตู้ PBX ตอบ \"Not have free PABX telnet port\" → power-cycle ตู้ ~15 วินาที แล้ว handshake จะผ่าน 100%",
    "สาย SMDR หลุดทุก ~60 วิ → listener เก่าไม่มี heartbeat ให้อัปเกรด snc_pbx_listener.py",
    "ห้องขึ้นผิด (0400 แทน 0401) → ต้องใช้ station_ext สำหรับ e. events (ไม่ใช่ event_code)",
    "เช็ก SLA ผ่าน /kpi — เป้า Ack ≤30s · Resolution ≤180s · compliance ≥98%",
    "KPI ปนข้อมูล legacy → lean-snc-data.sh --confirm --purge-legacy แล้ว /kpi ใหม่",
    "หน้า / โชว์ 404/blank → ต้อง deploy app/index.html ขึ้นเป็นหน้าแรก (ไม่ใช่ dashboard-status.html)",
]
tip = tips[int(datetime.date.today().strftime("%j")) % len(tips)]

lines = [f"🌙 <b>SNC สรุปประจำเย็น</b> ({now})"]
try:
    lines.append(a.kpi_reply())
except Exception as e:
    lines.append(f"KPI อ่านไม่ได้: {e}")
try:
    lines.append(a.rooms_reply())
except Exception as e:
    lines.append(f"rooms อ่านไม่ได้: {e}")
lines.append("")
lines.append(f"💡 <b>ทิปวันนี้:</b> {tip}")

try:
    a.send(chat_id, "\n".join(lines))
    print("[snc-evening-digest] ส่งสำเร็จ ✅")
except Exception as e:
    print(f"[snc-evening-digest] ส่ง FAILED: {e}")
PY
