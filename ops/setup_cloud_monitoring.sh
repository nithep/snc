#!/usr/bin/env bash
# ============================================================================
# setup_cloud_monitoring.sh — Cloud Monitoring uptime check + alert → Telegram
# ----------------------------------------------------------------------------
# วิธีใช้ (Cloud Shell — https://shell.cloud.google.com):
#
#   export TELEGRAM_BOT_TOKEN="<token จาก api/.env บน Pi4>"
#   export TELEGRAM_CHAT_ID="7346817215"
#   bash ops/setup_cloud_monitoring.sh
#
# สิ่งที่สคริปต์ทำ (idempotent — รันซ้ำได้):
#   1. enable monitoring.googleapis.com
#   2. สร้าง MONITOR_WEBHOOK_TOKEN (ถ้ายังไม่มี) + ตั้ง env บน Cloud Run
#      (TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID / MONITOR_WEBHOOK_TOKEN)
#      → ต้อง deploy server.py ที่มี /api/webhooks/gcp-alert ก่อน!
#   3. สร้าง uptime check ที่ /health (ทุก 5 นาที)
#   4. สร้าง notification channel (webhook) ชี้ไปที่ bridge endpoint
#   5. สร้าง alerting policy: uptime fail 120s → ส่ง webhook → Telegram
#   6. ทดสอบ bridge จริง (คุณควรเห็นข้อความใน Telegram)
# อ้างอิง: doc/wiki/SNC_API_KEY_ROTATION_GUIDE.md, doc/BLUEPRINT_5CORE.md
# ============================================================================
set -euo pipefail

PROJECT_ID="${GCP_PROJECT_ID:-hotel-ecs-nithep}"
SERVICE_NAME="snc-cloud-backend"
REGION="asia-southeast1"
SERVICE_URL="https://snc-cloud-backend-59781590359.asia-southeast1.run.app"
UPTIME_ID="snc-cloud-run-health"
CHANNEL_NAME="SNC Telegram alert bridge"
POLICY_NAME="SNC Cloud Run uptime alert"
API="https://monitoring.googleapis.com/v3/projects/$PROJECT_ID"

echo "═══════════ Cloud Monitoring Setup (uptime → Telegram) ═══════════"
echo "Project : $PROJECT_ID"
echo "Service : $SERVICE_URL"

# ── ตรวจ prerequisites ─────────────────────────────────────────────────────
if ! command -v gcloud >/dev/null 2>&1; then
  echo "❌ ไม่พบ gcloud — ใช้ Cloud Shell (https://shell.cloud.google.com) เท่านั้น" >&2
  exit 1
fi
if [ -z "${TELEGRAM_BOT_TOKEN:-}" ] || [ -z "${TELEGRAM_CHAT_ID:-}" ]; then
  echo "❌ ต้อง export TELEGRAM_BOT_TOKEN + TELEGRAM_CHAT_ID (ดูจาก api/.env บน Pi4)" >&2
  echo "   รันบน Pi: grep -E 'TELEGRAM' /home/ecs-agent/snc-poc/api/.env" >&2
  exit 1
fi
echo "✅ TELEGRAM env พร้อม (bot token len ${#TELEGRAM_BOT_TOKEN})"

gcloud config set project "$PROJECT_ID" >/dev/null
ACCESS_TOKEN="$(gcloud auth print-access-token)"

# ── [1] enable Monitoring API ─────────────────────────────────────────────
echo "[1/6] enable monitoring.googleapis.com..."
gcloud services enable monitoring.googleapis.com --project "$PROJECT_ID" >/dev/null 2>&1 \
  || echo "  ⚠️ enable ล้มเหลว (อาจ enable แล้ว) — ดำเนินการต่อ"

# ── [2] ตั้ง env บน Cloud Run (bridge → Telegram) ──────────────────────────
echo "[2/6] ตั้ง env บน Cloud Run (bridge webhook → Telegram)..."
MONITOR_WEBHOOK_TOKEN="${MONITOR_WEBHOOK_TOKEN:-$(openssl rand -hex 16)}"
echo "  MONITOR_WEBHOOK_TOKEN: ${MONITOR_WEBHOOK_TOKEN:0:8}... (len ${#MONITOR_WEBHOOK_TOKEN})"
# บันทึก token ไว้ใช้ตอน deploy ครั้งถัดไปด้วย (ถ้ารัน deploy ใหม่จะได้ส่งต่อ)
gcloud run services update "$SERVICE_NAME" \
  --region "$REGION" --project "$PROJECT_ID" \
  --update-env-vars "TELEGRAM_BOT_TOKEN=$TELEGRAM_BOT_TOKEN,TELEGRAM_CHAT_ID=$TELEGRAM_CHAT_ID,MONITOR_WEBHOOK_TOKEN=$MONITOR_WEBHOOK_TOKEN" >/dev/null

# ── [3] สร้าง uptime check (GET /health ทุก 5 นาที) ─────────────────────────
echo "[3/6] สร้าง uptime check (GET /health, ทุก 300s)..."
HOST="${SERVICE_URL#https://}"
curl -sS -X PUT "$API/uptimeCheckConfigs/$UPTIME_ID" \
  -H "Authorization: Bearer $ACCESS_TOKEN" -H "Content-Type: application/json" \
  -d "{
    \"displayName\": \"SNC Cloud Run /health\",
    \"period\": \"300s\",
    \"timeout\": \"10s\",
    \"httpCheck\": {\"requestMethod\": \"GET\", \"path\": \"/health\", \"useSsl\": true, \"validateSsl\": true},
    \"monitoredResource\": {\"type\": \"uptime_url\", \"labels\": {\"host\": \"$HOST\", \"project_id\": \"$PROJECT_ID\"}},
    \"selectedRegions\": [\"ASIA_PACIFIC\"]
  }" | python3 -c "import sys,json; d=json.load(sys.stdin); print('  ✅ uptime check:', d.get('name', d))" \
  || { echo "  ❌ สร้าง uptime check ล้มเหลว (ดู error ด้านบน)" >&2; exit 1; }

# ── [4] สร้าง notification channel (webhook → bridge) ───────────────────────
echo "[4/6] สร้าง notification channel (webhook)..."
CHANNEL_JSON='{
  "type": "webhook_tokenauth",
  "displayName": "'"$CHANNEL_NAME"'",
  "labels": {"endpoint": "'"$SERVICE_URL"'/api/webhooks/gcp-alert?token='"$MONITOR_WEBHOOK_TOKEN"'", "auth_token": ""},
  "userLabels": {"purpose": "telegram-alert"}
}'
# idempotent: ถ้ามี channel ชื่อเดียวกันอยู่แล้ว → ใช้เดิม (ไม่สร้างซ้ำ)
EXISTING="$(curl -sS -G "$API/notificationChannels" -H "Authorization: Bearer $ACCESS_TOKEN" \
  --data-urlencode "filter=user_labels.purpose=\"telegram-alert\"" | python3 -c "
import sys, json
d = json.load(sys.stdin)
chs = d.get('channels', [])
print(chs[0]['name'] if chs else '')
" 2>/dev/null || true)"
if [ -n "$EXISTING" ]; then
  CHANNEL="$EXISTING"
  echo "  ✅ ใช้ channel เดิม: $CHANNEL"
else
  CHANNEL="$(curl -sS -X POST "$API/notificationChannels" \
    -H "Authorization: Bearer $ACCESS_TOKEN" -H "Content-Type: application/json" \
    -d "$CHANNEL_JSON" | python3 -c "import sys,json; print(json.load(sys.stdin)['name'])")"
  echo "  ✅ channel ใหม่: $CHANNEL"
fi

# ── [5] สร้าง alerting policy (uptime fail 120s → webhook) ──────────────────
echo "[5/6] สร้าง alerting policy..."
POLICY_JSON='{
  "displayName": "'"$POLICY_NAME"'",
  "combiner": "OR",
  "conditions": [{
    "displayName": "Uptime check /health failed",
    "conditionThreshold": {
      "filter": "metric.type=\"monitoring.googleapis.com/uptime_check/check_passed\" AND resource.type=\"uptime_url\" AND metric.label.\"check_id\"=\"'"$UPTIME_ID"'\"",
      "comparison": "COMPARISON_LT",
      "thresholdValue": 1,
      "duration": "120s",
      "trigger": {"count": 1},
      "aggregations": [{"alignmentPeriod": "120s", "perSeriesAligner": "ALIGN_NEXT_OLDER"}]
    }
  }],
  "alertStrategy": {"autoClose": "3600s"},
  "notificationChannels": ["'"$CHANNEL"'"]
}'
EXIST_POLICY="$(curl -sS -G "$API/alertPolicies" -H "Authorization: Bearer $ACCESS_TOKEN" \
  --data-urlencode 'filter=display_name="'"$POLICY_NAME"'"' | python3 -c "
import sys, json
d = json.load(sys.stdin)
pols = d.get('alertPolicies', [])
print(pols[0]['name'] if pols else '')
" 2>/dev/null || true)"
if [ -n "$EXIST_POLICY" ]; then
  echo "  ✅ policy มีอยู่แล้ว: $EXIST_POLICY"
else
  curl -sS -X POST "$API/alertPolicies" \
    -H "Authorization: Bearer $ACCESS_TOKEN" -H "Content-Type: application/json" \
    -d "$POLICY_JSON" | python3 -c "import sys,json; d=json.load(sys.stdin); print('  ✅ policy:', d.get('name', d))" \
    || { echo "  ❌ สร้าง alerting policy ล้มเหลว (ดู error ด้านบน)" >&2; exit 1; }
fi

# ── [6] ทดสอบ bridge จริง (คุณควรเห็นข้อความใน Telegram) ────────────────────
echo "[6/6] ทดสอบ webhook bridge → Telegram..."
sleep 5
TEST=$(curl -sS -X POST "$SERVICE_URL/api/webhooks/gcp-alert?token=$MONITOR_WEBHOOK_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"incident":{"state":"OPEN","summary":"ทดสอบจาก setup_cloud_monitoring.sh (uptime check พร้อมใช้)","condition_name":"Uptime check /health failed"}}')
echo "  bridge → $TEST"
echo "$TEST" | grep -q '"status": *"sent"' && echo "  ✅ Telegram ส่งแล้ว (เช็คแชทได้)" \
  || echo "  ⚠️ bridge ยังส่งไม่ได้ — ตรวจว่า deploy server.py ที่มี /api/webhooks/gcp-alert แล้วหรือยัง"

echo ""
echo "✅ เสร็จสิ้น — uptime check: https://console.cloud.google.com/monitoring/uptime?project=$PROJECT_ID"
echo "   หมายเหตุ: bridge อยู่บน snc-cloud-backend เอง — ถ้า service ทั้งตัว down จริง alert จะส่งไม่ถึง"
echo "   (กรณีนั้นยังมี verify-daily บน Pi + Cloud Console เป็นทางสำรอง)"
