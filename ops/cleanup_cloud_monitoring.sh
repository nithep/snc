#!/usr/bin/env bash
# ============================================================================
# cleanup_cloud_monitoring.sh — ลบ notification channels เก่าที่ไม่ใช้แล้ว
# ----------------------------------------------------------------------------
# วิธีใช้ (Cloud Shell — https://shell.cloud.google.com):
#
#   # ดูว่าจะลบ channel ไหนบ้าง (ไม่ลบจริง):
#   DRY_RUN=1 bash ops/cleanup_cloud_monitoring.sh
#
#   # ลบจริง:
#   bash ops/cleanup_cloud_monitoring.sh
#
# ทำไมต้องมีสคริปต์: ระหว่าง debug Cloud Monitoring เกิด channel ซ้ำหลายตัว
# (webhook_tokenauth ชี้ bridge เดียวกัน) — channel เก่าทำให้ console รก/สับสน
#
# ความปลอดภัย:
#   - ลบเฉพาะ channel ที่อยู่ใน allowlist (STALE_CHANNEL_IDS) เท่านั้น
#   - ACTIVE_CHANNEL_ID (channel ที่ alerting policy ใช้จริง) ถูก guard — ไม่ลบเด็ดขาด
#   - ถ้า channel ยังถูก alerting policy ผูกอยู่ Monitoring API จะคืน 400 → สคริปต์เตือน
#     (ต้อง unbind ที่ policy ก่อนลบ)
# ============================================================================
set -euo pipefail

PROJECT_ID="${GCP_PROJECT_ID:-hotel-ecs-nithep}"
API="https://monitoring.googleapis.com/v3/projects/$PROJECT_ID"

# channel ที่ใช้จริง (ห้ามลบ) — id `6246499446847685992` จาก handover 19 ส.ค.
ACTIVE_CHANNEL_ID="6246499446847685992"
# channel เก่าที่สร้างซ้ำระหว่าง debug — allowlist สำหรับลบ
STALE_CHANNEL_IDS=(
  "12417720015775998846"
  "276357567739982957"
  "3584692914350070116"
  "9802072087643608996"
)

DRY_RUN="${DRY_RUN:-0}"

echo "═══════════ Cloud Monitoring Channel Cleanup ═══════════"
echo "Project : $PROJECT_ID"
echo "Mode    : $([ "$DRY_RUN" = "1" ] && echo 'DRY-RUN (ไม่ลบจริง)' || echo 'DELETE (ลบจริง)')"
echo ""

if ! command -v gcloud >/dev/null 2>&1; then
  echo "❌ ไม่พบ gcloud — ใช้ Cloud Shell (https://shell.cloud.google.com) เท่านั้น" >&2
  exit 1
fi
gcloud config set project "$PROJECT_ID" >/dev/null
ACCESS_TOKEN="$(gcloud auth print-access-token)"

# ── guard: ชี้ชัดว่าห้ามลบ channel ที่ใช้งานจริง ─────────────────────────────
for id in "${STALE_CHANNEL_IDS[@]}"; do
  if [ "$id" = "$ACTIVE_CHANNEL_ID" ]; then
    echo "❌ $id อยู่ใน allowlist แต่คือ ACTIVE channel — ห้ามลบ (แก้ STALE_CHANNEL_IDS)" >&2
    exit 1
  fi
done

# helper: GET/DELETE channel → คืน HTTP code + body (วินิจฉัยชัด)
_api() {  # usage: _api METHOD CHANNEL_ID
  local method="$1" id="$2" out
  out="$(curl -sS --connect-timeout 15 --max-time 40 -w '\n%{http_code}' \
    -X "$method" "$API/notificationChannels/$id" \
    -H "Authorization: Bearer $ACCESS_TOKEN" 2>&1 || true)"
  _API_CODE="$(printf '%s' "$out" | tail -1)"
  _API_BODY="$(printf '%s' "$out" | sed '$d')"
}

DELETED=0
SKIPPED=0
FAILED=0

for id in "${STALE_CHANNEL_IDS[@]}"; do
  echo "── channel $id ──"
  _api GET "$id"
  case "$_API_CODE" in
    404)
      echo "  ✅ ไม่มีอยู่แล้ว — ข้าม"
      SKIPPED=$((SKIPPED + 1))
      ;;
    200)
      # แสดงชื่อ channel (ถ้ามี) เพื่อให้ตรวจได้ว่าใช่ตัวเก่าจริง
      DISPLAY="$(printf '%s' "$_API_BODY" | python3 -c 'import sys,json
try:
    print(json.load(sys.stdin).get("displayName", "(ไม่มีชื่อ)"))
except Exception:
    print("(parse ไม่ได้)")' 2>/dev/null || true)"
      echo "  พบ: ${DISPLAY}"
      if [ "$DRY_RUN" = "1" ]; then
        echo "  🔍 [DRY-RUN] จะลบ channel $id"
        SKIPPED=$((SKIPPED + 1))
        continue
      fi
      _api DELETE "$id"
      case "$_API_CODE" in
        200|204)
          echo "  ✅ ลบแล้ว ($_API_CODE)"
          DELETED=$((DELETED + 1))
          ;;
        400)
          echo "  ⚠️ ลบไม่ได้ ($_API_CODE) — channel ยังถูก alerting policy ผูกอยู่ (unbind ก่อน)"
          FAILED=$((FAILED + 1))
          ;;
        *)
          echo "  ❌ ลบล้มเหลว ($_API_CODE): $(printf '%s' "$_API_BODY" | head -c 300)"
          FAILED=$((FAILED + 1))
          ;;
      esac
      ;;
    *)
      echo "  ❌ GET ล้มเหลว ($_API_CODE): $(printf '%s' "$_API_BODY" | head -c 300)"
      FAILED=$((FAILED + 1))
      ;;
  esac
  echo ""
done

echo "═══════════ สรุป ═══════════"
echo "ลบแล้ว : $DELETED | ข้าม/ไม่มี : $SKIPPED | ล้มเหลว : $FAILED"
if [ "$DRY_RUN" = "1" ]; then
  echo "⚠️ DRY-RUN — ยังไม่ลบจริง รัน 'bash ops/cleanup_cloud_monitoring.sh' เพื่อลบ"
fi
exit $([ "$FAILED" = "0" ] && echo 0 || echo 1)
