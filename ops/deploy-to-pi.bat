@echo off
REM Deploy SNC scripts to Raspberry Pi 4
REM Update PI_IP with your Pi's IP address

set PI_IP=192.168.1.94
set PI_USER=pi
set REMOTE_DIR=/home/ecs-agent/snc-poc

echo ==========================================
echo SNC System Deployment to Pi 4
echo Target: %PI_USER%@%PI_IP%
echo ==========================================
echo.

REM Check if scp is available
where scp >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: scp not found. Please install OpenSSH client.
    echo Download from: https://github.com/PowerShell/Win32-OpenSSH/releases
    pause
    exit /b 1
)

echo [1/5] Copying startup script...
scp start-snc-system.sh %PI_USER%@%PI_IP%:%REMOTE_DIR%/
if %ERRORLEVEL% NEQ 0 goto error

echo [2/5] Copying monitoring script...
scp monitor-snc-status.sh %PI_USER%@%PI_IP%:%REMOTE_DIR%/
if %ERRORLEVEL% NEQ 0 goto error

echo [3/5] Copying diagnostic script...
scp test-pbx-connectivity.sh %PI_USER%@%PI_IP%:%REMOTE_DIR%/
if %ERRORLEVEL% NEQ 0 goto error

echo [4/5] Copying dashboard HTML...
scp dashboard-status.html %PI_USER%@%PI_IP%:%REMOTE_DIR%/
if %ERRORLEVEL% NEQ 0 goto error

echo [5/5] Copying deployment guide...
scp DEPLOYMENT_PI4.md %PI_USER%@%PI_IP%:%REMOTE_DIR%/
if %ERRORLEVEL% NEQ 0 goto error

echo.
echo ==========================================
echo Deployment Complete!
echo ==========================================
echo.
echo Next steps on Pi 4:
echo   ssh %PI_USER%@%PI_IP%
echo   cd %REMOTE_DIR%
echo   chmod +x *.sh
echo   ./test-pbx-connectivity.sh
echo   ./start-snc-system.sh
echo.
echo Access dashboard: http://%PI_IP%:8000/dashboard-status.html
echo.
pause
exit /b 0

:error
echo.
echo ==========================================
echo ERROR: Deployment failed!
echo ==========================================
echo.
echo Please check:
echo   1. Pi is powered on and connected to network
echo   2. IP address is correct (%PI_IP%)
echo   3. SSH is enabled on Pi
echo   4. Network connectivity (ping %PI_IP%)
echo.
pause
exit /b 1
