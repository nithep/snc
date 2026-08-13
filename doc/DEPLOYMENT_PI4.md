# Smart Nurse Call (SNC) System - Pi 4 Deployment Guide

## Overview
This guide covers deploying and monitoring the SNC system on Raspberry Pi 4, including:
- Backend server (FastAPI on port 8000)
- PBX listener (Telnet connection to 192.168.1.91:23)
- Real-time status monitoring with timeout/ACK logic
- Web-based dashboard

## Prerequisites

### Hardware
- Raspberry Pi 4 (2GB+ RAM recommended)
- Network connectivity to PBX (192.168.1.91)
- SSH access or direct terminal access

### Software
```bash
# Update system
sudo apt-get update && sudo apt-get upgrade -y

# Install Python dependencies
sudo apt-get install -y python3 python3-pip python3-venv telnet curl

# Install Python packages for backend
cd /home/ecs-agent/nithep/snc/api
pip3 install fastapi uvicorn pydantic aiohttp

# Install Python packages for PBX listener
cd /home/ecs-agent/nithep/snc/pbx
pip3 install aiohttp
```

## Quick Start

### 1. Deploy Scripts to Pi
Copy these files to your Pi 4:
```bash
# From your development machine
scp ops/start-snc-system.sh pi@192.168.1.94:/home/ecs-agent/nithep/snc/ops/
scp ops/monitor-snc-status.sh pi@192.168.1.94:/home/ecs-agent/nithep/snc/
scp ops/test-pbx-connectivity.sh pi@192.168.1.94:/home/ecs-agent/nithep/snc/
scp app/dashboard-status.html pi@192.168.1.94:/home/ecs-agent/nithep/snc/app/
```

### 2. Make Scripts Executable
```bash
ssh pi@192.168.1.94
cd /home/ecs-agent/nithep/snc
chmod +x *.sh
```

### 3. Test PBX Connectivity First
```bash
./test-pbx-connectivity.sh
```

**Expected Output:**
- ✓ Network Reachability: PASS
- ✓ TCP Port Connectivity: PASS (port 23 open)
- ✓ Manual Connection Test: PASS (can see SMDR data)

**If tests fail:**
- Check firewall rules on Pi: `sudo iptables -L`
- Verify PBX telnet is enabled
- Confirm SMDR output is configured on PBX
- Check network routing between Pi and PBX

### 4. Start SNC System
```bash
./start-snc-system.sh
```

This will:
1. Check PBX connectivity
2. Start Backend server on port 8000
3. Wait for backend health check
4. Start PBX listener
5. Display status summary with PIDs

### 5. Monitor System Status

#### Option A: Terminal Monitor (Real-time)
```bash
./monitor-snc-status.sh
```

Shows:
- **Backend Server**: Health endpoint status, response time
- **PBX Listener**: Process status, connection state from logs
- **PBX Stream**: TCP connectivity, data flow status
- Overall system health with color-coded indicators

Updates every 10 seconds with timeout/ACK logic.

#### Option B: Web Dashboard
Open browser on any device:
```
http://192.168.1.94:8000/dashboard-status.html
```

Or from Pi itself:
```bash
# Install a text-based browser
sudo apt-get install -y w3m
w3m http://localhost:8000/dashboard-status.html
```

The dashboard shows:
- Separate status cards for each component
- Real-time updates every 10 seconds
- Response times and latency metrics
- Color-coded status indicators (Green/Yellow/Red)
- Quick action buttons

### 6. Verify System Operation

#### Test Backend Health
```bash
curl http://localhost:8000/health
```

**Expected Response:**
```json
{
  "status": "healthy",
  "service": "snc-backend",
  "timestamp": "2024-01-15T10:30:00.000000"
}
```

#### Check PBX Listener Logs
```bash
tail -f /home/ecs-agent/nithep/snc/logs/pbx_listener.log
```

**Look for:**
```
INFO: Connecting to Phonik PBX Telnet at 192.168.1.91:23...
INFO: Connected successfully to Phonik PBX!
```

#### Test Event Flow
Trigger a test event:
```bash
curl -X POST http://localhost:8000/api/events/trigger \
  -H "Content-Type: application/json" \
  -d '{"room_id": "400", "event_type": "CALL_BEDSIDE"}'
```

Check events API:
```bash
curl http://localhost:8000/api/events | python3 -m json.tool
```

## Troubleshooting

### Backend Won't Start
```bash
# Check logs
cat /home/ecs-agent/nithep/snc/logs/backend.log

# Check if port 8000 is in use
sudo lsof -i :8000

# Kill existing process
pkill -f "uvicorn.*server:app"

# Restart
./start-snc-system.sh
```

### PBX Listener Can't Connect
```bash
# Run diagnostic
./test-pbx-connectivity.sh

# Check PBX configuration:
# 1. Access PBX web interface
# 2. Enable Telnet server (System > Network > Services)
# 3. Enable SMDR output (SMDR/Call Accounting settings)
# 4. Configure SMDR format to match: ==SMDX...

# Check firewall on Pi
sudo ufw status
sudo ufw allow out 23/tcp

# Test manually
telnet 192.168.1.91 23
```

### No Events Appearing
```bash
# Check listener is running
ps aux | grep snc_pbx_listener

# View recent logs
tail -50 /home/ecs-agent/nithep/snc/logs/pbx_listener.log

# Look for SMDR pattern matches
grep "SNC Event Detected" /home/ecs-agent/nithep/snc/logs/pbx_listener.log

# Verify backend is receiving
tail -50 /home/ecs-agent/nithep/snc/logs/backend.log | grep "Event sent"
```

### Dashboard Not Loading
```bash
# Check if backend is serving static files
ls -la /home/ecs-agent/nithep/snc/backend/public/

# Copy dashboard to backend public folder
cp dashboard-status.html /home/ecs-agent/nithep/snc/backend/public/

# Or serve directly with Python
cd /home/ecs-agent/nithep/snc
python3 -m http.server 8080
# Then access: http://192.168.1.94:8080/dashboard-status.html
```

## Service Management

### Stop All Services
```bash
pkill -f "uvicorn.*server:app"
pkill -f "snc_pbx_listener.py"
```

### Restart Single Service
```bash
# Backend only
pkill -f "uvicorn.*server:app"
cd /home/ecs-agent/nithep/snc/api
nohup python3 -m uvicorn server:app --host 0.0.0.0 --port 8000 > /home/ecs-agent/nithep/snc/logs/backend.log 2>&1 &

# PBX Listener only
pkill -f "snc_pbx_listener.py"
cd /home/ecs-agent/nithep/snc/pbx
nohup python3 snc_pbx_listener.py > /home/ecs-agent/nithep/snc/logs/pbx_listener.log 2>&1 &
```

### View Running Processes
```bash
ps aux | grep -E "uvicorn|snc_pbx"
```

### Auto-start on Boot (Optional)
Create systemd service files:

**Backend Service** (`/etc/systemd/system/snc-backend.service`):
```ini
[Unit]
Description=SNC Backend Server
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/ecs-agent/nithep/snc/api
ExecStart=/usr/bin/python3 -m uvicorn server:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=5
StandardOutput=append:/home/ecs-agent/nithep/snc/logs/backend.log
StandardError=append:/home/ecs-agent/nithep/snc/logs/backend.log

[Install]
WantedBy=multi-user.target
```

**PBX Listener Service** (`/etc/systemd/system/snc-pbx-listener.service`):
```ini
[Unit]
Description=SNC PBX Listener
After=network.target snc-backend.service

[Service]
Type=simple
User=pi
WorkingDirectory=/home/ecs-agent/nithep/snc/pbx
ExecStart=/usr/bin/python3 snc_pbx_listener.py
Restart=always
RestartSec=5
StandardOutput=append:/home/ecs-agent/nithep/snc/logs/pbx_listener.log
StandardError=append:/home/ecs-agent/nithep/snc/logs/pbx_listener.log

[Install]
WantedBy=multi-user.target
```

Enable services:
```bash
sudo systemctl daemon-reload
sudo systemctl enable snc-backend
sudo systemctl enable snc-pbx-listener
sudo systemctl start snc-backend
sudo systemctl start snc-pbx-listener
```

Check status:
```bash
sudo systemctl status snc-backend
sudo systemctl status snc-pbx-listener
```

## Architecture Diagram

```
┌─────────────┐     Telnet      ┌──────────────┐
│  Phonik PBX │◄──────────────►│ PBX Listener │
│ 192.168.1.91│    Port 23      │   (Python)   │
└─────────────┘                 └──────┬───────┘
                                      │ HTTP POST
                                      ▼
                               ┌──────────────┐
                               │  Backend API  │
                               │  FastAPI :8000│
                               └──────┬───────┘
                                      │
                    ┌─────────────────┼─────────────────┐
                    ▼                 ▼                 ▼
            ┌──────────────┐  ┌──────────┐    ┌─────────────┐
            │ SQLite DB    │  │ WebSocket│    │ REST API    │
            │ Events       │  │ Broadcast│    │ Endpoints   │
            └──────────────┘  └──────────┘    └─────────────┘
                                                    ▲
                                                    │
                                            ┌───────┴───────┐
                                            │  Web Browser  │
                                            │  Dashboard    │
                                            └───────────────┘
```

## Status Indicators Explained

### Backend Server
- **RUNNING (Green)**: Health endpoint responding, < 5s timeout
- **DOWN (Red)**: Port 8000 not responding or timeout exceeded

### PBX Listener
- **RUNNING (Green)**: Process active, connected to PBX
- **Reconnecting (Yellow)**: Process running but retrying connection
- **STOPPED (Red)**: Process not running

### PBX Stream
- **ACCESSIBLE (Green)**: TCP port 23 open, data flowing
- **CONFIGURED (Yellow)**: Port accessible but no events yet
- **BLOCKED (Red)**: Connection timeout, firewall/network issue

## Performance Tuning

### For Better Response Times
```bash
# Use uvicorn workers
python3 -m uvicorn server:app --host 0.0.0.0 --port 8000 --workers 4

# Optimize SQLite
sqlite3 nurse_call_events.db "PRAGMA journal_mode=WAL; PRAGMA synchronous=NORMAL;"
```

### For Production Deployment
- Use reverse proxy (nginx) in front of uvicorn
- Enable HTTPS with Let's Encrypt
- Set up log rotation
- Configure monitoring alerts (Prometheus/Grafana)
- Use Docker containers for isolation

## Support & Resources

- Backend API Docs: `http://192.168.1.94:8000/docs` (Swagger UI)
- Events API: `http://192.168.1.94:8000/api/events`
- Analytics: `http://192.168.1.94:8000/api/analytics/kpi`

## Version History
- v1.0: Initial deployment scripts with status monitoring
- Features: Timeout/ACK logic, separate component status, web dashboard
