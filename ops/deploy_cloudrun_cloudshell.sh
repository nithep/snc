#!/usr/bin/env bash
# ============================================================================
# deploy_cloudrun_cloudshell.sh — Cloud Run One-Shot Deploy (สำหรับ Cloud Shell)
# ----------------------------------------------------------------------------
# วิธีใช้ (เปิด https://shell.cloud.google.com แล้ววาง/รัน):
#
#   export SNC_API_KEY="<key ใหม่จากคู่มือ rotate>"
#   bash ops/deploy_cloudrun_cloudshell.sh
#
# หรือรันแบบครั้งเดียว:
#   SNC_API_KEY="<key>" bash ops/deploy_cloudrun_cloudshell.sh
#
# สคริปต์จะ: clone repo (ถ้ายังไม่มี) → build image → deploy + ตั้ง SNC_API_KEY
# อ้างอิง: doc/BLUEPRINT_5CORE.md, doc/wiki/SNC_API_KEY_ROTATION_GUIDE.md
# ============================================================================
set -euo pipefail

PROJECT_ID="${GCP_PROJECT_ID:-hotel-ecs-nithep}"
SERVICE_NAME="snc-cloud-backend"
REGION="asia-southeast1"
IMAGE_TAG="gcr.io/$PROJECT_ID/$SERVICE_NAME:latest"
SERVICE_URL="https://snc-cloud-backend-59781590359.asia-southeast1.run.app"
REPO_URL="https://github.com/nithep/snc.git"
WORK_DIR="${WORK_DIR:-$HOME/snc}"

echo "═══════════ Cloud Run One-Shot Deploy ═══════════"
echo "Project : $PROJECT_ID"
echo "Service : $SERVICE_NAME ($REGION)"

# ── ตรวจ key ─────────────────────────────────────────────────────────────
if [ -z "${SNC_API_KEY:-}" ]; then
  echo "❌ ยังไม่ได้ตั้ง SNC_API_KEY — ดู doc/wiki/SNC_API_KEY_ROTATION_GUIDE.md" >&2
  exit 1
fi
echo "✅ SNC_API_KEY พร้อม (len ${#SNC_API_KEY})"

# ── ตรวจ gcloud ──────────────────────────────────────────────────────────
if ! command -v gcloud >/dev/null 2>&1; then
  echo "❌ ไม่พบ gcloud — ใช้ Cloud Shell (https://shell.cloud.google.com) เท่านั้น" >&2
  exit 1
fi

# ── clone repo (ถ้ายังไม่มี) ───────────────────────────────────────────────
if [ ! -d "$WORK_DIR/api" ]; then
  echo ""
  echo "[1/4] Clone repo..."
  git clone "$REPO_URL" "$WORK_DIR" || { echo "❌ clone ล้มเหลว (repo อาจเป็น private — ต้องมี GitHub auth)" >&2; exit 1; }
else
  echo "[1/4] ใช้ repo ที่มีอยู่: $WORK_DIR"
fi

# ── set project ───────────────────────────────────────────────────────────
echo "[2/4] gcloud config set project $PROJECT_ID"
gcloud config set project "$PROJECT_ID"

# ── build image ───────────────────────────────────────────────────────────
echo "[3/4] Build image: $IMAGE_TAG"
gcloud builds submit --tag "$IMAGE_TAG" --project "$PROJECT_ID" "$WORK_DIR/api"

# ── deploy + set env ──────────────────────────────────────────────────────
echo "[4/4] Deploy + ตั้ง SNC_API_KEY"
gcloud run deploy "$SERVICE_NAME" \
  --image "$IMAGE_TAG" \
  --platform managed \
  --region "$REGION" \
  --allow-unauthenticated \
  --project "$PROJECT_ID" \
  --set-env-vars "SNC_API_KEY=$SNC_API_KEY"

# ── verify ────────────────────────────────────────────────────────────────
echo ""
echo "Verify..."
sleep 10
HEALTH=$(curl -s --max-time 15 "$SERVICE_URL/health" || true)
echo "  /health → $HEALTH"
CODE=$(curl -s -o /dev/null -w '%{http_code}' --max-time 15 \
  -X POST "$SERVICE_URL/api/events/acknowledge/9999" \
  -H 'Content-Type: application/json' -d '{}')
if [ "$CODE" = "401" ]; then
  echo "  ✅ Auth ทำงาน (POST ไม่มี key → 401)"
else
  echo "  ⚠️ POST ไม่มี key → HTTP $CODE (ตรวจสอบว่าอาจต้อง redeploy image ใหม่)"
fi

echo ""
echo "✅ เสร็จสิ้น — Service: $SERVICE_URL"
echo "   แดชบอร์ดที่ใช้ Cloud Run ต้องกรอก key เดียวกันใน ⚙️ ตั้งค่า"
