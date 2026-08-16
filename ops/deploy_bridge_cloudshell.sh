#!/usr/bin/env bash
# ============================================================================
# deploy_bridge_cloudshell.sh — Deploy SNC Alert Bridge (service แยกจาก backend)
# ----------------------------------------------------------------------------
# วิธีใช้ (Cloud Shell):
#
#   export TELEGRAM_BOT_TOKEN="<token จาก api/.env บน Pi4>"
#   export TELEGRAM_CHAT_ID="7346817215"
#   bash ops/deploy_bridge_cloudshell.sh
#
# ทำไมต้องแยก service: bridge ต้องส่ง alert ถึงแม้ snc-cloud-backend หลักจะ down
# (ชี้ webhook channel ไปที่ bridge ไม่ใช่ service หลัก — ดู setup_cloud_monitoring.sh)
#
# ความปลอดภัย (Secret Manager):
#   - TELEGRAM_BOT_TOKEN     → secret: snc-telegram-bot-token
#   - MONITOR_WEBHOOK_TOKEN  → secret: snc-monitor-webhook-token
#   Cloud Run mount เป็น secret env (ไม่เก็บ plaintext ใน --set-env-vars)
#   MONITOR_WEBHOOK_TOKEN อ่านจาก Secret Manager เดิมถ้ามี (กัน channel URL เก่าแตก)
#
# สคริปต์จะ: clone repo → build ผ่าน Cloud Build (ไม่พึ่ง docker push จาก Cloud Shell)
# → สร้าง/update secret → grant IAM → deploy ด้วย digest + secret mount
# → ทดสอบ webhook จริง
# ============================================================================
set -euo pipefail

PROJECT_ID="${GCP_PROJECT_ID:-hotel-ecs-nithep}"
SERVICE_NAME="snc-alert-bridge"
REGION="asia-southeast1"
IMAGE_TAG="gcr.io/$PROJECT_ID/$SERVICE_NAME:latest"
SERVICE_URL="https://snc-alert-bridge-59781590359.asia-southeast1.run.app"
REPO_URL="https://github.com/nithep/snc.git"
WORK_DIR="${WORK_DIR:-$HOME/snc}"

SECRET_BOT="snc-telegram-bot-token"
SECRET_MONITOR="snc-monitor-webhook-token"

echo "═══════════ SNC Alert Bridge Deploy ═══════════"
echo "Project : $PROJECT_ID"
echo "Service : $SERVICE_NAME ($REGION)"

# ── ตรวจ env ที่จำเป็น ─────────────────────────────────────────────────────
if [ -z "${TELEGRAM_BOT_TOKEN:-}" ] || [ -z "${TELEGRAM_CHAT_ID:-}" ]; then
  echo "❌ ต้อง export TELEGRAM_BOT_TOKEN + TELEGRAM_CHAT_ID" >&2
  echo "   (ดูจาก Pi: grep -E 'TELEGRAM' /home/ecs-agent/snc-poc/api/.env)" >&2
  exit 1
fi
echo "✅ TELEGRAM env พร้อม (bot token len ${#TELEGRAM_BOT_TOKEN})"

if ! command -v gcloud >/dev/null 2>&1; then
  echo "❌ ไม่พบ gcloud — ใช้ Cloud Shell (https://shell.cloud.google.com) เท่านั้น" >&2
  exit 1
fi
gcloud config set project "$PROJECT_ID" >/dev/null

# ── clone/update repo ──────────────────────────────────────────────────────
if [ ! -d "$WORK_DIR/api" ]; then
  echo "[1/4] Clone repo..."
  git clone "$REPO_URL" "$WORK_DIR" || { echo "❌ clone ล้มเหลว (GitHub auth?)" >&2; exit 1; }
else
  echo "[1/4] ใช้ repo ที่มีอยู่ + git pull..."
  git -C "$WORK_DIR" pull --ff-only -q 2>/dev/null || echo "  ⚠️ pull ไม่สำเร็จ — build จากโค้ดปัจจุบัน"
fi

# ── build ผ่าน Cloud Build (รันในเครือข่าย Google — กัน network gcr.io หลุด) ─
echo "[2/4] Build image ผ่าน Cloud Build: $IMAGE_TAG"
gcloud builds submit --config "$WORK_DIR/api/cloudbuild-bridge.yaml" \
  --project "$PROJECT_ID" "$WORK_DIR" || { echo "❌ build ล้มเหลว" >&2; exit 1; }

# ── Secret Manager: บันทึก TELEGRAM_BOT_TOKEN ──────────────────────────────
echo "[2.5/4] บันทึก TELEGRAM_BOT_TOKEN ลง Secret Manager..."
TMP_TOKEN="$(mktemp)"
printf '%s' "$TELEGRAM_BOT_TOKEN" > "$TMP_TOKEN"
if gcloud secrets describe "$SECRET_BOT" --project "$PROJECT_ID" >/dev/null 2>&1; then
  gcloud secrets versions add "$SECRET_BOT" --data-file="$TMP_TOKEN" --project "$PROJECT_ID" >/dev/null
  echo "  🔑 เพิ่ม version ใหม่: $SECRET_BOT"
else
  gcloud secrets create "$SECRET_BOT" --data-file="$TMP_TOKEN" --project "$PROJECT_ID" >/dev/null
  echo "  🔑 สร้าง secret ใหม่: $SECRET_BOT"
fi
rm -f "$TMP_TOKEN"

# ── MONITOR_WEBHOOK_TOKEN: อ่านจาก Secret Manager เดิม ถ้ามี (กัน channel URL เก่าแตก) ──
MONITOR_WEBHOOK_TOKEN="$(gcloud secrets versions access latest \
  --secret="$SECRET_MONITOR" --project "$PROJECT_ID" --format='get(payload.data)' 2>/dev/null || true)"
if [ -z "$MONITOR_WEBHOOK_TOKEN" ]; then
  MONITOR_WEBHOOK_TOKEN="$(openssl rand -hex 16)"
  TMP_TOKEN="$(mktemp)"
  printf '%s' "$MONITOR_WEBHOOK_TOKEN" > "$TMP_TOKEN"
  gcloud secrets create "$SECRET_MONITOR" --data-file="$TMP_TOKEN" --project "$PROJECT_ID" >/dev/null
  rm -f "$TMP_TOKEN"
  echo "  🔑 สร้าง MONITOR_WEBHOOK_TOKEN ใหม่ (${MONITOR_WEBHOOK_TOKEN:0:8}...)"
else
  echo "  🔑 ใช้ MONITOR_WEBHOOK_TOKEN เดิมจาก Secret Manager (${MONITOR_WEBHOOK_TOKEN:0:8}...)"
fi

# ── grant IAM: ให้ service account ของ Cloud Run อ่าน secret ได้ ────────────
echo "  ⚙️ grant Secret Accessor ให้ Cloud Run service account..."
SA="$(gcloud run services describe "$SERVICE_NAME" --region "$REGION" \
  --project "$PROJECT_ID" --format='value(spec.template.spec.serviceAccountName)' 2>/dev/null || true)"
if [ -z "$SA" ]; then
  PN="$(gcloud projects describe "$PROJECT_ID" --format='value(projectNumber)')"
  SA="${PN}-compute@developer.gserviceaccount.com"
  echo "  (service ยังไม่เคย deploy — ใช้ compute SA: $SA)"
fi
for SECRET in "$SECRET_BOT" "$SECRET_MONITOR"; do
  gcloud secrets add-iam-policy-binding "$SECRET" \
    --member="serviceAccount:$SA" --role="roles/secretmanager.secretAccessor" \
    --project "$PROJECT_ID" >/dev/null 2>&1 \
    && echo "  ✅ grant IAM: $SECRET" \
    || echo "  ⚠️ grant IAM ล้มเหลว ($SECRET) — ตรวจสิทธิ์ผู้ใช้ Cloud Shell"
done

# ── deploy ด้วย digest + secret mount (กัน Cloud Run cache tag) ─────────────
echo "[3/4] Deploy + ตั้ง secret/env..."
DIGEST="$(gcloud container images describe "$IMAGE_TAG" --format='value(image_summary.digest)')"
DEPLOY_IMAGE="${IMAGE_TAG%@*}@$DIGEST"
echo "  image: $DEPLOY_IMAGE"
gcloud run deploy "$SERVICE_NAME" \
  --image "$DEPLOY_IMAGE" \
  --platform managed \
  --region "$REGION" \
  --allow-unauthenticated \
  --project "$PROJECT_ID" \
  --set-secrets "TELEGRAM_BOT_TOKEN=$SECRET_BOT:latest,MONITOR_WEBHOOK_TOKEN=$SECRET_MONITOR:latest" \
  --set-env-vars "TELEGRAM_CHAT_ID=$TELEGRAM_CHAT_ID"

# ── verify: health + ทดสอบ webhook จริง → Telegram ─────────────────────────
echo "[4/4] Verify..."
sleep 10
H=$(curl -s --max-time 15 "$SERVICE_URL/health" || true)
echo "  /health → $H"
echo "$H" | grep -q '"healthy"' || { echo "  ❌ bridge ยังไม่พร้อม — ตรวจ log: gcloud logging read" >&2; exit 1; }
T=$(curl -s --max-time 20 -X POST "$SERVICE_URL/webhook?token=$MONITOR_WEBHOOK_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"incident":{"state":"OPEN","summary":"bridge deploy สำเร็จ (จาก deploy_bridge_cloudshell.sh)","condition_name":"test"}}')
echo "  webhook → $T"
echo "$T" | grep -q '"sent"' && echo "✅ Telegram ส่งแล้ว (เช็คแชทได้)" \
  || echo "  ⚠️ bridge รับได้แต่ส่ง Telegram ไม่ได้ — ตรวจ secret snc-telegram-bot-token"

echo ""
echo "✅ เสร็จสิ้น — Bridge: $SERVICE_URL"
echo "   ต่อไปรัน: bash ops/setup_cloud_monitoring.sh (ชี้ uptime alert ไปที่ bridge นี้)"