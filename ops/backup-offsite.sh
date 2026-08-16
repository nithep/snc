#!/usr/bin/env bash
# ============================================================================
# backup-offsite.sh — Backup SNC DB บน Pi4 + ส่งสำเนาออกไปนอกเครื่อง (offsite)
# ----------------------------------------------------------------------------
# จุดประสงค์: แก้จุดอ่อน "backup อยู่เครื่องเดียวกับ Pi" (ถ้า Pi ตาย = ข้อมูลหาย)
# ทำงาน 2 ชั้น:
#   1. local backup (sqlite3 .backup, ปลอดภัย WAL) → $BACKUP_DIR
#   2. ส่งสำเนาขึ้น GCS bucket (offsite) + (optional) แจ้งเตือน Telegram
#
# วิธีใช้ (บน Pi4):
#   ./ops/backup-offsite.sh                  # backup local + push GCS
#   ./ops/backup-offsite.sh --install        # ติดตั้ง cron (ทุกวัน 03:05)
#   ./ops/backup-offsite.sh --no-offsite     # แค่ backup local (ไม่ push GCS)
#
# Config ผ่าน env (ค่า default ตั้งไว้):
#   SNC_DB_PATH        path ของ SQLite DB
#   BACKUP_DIR         dir เก็บ backup local
#   BACKUP_RETENTION_DAYS
#   GCS_BUCKET         bucket offsite (เช่น gs://snc-backup-nithep) — ว่าง = ข้าม
#   TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID  (optional แจ้งเตือน)
# ============================================================================
set -euo pipefail

DB_PATH="${SNC_DB_PATH:-/home/ecs-agent/snc/api/nurse_call_events.db}"
BACKUP_DIR="${BACKUP_DIR:-/home/ecs-agent/snc/backups}"
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-14}"
GCS_BUCKET="${GCS_BUCKET:-gs://snc-backup-nithep}"
NOTIFY_TELEGRAM="${NOTIFY_TELEGRAM:-0}"

INSTALL_MODE=0
OFFSITE=1
for arg in "$@"; do
  case "$arg" in
    --install)     INSTALL_MODE=1 ;;
    --no-offsite)  OFFSITE=0 ;;
    -h|--help)     grep -E '^#' "$0" | sed 's/^# \{0,1\}//' | head -30; exit 0 ;;
    *) echo "unknown option: $arg" >&2; exit 1 ;;
  esac
done

send_telegram() {
  [ "$NOTIFY_TELEGRAM" = "1" ] || return 0
  local msg="$1"
  [ -n "${TELEGRAM_BOT_TOKEN:-}" ] && [ -n "${TELEGRAM_CHAT_ID:-}" ] || return 0
  curl -s --max-time 10 -X POST \
    "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
    -d "chat_id=${TELEGRAM_CHAT_ID}" --data-urlencode "text=${msg}" >/dev/null 2>&1 || true
}

if [ "$INSTALL_MODE" -eq 1 ]; then
  CRON_LINE="0 5 * * * ${BACKUP_DIR%/*}/backup-offsite.sh >/dev/null 2>&1"
  ( crontab -l 2>/dev/null | grep -v 'backup-offsite' ; echo "$CRON_LINE" ) | crontab -
  echo "cron installed: $CRON_LINE"
  crontab -l | grep backup-offsite
  exit 0
fi

echo "[SNC Backup Offsite] $(date '+%Y-%m-%d %H:%M:%S')"

if [ ! -f "$DB_PATH" ]; then
  echo "[ERROR] ไม่พบ DB: $DB_PATH" >&2
  send_telegram "❌ SNC backup ล้มเหลว: ไม่พบ DB $DB_PATH"
  exit 1
fi

mkdir -p "$BACKUP_DIR"
TS="$(date +%Y%m%d_%H%M%S)"
OUT="$BACKUP_DIR/nurse_call_events_${TS}.db.bak"

# ── ชั้น 1: local backup ─────────────────────────────────────────────────────
if command -v sqlite3 >/dev/null 2>&1; then
  sqlite3 "$DB_PATH" ".backup '$OUT'"
else
  cp "$DB_PATH" "$OUT"
fi
chmod 600 "$OUT"
SIZE=$(stat -c%s "$OUT" 2>/dev/null || echo '?')
echo "[1/2] Local backup: $OUT ($SIZE bytes)"

# ── ชั้น 2: offsite → GCS ────────────────────────────────────────────────────
if [ "$OFFSITE" -eq 1 ] && [ -n "${GCS_BUCKET:-}" ]; then
  if command -v gsutil >/dev/null 2>&1; then
    echo "[2/2] Push ไป GCS: ${GCS_BUCKET%/}/"
    gsutil -q cp "$OUT" "${GCS_BUCKET%/}/" \
      && echo "  ✅ ส่งขึ้น GCS สำเร็จ" \
      || { echo "  ⚠️ GCS push ล้มเหลว (เก็บ local ไว้ก่อน)"; send_telegram "⚠️ SNC GCS offsite push ล้มเหลว"; }
  else
    echo "[2/2] ⚠️ ไม่พบ gsutil — ข้าม offsite (เก็บ local เท่านั้น)"
  fi
else
  echo "[2/2] ข้าม offsite (--no-offsite หรือไม่มี GCS_BUCKET)"
fi

# ── ลบของเก่าเกิน retention (ทั้ง local) ────────────────────────────────────
find "$BACKUP_DIR" -name 'nurse_call_events_*.db.bak' -mtime +$RETENTION_DAYS -delete
echo "[OK] Backup เสร็จสมบูรณ์"
ls -lh "$BACKUP_DIR" | tail -5

send_telegram "✅ SNC backup เรียบร้อย ($(basename "$OUT"), $SIZE bytes)"
exit 0