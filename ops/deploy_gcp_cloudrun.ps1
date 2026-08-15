# ============================================================================
# deploy_gcp_cloudrun.ps1 — SNC Cloud Run One-Shot Deploy (build + deploy + env)
# ----------------------------------------------------------------------------
# ใช้รันใน PowerShell ที่มี gcloud CLI (หรือ Cloud Shell: https://shell.cloud.google.com)
#
#   .\ops\deploy_gcp_cloudrun.ps1                              # deploy (key จาก env ถ้ามี)
#   $env:SNC_API_KEY="<key>"; .\ops\deploy_gcp_cloudrun.ps1   # deploy + ตั้ง key อัตโนมัติ
#
# โครงสร้าง 5-Core (doc/BLUEPRINT_5CORE.md): Dockerfile + server.py อยู่ที่ api/
# ============================================================================
$ErrorActionPreference = "Stop"

Write-Host "=======================================================" -ForegroundColor Green
Write-Host "🚀 SNC - GCP Cloud Run One-Shot Deploy" -ForegroundColor Green
Write-Host "=======================================================" -ForegroundColor Green

$PROJECT_ID   = "hotel-ecs-nithep"
$SERVICE_NAME = "snc-cloud-backend"
$REGION       = "asia-southeast1"
$IMAGE_TAG    = "gcr.io/$PROJECT_ID/${SERVICE_NAME}:latest"
$SERVICE_URL  = "https://snc-cloud-backend-59781590359.asia-southeast1.run.app"
$REPO_ROOT    = Split-Path -Parent $PSScriptRoot   # root ของ repo (ops/ อยู่ใต้ root)
$API_DIR      = Join-Path $REPO_ROOT "api"
$SNC_API_KEY  = $env:SNC_API_KEY

Write-Host "Target GCP Project : $PROJECT_ID" -ForegroundColor Yellow
Write-Host "Service            : $SERVICE_NAME" -ForegroundColor Yellow
Write-Host "Region             : $REGION" -ForegroundColor Yellow

# --- ตรวจ gcloud ---
if (-not (Get-Command gcloud -ErrorAction SilentlyContinue)) {
    Write-Host "`n❌ ไม่พบ gcloud CLI — ใช้ Cloud Shell (https://shell.cloud.google.com) หรือติดตั้ง Google Cloud SDK ก่อน" -ForegroundColor Red
    exit 1
}

# --- ตรวจ Dockerfile (5-Core: api/) ---
Write-Host "`n[Step 1] ตรวจ Dockerfile & SNC_API_KEY..." -ForegroundColor Cyan
if (Test-Path (Join-Path $API_DIR "Dockerfile")) {
    Write-Host "  ✅ Dockerfile found: api/Dockerfile" -ForegroundColor Green
} else {
    Write-Host "  ❌ Dockerfile missing: $API_DIR/Dockerfile" -ForegroundColor Red
    exit 1
}
if ($SNC_API_KEY) {
    Write-Host "  ✅ SNC_API_KEY ถูกตั้งจาก environment (ความยาว $($SNC_API_KEY.Length) chars)" -ForegroundColor Green
} else {
    Write-Host "  ⚠️ SNC_API_KEY ไม่ได้ตั้ง — จะ deploy โดยไม่ตั้ง key (POST ไร้ auth)" -ForegroundColor Yellow
}

# --- set project ---
Write-Host "`n[Step 2] ตั้งค่า project..." -ForegroundColor Cyan
gcloud config set project $PROJECT_ID

# --- build image ---
# build context = repo root (รวม app/ ตาม 5-Core — image ต้องมี dashboard)
Write-Host "`n[Step 3] Build image ($IMAGE_TAG)..." -ForegroundColor Cyan
Push-Location $REPO_ROOT
try {
    gcloud builds submit --config api/cloudbuild.yaml --project $PROJECT_ID
} finally {
    Pop-Location
}

# --- deploy + set env ---
# ⚠️ deploy ด้วย digest (sha256) ไม่ใช่ tag :latest — Cloud Run cache tag ไว้
# ถ้า deploy tag เดิมซ้ำจะไม่ re-resolve → ใช้ image เก่า
Write-Host "`n[Step 4] Deploy Cloud Run + ตั้ง env vars..." -ForegroundColor Cyan
$digest = (gcloud container images describe $IMAGE_TAG --format="value(image_summary.digest)" 2>$null).Trim()
$deployImage = $IMAGE_TAG
if ($digest) {
    $deployImage = "$($IMAGE_TAG.Split('@')[0])@$digest"
}
Write-Host "  image: $deployImage" -ForegroundColor Gray
$deployArgs = @(
    "run", "deploy", $SERVICE_NAME,
    "--image", $deployImage,
    "--platform", "managed",
    "--region", $REGION,
    "--allow-unauthenticated",
    "--project", $PROJECT_ID
)
if ($SNC_API_KEY) {
    $deployArgs += "--set-env-vars", "SNC_API_KEY=$SNC_API_KEY"
}
& gcloud @deployArgs
if ($LASTEXITCODE -ne 0) {
    Write-Host "`n❌ deploy ล้มเหลว (exit $LASTEXITCODE)" -ForegroundColor Red
    exit $LASTEXITCODE
}

# --- verify ---
Write-Host "`n[Step 5] Verify..." -ForegroundColor Cyan
Start-Sleep -Seconds 10
try {
    $health = Invoke-RestMethod -Uri "$SERVICE_URL/health" -TimeoutSec 15
    Write-Host "  ✅ /health: $($health.status)" -ForegroundColor Green
} catch {
    Write-Host "  ⚠️ /health ยังไม่พร้อม: $($_.Exception.Message)" -ForegroundColor Yellow
}
if ($SNC_API_KEY) {
    try {
        $resp = Invoke-WebRequest -Uri "$SERVICE_URL/api/events/acknowledge/9999" -Method POST -ContentType "application/json" -Body "{}" -TimeoutSec 15
        Write-Host "  ℹ️ POST (ไม่มี key) → HTTP $($resp.StatusCode) — auth อาจไม่เปิดใช้งาน" -ForegroundColor Yellow
    } catch {
        $code = $_.Exception.Response.StatusCode.value__
        if ($code -eq 401) {
            Write-Host "  ✅ Auth ทำงาน (POST ไม่มี key → 401)" -ForegroundColor Green
        } else {
            Write-Host "  ℹ️ ตรวจ auth ได้ผล: HTTP $code" -ForegroundColor Yellow
        }
    }
}

Write-Host "`n✅ Deploy เสร็จสิ้น — Service: $SERVICE_URL" -ForegroundColor Green
Write-Host "   จำไว้ว่า: แดชบอร์ดที่ใช้ Cloud Run ต้องกรอก key เดียวกับ SNC_API_KEY ในช่องตั้งค่า ⚙️" -ForegroundColor Gray
