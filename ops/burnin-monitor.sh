#!/usr/bin/env bash
# ============================================================================
# burnin-monitor.sh — Burn-in Test Monitor 48 ชม. สำหรับ SNC System
# ----------------------------------------------------------------------------
# ตรวจระบบอย่างต่อเนื่อง และบันทึก log เพื่อวิเคราะห์ความเสถียร:
#   - Health ของ backend (/health) และ response time
#   - สถานะ services (snc-backend, snc-pbx-listener)
#   - จำนวนเหตุการณ์ใน DB + จำนวนสายค้าง (SLA ไม่ควรสะสมเกิน)
#   - พื้นที่ disk และหน่วยความจำ
#   - ตรวจจับ WS disconnect/reconnect ผ่านจำนวน client ที่ log backend
#
# วิธีใช้:
#   ./burnin-monitor.sh                  # รัน monitor แบบ interactive (Ctrl+C หยุด)
#   ./burnin-monitor.sh --background 48  # รันเป็น background 48 ชม. (nohup) — ใช้กับ Pi
#   ./burnin-monitor.sh --report         # สรุปผลจาก log ที่มีอยู่
#
# Log: /home/ecs-agent/snc/burnin.log (บน Pi)
# ============================================================================
set -uo pipefail

# --- Config ---
LOG_FILE="/home/ecs-agent/snc/burnin.log"
DB="/home/ecs-agent/snc/api/nurse_call_events.db"
HEALTH_URL="http://localhost:8000/health"
INTERVAL=60          # วินาทีระหว่างการตรวจแต่ละรอบ
DEFAULT_HOURS=48

BACKGROUND=0
REPORT=0
HOURS=$DEFAULT_HOURS
for arg in "$@"; do
  case "$arg" in
    --background) BACKGROUND=1 ;;
    --report)     REPORT=1 ;;
    --hours=*)    HOURS="${arg#--hours=}" ;;
    -h|--help)    grep -E '^#' "$0" | sed 's/^# \{0,1\}//' | head -30; exit 0 ;;
    *) echo "unknown option: $arg" >&2; exit 1 ;;
  esac
done

log() { echo "$(date '+%Y-%m-%d %H:%M:%S') $*" >> "$LOG_FILE"; }

if [ "$REPORT" -eq 1 ]; then
  echo "=== Burn-in Report (จาก $LOG_FILE) ==="
  if [ ! -f "$LOG_FILE" ]; then echo "ยังไม่มี log" ; exit 0; fi
  echo "รอบทั้งหมด: $(grep -c '^2026' "$LOG_FILE") บรรทัดตรวจสอบ"
  echo "-- จำนวนรอบที่ไม่ healthy --"
  grep -E 'FAIL|ERROR|DOWN' "$LOG_FILE" | head -20
  echo "-- สรุป KPI ในช่วงที่ผ่านมา --"
  grep -E 'OK' "$LOG_FILE" | tail -10
  echo "-- ระยะเวลารัน --"
  head -1 "$LOG_FILE" && tail -1 "$LOG_FILE"
  exit 0
fi

if [ "$BACKGROUND" -eq 1 ]; then
  # รัน background ผ่าน nohup
  if [ -f "/tmp/burnin.pid" ] && kill -0 "$(cat /tmp/burnin.pid 2>/dev/null)" 2>/dev/null; then
    echo "Burn-in กำลังรันอยู่แล้ว (PID $(cat /tmp/burnin.pid))"
    exit 0
  fi
  nohup bash "$0" --hours="$HOURS" > /dev/null 2>&1 &
  echo $! > /tmp/burnin.pid
  echo "Burn-in monitor เริ่มรันแล้ว (PID $!) — log: $LOG_FILE"
  echo "ดูผล: ./burnin-monitor.sh --report  |  หยุด: kill \$(cat /tmp/burnin.pid)"
  exit 0
fi

# --- รัน monitor จริง ---
START=$(date +%s)
END=$(( START + HOURS * 3600 ))
log "=== Burn-in เริ่ม (${HOURS} ชม.) ==="
log "Config: interval=${INTERVAL}s, db=${DB}"

ROUND=0
while [ "$(date +%s)" -lt "$END" ]; do
  ROUND=$(( ROUND + 1 ))

  # 1) Health + response time
  T0=$(date +%s%N)
  HEALTH=$(curl -s --max-time 8 "$HEALTH_URL" 2>/dev/null || echo 'DOWN')
  T1=$(date +%s%N)
  MS=$(( (T1 - T0) / 1000000 ))
  if echo "$HEALTH" | grep -q '"status".*healthy'; then
    log "OK health ${MS}ms round=${ROUND}"
  else
    log "FAIL health response=${HEALTH:0:80} ms=${MS} round=${ROUND}"
  fi

  # 2) Services
  SVCS=$(systemctl is-active snc-backend.service snc-pbx-listener.service 2>/dev/null | paste -sd ',' -)
  log "INFO services=${SVCS} round=${ROUND}"

  # 3) DB stats
  if [ -f "$DB" ]; then
    EVENTS=$(python3 -c "import sqlite3; c=sqlite3.connect('$DB'); print(c.execute('SELECT COUNT(*) FROM nurse_call_events').fetchone()[0])" 2>/dev/null || echo '?')
    OPEN=$(python3 -c "import sqlite3; c=sqlite3.connect('$DB'); print(c.execute(\"SELECT COUNT(*) FROM nurse_call_events WHERE status IN ('active','acknowledged')\").fetchone()[0])" 2>/dev/null || echo '?')
    log "INFO db_events=${EVENTS} open=${OPEN} round=${ROUND}"
  else
    log "FAIL db_missing round=${ROUND}"
  fi

  # 4) disk + mem
  DISK=$(df -h /home 2>/dev/null | awk 'NR==2{print $5}')
  MEM=$(free -m 2>/dev/null | awk '/Mem/{print $3"/"$2"MB"}')
  log "INFO disk=${DISK} mem=${MEM} round=${ROUND}"

  # 5) WS active clients (ดูจาก log ของ backend)
  WSC=$(sudo journalctl -u snc-backend.service --since "$INTERVAL seconds ago" --no-pager 2>/dev/null | grep -c 'Client connected' || true)
  [ "$WSC" -gt 0 ] && log "INFO ws_connects=${WSC} round=${ROUND}"

  sleep "$INTERVAL"
done

log "=== Burn-in สิ้นสุด (${ROUND} รอบ) ==="
log "RESULT: ดูสรุปด้วย ./burnin-monitor.sh --report"
