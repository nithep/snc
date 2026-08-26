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
#   [3b] สร้าง uptime check ของ Pi ผ่าน tunnel (https://snc.nithep.com/health) —
#       ตรวจจับ ไฟดับ/เน็ตหลุด/ตู้ล่ม ที่ Pi (สำคัญ: Pi เองแจ้งเองไม่ได้ตอนไฟดับ)
#   [4] สร้าง notification channel (webhook) ชี้ไปที่ bridge
#   [5] สร้าง alerting policy: uptime fail 120s → ส่ง webhook → bridge → Telegram
#   [5b] สร้าง alerting policy ของ Pi (แยก policy — ดูได้ว่า "Cloud Run down" หรือ "Pi down")
#   [6] ทดสอบ bridge จริง (คุณควรเห็นข้อความใน Telegram)
# อ้างอิง: doc/wiki/TELEGRAM_ALERTS.md, doc/BLUEPRINT_5CORE.md
# ============================================================================
set -euo pipefail

PROJECT_ID="${GCP_PROJECT_ID:-hotel-ecs-nithep}"
SERVICE_NAME="snc-cloud-backend"
BRIDGE_NAME="snc-alert-bridge"
REGION="asia-southeast1"
SECRET_MONITOR="snc-monitor-webhook-token"
SERVICE_URL="https://snc-cloud-backend-59781590359.asia-southeast1.run.app"
BRIDGE_URL="https://snc-alert-bridge-59781590359.asia-southeast1.run.app"
UPTIME_ID="snc-cloud-run-health"
CHANNEL_NAME="SNC Telegram alert bridge"
POLICY_NAME="SNC Cloud Run uptime alert"
# ── ตรวจ Pi ผ่าน tunnel (สำคัญ: ไฟดับ/เน็ตหลุดที่ Pi → snc.nithep.com ตาย → alert ผ่าน GCP) ──
PI_URL="https://snc.nithep.com"
PI_HOST="snc.nithep.com"
UPTIME_PI_ID="snc-pi-tunnel-health"
PI_POLICY_NAME="SNC Pi (tunnel) uptime alert"
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
# รองรับทั้ง Linux (python3) และ Windows (python) — ใช้สำหรับ parse JSON จาก API
# ต้องทดสอบจริง กัน Microsoft Store stub (python3.exe ปลอมที่ปริ้นต์ "Python was not found")
PY=""
for _cand in python3 python py; do
  if command -v "$_cand" >/dev/null 2>&1 && "$_cand" -c 'import sys' >/dev/null 2>&1; then
    PY="$_cand"; break
  fi
done
[ -n "$PY" ] || PY="python"

# ── [2] ดึง MONITOR_WEBHOOK_TOKEN จาก Secret Manager (source of truth) ─────
echo "[2/6] ดึง MONITOR_WEBHOOK_TOKEN จาก Secret Manager..."
MONITOR_WEBHOOK_TOKEN="$(gcloud secrets versions access latest \
  --secret="$SECRET_MONITOR" --project "$PROJECT_ID" 2>/dev/null || true)"
if [ -z "$MONITOR_WEBHOOK_TOKEN" ]; then
  echo "❌ bridge ไม่มี secret $SECRET_MONITOR — deploy bridge ใหม่ (deploy script จะสร้างให้)" >&2
  exit 1
fi
echo "  ✅ token พร้อม (${MONITOR_WEBHOOK_TOKEN:0:8}... len ${#MONITOR_WEBHOOK_TOKEN})"

# helper: เรียก REST API + แสดง HTTP code + raw body (diagnose ชัด ไม่หลุดเงียบ)
# ใช้ตัวแปร global _API_BODY เก็บ response body — สำเร็จเมื่อ HTTP 200/201
_API_BODY=""
_API_CODE=""
_api() {  # usage: _api METHOD URL [DATA] — success เมื่อ HTTP 200/201
  local method="$1" url="$2" data="${3:-}"
  local out
  if [ -n "$data" ]; then
    out="$(curl -sS --connect-timeout 15 --max-time 40 -w '\n%{http_code}' \
      -X "$method" "$url" -H "Authorization: Bearer $ACCESS_TOKEN" \
      -H "Content-Type: application/json" -d "$data" 2>&1 || true)"
  else
    out="$(curl -sS --connect-timeout 15 --max-time 40 -w '\n%{http_code}' \
      -X "$method" "$url" -H "Authorization: Bearer $ACCESS_TOKEN" 2>&1 || true)"
  fi
  _API_CODE="$(printf '%s' "$out" | tail -1)"
  _API_BODY="$(printf '%s' "$out" | sed '$d')"
  echo "    HTTP $_API_CODE"
  [ -n "$_API_BODY" ] && printf '%s\n' "$_API_BODY" | head -c 1200
  echo ""
  [ "$_API_CODE" = "200" ] || [ "$_API_CODE" = "201" ]
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
  "selectedRegions": ["USA", "EUROPE", "ASIA_PACIFIC"]
}
JSON
)
# หมายเหตุ: uptimeCheckConfigs.update (PUT) ไม่ auto-create — ถ้ายังไม่มีต้อง POST (create) ก่อน
if _api GET "$API/uptimeCheckConfigs/$UPTIME_ID"; then
  echo "  ✅ uptime check มีอยู่แล้ว ($UPTIME_ID)"
elif _api POST "$API/uptimeCheckConfigs" "$UP_JSON"; then
  echo "  ✅ uptime check สร้างแล้ว ($UPTIME_ID)"
else
  echo "  ❌ [3/6] HTTP $_API_CODE — สร้าง uptime check ล้มเหลว (body: $(printf '%s' "$_API_BODY" | head -c 300))" >&2
  exit 1
fi

# ── [3b] สร้าง uptime check ของ Pi (snc.nithep.com — ตรวจจับไฟดับ/ตู้หลุด) ─────
echo "[3b/6] สร้าง uptime check ของ Pi ($PI_URL/health, ทุก 300s)..."
PI_UP_JSON=$(cat <<JSON
{
  "displayName": "SNC Pi (tunnel) /health",
  "period": "300s",
  "timeout": "10s",
  "httpCheck": {"requestMethod": "GET", "path": "/health", "useSsl": true, "validateSsl": true},
  "monitoredResource": {"type": "uptime_url", "labels": {"host": "$PI_HOST", "project_id": "$PROJECT_ID"}},
  "selectedRegions": ["USA", "EUROPE", "ASIA_PACIFIC"]
}
JSON
)
if _api GET "$API/uptimeCheckConfigs/$UPTIME_PI_ID"; then
  echo "  ✅ uptime check Pi มีอยู่แล้ว ($UPTIME_PI_ID)"
elif _api POST "$API/uptimeCheckConfigs" "$PI_UP_JSON"; then
  echo "  ✅ uptime check Pi สร้างแล้ว ($UPTIME_PI_ID)"
else
  echo "  ❌ [3b/6] HTTP $_API_CODE — สร้าง uptime check Pi ล้มเหลว (body: $(printf '%s' "$_API_BODY" | head -c 300))" >&2
  exit 1
fi

# ── [4] สร้าง notification channel (webhook → bridge) ────────────────────────
echo "[4/6] สร้าง notification channel (webhook → bridge)..."
# descriptor ของ webhook_tokenauth รับ label "url" เท่านั้น (ไม่ใช่ endpoint/auth_token)
# auth แท้คือ ?token ใน URL — ตั้ง userLabels ไว้ค้นหา channel เดิมตอน rerun
CHANNEL_JSON='{
  "type": "webhook_tokenauth",
  "displayName": "'"$CHANNEL_NAME"'",
  "labels": {"url": "'"$BRIDGE_URL"'/webhook?token='"$MONITOR_WEBHOOK_TOKEN"'"},
  "userLabels": {"purpose": "telegram-alert"}
}'
EXISTING="$(curl -sS -G --connect-timeout 15 --max-time 40 "$API/notificationChannels" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  --data-urlencode 'filter=user_labels.purpose="telegram-alert"' | "$PY" -c "
import sys, json
try:
    d = json.load(sys.stdin)
    print((d.get('channels') or [{}])[0].get('name', ''))
except Exception:
    print('')
" || true)"
if [ -n "$EXISTING" ]; then
  CHANNEL="$EXISTING"
  CHANNEL_ID="$(printf '%s' "$CHANNEL" | sed 's|.*/||')"
  echo "  ✅ พบ channel เดิม: $CHANNEL_ID"
  # ── กัน stale-token: เทียบ token ใน URL ที่ channel ใช้อยู่กับ token ปัจจุบัน ──
  CUR_URL="$(curl -sS --connect-timeout 15 --max-time 40 \
    "$API/notificationChannels/$CHANNEL_ID" -H "Authorization: Bearer $ACCESS_TOKEN" \
    2>/dev/null | "$PY" -c 'import sys,json; print(json.load(sys.stdin).get("labels",{}).get("url",""))' 2>/dev/null || true)"
  CUR_TOKEN="$(printf '%s' "$CUR_URL" | sed -n 's/.*token=\([^&]*\).*/\1/p')"
  if [ "$CUR_TOKEN" != "$MONITOR_WEBHOOK_TOKEN" ]; then
    echo "  ⚠️ channel มี token เก่า (${CUR_TOKEN:0:8}... ≠ ${MONITOR_WEBHOOK_TOKEN:0:8}...) — PATCH URL ให้ตรง"
    if _api PATCH "$API/notificationChannels/$CHANNEL_ID?updateMask=labels.url" \
      '{"labels":{"url":"'"$BRIDGE_URL"'/webhook?token='"$MONITOR_WEBHOOK_TOKEN"'"}}'; then
      echo "  ✅ อัปเดต URL channel เรียบร้อย (กัน stale-token)"
    else
      echo "  ❌ [4/6] HTTP $_API_CODE — PATCH channel ล้มเหลว (body: $(printf '%s' "$_API_BODY" | head -c 300))" >&2
      exit 1
    fi
  else
    echo "  ✅ ใช้ channel เดิม (token ตรง ไม่ต้องอัปเดต): $CHANNEL_ID"
  fi
else
  if _api POST "$API/notificationChannels" "$CHANNEL_JSON"; then
    CHANNEL="$(printf '%s' "$_API_BODY" | "$PY" -c 'import sys,json; print(json.load(sys.stdin)["name"])' 2>/dev/null || true)"
    [ -n "$CHANNEL" ] && echo "  ✅ channel ใหม่: $CHANNEL" \
      || { echo "  ❌ [4/6] HTTP $_API_CODE — parse channel name ล้มเหลว (body: $(printf '%s' "$_API_BODY" | head -c 300))" >&2; exit 1; }
  else
    echo "  ❌ [4/6] HTTP $_API_CODE — สร้าง channel ล้มเหลว (body: $(printf '%s' "$_API_BODY" | head -c 300))" >&2
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
  --data-urlencode 'filter=display_name="'"$POLICY_NAME"'"' | "$PY" -c "
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
    echo "  ❌ [5/6] HTTP $_API_CODE — สร้าง alerting policy ล้มเหลว (body: $(printf '%s' "$_API_BODY" | head -c 300))" >&2
    exit 1
  fi
fi

# ── [5b] สร้าง alerting policy ของ Pi (uptime fail 120s → webhook → Telegram) ─
echo "[5b/6] สร้าง alerting policy ของ Pi (ไฟดับ/หลุด)..."
PI_POLICY_JSON='{
  "displayName": "'"$PI_POLICY_NAME"'",
  "combiner": "OR",
  "conditions": [{
    "displayName": "Pi (tunnel) /health failed",
    "conditionThreshold": {
      "filter": "metric.type=\"monitoring.googleapis.com/uptime_check/check_passed\" AND resource.type=\"uptime_url\" AND metric.label.\"check_id\"=\"'"$UPTIME_PI_ID"'\"",
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
EXIST_PI_POLICY="$(curl -sS -G --connect-timeout 15 --max-time 40 "$API/alertPolicies" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  --data-urlencode 'filter=display_name="'"$PI_POLICY_NAME"'"' | "$PY" -c "
import sys, json
try:
    d = json.load(sys.stdin)
    print((d.get('alertPolicies') or [{}])[0].get('name', ''))
except Exception:
    print('')
" || true)"
if [ -n "$EXIST_PI_POLICY" ]; then
  echo "  ✅ policy Pi มีอยู่แล้ว: $EXIST_PI_POLICY"
else
  if _api POST "$API/alertPolicies" "$PI_POLICY_JSON"; then
    echo "  ✅ policy Pi สร้างแล้ว"
  else
    echo "  ❌ [5b/6] HTTP $_API_CODE — สร้าง alerting policy Pi ล้มเหลว (body: $(printf '%s' "$_API_BODY" | head -c 300))" >&2
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
echo "✅ เสร็จสิ้น — uptime checks: https://console.cloud.google.com/monitoring/uptime?project=$PROJECT_ID"
echo "   • $SERVICE_URL (/health) → Cloud Run หลัก"
echo "   • $PI_URL (/health) → Pi ผ่าน tunnel (ตรวจจับไฟดับ/ตู้หลุด/เน็ตตัด)"
echo "   เส้นทาง alert: Cloud Monitoring → webhook → snc-alert-bridge → Telegram"
echo "   (bridge อยู่คนละ service กับ backend หลัก — alert ส่งถึงแม้ backend หลัก down)"
