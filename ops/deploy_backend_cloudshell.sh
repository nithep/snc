#!/usr/bin/env bash
# ============================================================================
# deploy_backend_cloudshell.sh — Deploy SNC Cloud Backend (snc-cloud-backend)
# ----------------------------------------------------------------------------
# วิธีใช้ (Cloud Shell):
#
#   export SNC_API_KEY="<key ตรงกับ api/.env บน Pi4>"
#   bash ops/deploy_backend_cloudshell.sh
#
# ทำอะไร:
#   - build ผ่าน Cloud Build จาก Dockerfile ใหม่ (multi-stage + nonroot + HEALTHCHECK)
#   - เก็บ SNC_API_KEY ลง Secret Manager (snc-api-key) — mount เป็น secret env
#     (ไม่เก็บ plaintext ใน --set-env-vars) ตาม ADR 0005
#   - grant IAM ให้ Cloud Run SA อ่าน secret
#   - deploy ด้วย digest (กัน Cloud Run cache image ตาม tag เก่า)
#   - verify: /health (db=firestore) + auth (ไม่มี key → 401)
#
# ความปลอดภัย:
#   - SNC_API_KEY ไม่ log/ไม่โชว์ — ผ่าน secret mount
#   - ใช้ digest แทน tag: https://gcr.io ดู handover 16 ส.ค. (กัน deploy image เก่า)
# ============================================================================
set -euo pipefail

PROJECT_ID="${GCP_PROJECT_ID:-hotel-ecs-nithep}"
SERVICE_NAME="snc-cloud-backend"
REGION="asia-southeast1"
IMAGE_TAG="gcr.io/$PROJECT_ID/$SERVICE_NAME:latest"
SERVICE_URL="https://snc-cloud-backend-59781590359.asia-southeast1.run.app"
REPO_URL="https://github.com/nithep/snc.git"
WORK_DIR="${WORK_DIR:-$HOME/snc}"

SECRET_API_KEY="snc-api-key"

echo "═══════════ SNC Cloud Backend Deploy ═══════════"
echo "Project : $PROJECT_ID"
echo "Service : $SERVICE_NAME ($REGION)"

# ── ตรวจ env ที่จำเป็น ─────────────────────────────────────────────────────
if [ -z "${SNC_API_KEY:-}" ]; then
  echo "❌ ต้อง export SNC_API_KEY ก่อน (key ตรงกับ api/.env บน Pi4)" >&2
  echo "   ดู: grep SNC_API_KEY /home/ecs-agent/snc-poc/api/.env" >&2
  exit 1
fi
echo "✅ SNC_API_KEY พร้อม (len ${#SNC_API_KEY})"

if ! command -v gcloud >/dev/null 2>&1; then
  echo "❌ ไม่พบ gcloud — ใช้ Cloud Shell (https://shell.cloud.google.com) เท่านั้น" >&2
  exit 1
fi
gcloud config set project "$PROJECT_ID" >/dev/null

# ── clone/update repo ──────────────────────────────────────────────────────
if [ ! -d "$WORK_DIR/api" ]; then
  echo "[1/5] Clone repo..."
  git clone "$REPO_URL" "$WORK_DIR" || { echo "❌ clone ล้มเหลว (GitHub auth?)" >&2; exit 1; }
else
  echo "[1/5] ใช้ repo ที่มีอยู่ + git pull..."
  git -C "$WORK_DIR" pull --ff-only -q 2>/dev/null || echo "  ⚠️ pull ไม่สำเร็จ — build จากโค้ดปัจจุบัน"
fi

# ── build ผ่าน Cloud Build (Dockerfile ใหม่: multi-stage + nonroot) ────────
echo "[2/5] Build image ผ่าน Cloud Build: $IMAGE_TAG"
gcloud builds submit --config "$WORK_DIR/api/cloudbuild.yaml" \
  --project "$PROJECT_ID" "$WORK_DIR" || { echo "❌ build ล้มเหลว" >&2; exit 1; }

# ── Secret Manager: เก็บ SNC_API_KEY (ไม่อยู่ใน env) ────────────────────────
echo "[3/5] บันทึก SNC_API_KEY ลง Secret Manager..."
TMP_KEY="$(mktemp)"
printf '%s' "$SNC_API_KEY" > "$TMP_KEY"
if gcloud secrets describe "$SECRET_API_KEY" --project "$PROJECT_ID" >/dev/null 2>&1; then
  gcloud secrets versions add "$SECRET_API_KEY" --data-file="$TMP_KEY" --project "$PROJECT_ID" >/dev/null
  echo "  🔑 เพิ่ม version ใหม่: $SECRET_API_KEY"
else
  gcloud secrets create "$SECRET_API_KEY" --data-file="$TMP_KEY" --project "$PROJECT_ID" >/dev/null
  echo "  🔑 สร้าง secret ใหม่: $SECRET_API_KEY"
fi
rm -f "$TMP_KEY"

# ── grant IAM: ให้ Cloud Run SA อ่าน secret ────────────────────────────────
echo "  ⚙️ grant Secret Accessor ให้ Cloud Run service account..."
SA="$(gcloud run services describe "$SERVICE_NAME" --region "$REGION" \
  --project "$PROJECT_ID" --format='value(spec.template.spec.serviceAccountName)' 2>/dev/null || true)"
if [ -z "$SA" ]; then
  PN="$(gcloud projects describe "$PROJECT_ID" --format='value(projectNumber)')"
  SA="${PN}-compute@developer.gserviceaccount.com"
  echo "  (service ยังไม่เคย deploy — ใช้ compute SA: $SA)"
fi
gcloud secrets add-iam-policy-binding "$SECRET_API_KEY" \
  --member="serviceAccount:$SA" --role="roles/secretmanager.secretAccessor" \
  --project "$PROJECT_ID" >/dev/null 2>&1 \
  && echo "  ✅ grant IAM: $SECRET_API_KEY" \
  || echo "  ⚠️ grant IAM ล้มเหลว — ตรวจสิทธิ์ผู้ใช้ Cloud Shell"

# ── deploy ด้วย digest + secret mount ──────────────────────────────────────
echo "[4/5] Deploy + ตั้ง secret/env..."
DIGEST="$(gcloud container images describe "$IMAGE_TAG" --format='value(image_summary.digest)')"
DEPLOY_IMAGE="${IMAGE_TAG%@*}@$DIGEST"
echo "  image: $DEPLOY_IMAGE"
gcloud run deploy "$SERVICE_NAME" \
  --image "$DEPLOY_IMAGE" \
  --platform managed \
  --region "$REGION" \
  --allow-unauthenticated \
  --project "$PROJECT_ID" \
  --set-secrets "SNC_API_KEY=$SECRET_API_KEY:latest" \
  --set-env-vars "SNC_DB_BACKEND=firestore"

# ── verify: health + auth fail-closed ──────────────────────────────────────
echo "[5/5] Verify..."
sleep 10
H=$(curl -s --max-time 15 "$SERVICE_URL/health" || true)
echo "  /health → $H"
echo "$H" | grep -q 'firestore' || { echo "  ❌ backend db≠firestore — ตรวจ env" >&2; exit 1; }

AUTH=$(curl -s --max-time 15 -o /dev/null -w "%{http_code}" \
  -X POST "$SERVICE_URL/api/events/trigger" \
  -H "Content-Type: application/json" -d '{}' || true)
echo "  POST trigger ไม่มี key → HTTP $AUTH (ควรเป็น 401)"
if [ "$AUTH" != "401" ]; then
  echo "  ⚠️ auth ยัง fail-open? ตรวจ SNC_API_KEY mount"
else
  echo "  ✅ auth fail-closed ทำงาน (401)"
fi

echo ""
echo "✅ เสร็จสิ้น — Backend: $SERVICE_URL"
echo "   Dashboard:  $SERVICE_URL/"
echo "   API Docs:   $SERVICE_URL/docs"
echo "   ต่อไป (ถ้ายังไม่ทำ): bash ops/deploy_bridge_cloudshell.sh + bash ops/setup_cloud_monitoring.sh"