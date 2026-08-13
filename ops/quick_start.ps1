# Quick Start Script for Smart Nurse Call (SNC) System - Windows PowerShell
# Usage: .\quick_start.ps1

Write-Host "🏥 Smart Nurse Call (SNC) - Quick Start" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if Python is installed
try {
    $pythonVersion = python --version 2>&1
    Write-Host "✅ Python found: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ Python is not installed. Please install Python 3.10+" -ForegroundColor Red
    exit 1
}

# Install Backend dependencies
Write-Host ""
Write-Host "📦 Installing Backend dependencies..." -ForegroundColor Yellow
Set-Location backend
pip install fastapi uvicorn aiohttp websockets pydantic | Out-Null
Write-Host "✅ Backend dependencies installed" -ForegroundColor Green

# Install PBX Connector dependencies
Write-Host ""
Write-Host "📦 Installing PBX Connector dependencies..." -ForegroundColor Yellow
Set-Location ../pbx-connector
pip install -r requirements.txt | Out-Null
Write-Host "✅ PBX Connector dependencies installed" -ForegroundColor Green

Set-Location ..

Write-Host ""
Write-Host "🚀 Starting Services..." -ForegroundColor Yellow
Write-Host ""

# Start Backend Server
Write-Host "1️⃣  Starting Backend Server on port 8000..." -ForegroundColor Yellow
$backendJob = Start-Job -ScriptBlock {
    Set-Location "backend"
    python server.py
} -Name "BackendServer"
Write-Host "   ✅ Backend started (Job ID: $($backendJob.Id))" -ForegroundColor Green

# Wait for Backend to start
Write-Host "   ⏱️  Waiting for Backend to initialize..." -ForegroundColor Gray
Start-Sleep -Seconds 5

# Check if Backend is running
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8000/health" -UseBasicParsing -TimeoutSec 3
    if ($response.StatusCode -eq 200) {
        Write-Host "   ✅ Backend is healthy" -ForegroundColor Green
    }
} catch {
    Write-Host "   ❌ Backend failed to start. Check logs for details" -ForegroundColor Red
    Stop-Job -Id $backendJob.Id
    exit 1
}

# Start PBX Listener
Write-Host ""
Write-Host "2️⃣  Starting PBX Listener..." -ForegroundColor Yellow
Write-Host "   ℹ️  Note: This will attempt to connect to PBX at 192.168.1.91:23" -ForegroundColor Gray
Write-Host "   ℹ️  If PBX is not available, the listener will retry every 5 seconds" -ForegroundColor Gray
$pbxJob = Start-Job -ScriptBlock {
    Set-Location "pbx-connector"
    python snc_pbx_listener.py
} -Name "PBXListener"
Write-Host "   ✅ PBX Listener started (Job ID: $($pbxJob.Id))" -ForegroundColor Green

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "🎉 All services started successfully!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "📊 Service Status:" -ForegroundColor Cyan
Write-Host "   • Backend API: http://localhost:8000" -ForegroundColor White
Write-Host "   • Health Check: http://localhost:8000/health" -ForegroundColor White
Write-Host "   • WebSocket: ws://localhost:8000/ws/nurse-station" -ForegroundColor White
Write-Host ""
Write-Host "🌐 Frontend Dashboard:" -ForegroundColor Cyan
Write-Host "   • Open: app/index.html in your browser" -ForegroundColor White
Write-Host "   • Or run: npx serve app" -ForegroundColor White
Write-Host ""
Write-Host "🧪 Run Integration Tests:" -ForegroundColor Cyan
Write-Host "   cd api && python integration_test.py" -ForegroundColor White
Write-Host ""
Write-Host "🛑 Stop Services:" -ForegroundColor Cyan
Write-Host "   Stop-Job -Id $($backendJob.Id), $($pbxJob.Id)" -ForegroundColor White
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Press Ctrl+C to stop all services..." -ForegroundColor Yellow

# Keep script running
try {
    while ($true) {
        Start-Sleep -Seconds 1
        
        # Check if jobs are still running
        $backendState = Get-Job -Id $backendJob.Id
        $pbxState = Get-Job -Id $pbxJob.Id
        
        if ($backendState.State -ne "Running" -or $pbxState.State -ne "Running") {
            Write-Host ""
            Write-Host "⚠️  One or more services have stopped" -ForegroundColor Yellow
            break
        }
    }
} finally {
    Write-Host ""
    Write-Host "Stopping services..." -ForegroundColor Yellow
    Stop-Job -Id $backendJob.Id -ErrorAction SilentlyContinue
    Stop-Job -Id $pbxJob.Id -ErrorAction SilentlyContinue
    Remove-Job -Id $backendJob.Id -ErrorAction SilentlyContinue
    Remove-Job -Id $pbxJob.Id -ErrorAction SilentlyContinue
    Write-Host "Services stopped." -ForegroundColor Green
}
