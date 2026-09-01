#!/bin/bash
# ============================================================================
# ops/ws-tunnel-cron.sh — ตรวจ WS tunnel ผ่าน cron + แจ้ง Telegram เมื่อตายซ้ำ
# ----------------------------------------------------------------------------
# รัน ops/ws-tunnel-test.py --check-only (ไม่ยิง event)
#   - สำเร็จ     → ล้าง counter
#   - ล้มเหลว    → นับ consecutive fail ใน state file
#                  ถ้า fail 2 ครั้งติด (≈30 นาที) → ส่ง Telegram ผ่าน notify-telegram.sh
#                  แล้วรีเซ็ต counter (กันสแปม alert ทุก 15 นาที)
#
# วิธีใช้ (cron ของ ecs-agent):
#   */15 * * * * /home/ecs-agent/snc/ops/ws-tunnel-cron.sh
# ============================================================================
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SNC_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
LOG_DIR="$SNC_ROOT/logs"
LOG="$LOG_DIR/ws-tunnel-check.log"
STATE="$LOG_DIR/.ws-tunnel-fail-count"
ALERT_AFTER=2   # จำนวนครั้งล้มเหลวติดต่อกันก่อนแจ้งเตือน

mkdir -p "$LOG_DIR"

if /usr/bin/python3 "$SCRIPT_DIR/ws-tunnel-test.py" --check-only >> "$LOG" 2>&1; then
  [ -f "$STATE" ] && rm -f "$STATE"
  exit 0
fi

# ── ล้มเหลว: นับ + แจ้งเตือนเมื่อถึงเกณฑ์ ──
N=1
[ -f "$STATE" ] && N=$(( $(cat "$STATE") + 1 ))
echo "$N" > "$STATE"
echo "$(date '+%Y-%m-%d %H:%M:%S') [ws-tunnel-cron] FAIL ครั้งที่ $N ติดต่อกัน" >> "$LOG"

if [ "$N" -ge "$ALERT_AFTER" ]; then
  echo "$(date '+%Y-%m-%d %H:%M:%S') [ws-tunnel-cron] ส่ง Telegram alert (ผ่าน ops/alerting.py)..." >> "$LOG"
  # alerting.py สร้างรหัส SNC-AL-TUNNEL-... + เขียนหลักฐานใน logs/alerts.log อัตโนมัติ
  /usr/bin/python3 "$SCRIPT_DIR/alerting.py" \
    --severity CRITICAL --type TUNNEL \
    --summary "WS Tunnel ตาย ${N} ครั้งติดต่อกัน" \
    --details "wss://snc.nithep.com/ws/nurse-station ล้มเหลว ${N} ครั้ง (cron ทุก 15 นาที)" \
    --verify "ssh pi4 tail -20 logs/ws-tunnel-check.log" \
    --dedupe-minutes 30 >> "$LOG" 2>&1   # กันซ้ำซ้อนกับ GCP uptime alert
  echo "0" > "$STATE"   # รีเซ็ต หลังแจ้งแล้วต้อง fail ใหม่ 2 ครั้งถึงแจ้งอีก
fi
exit 1
