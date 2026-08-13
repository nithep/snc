#!/usr/bin/env bash
# ============================================================================
# burnin-reminder.sh — เตือนสถานะ Burn-in 48 ชม. + คำเตือน "ห้ามแตะต้อง Pi4"
# ----------------------------------------------------------------------------
# ออกแบบให้รันด้วย cron ทุก 1 ชม. (ติดตั้งอัตโนมัติ: --install):
#   - แจ้งสถานะกลางทางทุก 6 ชม. พร้อมคำเตือนห้ามแตะต้องระบบ
#   - แจ้ง "ครบ 48 ชม. = Burn-in เสร็จ" เพียงครั้งเดียวเมื่อถึงกำหนด
#   - ไม่แตะต้อง services / DB / config ใด ๆ (อ่านอย่างเดียว ปลอดภัย 100%)
#
# วิธีใช้:
#   ./burnin-reminder.sh               # รันแบบ cron (default)
#   ./burnin-reminder.sh --check       # ดูสถานะปัจจุบัน (ไม่อัปเดต log)
#   ./burnin-reminder.sh --install     # ติดตั้ง cron (ทุกชั่วโมง นาทีที่ 7)
#   ./burnin-reminder.sh --simulate    # จำลองผลลัพธ์โดยไม่เขียนอะไรเลย
#   ./burnin-reminder.sh --help
#
# Log: /home/ecs-agent/nithep/snc/burnin_reminder.log (บน Pi)
# ============================================================================
set -uo pipefail

BASE="${SNC_BASE:-/home/ecs-agent/nithep/snc}"
LOG_FILE="${BURNIN_LOG:-$BASE/burnin.log}"
REMINDER_LOG="${BURNIN_REMINDER_LOG:-$BASE/burnin_reminder.log}"
COMPLETE_MARKER="${BURNIN_COMPLETE_MARKER:-$BASE/.burnin_complete}"
LAST_STATUS_FILE="${BURNIN_LAST_STATUS_FILE:-$BASE/.burnin_last_status}"

TARGET_HOURS=48          # ระยะเวลาทั้งหมด (ชั่วโมง)
STATUS_EVERY_HOURS=6     # ความถี่ของสถานะกลางทาง (ชั่วโมง)

log() { echo "$(date '+%Y-%m-%d %H:%M:%S') $*" >> "$REMINDER_LOG"; }

# ---------------------------------------------------------------------------
# คำเตือนห้ามแตะต้อง (แสดงในทุก reminder)
# ---------------------------------------------------------------------------
WARN_DO_NOT=(
"⛔ คำเตือน ระหว่าง Burn-in 48 ชม. ห้ามทำสิ่งต่อไปนี้กับ Pi 4:"
"  1. ห้าม restart/stop services (snc-backend, snc-pbx-listener)"
"  2. ห้าม reboot / ปิด-เปิดเครื่อง Pi 4"
"  3. ห้าม deploy / scp ไฟล์โค้ดหรือ config ใหม่ขึ้น Pi"
"  4. ห้ามปิด-เปิดตู้ Phonik PBX (power cycle) เว้นจำเป็นจริง ๆ"
"  5. ห้ามรันงานหนัก (apt upgrade, stress test, ขนไฟล์ใหญ่)"
"  6. ห้ามถอดสาย LAN / สายไฟ / ย้ายตำแหน่ง Pi"
"  7. ห้ามแก้ .env / เปลี่ยน API key / เปลี่ยน config ใด ๆ"
"  8. ห้ามลบ-ย้าย burnin.log หรือ nurse_call_events.db"
"✅ อนุญาต: เปิด dashboard ดูผล, อ่าน log ได้ตามปกติ (read-only เท่านั้น)"
"   ตรวจผลด้วย: ssh pi4 '/home/ecs-agent/nithep/snc/burnin-monitor.sh --report'"
)

print_warnings() {
  local i
  for i in "${WARN_DO_NOT[@]}"; do echo "$i"; done
}

usage() {
  grep -E '^#' "$0" | sed 's/^# \{0,1\}//' | head -25
  exit 0
}

# ---------------------------------------------------------------------------
# ตรวจหาเวลาที่ burn-in เริ่ม (จากบรรทัดแรกของ burnin.log)
# ---------------------------------------------------------------------------
get_start_epoch() {
  [ -f "$LOG_FILE" ] || { echo "ERROR: ไม่พบ $LOG_FILE" >&2; return 1; }
  local start_str
  start_str=$(head -1 "$LOG_FILE" | cut -c1-19)
  date -d "$start_str" +%s 2>/dev/null || { echo "ERROR: อ่านเวลเริ่มไม่ได้: $start_str" >&2; return 1; }
}

# ---------------------------------------------------------------------------
# โหมดคำสั่ง
# ---------------------------------------------------------------------------
MODE="cron"
for arg in "$@"; do
  case "$arg" in
    --check)    MODE="check" ;;
    --install)  MODE="install" ;;
    --simulate) MODE="simulate" ;;
    -h|--help)  usage ;;
    *) echo "unknown option: $arg" >&2; exit 1 ;;
  esac
done

# ---------------------------------------------------------------------------
# --install: ลง cron line (ทุกชั่วโมง นาทีที่ 7 หลีกเลี่ยงชนกับงานอื่น)
# ---------------------------------------------------------------------------
if [ "$MODE" = "install" ]; then
  CRON_LINE="7 * * * * $BASE/burnin-reminder.sh >/dev/null 2>&1"
  if crontab -l 2>/dev/null | grep -Fq "$BASE/burnin-reminder.sh"; then
    echo "cron ติดตั้งอยู่แล้ว (ข้าม): $CRON_LINE"
  else
    ( crontab -l 2>/dev/null; echo "$CRON_LINE" ) | crontab -
    echo "ติดตั้ง cron แล้ว: $CRON_LINE"
  fi
  echo "--- crontab ปัจจุบัน ---"
  crontab -l 2>/dev/null | grep -E 'burnin|backup|watchdog'
  exit 0
fi

# ---------------------------------------------------------------------------
# คำนวณสถานะ
# ---------------------------------------------------------------------------
START_EPOCH=$(get_start_epoch) || exit 1
NOW_EPOCH=$(date +%s)
ELAPSED=$(awk -v s="$START_EPOCH" -v n="$NOW_EPOCH" 'BEGIN{printf "%.2f", (n-s)/3600}')
REMAINING=$(awk -v e="$ELAPSED" -v t="$TARGET_HOURS" 'BEGIN{r=t-e; if(r<0)r=0; printf "%.1f", r}')
PCT=$(awk -v e="$ELAPSED" -v t="$TARGET_HOURS" 'BEGIN{printf "%d", (e*100)/t}')
BLOCK=$(awk -v e="$ELAPSED" -v s="$STATUS_EVERY_HOURS" 'BEGIN{printf "%d", int(e/s)}')
DONE=$(awk -v e="$ELAPSED" -v t="$TARGET_HOURS" 'BEGIN{print (e>=t)?"1":"0"}')
START_HUMAN=$(date -d "@$START_EPOCH" '+%Y-%m-%d %H:%M')
FINISH_HUMAN=$(date -d "@$((START_EPOCH + TARGET_HOURS*3600))" '+%Y-%m-%d %H:%M')

if [ "$MODE" = "check" ]; then
  echo "=== สถานะ Burn-in (read-only) ==="
  echo "เริ่ม: $START_HUMAN  |  ผ่านไป: ${ELAPSED} ชม. (${PCT}%)  |  เหลือ: ${REMAINING} ชม."
  echo "ครบกำหนด: $FINISH_HUMAN  ($TARGET_HOURS ชม.)"
  if [ "$DONE" = "1" ]; then
    echo ">> ✅ Burn-in ครบ 48 ชม. แล้ว — รัน 'burnin-monitor.sh --report' เพื่อดูผลสรุป"
  else
    echo ">> ยังไม่ครบ — ระบบอยู่ระหว่างทดสอบ รอตามกำหนด"
  fi
  echo
  print_warnings
  exit 0
fi

if [ "$MODE" = "simulate" ]; then
  echo "=== SIMULATE (ไม่เขียน log / ไม่สร้าง marker) ==="
  echo "เริ่ม: $START_HUMAN | ผ่านไป: ${ELAPSED} ชม. (${PCT}%) | เหลือ: ${REMAINING} ชม. | block=$BLOCK | done=$DONE"
  if [ "$DONE" = "1" ]; then
    echo ">> จะแจ้งเตือน: BURN-IN COMPLETE (ครบ 48 ชม.)"
  else
    echo ">> จะแจ้งเตือน: สถานะกลางทาง block=$BLOCK (ทุก ${STATUS_EVERY_HOURS} ชม.)"
  fi
  exit 0
fi

# ---------------------------------------------------------------------------
# MODE=cron — เขียน reminder จริง
# ---------------------------------------------------------------------------
if [ "$DONE" = "1" ]; then
  # ครบ 48 ชม. — แจ้งเตือนเพียงครั้งเดียว
  if [ ! -f "$COMPLETE_MARKER" ]; then
    {
      echo "=============================================================="
      echo "🎉 BURN-IN ครบ $TARGET_HOURS ชม. แล้ว ($FINISH_HUMAN)"
      echo "เริ่ม: $START_HUMAN | ผ่านไป: ${ELAPSED} ชม. | ครบกำหนด: $FINISH_HUMAN"
      echo "--- ตรวจผลสรุปสุดท้าย ---"
      "$BASE/burnin-monitor.sh" --report 2>/dev/null | head -30
      echo "=============================================================="
      echo "✅ ตั้งแต่นี้ระบบผ่าน Burn-in แล้ว — แตะต้อง Pi ได้ตามปกติ"
      echo "   ขั้นต่อไป: สรุปผล → นัดวันทดสอบหน้างาน → วางจำหน่าย"
    } >> "$REMINDER_LOG"
    log "BURN-IN COMPLETE (marker created)"
    : > "$COMPLETE_MARKER"
    echo "BURN-IN COMPLETE — แจ้งเตือนครบ 48 ชม. แล้ว (ดู $REMINDER_LOG)" >&2
  fi
  exit 0
fi

# ยังไม่ครบ — สถานะกลางทางทุก STATUS_EVERY_HOURS ชม. (block เดิมไม่ซ้ำ)
LAST_BLOCK=$(cat "$LAST_STATUS_FILE" 2>/dev/null || echo "-1")
if [ "$BLOCK" != "$LAST_BLOCK" ]; then
  {
    echo "=============================================================="
    echo "📌 สถานะ Burn-in กลางทาง: ผ่าน ${ELAPSED} ชม. จาก $TARGET_HOURS ชม. (${PCT}%)"
    echo "เริ่ม: $START_HUMAN | เหลืออีก: ${REMAINING} ชม. | ครบกำหนด: $FINISH_HUMAN"
    print_warnings
    echo "=============================================================="
  } >> "$REMINDER_LOG"
  echo "$BLOCK" > "$LAST_STATUS_FILE"
  echo "บันทึกสถานะกลางทาง block=$BLOCK (${ELAPSED} ชม. ผ่าน)" >&2
fi
exit 0
