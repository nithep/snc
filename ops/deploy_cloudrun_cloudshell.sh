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
  echo "      อัปเดตโค้ดให้ล่าสุด (git pull)..."
  git -C "$WORK_DIR" pull --ff-only -q 2>/dev/null \
    || echo "      ⚠️ pull ไม่สำเร็จ (มี local change?) — build จากโค้ดปัจจุบัน"
fi

# ── fail-fast: ตรวจว่าโค้ดเป็นเวอร์ชันที่ image มี app/ (5-Core) ─────────────
if ! grep -q 'COPY app/ app/' "$WORK_DIR/api/Dockerfile" 2>/dev/null; then
  echo "❌ $WORK_DIR/api/Dockerfile ยังเป็นเวอร์ชันเก่า (ไม่มี 'COPY app/ app/')" >&2
  echo "   image ที่ build จะไม่มี dashboard — รัน 'git -C $WORK_DIR pull' แล้วลองใหม่" >&2
  exit 1
fi
if [ ! -f "$WORK_DIR/app/index.html" ]; then
  echo "❌ ไม่พบ $WORK_DIR/app/index.html — build context ต้องเป็น repo root ที่มี app/" >&2
  exit 1
fi
echo "✅ โค้ดพร้อม build (Dockerfile ใหม่ + app/index.html ครบ)"

# ── set project ───────────────────────────────────────────────────────────
echo "[2/4] gcloud config set project $PROJECT_ID"
gcloud config set project "$PROJECT_ID"

# ── build + push image ─────────────────────────────────────────────────────
# ใช้ docker push ผ่านสิทธิ์ของ user ก่อน (Cloud Shell มี docker — กันปัญหา
# default compute SA ไม่มี artifactregistry.repositories.createOnPush / logWriter)
# ถ้าไม่มี docker → fallback ไป gcloud builds submit (ต้อง grant IAM ให้ SA)
echo "[3/4] Build + push image: $IMAGE_TAG"
if command -v docker >/dev/null 2>&1; then
  echo "  วิธี: docker build (context=repo root, รวม app/) + docker push"
  docker build -t "$IMAGE_TAG" -f "$WORK_DIR/api/Dockerfile" "$WORK_DIR" || { echo "❌ docker build ล้มเหลว" >&2; exit 1; }
  gcloud auth configure-docker -q || true
  # Cloud Shell บางครั้ง connection ไป gcr.io หลุดชั่วคราว — ลองใหม่ 3 ครั้ง
  PUSHED=0
  for i in 1 2 3; do
    if docker push "$IMAGE_TAG"; then PUSHED=1; break; fi
    echo "  ⚠️ docker push ครั้งที่ $i ล้มเหลว — ลองใหม่ใน 10 วิ..." >&2
    sleep 10
  done
  [ "$PUSHED" = "1" ] || { echo "❌ docker push ล้มเหลว (ลอง 3 ครั้งแล้ว)" >&2; exit 1; }
else
  echo "  วิธี: gcloud builds submit (cloudbuild.yaml — context root รวม app/)"
  gcloud builds submit --config "$WORK_DIR/api/cloudbuild.yaml" --project "$PROJECT_ID" "$WORK_DIR" || { echo "❌ gcloud builds submit ล้มเหลว" >&2; exit 1; }
fi

# ── deploy + set env ──────────────────────────────────────────────────────
echo "[4/4] Deploy + ตั้ง SNC_API_KEY"
# ⚠️ ต้อง deploy ด้วย digest (sha256) ไม่ใช่ tag :latest — Cloud Run cache tag ไว้
# ถ้า deploy tag เดิมซ้ำจะไม่ re-resolve → ใช้ image เก่า (เจอจริง 07/2569)
IMAGE_DIGEST="$(gcloud container images describe "$IMAGE_TAG" --format='value(image_summary.digest)' 2>/dev/null || true)"
DEPLOY_IMAGE="$IMAGE_TAG"
if [ -n "$IMAGE_DIGEST" ]; then
  DEPLOY_IMAGE="${IMAGE_TAG%@*}@${IMAGE_DIGEST}"
fi
echo "  image: $DEPLOY_IMAGE"
gcloud run deploy "$SERVICE_NAME" \
  --image "$DEPLOY_IMAGE" \
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
# ตรวจ dashboard: GET / ต้องเป็น 200 HTML (ไม่ใช่ 307/error)
ROOT_CODE=$(curl -s -o /dev/null -w '%{http_code}' --max-time 15 "$SERVICE_URL/" || true)
if [ "$ROOT_CODE" = "200" ]; then
  echo "  ✅ Dashboard / → HTTP 200"
else
  echo "  ❌ Dashboard / → HTTP $ROOT_CODE (ควรเป็น 200 — image อาจไม่มี app/ ตรวจ Dockerfile)" >&2
  exit 1
fi

echo ""
echo "✅ เสร็จสิ้น — Service: $SERVICE_URL"
echo "   แดชบอร์ดที่ใช้ Cloud Run ต้องกรอก key เดียวกันใน ⚙️ ตั้งค่า"
