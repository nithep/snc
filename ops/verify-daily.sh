#!/usr/bin/env bash
# ============================================================================
# verify-daily.sh — ตรวจระบบรายวัน (cron) + แจ้งเตือน Telegram เมื่อมีปัญหา
# ----------------------------------------------------------------------------
# cron (บน Pi):  0 7 * * * /home/ecs-agent/snc-poc/ops/verify-daily.sh   # (log เก็บใน verify_daily.log เอง ไม่ต้อง redirect)
#
# พฤติกรรม:
#   - รัน verify-system.sh (ค่าเริ่มต้น --all; หรือระบุชื่อโปรเจกต์ผ่าน VERIFY_ARGS)
#   - เก็บผลลัพธ์ทั้งหมดที่ <root>/verify_daily.log
#   - PASS ครบทุกจุด → เงียบ (หรือส่งสรุปสั้น ถ้าตั้ง VERIFY_ALWAYS=1)
#   - มี FAIL      → ส่งรายละเอียดไป Telegram (ผ่าน notify-telegram.sh) + exit 1
#
# ตั้งค่า:
#   VERIFY_ARGS="snc"        # ตรวจเฉพาะโปรเจกต์ snc (default: --all)
#   VERIFY_ALWAYS=1          # ส่งแจ้งเตือนแม้ผ่านทุกจุด
#   VERIFY_CONF=/path/conf   # ชี้ conf อื่น (default: ops/verify-projects.conf)
#
# อ้างอิง: doc/BLUEPRINT_5CORE.md, doc/wiki/TELEGRAM_ALERTS.md
# ============================================================================
set -uo pipefail

OPS_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$OPS_DIR/.." && pwd)"
VERIFY="$OPS_DIR/verify-system.sh"
NOTIFY="$OPS_DIR/notify-telegram.sh"
LOG="$ROOT/verify_daily.log"
VERIFY_ARGS="${VERIFY_ARGS:---all}"

# ถ้าไม่มี conf ให้รันโปรเจกต์ default (ไม่มี arg)
[ -f "$OPS_DIR/verify-projects.conf" ] || VERIFY_ARGS=""

OUT="$("$VERIFY" $VERIFY_ARGS 2>&1)"
RC=$?

# ── บันทึก log ─────────────────────────────────────────────────────────────
{
  echo "──────── verify-daily $(date '+%Y-%m-%d %H:%M:%S') (exit=$RC) ────────"
  echo "$OUT"
  echo
} >> "$LOG"

SUMMARIES=$(echo "$OUT" | grep -E 'สรุป:' | sed 's/^ *//')
SUMMARY_LINE=$(echo "$SUMMARIES" | tail -1)

if [ "$RC" -eq 0 ]; then
  if [ "${VERIFY_ALWAYS:-0}" = "1" ]; then
    "$NOTIFY" "✅ <b>Verify รายวันผ่าน</b> ($(hostname))
$SUMMARIES" >/dev/null 2>&1 || true
  fi
  echo "[verify-daily] PASS — $SUMMARY_LINE"
  exit 0
fi

# ── มีปัญหา → ส่งไป Telegram ───────────────────────────────────────────────
BODY="$(echo "$OUT" | grep -E '\[FAIL\]|\[WARN\]|สรุป:' | head -c 3400)"
"$NOTIFY" "🚨 <b>Verify รายวันพบปัญหา</b> ($(hostname) — $(date '+%d %b %H:%M'))

$BODY" >/dev/null 2>&1 || true

echo "[verify-daily] FAIL — $SUMMARY_LINE (แจ้งเตือนแล้ว)"
exit 1
