---
title: "🏥 Smart Nurse Call System - Pi 4 Complete Deployment Package"
type: raw
tags: [deploy, ops]
---

# 🏥 Smart Nurse Call System - Pi 4 Complete Deployment Package

## 📦 What's Included

This deployment package provides everything needed to run the SNC system on Raspberry Pi 4 with comprehensive monitoring and status tracking.

### Core Components

1. **Backend Server** (FastAPI, Port 8000)
   - REST API for event management
   - WebSocket for real-time updates
   - SQLite database with SLA tracking
   - Health check endpoint

2. **PBX Listener** (Python Async)
   - Telnet connection to Phonik PBX (192.168.1.91:23)
   - SMDR log parsing and classification
   - Auto-reconnect with retry logic
   - Event forwarding to backend

3. **Status Monitoring** (Multi-layered)
   - Web-based dashboard with auto-refresh
   - Terminal-based real-time monitor
   - Interactive log viewer
   - Diagnostic and verification tools

### Key Features

✅ **Separate Status Indicators**
- Backend Server status (HTTP health check with 5s timeout)
- PBX Listener status (process + log analysis)
- PBX Stream status (TCP connectivity with 3s timeout)

✅ **Timeout/ACK Logic**
- Not static "Connected" messages
- Real-time health checking
- Automatic reconnection attempts
- Visual status changes (Green/Yellow/Red)

✅ **Comprehensive Tooling**
- Startup automation
- Continuous monitoring
- Connectivity diagnostics
- Log analysis
- Quick verification

## 📁 File Inventory

| File | Purpose | Deploy to Pi? |
|------|---------|---------------|
| `start-snc-system.sh` | Main startup script | ✅ Yes |
| `monitor-snc-status.sh` | Real-time terminal monitor | ✅ Yes |
| `test-pbx-connectivity.sh` | Network/PBX diagnostics | ✅ Yes |
| `verify-installation.sh` | Automated test suite | ✅ Yes |
| `view-logs.sh` | Interactive log viewer | ✅ Yes |
| `dashboard-status.html` | Web-based status dashboard | ✅ Yes |
| `deploy-to-pi.bat` | Windows deployment script | ❌ No (run on Windows) |
| `DEPLOYMENT_PI4.md` | Full deployment guide | Optional |
| `IMPLEMENTATION_SUMMARY.md` | Technical details | Optional |
| `QUICK_REFERENCE.md` | Quick command reference | Optional |
| `DEPLOYMENT_CHECKLIST.md` | Step-by-step checklist | Optional |

## 🚀 Quick Start Guide

### Step 1: Deploy Files to Pi

**Option A: Use Deployment Script (Windows)**
```bash
deploy-to-pi.bat
```

**Option B: Manual SCP**
```bash
scp *.sh pi@192.168.1.94:/home/ecs-agent/snc-poc/
scp dashboard-status.html pi@192.168.1.94:/home/ecs-agent/snc-poc/
```

### Step 2: SSH to Pi and Prepare
```bash
ssh pi@192.168.1.94
cd /home/ecs-agent/snc-poc
chmod +x *.sh
```

### Step 3: Test PBX Connectivity
```bash
./test-pbx-connectivity.sh
```
**Must see**: All tests PASS, especially port 23 connectivity

### Step 4: Start System
```bash
./start-snc-system.sh
```
**Look for**: 
- Backend health check OK
- PBX listener connected
- PIDs displayed

### Step 5: Access Dashboard
Open browser: `http://192.168.1.94:8000/dashboard-status.html`

**Verify**: Three status cards showing green indicators

## 🎯 Success Verification

Run the automated test:
```bash
./verify-installation.sh
```

Expected output: All tests PASS ✅

Manual checks:
```bash
# Backend responding?
curl http://localhost:8000/health

# PBX connected?
grep "Connected successfully" /home/ecs-agent/snc-poc/pbx_listener.log

# Events working?
curl http://localhost:8000/api/events
```

## 📊 Understanding the Status Dashboard

The web dashboard shows three critical components:

### 1. Backend Server (FastAPI)
- **What it does**: Handles API requests, stores events, serves dashboard
- **Health check**: HTTP GET /health with 5-second timeout
- **Green**: Responding normally (< 5s response time)
- **Red**: Down or not responding

### 2. PBX Listener (Python Process)
- **What it does**: Connects to PBX, parses SMDR logs, forwards events
- **Health check**: Process detection + log file analysis
- **Green**: Running and connected to PBX
- **Yellow**: Running but reconnecting
- **Red**: Process stopped/crashed

### 3. PBX Stream (Telnet Connection)
- **What it does**: Physical TCP connection to PBX on port 23
- **Health check**: TCP connection test with 3-second timeout
- **Green**: Port accessible, data flowing
- **Yellow**: Port accessible but idle (no events yet)
- **Red**: Connection blocked (firewall/network issue)

### Overall System Status
- **ALL SYSTEMS OPERATIONAL** (Green): All three components healthy
- **PARTIAL** (Yellow): Some components degraded
- **SYSTEM DOWN** (Red): Critical failures

## 🔧 Daily Operations

### Starting the System
```bash
./start-snc-system.sh
```

### Monitoring Status
**Terminal mode:**
```bash
./monitor-snc-status.sh
```

**Web mode:**
Open: `http://192.168.1.94:8000/dashboard-status.html`

### Viewing Logs
```bash
./view-logs.sh
# Then select option 1-6
```

### Testing Events
```bash
# Trigger test call
curl -X POST http://localhost:8000/api/events/trigger \
  -H 'Content-Type: application/json' \
  -d '{"room_id":"400","event_type":"CALL_BEDSIDE"}'

# View all events
curl http://localhost:8000/api/events | python3 -m json.tool
```

### Stopping the System
```bash
pkill -f "uvicorn.*server:app"
pkill -f "snc_pbx_listener"
```

## 🐛 Troubleshooting Flowchart

```
System not working?
│
├─ Backend not responding?
│  ├─ Check: curl http://localhost:8000/health
│  ├─ Fix: pkill -f uvicorn; ./start-snc-system.sh
│  └─ Logs: tail -f logs/backend.log
│
├─ PBX not connecting?
│  ├─ Check: ./test-pbx-connectivity.sh
│  ├─ Fix: Enable telnet/SMDR on PBX, check firewall
│  └─ Logs: tail -f logs/pbx_listener.log
│
├─ No events appearing?
│  ├─ Check: ps aux | grep snc_pbx
│  ├─ Fix: Restart listener, verify PBX sending data
│  └─ Test: Trigger manual event via API
│
└─ Dashboard not loading?
   ├─ Check: Backend is running
   ├─ Fix: Copy dashboard to app/
   └─ Alt: Use ./monitor-snc-status.sh instead
```

## 📈 Performance Expectations

- **Backend startup**: 5-10 seconds
- **Health check response**: < 1 second
- **Event processing**: < 2 seconds end-to-end
- **Dashboard refresh**: Every 10 seconds
- **Memory usage**: ~100-200 MB total
- **CPU usage**: < 5% when idle

## 🛡️ Security Considerations

**Current Configuration (Development):**
- CORS allows all origins
- No authentication required
- HTTP (not HTTPS)
- Open API endpoints

**For Production:**
- Add user authentication
- Enable HTTPS/TLS
- Restrict CORS to specific domains
- Add rate limiting
- Set up firewall rules
- Enable audit logging

## 📚 Documentation Hierarchy

1. **QUICK_REFERENCE.md** - Start here for common commands
2. **DEPLOYMENT_CHECKLIST.md** - Use for initial setup
3. **DEPLOYMENT_PI4.md** - Detailed guide with explanations
4. **IMPLEMENTATION_SUMMARY.md** - Technical architecture details

## 🔄 Update Procedure

To update the system with new code:

1. Stop services:
   ```bash
   pkill -f "uvicorn|snc_pbx"
   ```

2. Pull/update code from repository

3. Restart:
   ```bash
   ./start-snc-system.sh
   ```

4. Verify:
   ```bash
   ./verify-installation.sh
   ```

## 💾 Backup & Recovery

### Backup Database
```bash
cp /home/ecs-agent/snc-poc/api/nurse_call_events.db \
   /home/pi/backups/nurse_call_$(date +%Y%m%d_%H%M%S).db
```

### Backup Logs
```bash
tar czf /home/pi/backups/logs_$(date +%Y%m%d).tar.gz \
   /home/ecs-agent/snc-poc/
```

### Restore Database
```bash
cp /path/to/backup.db /home/ecs-agent/snc-poc/api/nurse_call_events.db
./start-snc-system.sh
```

## 🎓 Training Checklist

Team members should know how to:
- [ ] Start the system (`./start-snc-system.sh`)
- [ ] Check status (web dashboard or terminal monitor)
- [ ] View logs (`./view-logs.sh`)
- [ ] Trigger test events (curl command)
- [ ] Recognize status colors (green/yellow/red)
- [ ] Contact support when issues occur
- [ ] Perform basic troubleshooting

## 📞 Support Resources

- **API Documentation**: http://192.168.1.94:8000/docs
- **Event History**: http://192.168.1.94:8000/api/events
- **Analytics**: http://192.168.1.94:8000/api/analytics/kpi
- **Logs**: `/home/ecs-agent/snc-poc/`

## ✅ Final Pre-Flight Checklist

Before going live:

- [ ] All deployment checklist items completed
- [ ] PBX connectivity verified and stable
- [ ] Test events flowing correctly
- [ ] Dashboard accessible from nurse station computers
- [ ] Staff trained on basic operations
- [ ] Backup procedure tested
- [ ] Emergency contact list available
- [ ] System running for 24+ hours without issues

---

## 🎉 You're Ready!

Your Smart Nurse Call system is now deployed and ready to use on Pi 4.

**Key URLs to bookmark:**
- Dashboard: http://192.168.1.94:8000/dashboard-status.html
- API Docs: http://192.168.1.94:8000/docs

**Essential commands to remember:**
```bash
./start-snc-system.sh      # Start
./monitor-snc-status.sh    # Monitor
./view-logs.sh             # Logs
./verify-installation.sh   # Test
```

**For help:**
- Quick questions: See QUICK_REFERENCE.md
- Troubleshooting: See DEPLOYMENT_PI4.md
- Technical details: See IMPLEMENTATION_SUMMARY.md

---

**Version**: 1.0  
**Platform**: Raspberry Pi 4  
**Network**: 192.168.1.x  
**PBX**: Phonik 192.168.1.91:23  
**Backend**: FastAPI on port 8000  

🏥 **Happy Monitoring!** 🏥
