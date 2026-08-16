#!/usr/bin/env bash
# ============================================================================
# ops/synthetic-e2e-check.sh — Synthetic End-to-End Health Check (ADR 0004/0005)
# ----------------------------------------------------------------------------
# ตรวจมากกว่า /health 200: ยิง event จำลองจริง → ตรวจว่า backend รับ + เก็บได้
# (แล้วคืน id จาก outbox/idempotency) → (optional) ตรวจเส้นทาง bridge → Telegram
#
# วิธีใช้ (cron หรือ Cloud Shell):
#   BACKEND_URL="http://localhost:8000" SNC_API_KEY="xxx" bash ops/synthetic-e2e-check.sh
#   BRIDGE_URL="https://...run.app" MONITOR_WEBHOOK_TOKEN="yyy" \
#     BACKEND_URL="https://...run.app" SNC_API_KEY="xxx" bash ops/synthetic-e2e-check.sh
#
# exit code: 0 = OK, 1 = fail (ใช้ใน cron ตรวจ alert ได้)
# ============================================================================
set -u

BACKEND_URL="${BACKEND_URL:-http://localhost:8000}"
SNC_API_KEY="${SNC_API_KEY:-}"
BRIDGE_URL="${BRIDGE_URL:-}"
MONITOR_WEBHOOK_TOKEN="${MONITOR_WEBHOOK_TOKEN:-}"
ROOM_ID="${SYNTH_ROOM_ID:-0888}"
EVENT_TYPE="${SYNTH_EVENT_TYPE:-CALL_BEDSIDE}"
TIMEOUT="${SYNTH_TIMEOUT:-15}"

# idempotency key เฉพาะแต่ละ run — backend dedup ถ้า retry ครั้งเดียวกัน
EVENT_ID="snc-synth-${ROOM_ID}-$(date +%s%N)"

fail() { echo "❌ $*"; exit 1; }

echo "═══════ SNC Synthetic E2E Check ═══════"
echo "Target : $BACKEND_URL"
echo "Event  : $EVENT_ID ($EVENT_TYPE)"

# ── [1] trigger event จริง (พร้อม event_id) ────────────────────────────────
AUTH=()
[ -n "$SNC_API_KEY" ] && AUTH=(-H "X-API-Key: $SNC_API_KEY")
TRIG=$(curl -sS --max-time "$TIMEOUT" -X POST "$BACKEND_URL/api/events/trigger" \
  "${AUTH[@]}" -H "Content-Type: application/json" \
  -d "{\"room_id\":\"$ROOM_ID\",\"event_type\":\"$EVENT_TYPE\",\"event_id\":\"$EVENT_ID\"}") \
  || fail "POST trigger ไม่สำเร็จ (backend down?)"

echo "  trigger → $TRIG"
echo "$TRIG" | grep -qE '"(status|result)"' || fail "trigger response ผิดปกติ"

# ── [2] ยิงซ้ำด้วย id เดียวกัน → ต้องถูก dedup (idempotent) ────────────────
TRIG2=$(curl -sS --max-time "$TIMEOUT" -X POST "$BACKEND_URL/api/events/trigger" \
  "${AUTH[@]}" -H "Content-Type: application/json" \
  -d "{\"room_id\":\"$ROOM_ID\",\"event_type\":\"$EVENT_TYPE\",\"event_id\":\"$EVENT_ID\"}")
echo "  trigger(ซ้ำ) → $TRIG2"
echo "$TRIG2" | grep -qiE 'duplicate|exists' \
  || echo "  ⚠️ ไม่ได้ dedup (backend ยังไม่รองรับ event_id หรือสร้างใหม่) — ยัง OK แต่ไม่ถือว่า idempotent"

# ── [3] ตรวจว่า event ถูกเก็บจริง (query กลับ) ──────────────────────────────
EVENTS=$(curl -sS --max-time "$TIMEOUT" "$BACKEND_URL/api/events" "${AUTH[@]}") \
  || fail "GET /api/events ล้มเหลว"
echo "$EVENTS" | grep -q "\"$EVENT_ID\"" \
  && echo "  ✅ event ถูกเก็บแล้ว (พบ id)" \
  || fail "event ไม่อยู่ใน /api/events (เก็บ/คิวไม่สำเร็จ)"

# ── [4] (optional) ตรวจเส้นทาง bridge → Telegram ───────────────────────────
if [ -n "$BRIDGE_URL" ] && [ -n "$MONITOR_WEBHOOK_TOKEN" ]; then
  T=$(curl -sS --max-time "$TIMEOUT" -X POST "$BRIDGE_URL/webhook?token=$MONITOR_WEBHOOK_TOKEN" \
    -H "Content-Type: application/json" \
    -d "{\"incident\":{\"state\":\"OPEN\",\"summary\":\"SNC synthetic E2E check\",\"condition_name\":\"synthetic\"}}")
  echo "  bridge → $T"
  echo "$T" | grep -q '"sent"' && echo "  ✅ bridge→Telegram ทำงาน" \
    || echo "  ⚠️ bridge รับได้แต่ส่ง Telegram ไม่ได้"
else
  echo "  (ไม่ตรวจ bridge — ไม่ได้ตั้ง BRIDGE_URL/MONITOR_WEBHOOK_TOKEN)"
fi

echo ""
echo "✅ Synthetic E2E PASS — $BACKEND_URL healthy (event ครบวงจร)"
exit 0