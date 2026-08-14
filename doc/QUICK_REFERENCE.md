# SNC System - Quick Reference Card

## 🚀 Quick Start (3 Steps)

```bash
# 1. SSH to Pi (alias: ssh pi4)
ssh ecs-agent@192.168.1.94

# 2. Start system
cd /home/ecs-agent/nithep/snc
./ops/start-snc-system.sh

# 3. View dashboard
# Open browser: http://192.168.1.94:8000/  (main dashboard served at /)
```

## 📊 Key URLs

| Service | URL |
|---------|-----|
| Dashboard (main, served at `/`) | http://192.168.1.94:8000/ |
| Dashboard (legacy status page) | http://192.168.1.94:8000/dashboard-status.html |
| Health Check | http://192.168.1.94:8000/health |
| Events API | http://192.168.1.94:8000/api/events |
| API Docs | http://192.168.1.94:8000/docs |
| Analytics (KPI) | http://192.168.1.94:8000/api/analytics/kpi |
| SMDR proxy (Room Manager mirror) | telnet 192.168.1.94 2323 |

## 🔧 Essential Commands

### Start/Stop (systemd — production)
```bash
sudo systemctl status snc-backend snc-pbx-listener
sudo systemctl restart snc-backend snc-pbx-listener
sudo journalctl -u snc-backend -f          # Backend logs (follow)
```

### Monitor
```bash
ops/monitor-snc-status.sh                  # Real-time status (terminal)
ops/view-logs.sh                           # Interactive log viewer
tail -f /home/ecs-agent/nithep/snc/logs/backend.log
tail -f /home/ecs-agent/nithep/snc/logs/pbx_listener.log
ops/burnin-monitor.sh --report             # Burn-in summary
```

### Test
```bash
ops/test-pbx-connectivity.sh               # Diagnose PBX connection
ops/verify-installation.sh                 # Run all tests
curl http://localhost:8000/health          # Quick health check

# Synthetic event (needs SNC_API_KEY if set — 401 without it)
curl -X POST http://localhost:8000/api/events/trigger \
  -H "Content-Type: application/json" -H "X-API-Key: $SNC_API_KEY" \
  -d '{"room_id":"400","event_type":"CALL_BEDSIDE"}'

# Full deterministic demo (no PBX needed)
curl -X POST http://localhost:8000/api/demo/scenario \
  -H "Content-Type: application/json" \
  -d '{"room_id":"400","ack_after":5,"clear_after":12,"include_emergency":true}'
```

## 🎯 Status Indicators

### ✅ Healthy System
- **Backend**: `GET /health` → `{"status":"healthy"}` (response < 1s)
- **PBX Listener**: log shows `Connected successfully to Phonik PBX!`
- **PBX Stream**: SMDR events flowing (`==SMDX…`, `==RDSS…`)

### ⚠️ Degraded System
- Listener "Reconnecting" → single-session cabinet or idle-timeout (check heartbeat)
- PBX reachable but idle → no calls pressed (normal) or SMDR not configured

### ❌ System Down
- Backend: port 8000 not responding
- PBX: port 23 blocked / `Connection refused` (another client holds the session)

## 🐛 Troubleshooting Cheat Sheet

### Backend won't start
```bash
sudo lsof -i :8000                          # Check port usage
sudo systemctl restart snc-backend          # systemd auto-restarts on crash
tail -50 /home/ecs-agent/nithep/snc/logs/backend.log
```

### PBX not connecting
```bash
telnet 192.168.1.91 23                      # Manual test (single session!)
ops/test-pbx-connectivity.sh                # Full diagnostic
# If "Not have free PABX telnet port" → power-cycle cabinet (off ~15s)
```

### No events appearing
```bash
sudo systemctl status snc-pbx-listener
grep "SNC Event" /home/ecs-agent/nithep/snc/logs/pbx_listener.log
```

### Dashboard `/` 404/blank
```bash
# server.py serves static_dir = ../app — deploy app/index.html
scp app/index.html pi4:/home/ecs-agent/nithep/snc/app/
sudo systemctl restart snc-backend
```

### PC Room Manager says "Authenticate Failed!!" on :2323
→ upgrade `pbx/snc_pbx_listener.py` (handshake emulation) and reconnect.

## 📁 File Locations (repo 5-Core layout)

| File | Repo | Pi |
|------|------|----|
| Backend | `api/server.py` | `/home/ecs-agent/nithep/snc/api/server.py` |
| PBX Listener | `pbx/snc_pbx_listener.py` | `/home/ecs-agent/nithep/snc/pbx/snc_pbx_listener.py` |
| Dashboard (main) | `app/index.html` | `/home/ecs-agent/nithep/snc/app/index.html` |
| Dashboard (legacy) | `app/dashboard-status.html` | `/home/ecs-agent/nithep/snc/app/dashboard-status.html` |
| Scripts | `ops/*.sh` | `/home/ecs-agent/nithep/snc/ops/` |
| Database | `api/nurse_call_events.db` (runtime) | `/home/ecs-agent/nithep/snc/api/nurse_call_events.db` |
| Logs | — (runtime) | `/home/ecs-agent/nithep/snc/logs/` |
| Docs | `doc/*.md`, `doc/wiki/*.md` | `/home/ecs-agent/nithep/snc/doc/` |

## 🔄 Service Management (systemd)

```bash
systemctl status snc-backend snc-pbx-listener
sudo systemctl restart snc-backend            # backend only
sudo systemctl restart snc-pbx-listener       # listener only
# Units: /etc/systemd/system/snc-{backend,pbx-listener}.service
# User=ecs-agent, WorkingDirectory=/home/ecs-agent/nithep/snc/{api,pbx}
```

## 📈 Testing Event Flow

```bash
# 1. Trigger test event
curl -X POST http://localhost:8000/api/events/trigger \
  -H 'Content-Type: application/json' -H "X-API-Key: $SNC_API_KEY" \
  -d '{"room_id":"400","event_type":"CALL_BEDSIDE"}'

# 2. Check it was stored
curl http://localhost:8000/api/events | python3 -m json.tool

# 3. Acknowledge the call
curl -X POST http://localhost:8000/api/events/acknowledge/0400 -H "X-API-Key: $SNC_API_KEY"

# 4. Clear the call
curl -X POST http://localhost:8000/api/events/clear/0400 -H "X-API-Key: $SNC_API_KEY"

# 5. Check analytics
curl http://localhost:8000/api/analytics/kpi | python3 -m json.tool
```

## 🎨 Dashboard Keyboard Shortcuts

- **F5** / **Ctrl+R**: Manual refresh
- **F11**: Fullscreen mode
- **Ctrl+D**: Bookmark for quick access

## 📞 Network Configuration

| Component | IP/Port | Protocol |
|-----------|---------|----------|
| Pi 4 | 192.168.1.94 | - |
| Backend API | :8000 | HTTP |
| Phonik PBX | 192.168.1.91:23 | Telnet (TCP) |
| SMDR proxy (Room Manager) | 192.168.1.94:2323 | Telnet (TCP) |

## 🔐 Security Notes

- POST/PUT/DELETE require `X-API-Key` header when `SNC_API_KEY` is set (GET stays open for polling)
- Rate limit: GET 120/min, writes 20/min per IP
- Secrets (`PBX_PASS`, `SNC_API_KEY`, tunnel tokens) live in `.env` only — never committed
- SQLite DB contains event history; logs may contain room/patient data

## 💡 Pro Tips

1. **Use tmux** for persistent sessions:
   ```bash
   sudo apt-get install tmux
   tmux new -s snc-monitor
   ops/monitor-snc-status.sh
   # Ctrl+B, D to detach; tmux attach -t snc-monitor to reattach
   ```

2. **Aliases** in `~/.bashrc`:
   ```bash
   alias snc-start='cd /home/ecs-agent/nithep/snc && ./ops/start-snc-system.sh'
   alias snc-status='ops/monitor-snc-status.sh'
   alias snc-logs='ops/view-logs.sh'
   alias snc-test='ops/verify-installation.sh'
   ```

3. **Monitor disk** (logs can grow):
   ```bash
   df -h /
   du -sh /home/ecs-agent/nithep/snc/logs/*
   ```

4. **Backup DB** (auto cron 03:00 daily):
   ```bash
   ops/backup-snc-db.sh --pi
   ```

## 📚 Documentation

- **Deploy**: `doc/DEPLOYMENT_PI4.md`, `doc/DEPLOYMENT_CHECKLIST.md`
- **SOP**: `doc/PBX_POWER_CYCLE_SOP.md`, `doc/STAFF_GUIDE_TH.md`
- **Field test**: `doc/FIELD_TEST_CHECKLIST.md`, `doc/FIELD_TEST_DAY_PLAN.md`
- **Knowledge base**: `doc/wiki/*.md` (SYSTEMD_SERVICES_SUMMARY, CLOUDFLARE_TUNNEL_SUMMARY, PBX_CONNECTIVITY_TROUBLESHOOTING)

---

**Print this card and keep it near your Pi 4 for quick reference!**
