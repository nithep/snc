# Cloud Run & Container Build Script for Smart Nurse Call (SNC)
# Target GCP Project: hotel-ecs-nithep
# Service Name: snc-cloud-backend

Write-Host "=======================================================" -ForegroundColor Green
Write-Host "🚀 Smart Nurse Call - GCP Cloud Run Deployment Package" -ForegroundColor Green
Write-Host "=======================================================" -ForegroundColor Green
Write-Host "Target GCP Project ID : hotel-ecs-nithep" -ForegroundColor Yellow
Write-Host "Service Name          : snc-cloud-backend" -ForegroundColor Yellow
Write-Host "Region                : asia-southeast1 (Bangkok/Singapore)" -ForegroundColor Yellow
Write-Host "-------------------------------------------------------"

$PROJECT_ID = "hotel-ecs-nithep"
$SERVICE_NAME = "snc-cloud-backend"
$REGION = "asia-southeast1"
$IMAGE_TAG = "gcr.io/$PROJECT_ID/${SERVICE_NAME}:latest"

Write-Host "`n[Step 1] Verifying Dockerfile & Requirements..." -ForegroundColor Cyan
if (Test-Path "./backend/Dockerfile") {
    Write-Host "  ✅ Dockerfile found." -ForegroundColor Green
} else {
    Write-Host "  ❌ Dockerfile missing in ./backend/" -ForegroundColor Red
    exit 1
}

Write-Host "`n[Step 2] Commands to execute on Google Cloud SDK / Cloud Shell:" -ForegroundColor Cyan
Write-Host "---------------------------------------------------------------" -ForegroundColor Gray
Write-Host "1) gcloud config set project $PROJECT_ID" -ForegroundColor White
Write-Host "2) cd ./api" -ForegroundColor White
Write-Host "3) gcloud builds submit --tag $IMAGE_TAG" -ForegroundColor White
Write-Host "4) gcloud run deploy $SERVICE_NAME --image $IMAGE_TAG --platform managed --region $REGION --allow-unauthenticated" -ForegroundColor White
Write-Host "---------------------------------------------------------------" -ForegroundColor Gray
Write-Host "`n✅ Build package prepared successfully!" -ForegroundColor Green
