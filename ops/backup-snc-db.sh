#!/usr/bin/env bash
# ============================================================================
# backup-snc-db.sh — Backup ฐานข้อมูล SNC (SQLite) บน Raspberry Pi 4
# ----------------------------------------------------------------------------
# - ใช้ sqlite3 .backup (ปลอดภัยต่อ WAL ระหว่างการเขียน) ไม่ใช่ cp ตรง ๆ
# - เก็บไฟล์ .bak นาน 14 วัน แล้วลบอัตโนมัติ
# - รันด้วย cron ทุกวัน 03:00 (ติดตั้งอัตโนมัติได้: --install)
#
# วิธีใช้:
#   ./ops/backup-snc-db.sh                # backup ครั้งเดียว
#   ./ops/backup-snc-db.sh --install      # ติดตั้ง cron บน Pi (ทุกวัน 03:00)
#   ./ops/backup-snc-db.sh --pi           # รันบน Pi โดยตรง
# ============================================================================
set -euo pipefail

DB="/home/ecs-agent/nithep/snc/api/nurse_call_events.db"
BACKUP_DIR="/home/ecs-agent/nithep/snc/backups"
RETENTION_DAYS=14

# --- Flags ---
PI_MODE=0
INSTALL_MODE=0
for arg in "$@"; do
  case "$arg" in
    --pi)      PI_MODE=1 ;;
    --install) INSTALL_MODE=1 ;;
    -h|--help) grep -E '^#' "$0" | sed 's/^# \{0,1\}//' | head -25; exit 0 ;;
    *) echo "unknown option: $arg" >&2; exit 1 ;;
  esac
done

run_on_pi() {
  # ถ้าเรียกจากเครื่อง local → ส่งไปรันบน Pi ผ่าน ssh
  if [ "$PI_MODE" -eq 1 ]; then
    # เรียกตัวเองในโหมด --pi เพื่อให้รันบน Pi
    ssh -o ConnectTimeout=8 pi4 "bash -s" < "$0" --pi "$@"
  fi
}

if [ "$PI_MODE" -eq 1 ] && [ -z "${RUNNING_ON_PI:-}" ]; then
  # โหมด --pi: รันจริงบน Pi (ตัวสคริปต์ถูกส่งมาแล้ว)
  export RUNNING_ON_PI=1
fi

if [ "$INSTALL_MODE" -eq 1 ]; then
  # ติดตั้ง cron บน Pi
  CRON_LINE="0 3 * * * /home/ecs-agent/nithep/snc/backup-snc-db.sh --pi >/dev/null 2>&1"
  if [ "$PI_MODE" -eq 1 ]; then
    ( crontab -l 2>/dev/null | grep -v 'backup-snc-db' ; echo "$CRON_LINE" ) | crontab -
    echo "cron installed: $CRON_LINE"
    crontab -l | grep backup-snc-db
  else
    # ต้อง deploy สคริปต์ขึ้น Pi ก่อน แล้วติดตั้ง cron
    echo "ติดตั้งสคริปต์ขึ้น Pi..."
    scp -o ConnectTimeout=8 "$0" pi4:/home/ecs-agent/nithep/snc/backup-snc-db.sh
    ssh -o ConnectTimeout=8 pi4 "chmod +x /home/ecs-agent/nithep/snc/backup-snc-db.sh"
    # รันติดตั้ง cron ด้วยตัวเองบน Pi
    ssh -o ConnectTimeout=8 pi4 "/home/ecs-agent/nithep/snc/backup-snc-db.sh --install --pi"
  fi
  exit 0
fi

# --- รัน backup จริง (บน Pi) ---
echo "[SNC Backup] $(date '+%Y-%m-%d %H:%M:%S')"

if [ ! -f "$DB" ]; then
  echo "[ERROR] ไม่พบ DB: $DB" >&2
  exit 1
fi

mkdir -p "$BACKUP_DIR"
TS="$(date +%Y%m%d_%H%M%S)"
OUT="$BACKUP_DIR/nurse_call_events_${TS}.db.bak"

# ใช้ sqlite3 .backup (รองรับ WAL mode ปลอดภัย) ถ้ามี ไม่มีก็ cp
if command -v sqlite3 >/dev/null 2>&1; then
  sqlite3 "$DB" ".backup '$OUT'"
else
  cp "$DB" "$OUT"
fi

chmod 600 "$OUT"
SIZE=$(stat -c%s "$OUT" 2>/dev/null || echo '?')
echo "[OK] Backup: $OUT ($SIZE bytes)"

# ลบของเก่าเกิน retention
find "$BACKUP_DIR" -name 'nurse_call_events_*.db.bak' -mtime +$RETENTION_DAYS -delete

echo "[OK] Backup เสร็จสมบูรณ์"
ls -lh "$BACKUP_DIR" | tail -5
