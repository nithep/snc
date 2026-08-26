@echo off
REM ============================================================================
REM deploy-to-pi.bat — Deploy SNC system to Raspberry Pi 4 from Windows
REM ============================================================================
REM ต้องการ: OpenSSH (scp/ssh) — ติดตั้งจาก Settings > Apps > Optional Features
REM
REM วิธีใช้:
REM   deploy-to-pi.bat                    deploy ไฟล์ทั้งหมด
REM   deploy-to-pi.bat --backend-only     deploy เฉพาะ backend
REM   deploy-to-pi.bat --status           ตรวจสถานะ
REM ============================================================================

set PI_HOST=pi4
set PI_USER=ecs-agent
set PI_ROOT=/home/ecs-agent/snc
set SSH_OPTS=-o ConnectTimeout=10 -o BatchMode=yes

echo ==========================================
echo SNC System Deployment to Pi 4
echo Target: %PI_USER%@%PI_HOST%
echo Root:   %PI_ROOT%
echo ==========================================
echo.

REM Check if scp is available
where scp >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: scp not found.
    echo Install OpenSSH: Settings ^> Apps ^> Optional Features ^> Add a feature ^> OpenSSH Client
    pause
    exit /b 1
)

REM Check SSH connectivity
echo [1/6] Checking SSH connectivity...
ssh %SSH_OPTS% %PI_USER%@%PI_HOST% "echo SSH_OK && hostname" >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Cannot SSH to %PI_HOST%
    echo Check: SSH key, ~/.ssh/config alias "pi4", Pi is online
    pause
    exit /b 1
)
echo [OK] SSH connected to %PI_HOST%
echo.

REM Deploy files
echo [2/6] Deploying API server...
scp %SSH_OPTS% api\server.py %PI_USER%@%PI_HOST%:%PI_ROOT%/api/server.py
if %ERRORLEVEL% NEQ 0 goto error

scp %SSH_OPTS% api\requirements.txt %PI_USER%@%PI_HOST%:%PI_ROOT%/api/requirements.txt
if %ERRORLEVEL% NEQ 0 goto error
echo [OK] API deployed

echo [3/6] Deploying dashboard...
scp %SSH_OPTS% app\index.html %PI_USER%@%PI_HOST%:%PI_ROOT%/app/index.html
if %ERRORLEVEL% NEQ 0 goto error
scp %SSH_OPTS% app\demo.html %PI_USER%@%PI_HOST%:%PI_ROOT%/app/demo.html
if %ERRORLEVEL% NEQ 0 goto error
echo [OK] Dashboard deployed

echo [4/6] Deploying PBX listener...
scp %SSH_OPTS% pbx\snc_pbx_listener.py %PI_USER%@%PI_HOST%:%PI_ROOT%/pbx/snc_pbx_listener.py
if %ERRORLEVEL% NEQ 0 goto error
echo [OK] PBX listener deployed

echo [5/6] Deploying ops scripts + systemd services...
scp %SSH_OPTS% ops\snc-backend.service %PI_USER%@%PI_HOST%:%PI_ROOT%/ops/snc-backend.service
scp %SSH_OPTS% ops\snc-pbx-listener.service %PI_USER%@%PI_HOST%:%PI_ROOT%/ops/snc-pbx-listener.service
scp %SSH_OPTS% ops\snc-tg-agent.service %PI_USER%@%PI_HOST%:%PI_ROOT%/ops/snc-tg-agent.service
scp %SSH_OPTS% ops\snc-cloudflared.service %PI_USER%@%PI_HOST%:%PI_ROOT%/ops/snc-cloudflared.service
scp %SSH_OPTS% ops\verify-system.sh %PI_USER%@%PI_HOST%:%PI_ROOT%/ops/verify-system.sh
scp %SSH_OPTS% ops\backup-snc-db.sh %PI_USER%@%PI_HOST%:%PI_ROOT%/ops/backup-snc-db.sh
scp %SSH_OPTS% ops\burnin-monitor.sh %PI_USER%@%PI_HOST%:%PI_ROOT%/ops/burnin-monitor.sh
echo [OK] Ops deployed

echo [6/6] Restarting services on Pi...
ssh %SSH_OPTS% %PI_USER%@%PI_HOST% "sudo systemctl daemon-reload && sudo systemctl restart snc-backend snc-pbx-listener && echo RESTART_OK"
if %ERRORLEVEL% NEQ 0 (
    echo [!] Service restart failed — check manually
    echo     ssh %PI_HOST% "sudo systemctl status snc-backend"
)
echo [OK] Services restarted
echo.

REM Verify
echo ==========================================
echo Verifying deployment...
echo ==========================================
ssh %SSH_OPTS% %PI_USER%@%PI_HOST% "sleep 2 && curl -s --max-time 5 http://localhost:8000/health"
echo.

echo ==========================================
echo Deployment Complete!
echo ==========================================
echo.
echo Dashboard:  https://snc.nithep.com
echo LAN:        http://192.168.1.94:8000
echo Health:     http://localhost:8000/health
echo.
echo Verify:     ssh %PI_HOST% "bash %PI_ROOT%/ops/verify-system.sh"
echo Logs:       ssh %PI_HOST% "sudo journalctl -u snc-backend -f"
echo.
pause
exit /b 0

:error
echo.
echo ==========================================
echo ERROR: Deployment failed!
echo ==========================================
echo.
echo Check:
echo   1. Pi is powered on and connected
echo   2. SSH key configured
echo   3. Files exist locally
echo.
pause
exit /b 1
