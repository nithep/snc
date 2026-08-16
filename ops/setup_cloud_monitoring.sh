#!/usr/bin/env bash
# ============================================================================
# setup_cloud_monitoring.sh — Cloud Monitoring uptime check + alert → Telegram
# ----------------------------------------------------------------------------
# วิธีใช้ (Cloud Shell — https://shell.cloud.google.com):
#
#   bash ops/setup_cloud_monitoring.sh
#
# ข้อกำหนด: deploy bridge service ก่อน (service แยก — alert ถึงแม้ backend หลัก down):
#   export TELEGRAM_BOT_TOKEN="<token จาก api/.env บน Pi4>"
#   export TELEGRAM_CHAT_ID="7346817215"
#   bash ops/deploy_bridge_cloudshell.sh
#
# สิ่งที่สคริปต์ทำ (idempotent — รันซ้ำได้):
#   [0] ตรวจ bridge ว่า live (ถ้ายังไม่ → บอกให้ deploy ก่อน)
#   [1] enable monitoring.googleapis.com
#   [2] ดึง MONITOR_WEBHOOK_TOKEN จาก env ของ bridge service (source of truth)
#   [3] สร้าง uptime check ที่ /health ของ service หลัก (ทุก 5 นาที)
#   [4] สร้าง notification channel (webhook) ชี้ไปที่ bridge
#   [5] สร้าง alerting policy: uptime fail 120s → ส่ง webhook → bridge → Telegram
#   [6] ทดสอบ bridge จริง (คุณควรเห็นข้อความใน Telegram)
# อ้างอิง: doc/wiki/TELEGRAM_ALERTS.md, doc/BLUEPRINT_5CORE.md
# ============================================================================
set -euo pipefail

PROJECT_ID="${GCP_PROJECT_ID:-hotel-ecs-nithep}"
SERVICE_NAME="snc-cloud-backend"
BRIDGE_NAME="snc-alert-bridge"
REGION="asia-southeast1"
SERVICE_URL="https://snc-cloud-backend-59781590359.asia-southeast1.run.app"
BRIDGE_URL="https://snc-alert-bridge-59781590359.asia-southeast1.run.app"
UPTIME_ID="snc-cloud-run-health"
CHANNEL_NAME="SNC Telegram alert bridge"
POLICY_NAME="SNC Cloud Run uptime alert"
API="https://monitoring.googleapis.com/v3/projects/$PROJECT_ID"

echo "═══════════ Cloud Monitoring Setup (uptime → Telegram) ═══════════"
echo "Project : $PROJECT_ID"
echo "Target  : $SERVICE_URL"
echo "Bridge  : $BRIDGE_URL (service แยก — alert ถึงแม้ backend หลัก down)"

if ! command -v gcloud >/dev/null 2>&1; then
  echo "❌ ไม่พบ gcloud — ใช้ Cloud Shell (https://shell.cloud.google.com) เท่านั้น" >&2
  exit 1
fi
gcloud config set project "$PROJECT_ID" >/dev/null

# ── [0] ตรวจ bridge ว่า live ────────────────────────────────────────────────
echo "[0/6] ตรวจ bridge service..."
if ! curl -s --max-time 15 "$BRIDGE_URL/health" 2>/dev/null | grep -q '"healthy"'; then
  echo "❌ bridge ยังไม่ทำงาน ($BRIDGE_URL)" >&2
  echo "   รันก่อน (Cloud Shell):" >&2
  echo "     export TELEGRAM_BOT_TOKEN=\"<token จาก api/.env บน Pi4>\"" >&2
  echo "     export TELEGRAM_CHAT_ID=\"7346817215\"" >&2
  echo "     bash ops/deploy_bridge_cloudshell.sh" >&2
  exit 1
fi
echo "  ✅ bridge live"

# ── [1] enable Monitoring API ───────────────────────────────────────────────
echo "[1/6] enable monitoring.googleapis.com..."
gcloud services enable monitoring.googleapis.com --project "$PROJECT_ID" >/dev/null 2>&1 \
  || echo "  ⚠️ enable ล้มเหลว (อาจ enable แล้ว) — ดำเนินการต่อ"

ACCESS_TOKEN="$(gcloud auth print-access-token)"

# ── [2] ดึง MONITOR_WEBHOOK_TOKEN จาก env ของ bridge (source of truth) ──────
echo "[2/6] ดึง MONITOR_WEBHOOK_TOKEN จาก bridge service..."
MONITOR_WEBHOOK_TOKEN="$(gcloud run services describe "$BRIDGE_NAME" --region "$REGION" \
  --project "$PROJECT_ID" --format='json' 2>/dev/null | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    for e in d['spec']['template']['spec']['containers'][0].get('env', []):
        if e.get('name') == 'MONITOR_WEBHOOK_TOKEN':
            print(e.get('value', ''))
except Exception:
    pass
" || true)"
if [ -z "$MONITOR_WEBHOOK_TOKEN" ]; then
  echo "❌ bridge ไม่มี MONITOR_WEBHOOK_TOKEN — deploy bridge ใหม่ (deploy script จะสร้างให้)" >&2
  exit 1
fi
echo "  ✅ token พร้อม (${MONITOR_WEBHOOK_TOKEN:0:8}... len ${#MONITOR_WEBHOOK_TOKEN})"

# helper: เรียก REST API + แสดง HTTP code + raw body (diagnose ชัด ไม่หลุดเงียบ)
# ใช้ตัวแปร global _API_BODY เก็บ response body — สำเร็จเมื่อ HTTP 200/201
_API_BODY=""
_api() {  # usage: _api METHOD URL [DATA]
  local method="$1" url="$2" data="${3:-}"
  local out code
  if [ -n "$data" ]; then
    out="$(curl -sS --connect-timeout 15 --max-time 40 -w '\n%{http_code}' \
      -X "$method" "$url" -H "Authorization: Bearer $ACCESS_TOKEN" \
      -H "Content-Type: application/json" -d "$data" 2>&1 || true)"
  else
    out="$(curl -sS --connect-timeout 15 --max-time 40 -w '\n%{http_code}' \
      -X "$method" "$url" -H "Authorization: Bearer $ACCESS_TOKEN" 2>&1 || true)"
  fi
  code="$(printf '%s' "$out" | tail -1)"
  _API_BODY="$(printf '%s' "$out" | sed '$d')"
  echo "    HTTP $code"
  [ -n "$_API_BODY" ] && printf '%s\n' "$_API_BODY" | head -c 1200
  echo ""
  [ "$code" = "200" ] || [ "$code" = "201" ]
}

# ── [3] สร้าง uptime check (GET /health ของ service หลัก ทุก 5 นาที) ─────────
echo "[3/6] สร้าง uptime check (GET /health, ทุก 300s)..."
HOST="${SERVICE_URL#https://}"
UP_JSON=$(cat <<JSON
{
  "displayName": "SNC Cloud Run /health",
  "period": "300s",
  "timeout": "10s",
  "httpCheck": {"requestMethod": "GET", "path": "/health", "useSsl": true, "validateSsl": true},
  "monitoredResource": {"type": "uptime_url", "labels": {"host": "$HOST", "project_id": "$PROJECT_ID"}},
  "selectedRegions": ["ASIA_PACIFIC"]
}
JSON
)
# หมายเหตุ: uptimeCheckConfigs.update (PUT) ไม่ auto-create — ถ้ายังไม่มีต้อง POST (create) ก่อน
if _api GET "$API/uptimeCheckConfigs/$UPTIME_ID"; then
  echo "  ✅ uptime check มีอยู่แล้ว ($UPTIME_ID)"
elif _api POST "$API/uptimeCheckConfigs" "$UP_JSON"; then
  echo "  ✅ uptime check สร้างแล้ว ($UPTIME_ID)"
else
  echo "  ❌ สร้าง uptime check ล้มเหลว (ดู HTTP code + body ด้านบน)" >&2
  exit 1
fi

# ── [4] สร้าง notification channel (webhook → bridge) ────────────────────────
echo "[4/6] สร้าง notification channel (webhook → bridge)..."
CHANNEL_JSON='{
  "type": "webhook_tokenauth",
  "displayName": "'"$CHANNEL_NAME"'",
  "labels": {"endpoint": "'"$BRIDGE_URL"'/webhook?token='"$MONITOR_WEBHOOK_TOKEN"'", "auth_token": ""},
  "userLabels": {"purpose": "telegram-alert"}
}'
EXISTING="$(curl -sS -G --connect-timeout 15 --max-time 40 "$API/notificationChannels" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  --data-urlencode 'filter=user_labels.purpose="telegram-alert"' | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    print((d.get('channels') or [{}])[0].get('name', ''))
except Exception:
    print('')
" || true)"
if [ -n "$EXISTING" ]; then
  CHANNEL="$EXISTING"
  echo "  ✅ ใช้ channel เดิม: $CHANNEL"
else
  if _api POST "$API/notificationChannels" "$CHANNEL_JSON"; then
    CHANNEL="$(printf '%s' "$_API_BODY" | python3 -c 'import sys,json; print(json.load(sys.stdin)["name"])' 2>/dev/null || true)"
    [ -n "$CHANNEL" ] && echo "  ✅ channel ใหม่: $CHANNEL" \
      || { echo "  ❌ parse channel name ล้มเหลว (body: $_API_BODY)" >&2; exit 1; }
  else
    echo "  ❌ สร้าง notification channel ล้มเหลว (ดู HTTP code + body ด้านบน)" >&2
    exit 1
  fi
fi

# ── [5] สร้าง alerting policy (uptime fail 120s → webhook → bridge) ─────────
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
EXIST_POLICY="$(curl -sS -G --connect-timeout 15 --max-time 40 "$API/alertPolicies" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  --data-urlencode 'filter=display_name="'"$POLICY_NAME"'"' | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    print((d.get('alertPolicies') or [{}])[0].get('name', ''))
except Exception:
    print('')
" || true)"
if [ -n "$EXIST_POLICY" ]; then
  echo "  ✅ policy มีอยู่แล้ว: $EXIST_POLICY"
else
  if _api POST "$API/alertPolicies" "$POLICY_JSON"; then
    echo "  ✅ policy สร้างแล้ว"
  else
    echo "  ❌ สร้าง alerting policy ล้มเหลว (ดู HTTP code + body ด้านบน)" >&2
    exit 1
  fi
fi

# ── [6] ทดสอบ bridge จริง (คุณควรเห็นข้อความใน Telegram) ────────────────────
echo "[6/6] ทดสอบ webhook bridge → Telegram..."
T=$(curl -sS --max-time 20 -X POST "$BRIDGE_URL/webhook?token=$MONITOR_WEBHOOK_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"incident":{"state":"OPEN","summary":"ทดสอบจาก setup_cloud_monitoring.sh (uptime check พร้อมใช้)","condition_name":"Uptime check /health failed"}}')
echo "  bridge → $T"
echo "$T" | grep -q '"sent"' && echo "  ✅ Telegram ส่งแล้ว (เช็คแชทได้)" \
  || echo "  ⚠️ bridge รับได้แต่ส่ง Telegram ไม่ได้ — ตรวจ TELEGRAM env บน bridge service"

echo ""
echo "✅ เสร็จสิ้น — uptime check: https://console.cloud.google.com/monitoring/uptime?project=$PROJECT_ID"
echo "   เส้นทาง alert: Cloud Monitoring → webhook → snc-alert-bridge → Telegram"
echo "   (bridge อยู่คนละ service กับ backend หลัก — alert ส่งถึงแม้ backend หลัก down)"
