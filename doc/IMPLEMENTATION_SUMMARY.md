# SNC System - Pi 4 Implementation Summary

## 🎯 Objectives Completed

### ✅ 1. Backend Server (Port 8000)
- **Status**: Configured and ready to deploy
- **Health Endpoint**: `http://localhost:8000/health`
- **Framework**: FastAPI with uvicorn
- **Features**:
  - REST API for event management
  - WebSocket for real-time updates
  - SQLite database for event storage
  - SLA tracking and analytics
  - Static file serving for dashboard

### ✅ 2. PBX Listener (192.168.1.91:23)
- **Target**: Phonik PBX at 192.168.1.91:23 (Telnet)
- **Script**: `snc_pbx_listener.py`
- **Features**:
  - Async Telnet connection with auto-reconnect
  - SMDR log parsing with regex patterns
  - Temporal event memory (90-second window)
  - Event classification (CALL_BEDSIDE, CALL_BATHROOM_EMERGENCY, etc.)
  - HTTP POST to backend API
  - Proper logging and error handling

### ✅ 3. Firewall/PBX Connectivity Testing
- **Diagnostic Script**: `test-pbx-connectivity.sh`
- **Tests Performed**:
  - Network reachability (ping)
  - TCP port connectivity (port 23)
  - Firewall rules verification
  - Manual telnet connection test
  - Subnet configuration check
- **Troubleshooting Guidance**: Included for common issues

### ✅ 4. Web-Based Dashboard
- **File**: `dashboard-status.html`
- **Access**: `http://192.168.1.94:8000/dashboard-status.html`
- **Features**:
  - Three separate status cards:
    1. Backend Server (FastAPI)
    2. PBX Listener (Python process)
    3. PBX Stream (Telnet connectivity)
  - Real-time updates every 10 seconds
  - Color-coded indicators (Green/Yellow/Red)
  - Response time metrics
  - Quick action buttons
  - Mobile-responsive design

### ✅ 5. Status Indicators with Timeout/ACK Logic

#### Backend Status
- **Check Method**: HTTP GET /health with 5s timeout
- **States**:
  - ✅ RUNNING: HTTP 200, response < 5s
  - ❌ DOWN: Timeout or non-200 response

#### PBX Listener Status
- **Check Method**: Process detection + log analysis
- **States**:
  - ✅ RUNNING: Process active, "Connected successfully" in logs
  - ⚠️ Reconnecting: Process running, "Retrying" in logs
  - ❌ STOPPED: Process not found

#### PBX Stream Status
- **Check Method**: TCP connection test with 3s timeout
- **States**:
  - ✅ ACCESSIBLE: Port 23 open, events flowing
  - ⚠️ CONFIGURED: Port open but no events yet
  - ❌ BLOCKED: Connection timeout

## 📁 Files Created/Modified

### New Scripts (Deploy to Pi)
1. **start-snc-system.sh** - Main startup script
   - Checks PBX connectivity before starting
   - Starts backend and waits for health check
   - Starts PBX listener
   - Displays PIDs and log locations
   
2. **monitor-snc-status.sh** - Real-time terminal monitor
   - Updates every 10 seconds
   - Shows all three component statuses
   - Color-coded output
   - Overall system health summary

3. **test-pbx-connectivity.sh** - Diagnostic tool
   - 6-step connectivity test
   - Firewall rule checking
   - Troubleshooting recommendations

4. **verify-installation.sh** - Quick verification
   - Automated test suite
   - Pass/fail reporting
   - Troubleshooting hints

5. **deploy-to-pi.bat** - Windows deployment script
   - SCP file transfer
   - Error handling
   - Next steps guidance

### Modified Files
1. **api/server.py**
   - Added static file mounting
   - Added `/dashboard-status.html` endpoint
   - Created public directory for static assets

### Documentation
1. **DEPLOYMENT_PI4.md** - Complete deployment guide
   - Prerequisites and installation
   - Step-by-step deployment
   - Troubleshooting section
   - Service management commands
   - Architecture diagram

2. **dashboard-status.html** - Web-based monitoring UI
   - Responsive design
   - Real-time status updates
   - API integration

## 🚀 Deployment Sequence on Pi 4

### Step 1: Copy Files to Pi
```bash
# From Windows (PowerShell/CMD)
cd C:\Users\Nithep\ไดรฟ์ของฉัน (cnithep@gmail.com)\Hotel-ECS\snc-poc
deploy-to-pi.bat

# Or manually via SCP
scp *.sh pi@192.168.1.94:/home/ecs-agent/snc-poc/
scp dashboard-status.html pi@192.168.1.94:/home/ecs-agent/snc-poc/
scp DEPLOYMENT_PI4.md pi@192.168.1.94:/home/ecs-agent/snc-poc/
```

### Step 2: SSH into Pi
```bash
ssh pi@192.168.1.94
cd /home/ecs-agent/snc-poc
chmod +x *.sh
```

### Step 3: Test PBX Connectivity
```bash
./test-pbx-connectivity.sh
```

**Expected Results:**
- ✓ Network Reachability: PASS
- ✓ TCP Port Connectivity: PASS  
- ✓ Manual Connection Test: PASS (should see SMDR data streaming)

**If FAIL:**
- Check PBX telnet is enabled
- Verify SMDR output configured
- Check firewall: `sudo ufw allow out 23/tcp`

### Step 4: Start SNC System
```bash
./start-snc-system.sh
```

**What Happens:**
1. Checks PBX connectivity
2. Starts backend on port 8000
3. Waits for health check (max 20s)
4. Starts PBX listener
5. Shows status summary

### Step 5: Verify Operation
```bash
# Option A: Run verification script
./verify-installation.sh

# Option B: Manual checks
curl http://localhost:8000/health
tail -f /home/ecs-agent/snc-poc/pbx_listener.log
```

### Step 6: Access Dashboard
From any device on network:
```
http://192.168.1.94:8000/dashboard-status.html
```

Or from Pi terminal:
```bash
./monitor-snc-status.sh
```

## 🔍 Monitoring & Maintenance

### View Logs
```bash
# Backend logs
tail -f /home/ecs-agent/snc-poc/backend.log

# PBX listener logs
tail -f /home/ecs-agent/snc-poc/pbx_listener.log

# Both logs simultaneously
tail -f /home/ecs-agent/snc-poc/*.log
```

### Check Processes
```bash
# All SNC processes
ps aux | grep -E 'uvicorn|snc_pbx'

# Backend only
pgrep -f "uvicorn.*server:app"

# PBX listener only
pgrep -f "snc_pbx_listener"
```

### Restart Services
```bash
# Stop all
pkill -f "uvicorn.*server:app"
pkill -f "snc_pbx_listener"

# Start all
./start-snc-system.sh
```

### Test Event Flow
```bash
# Trigger test event
curl -X POST http://localhost:8000/api/events/trigger \
  -H "Content-Type: application/json" \
  -d '{"room_id":"400","event_type":"CALL_BEDSIDE"}'

# Check events
curl http://localhost:8000/api/events | python3 -m json.tool
```

## 🎨 Dashboard Features

### Status Cards Display

**Backend Server Card:**
- Process status (RUNNING/DOWN)
- Health endpoint URL
- Response time in ms
- Service name from health check

**PBX Listener Card:**
- Process status (RUNNING/STOPPED)
- Connection state from logs
- Last activity timestamp
- Total events processed

**PBX Stream Card:**
- TCP connectivity (ACCESSIBLE/BLOCKED)
- Target IP and port
- Latency measurement
- Data flow status (Active/Idle)

### Overall System Status
- ✅ ALL SYSTEMS OPERATIONAL (all green)
- ⚠️ PARTIAL (some yellow)
- ❌ SYSTEM DOWN (any red)

### Auto-Refresh
- Updates every 10 seconds
- Timestamp shows last update
- No page reload needed

## 🛠️ Troubleshooting Common Issues

### Issue: Backend won't start
```bash
# Check if port 8000 is in use
sudo lsof -i :8000

# Kill existing process
pkill -f "uvicorn.*server:app"

# Check Python dependencies
pip3 list | grep -E "fastapi|uvicorn"

# View error logs
cat /home/ecs-agent/snc-poc/backend.log
```

### Issue: PBX listener can't connect
```bash
# Test connectivity
telnet 192.168.1.91 23

# If connection refused:
# 1. Enable telnet on PBX web interface
# 2. Enable SMDR output
# 3. Check PBX firewall

# Check Pi firewall
sudo iptables -L | grep 23
sudo ufw allow out 23/tcp
```

### Issue: No events appearing
```bash
# Verify listener is running
ps aux | grep snc_pbx_listener

# Check recent logs
tail -50 /home/ecs-agent/snc-poc/pbx_listener.log | grep "SNC Event"

# Test manual event
curl -X POST http://localhost:8000/api/events/trigger \
  -H "Content-Type: application/json" \
  -d '{"room_id":"400","event_type":"CALL_BEDSIDE"}'

# Verify backend received it
curl http://localhost:8000/api/events
```

### Issue: Dashboard not loading
```bash
# Check if HTML file exists
ls -la /home/ecs-agent/snc-poc/app/dashboard-status.html

# Copy if missing
cp /home/ecs-agent/snc-poc/dashboard-status.html \
   /home/ecs-agent/snc-poc/app/

# Test direct access
curl http://localhost:8000/dashboard-status.html
```

## 📊 Architecture Overview

```
┌─────────────────────────────────────────────────────┐
│                  Raspberry Pi 4                      │
│                                                      │
│  ┌──────────────┐     ┌──────────────────────┐      │
│  │  Phonik PBX  │────▶│   PBX Listener       │      │
│  │ 192.168.1.91 │Telnet│   (snc_pbx_listener) │      │
│  │   Port 23    │◀────│   - Auto-reconnect   │      │
│  └──────────────┘     │   - SMDR parsing     │      │
│                       │   - Event forwarding │      │
│                       └──────────┬───────────┘      │
│                                  │ HTTP POST        │
│                                  ▼                  │
│                       ┌──────────────────────┐      │
│                       │   Backend API        │      │
│                       │   (FastAPI :8000)    │      │
│                       │   - Health check     │      │
│                       │   - Event storage    │      │
│                       │   - WebSocket        │      │
│                       │   - REST API         │      │
│                       └──────────┬───────────┘      │
│                                  │                  │
│              ┌───────────────────┼──────────────┐   │
│              ▼                   ▼              ▼   │
│     ┌──────────────┐   ┌──────────┐   ┌──────────┐│
│     │  SQLite DB   │   │ WebSocket│   │  Static  ││
│     │  (Events)    │   │ Broadcast│   │  Files   ││
│     └──────────────┘   └──────────┘   └────┬─────┘│
│                                            │      │
└────────────────────────────────────────────┼──────┘
                                             │
                                    ┌────────▼────────┐
                                    │  Web Browser    │
                                    │  Dashboard      │
                                    │  (Auto-refresh) │
                                    └─────────────────┘
```

## 🎯 Success Criteria Checklist

- [ ] Backend responds to `curl http://localhost:8000/health`
- [ ] PBX listener shows "Connected successfully to Phonik PBX!"
- [ ] Firewall allows TCP port 23 outbound
- [ ] PBX SMDR/Telnet output is enabled
- [ ] Dashboard accessible at `http://192.168.1.94:8000/dashboard-status.html`
- [ ] Three separate status indicators visible (Backend, Listener, Stream)
- [ ] Status updates with timeout/ACK logic (not static "Connected")
- [ ] Events flow from PBX → Listener → Backend → Dashboard
- [ ] All scripts executable and working
- [ ] Logs being written to `/home/ecs-agent/snc-poc/`

## 📞 Support Resources

- **API Documentation**: http://192.168.1.94:8000/docs (Swagger UI)
- **Events API**: http://192.168.1.94:8000/api/events
- **Analytics**: http://192.168.1.94:8000/api/analytics/kpi
- **Deployment Guide**: See DEPLOYMENT_PI4.md
- **Logs Location**: /home/ecs-agent/snc-poc/

## 🔄 Next Steps for Production

1. **Set up systemd services** for auto-start on boot
2. **Configure log rotation** to prevent disk fill
3. **Add HTTPS** with Let's Encrypt certificate
4. **Set up reverse proxy** (nginx) for better performance
5. **Configure monitoring alerts** (email/SMS on failures)
6. **Add authentication** to dashboard
7. **Set up backup** for SQLite database
8. **Configure NTP** for accurate timestamps

---

**Version**: 1.0  
**Last Updated**: 2024  
**Target Platform**: Raspberry Pi 4 (Raspbian/Debian)  
**Network**: 192.168.1.x subnet  
