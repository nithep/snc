# SNC System - Pi 4 Deployment Checklist

Use this checklist to ensure complete and successful deployment.

## 📋 Pre-Deployment Checklist

### Hardware & Network
- [ ] Pi 4 is powered on and accessible
- [ ] Pi 4 has network connectivity (Ethernet/WiFi)
- [ ] Pi 4 IP address is known (e.g., 192.168.1.94)
- [ ] Phonik PBX is powered on (192.168.1.91)
- [ ] Network cable/connection between Pi and PBX

### Software Prerequisites on Pi
```bash
# Run these commands first
sudo apt-get update && sudo apt-get upgrade -y
sudo apt-get install -y python3 python3-pip telnet curl
pip3 install fastapi uvicorn pydantic aiohttp
```
- [ ] Python 3 installed
- [ ] pip3 installed
- [ ] Required Python packages installed
- [ ] Telnet client available

### PBX Configuration
- [ ] Telnet server enabled on Phonik PBX
- [ ] SMDR output enabled on PBX
- [ ] SMDR format matches pattern: `==SMDX...`
- [ ] Port 23 open on PBX firewall
- [ ] PBX accessible from Pi network segment

## 📦 File Deployment Checklist

### Files to Copy to Pi
From Windows machine, run: `deploy-to-pi.bat`

Or manually copy via SCP:
- [ ] `start-snc-system.sh` → `/home/pi/Hotel-ECS/snc-poc/`
- [ ] `monitor-snc-status.sh` → `/home/pi/Hotel-ECS/snc-poc/`
- [ ] `test-pbx-connectivity.sh` → `/home/pi/Hotel-ECS/snc-poc/`
- [ ] `verify-installation.sh` → `/home/pi/Hotel-ECS/snc-poc/`
- [ ] `view-logs.sh` → `/home/pi/Hotel-ECS/snc-poc/`
- [ ] `dashboard-status.html` → `/home/pi/Hotel-ECS/snc-poc/`
- [ ] `DEPLOYMENT_PI4.md` → `/home/pi/Hotel-ECS/snc-poc/`
- [ ] `IMPLEMENTATION_SUMMARY.md` → `/home/pi/Hotel-ECS/snc-poc/`
- [ ] `QUICK_REFERENCE.md` → `/home/pi/Hotel-ECS/snc-poc/`

### Backend Modifications
- [ ] `backend/server.py` updated with static file serving
- [ ] `backend/public/` directory created
- [ ] `dashboard-status.html` copied to `backend/public/`

### Set Permissions
```bash
ssh pi@192.168.1.94
cd /home/pi/Hotel-ECS/snc-poc
chmod +x *.sh
```
- [ ] All .sh files are executable

## 🔍 Connectivity Testing Checklist

### Run Diagnostic Script
```bash
./test-pbx-connectivity.sh
```

Expected Results:
- [ ] Test 1/6: Network Reachability - PASS
- [ ] Test 2/6: IP Configuration - Same subnet or routing OK
- [ ] Test 3/6: TCP Port Connectivity - PASS (port 23 open)
- [ ] Test 4/6: Local Firewall Status - Port 23 allowed
- [ ] Test 5/6: Telnet Client - Installed
- [ ] Test 6/6: Manual Connection Test - PASS (can connect)

If any test fails:
- [ ] Check PBX telnet settings
- [ ] Verify SMDR is enabled
- [ ] Check Pi firewall rules
- [ ] Verify network routing
- [ ] Test from another device to isolate issue

## 🚀 System Startup Checklist

### Start Services
```bash
./start-snc-system.sh
```

Monitor output for:
- [ ] PBX connectivity check passes
- [ ] Backend starts successfully
- [ ] Health check returns 200 OK
- [ ] PBX listener starts
- [ ] "Connected successfully to Phonik PBX!" appears in logs
- [ ] PIDs displayed for both processes

### Verify Processes Running
```bash
ps aux | grep -E "uvicorn|snc_pbx"
```
Should see:
- [ ] Process: `python3 -m uvicorn server:app --host 0.0.0.0 --port 8000`
- [ ] Process: `python3 snc_pbx_listener.py`

## ✅ Functional Testing Checklist

### Backend Health Check
```bash
curl http://localhost:8000/health
```
Expected response:
```json
{
  "status": "healthy",
  "service": "snc-backend",
  "timestamp": "..."
}
```
- [ ] Returns HTTP 200
- [ ] JSON contains "status": "healthy"

### Test Event Creation
```bash
curl -X POST http://localhost:8000/api/events/trigger \
  -H 'Content-Type: application/json' \
  -d '{"room_id":"400","event_type":"CALL_BEDSIDE"}'
```
- [ ] Returns success status
- [ ] Event appears in API

### Verify Event Storage
```bash
curl http://localhost:8000/api/events
```
- [ ] Returns list of events
- [ ] Test event is visible
- [ ] Contains room_id, timestamp, status

### Test Acknowledge Flow
```bash
curl -X POST http://localhost:8000/api/events/acknowledge/0400
```
- [ ] Returns acknowledged status
- [ ] SLA metrics calculated

### Test Clear Flow
```bash
curl -X POST http://localhost:8000/api/events/clear/0400
```
- [ ] Returns cleared status
- [ ] Resolution time calculated

### Check Analytics
```bash
curl http://localhost:8000/api/analytics/kpi
```
- [ ] Returns KPI summary
- [ ] Contains avg_ack_time, sla_compliance_rate, etc.

## 🌐 Dashboard Access Checklist

### Web Dashboard
Open browser to: `http://192.168.1.94:8000/dashboard-status.html`

Verify:
- [ ] Page loads without errors
- [ ] Three status cards visible:
  - Backend Server (FastAPI)
  - PBX Listener (Python)
  - PBX Stream (Telnet)
- [ ] Status indicators show colors (green/yellow/red)
- [ ] Auto-refresh working (updates every 10s)
- [ ] Timestamp updates
- [ ] Overall system status shown at top

### Terminal Monitor
```bash
./monitor-snc-status.sh
```
Verify:
- [ ] Screen clears and shows status
- [ ] Three components listed separately
- [ ] Color-coded status dots
- [ ] Updates every 10 seconds
- [ ] Overall status summary shown
- [ ] Ctrl+C exits cleanly

### Log Viewer
```bash
./view-logs.sh
```
Test each option:
- [ ] Option 1: Backend log displays
- [ ] Option 2: PBX log displays
- [ ] Option 3: Merged logs display
- [ ] Option 4: Last 50 lines shown
- [ ] Option 5: Error search works
- [ ] Option 6: Recent events from API

## 📊 PBX Integration Checklist

### Verify PBX Data Flow
Check PBX listener logs:
```bash
tail -f /home/pi/Hotel-ECS/logs/pbx_listener.log
```

Look for:
- [ ] "Connecting to Phonik PBX Telnet at 192.168.1.91:23..."
- [ ] "Connected successfully to Phonik PBX!"
- [ ] RAW SMDR data appearing (if calls active)
- [ ] "SNC Event Detected" messages when calls occur
- [ ] "Event sent to Backend" confirmations

### Test with Real PBX Events
- [ ] Make a bedside call from room
- [ ] Verify event appears in backend
- [ ] Verify dashboard updates in real-time
- [ ] Nurse acknowledges call
- [ ] ACK event recorded with SLA time
- [ ] Call cleared
- [ ] Resolution time calculated

## 🔧 System Stability Checklist

### Process Monitoring
Leave system running for 15 minutes:
```bash
watch -n 5 'ps aux | grep -E "uvicorn|snc_pbx" | grep -v grep'
```
- [ ] Both processes remain stable
- [ ] No crashes or restarts
- [ ] Memory usage stable

### Log Rotation Check
```bash
ls -lh /home/pi/Hotel-ECS/logs/
```
- [ ] Logs being written
- [ ] File sizes reasonable (< 100MB each)
- [ ] No permission errors

### Database Integrity
```bash
sqlite3 /home/pi/Hotel-ECS/snc-poc/backend/nurse_call_events.db ".tables"
sqlite3 /home/pi/Hotel-ECS/snc-poc/backend/nurse_call_events.db "SELECT COUNT(*) FROM nurse_call_events;"
```
- [ ] Database accessible
- [ ] Tables exist
- [ ] Events being stored

## 🛡️ Security & Production Readiness

### For Production Deployment
- [ ] Add authentication to dashboard
- [ ] Enable HTTPS (Let's Encrypt)
- [ ] Set up reverse proxy (nginx)
- [ ] Configure log rotation
- [ ] Set up systemd services for auto-start
- [ ] Configure backup for database
- [ ] Set up monitoring alerts
- [ ] Restrict CORS origins
- [ ] Add rate limiting
- [ ] Review firewall rules

### Systemd Services (Optional)
If setting up auto-start:
- [ ] Created `/etc/systemd/system/snc-backend.service`
- [ ] Created `/etc/systemd/system/snc-pbx-listener.service`
- [ ] Ran `sudo systemctl daemon-reload`
- [ ] Enabled services: `sudo systemctl enable snc-backend snc-pbx-listener`
- [ ] Started services: `sudo systemctl start snc-backend snc-pbx-listener`
- [ ] Verified: `sudo systemctl status snc-backend snc-pbx-listener`

## 📝 Documentation Checklist

- [ ] DEPLOYMENT_PI4.md reviewed
- [ ] IMPLEMENTATION_SUMMARY.md reviewed
- [ ] QUICK_REFERENCE.md printed/copied
- [ ] Team trained on basic operations
- [ ] Emergency procedures documented
- [ ] Contact information for support available

## ✨ Final Verification

### Run Complete Test Suite
```bash
./verify-installation.sh
```
- [ ] All tests pass
- [ ] No failures reported

### Manual Smoke Test
1. [ ] SSH to Pi
2. [ ] Start system
3. [ ] Open dashboard in browser
4. [ ] Trigger test event
5. [ ] Verify event appears on dashboard
6. [ ] Acknowledge event
7. [ ] Clear event
8. [ ] Check analytics
9. [ ] View logs
10. [ ] Stop system
11. [ ] Restart system
12. [ ] Verify everything still works

### Performance Check
- [ ] Backend responds < 1 second to health check
- [ ] Dashboard loads < 3 seconds
- [ ] Events appear on dashboard < 2 seconds after trigger
- [ ] No noticeable lag in UI

## 🎉 Success Criteria

System is fully operational when ALL of the following are true:

- ✅ Backend responds to `curl http://localhost:8000/health` with HTTP 200
- ✅ PBX listener shows "Connected successfully to Phonik PBX!" in logs
- ✅ Dashboard accessible at `http://192.168.1.94:8000/dashboard-status.html`
- ✅ Three separate status indicators visible and updating
- ✅ Events flow: PBX → Listener → Backend → Dashboard
- ✅ Status uses timeout/ACK logic (not static "Connected")
- ✅ All scripts executable and functional
- ✅ Logs being written to `/home/pi/Hotel-ECS/logs/`
- ✅ verify-installation.sh passes all tests

## 📞 Support Information

If issues persist after completing checklist:

1. **Review Logs**: `/home/pi/Hotel-ECS/logs/*.log`
2. **Run Diagnostics**: `./test-pbx-connectivity.sh`
3. **Check Documentation**: `DEPLOYMENT_PI4.md` troubleshooting section
4. **Verify Network**: Ensure Pi and PBX on same network segment
5. **Test Components Individually**: Backend, then listener, then integration

---

**Completion Date**: _______________  
**Deployed By**: _______________  
**Pi IP Address**: _______________  
**Notes**: _______________  

✅ **All items checked = System ready for production use!**
