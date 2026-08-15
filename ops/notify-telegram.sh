#!/usr/bin/env bash
# notify-telegram.sh — ส่งข้อความแจ้งเตือนไปที่ Telegram bot (เช่น @snc2569_bot)
#
# วิธีใช้:
#   ./notify-telegram.sh "ข้อความที่จะส่ง"
#
# อ่าน TELEGRAM_BOT_TOKEN + TELEGRAM_CHAT_ID จาก (อันแรกที่เจอ):
#   1) environment variables (override) 2) <SNC_ROOT>/.env
#   3) <SNC_ROOT>/backend/.env 4) <SNC_ROOT>/pbx-connector/.env 5) <SNC_ROOT>/api/.env
# ถ้ายังไม่ตั้ง key → ข้ามเงียบ ๆ (exit 0) ระบบไม่พัง (graceful like Gemini service)
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# root ของโปรเจกต์ = parent ของ ops/ (5-Core) หรือ dir ของสคริปต์เอง (legacy)
SNC_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

load_env() {
  local f="$1" k v
  [ -f "$f" ] || return 0
  while IFS='=' read -r k v; do
    [ -z "$k" ] && continue
    case "$k" in \#*) continue ;; esac
    k="${k//[$'\r']/}"   # strip CR (กัน Windows line endings)
    v="${v//[$'\r']/}"
    case "$k" in
      TELEGRAM_BOT_TOKEN|TELEGRAM_CHAT_ID)
        if [ -z "${!k:-}" ]; then export "$k=$v"; fi ;;
    esac
  done < "$f"
}

# ลองทั้ง 2 แบบ: สคริปต์ใน ops/ (root=parent) หรือที่ root ตรงๆ (legacy)
for base in "$SNC_ROOT" "$SCRIPT_DIR"; do
  for f in "$base/api/.env" "$base/.env" "$base/backend/.env" "$base/pbx-connector/.env"; do
    load_env "$f"
  done
done

TOKEN="${TELEGRAM_BOT_TOKEN:-}"
CHAT_ID="${TELEGRAM_CHAT_ID:-}"
MSG="${1:-}"

if [ -z "$TOKEN" ] || [ -z "$CHAT_ID" ]; then
  echo "[notify-telegram] SKIP: ยังไม่ตั้ง TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID (ดู doc/wiki/TELEGRAM_ALERTS.md)" >&2
  exit 0
fi
if [ -z "$MSG" ]; then
  echo "[notify-telegram] ข้อความว่างเปล่า" >&2
  exit 1
fi

RESP=$(curl -s -m 15 "https://api.telegram.org/bot${TOKEN}/sendMessage" \
  --data-urlencode "chat_id=${CHAT_ID}" \
  --data-urlencode "text=${MSG}" \
  --data-urlencode "parse_mode=HTML" 2>/dev/null) || RESP=""

case "$RESP" in
  *'"ok":true'*)
    echo "[notify-telegram] ส่งสำเร็จ ✅" ;;
  *)
    echo "[notify-telegram] ส่ง FAILED ❌: ${RESP:0:200}" >&2 ;;
esac
