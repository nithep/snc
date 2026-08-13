# SNC System - Quick Reference Card

## 🚀 Quick Start (3 Steps)

```bash
# 1. SSH to Pi
ssh pi@192.168.1.94

# 2. Start system
cd /home/pi/Hotel-ECS/snc-poc
./start-snc-system.sh

# 3. View dashboard
# Open browser: http://192.168.1.94:8000/dashboard-status.html
```

## 📊 Key URLs

| Service | URL |
|---------|-----|
| Dashboard (main, served at `/`) | http://192.168.1.94:8000/ |
| Dashboard (legacy status page) | http://192.168.1.94:8000/dashboard-status.html |
| Health Check | http://192.168.1.94:8000/health |
| Events API | http://192.168.1.94:8000/api/events |
| API Docs | http://192.168.1.94:8000/docs |
| Analytics | http://192.168.1.94:8000/api/analytics/kpi |

## 🔧 Essential Commands

### Start/Stop
```bash
./start-snc-system.sh          # Start all services
pkill -f "uvicorn|snc_pbx"     # Stop all services
```

### Monitor
```bash
./monitor-snc-status.sh        # Real-time status (terminal)
./view-logs.sh                 # Interactive log viewer
tail -f logs/backend.log       # Backend logs only
tail -f logs/pbx_listener.log  # PBX logs only
```

### Test
```bash
./test-pbx-connectivity.sh     # Diagnose PBX connection
./verify-installation.sh       # Run all tests
curl http://localhost:8000/health  # Quick health check
```

## 🎯 Status Indicators

### ✅ Healthy System
- **Backend**: Green dot, response time < 5s
- **PBX Listener**: Green dot, "Connected & Active"
- **PBX Stream**: Green dot, "Accessible", events flowing

### ⚠️ Degraded System
- **Backend**: Green, but Listener yellow = Reconnecting
- **PBX Stream**: Yellow = Configured but idle (no events yet)

### ❌ System Down
- **Backend**: Red dot = Not responding on port 8000
- **PBX Stream**: Red dot = Port 23 blocked/unreachable

## 🐛 Troubleshooting Cheat Sheet

### Backend won't start
```bash
sudo lsof -i :8000              # Check port usage
pkill -f "uvicorn.*server:app"  # Kill existing
cat logs/backend.log            # Check errors
pip3 list | grep fastapi        # Verify dependencies
```

### PBX not connecting
```bash
telnet 192.168.1.91 23          # Manual test
sudo ufw allow out 23/tcp       # Allow firewall
./test-pbx-connectivity.sh      # Full diagnostic
```

### No events appearing
```bash
ps aux | grep snc_pbx           # Check listener running
grep "SNC Event" logs/pbx_listener.log  # Check parsing
curl -X POST http://localhost:8000/api/events/trigger \
  -H 'Content-Type: application/json' \
  -d '{"room_id":"400","event_type":"CALL_BEDSIDE"}'  # Test manually
```

### Dashboard not loading
```bash
cp dashboard-status.html backend/public/   # Copy HTML file
python3 -m http.server 8080                # Alternative serve
```

## 📁 File Locations

| File | Location |
|------|----------|
| Scripts | `/home/pi/Hotel-ECS/snc-poc/*.sh` |
| Backend | `/home/pi/Hotel-ECS/snc-poc/backend/server.py` |
| PBX Listener | `/home/pi/Hotel-ECS/snc-poc/pbx-connector/snc_pbx_listener.py` |
| Logs | `/home/pi/Hotel-ECS/logs/` |
| Database | `/home/pi/Hotel-ECS/snc-poc/backend/nurse_call_events.db` |
| Dashboard | `/home/pi/Hotel-ECS/snc-poc/backend/public/dashboard-status.html` |

## 🔄 Service Management

### Check Status
```bash
ps aux | grep -E "uvicorn|snc_pbx"
systemctl status snc-backend        # If using systemd
systemctl status snc-pbx-listener   # If using systemd
```

### Restart Single Service
```bash
# Backend only
pkill -f "uvicorn.*server:app"
cd /home/pi/Hotel-ECS/snc-poc/backend
nohup python3 -m uvicorn server:app --host 0.0.0.0 --port 8000 > ../logs/backend.log 2>&1 &

# PBX Listener only
pkill -f "snc_pbx_listener"
cd /home/pi/Hotel-ECS/snc-poc/pbx-connector
nohup python3 snc_pbx_listener.py > ../logs/pbx_listener.log 2>&1 &
```

## 📈 Testing Event Flow

```bash
# 1. Trigger test event
curl -X POST http://localhost:8000/api/events/trigger \
  -H 'Content-Type: application/json' \
  -d '{"room_id":"400","event_type":"CALL_BEDSIDE"}'

# 2. Check it was stored
curl http://localhost:8000/api/events | python3 -m json.tool

# 3. Acknowledge the call
curl -X POST http://localhost:8000/api/events/acknowledge/0400

# 4. Clear the call
curl -X POST http://localhost:8000/api/events/clear/0400

# 5. Check analytics
curl http://localhost:8000/api/analytics/kpi | python3 -m json.tool
```

## 🎨 Dashboard Keyboard Shortcuts

When viewing dashboard in browser:
- **F5** or **Ctrl+R**: Manual refresh
- **F11**: Fullscreen mode
- **Ctrl+D**: Bookmark for quick access

## 📞 Network Configuration

| Component | IP/Port | Protocol |
|-----------|---------|----------|
| Pi 4 | 192.168.1.94 | - |
| Backend API | :8000 | HTTP |
| Phonik PBX | 192.168.1.91:23 | Telnet (TCP) |

## 🔐 Security Notes

- CORS is set to allow all origins (development mode)
- No authentication on dashboard (add for production!)
- SQLite database contains event history
- Logs may contain sensitive room/patient data

## 💡 Pro Tips

1. **Use tmux/screen** for persistent sessions:
   ```bash
   sudo apt-get install tmux
   tmux new -s snc-monitor
   ./monitor-snc-status.sh
   # Ctrl+B, D to detach
   # tmux attach -t snc-monitor to reattach
   ```

2. **Set up aliases** in `~/.bashrc`:
   ```bash
   alias snc-start='cd /home/pi/Hotel-ECS/snc-poc && ./start-snc-system.sh'
   alias snc-status='./monitor-snc-status.sh'
   alias snc-logs='./view-logs.sh'
   alias snc-test='./verify-installation.sh'
   ```

3. **Auto-refresh dashboard** in browser with meta tag or JavaScript interval

4. **Monitor disk space** (logs can grow):
   ```bash
   df -h /
   du -sh logs/*
   ```

5. **Backup database** regularly:
   ```bash
   cp backend/nurse_call_events.db backups/nurse_call_$(date +%Y%m%d).db
   ```

## 📚 Documentation

- **Full Guide**: `DEPLOYMENT_PI4.md`
- **Implementation Details**: `IMPLEMENTATION_SUMMARY.md`
- **API Examples**: `../backend/API_EXAMPLES.md`

---

**Print this card and keep it near your Pi 4 for quick reference!**
