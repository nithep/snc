---
title: "SNC System Architecture - Visual Guide"
type: doc
tags: [architecture]
---

# SNC System Architecture - Visual Guide

## 🏗️ System Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                    SMART NURSE CALL SYSTEM                           │
│                         Raspberry Pi 4                               │
│                        (192.168.1.94)                                │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                                  │
        ┌─────────────────────────┼─────────────────────────┐
        │                         │                         │
        ▼                         ▼                         ▼
┌──────────────┐         ┌──────────────┐         ┌──────────────┐
│   Phonik     │         │   Backend    │         │   Web        │
│   PBX        │         │   Server     │         │   Browser    │
│ 192.168.1.91 │         │   FastAPI    │         │   Dashboard  │
│   Port 23    │         │   Port 8000  │         │              │
└──────┬───────┘         └──────┬───────┘         └──────┬───────┘
       │                        │                        │
       │ Telnet                 │ HTTP POST              │ HTTP GET
       │ SMDR Stream            │ Events                 │ Status Updates
       │                        │                        │
       └───────────────────────►├───────────────────────►┘
                               │
                    ┌──────────▼──────────┐
                    │   PBX Listener      │
                    │   (Python Async)    │
                    │                     │
                    │ • Connect to PBX    │
                    │ • Parse SMDR logs   │
                    │ • Classify events   │
                    │ • Forward to API    │
                    │ • Auto-reconnect    │
                    └─────────────────────┘
```

## 🔄 Data Flow Sequence

```
1. Nurse presses call button in Room 400
         │
         ▼
2. PBX generates SMDR log entry
   "==SMDX2005=03/08/26 18:59 401 e.400 EC 0:00'09 0 #1"
         │
         ▼
3. PBX streams SMDR via Telnet (port 23)
         │
         ▼
4. PBX Listener receives raw log
   snc_pbx_listener.py line 165-175
         │
         ▼
5. Regex parsing & event classification
   Pattern: ==SMDX\d*\s*=?\s*\d{2}/\d{2}/\d{2}...
   Result: Room 0400, Event CALL_BEDSIDE
         │
         ▼
6. HTTP POST to Backend API
   POST http://localhost:8000/api/events/trigger
   Body: {"room_id": "0400", "event_type": "CALL_BEDSIDE"}
         │
         ▼
7. Backend processes event
   - Stores in SQLite database
   - Calculates SLA metrics
   - Broadcasts via WebSocket
         │
         ├────────────────┬────────────────┐
         ▼                ▼                ▼
8a. Database          8b. WebSocket    8c. REST API
    nurse_call_events     nurse-station    /api/events
    table updated         broadcast        endpoint
         │                │                │
         │                │                │
         └────────────────┴────────────────┘
                          │
                          ▼
9. Dashboard updates automatically
   - Shows new call for Room 0400
   - Status: ACTIVE (Red indicator)
   - Timestamp displayed
   - Alert sound (if enabled)
         │
         ▼
10. Nurse acknowledges on dashboard
    POST /api/events/acknowledge/0400
         │
         ▼
11. SLA tracking updated
    - Ack time calculated
    - Status: ACKNOWLEDGED (Yellow)
         │
         ▼
12. Issue resolved, call cleared
    POST /api/events/clear/0400
         │
         ▼
13. Resolution complete
    - Resolution time calculated
    - Status: RESOLVED (Green)
    - SLA compliance recorded
```

## 🔍 Component Interaction Details

### Backend Server (FastAPI)
```
┌─────────────────────────────────────────┐
│         FastAPI Application             │
│           server:app :8000              │
├─────────────────────────────────────────┤
│                                         │
│  Routes:                                │
│  ├── GET  /health                  ✓    │
│  ├── GET  /api/events              ✓    │
│  ├── POST /api/events/trigger      ✓    │
│  ├── POST /api/events/acknowledge  ✓    │
│  ├── POST /api/events/clear        ✓    │
│  ├── GET  /api/analytics/kpi       ✓    │
│  ├── WS   /ws/nurse-station        ✓    │
│  └── GET  /dashboard   ✓    │
│                                         │
│  Services:                              │
│  ├── SQLite Database Manager            │
│  ├── WebSocket ConnectionManager        │
│  ├── Gemini AI Service (optional)       │
│  └── Static File Server                 │
│                                         │
└─────────────────────────────────────────┘
```

### PBX Listener (Python)
```
┌─────────────────────────────────────────┐
│      PhonikSNCListener Class            │
│        snc_pbx_listener.py              │
├─────────────────────────────────────────┤
│                                         │
│  Configuration:                         │
│  ├── PBX_IP = "192.168.1.91"           │
│  ├── PBX_PORT = 23                     │
│  └── BACKEND_URL = "http://localhost:8000"
│                                         │
│  Methods:                               │
│  ├── start_listening()                  │
│  │   └── asyncio.open_connection()      │
│  ├── parse_smdr_line()                  │
│  │   └── Regex pattern matching         │
│  ├── _create_event_payload()            │
│  │   └── FHIR-compliant JSON            │
│  ├── send_event_to_backend()            │
│  │   └── aiohttp POST request           │
│  └── stop_listening()                   │
│      └── Cleanup resources              │
│                                         │
│  Features:                              │
│  ├── Auto-reconnect (5s delay)          │
│  ├── Temporal event memory (90s)        │
│  ├── Event classification logic         │
│  └── Persistent HTTP session            │
│                                         │
└─────────────────────────────────────────┘
```

### Status Monitoring Stack
```
┌──────────────────────────────────────────────────┐
│          Status Monitoring Layers                │
├──────────────────────────────────────────────────┤
│                                                  │
│  Layer 1: Health Check Endpoint                  │
│  ├── URL: /health                                │
│  ├── Timeout: 5 seconds                          │
│  ├── Method: HTTP GET                            │
│  └── Response: JSON {status, service, timestamp} │
│                                                  │
│  Layer 2: Process Monitoring                     │
│  ├── Backend: pgrep uvicorn                      │
│  ├── Listener: pgrep snc_pbx_listener            │
│  └── Update interval: 10 seconds                 │
│                                                  │
│  Layer 3: Log Analysis                           │
│  ├── Backend: logs/backend.log                   │
│  ├── Listener: logs/pbx_listener.log             │
│  └── Pattern matching for status keywords        │
│                                                  │
│  Layer 4: TCP Connectivity                       │
│  ├── Target: 192.168.1.91:23                     │
│  ├── Timeout: 3 seconds                          │
│  └── Method: bash /dev/tcp test                  │
│                                                  │
│  Layer 5: Data Flow Verification                 │
│  ├── Check recent events in database             │
│  ├── Verify SMDR parsing activity                │
│  └── Confirm event forwarding success            │
│                                                  │
└──────────────────────────────────────────────────┘
```

## 🎨 Dashboard Status Logic

```
Status Determination Flowchart:

Backend Status:
┌─────────────────────┐
│ curl /health        │
│ timeout 5s          │
└────────┬────────────┘
         │
    ┌────┴────┐
    │ HTTP 200?│
    └────┬────┘
         │
    ┌────┴────────┐
    YES           NO
    │             │
    ▼             ▼
🟢 RUNNING    🔴 DOWN
Response      Port not
time < 5s     responding


PBX Listener Status:
┌─────────────────────┐
│ ps aux | grep       │
│ snc_pbx_listener    │
└────────┬────────────┘
         │
    ┌────┴────┐
    │Running? │
    └────┬────┘
         │
    ┌────┴────────┐
    YES           NO
    │             │
    ▼             ▼
┌──────────┐   🔴 STOPPED
│Check logs│
└────┬─────┘
     │
┌────┴──────────┐
│Connected      │
│successfully?  │
└────┬──────────┘
     │
┌────┴────┬────────┐
YES       NO       Retrying?
│         │        │
▼         ▼        ▼
🟢       ⚠️      ⚠️
RUNNING  Error   Reconnecting


PBX Stream Status:
┌─────────────────────┐
│ Test TCP conn       │
│ 192.168.1.91:23     │
│ timeout 3s          │
└────────┬────────────┘
         │
    ┌────┴────┐
    │Port open?│
    └────┬────┘
         │
    ┌────┴────────┐
    YES           NO
    │             │
    ▼             ▼
┌──────────┐   🔴 BLOCKED
│Events    │   Firewall/
│flowing?  │   Network issue
└────┬─────┘
     │
┌────┴────┬────────┐
YES       NO       
│         │        
▼         ▼        
🟢       ⚠️        
ACCESSIBLE CONFIGURED
Data      Port open
flowing   but idle
```

## 📊 Database Schema

```sql
-- Nurse Call Events Table
CREATE TABLE nurse_call_events (
    id TEXT PRIMARY KEY,              -- Unique event ID
    room_id TEXT NOT NULL,            -- Room number (e.g., "0400")
    event_type TEXT NOT NULL,         -- CALL_TRIGGERED, ACKNOWLEDGED, etc.
    status TEXT NOT NULL,             -- active, acknowledged, resolved
    timestamp TEXT NOT NULL,          -- ISO 8601 datetime
    fhir_payload TEXT NOT NULL,       -- Full HL7 FHIR JSON
    acknowledged_at TEXT,             -- When nurse acknowledged
    resolved_at TEXT,                 -- When call was cleared
    ack_time_seconds INTEGER,         -- Time to acknowledge (SLA)
    resolution_time_seconds INTEGER,  -- Time to resolve (SLA)
    sla_breached BOOLEAN DEFAULT FALSE -- SLA threshold exceeded
);

-- Indexes for performance
CREATE INDEX idx_room_id ON nurse_call_events(room_id);
CREATE INDEX idx_status ON nurse_call_events(status);
CREATE INDEX idx_timestamp ON nurse_call_events(timestamp);
```

## 🔐 Security Architecture

```
Current (Development):
┌──────────────────────────────────────┐
│  No Authentication                   │
│  HTTP only                           │
│  CORS: allow all (*)                 │
│  Open API endpoints                  │
│  SQLite file-based DB                │
└──────────────────────────────────────┘

Recommended (Production):
┌──────────────────────────────────────┐
│  JWT/OAuth2 Authentication           │
│  HTTPS/TLS encryption                │
│  CORS: restricted domains            │
│  Rate limiting (100 req/min)         │
│  PostgreSQL with user auth           │
│  API key for PBX listener            │
│  Audit logging                       │
│  Input validation/sanitization       │
└──────────────────────────────────────┘
```

## 📈 Performance Characteristics

```
Component          Startup    Memory    CPU      Response
                   Time       Usage     Idle     Time
─────────────────────────────────────────────────────────
Backend (FastAPI)  5-10s      ~80 MB    <2%      <100ms
PBX Listener       2-3s       ~30 MB    <1%      N/A
SQLite DB          <1s        ~10 MB    0%       <10ms
Dashboard          <1s        Browser   0%       <500ms
Total System       10-15s     ~120 MB   <5%      <1s
```

## 🔄 Restart Behavior

```
Normal Restart:
1. pkill existing processes
2. Wait 1 second
3. Start backend (uvicorn)
4. Poll /health every 2s (max 10 attempts)
5. Start PBX listener
6. Display PIDs and status

Auto-Reconnect (PBX Listener):
1. Connection lost detected
2. Log error message
3. Sleep 5 seconds
4. Attempt reconnection
5. Repeat until successful

Crash Recovery:
- Backend: Manual restart required
- Listener: Manual restart required
- Future: systemd with Restart=always
```

## 🎯 Key Integration Points

```
1. PBX → Listener
   Protocol: Telnet (TCP port 23)
   Format: SMDR text logs
   Pattern: ==SMDX2005=03/08/26 18:59 401 e.400...
   
2. Listener → Backend
   Protocol: HTTP POST
   Endpoint: /api/events/trigger
   Format: JSON {room_id, event_type}
   
3. Backend → Database
   Protocol: SQLite3
   Driver: sqlite3 module
   Mode: WAL journaling
   
4. Backend → Dashboard
   Protocol: WebSocket + REST
   Real-time: /ws/nurse-station
   Polling: /api/events
   
5. External → Backend
   Protocol: HTTP/REST
   Auth: None (dev), JWT (prod)
   CORS: Enabled
```

---

**This architecture supports:**
- ✅ Real-time event processing
- ✅ SLA tracking and analytics
- ✅ Multi-component status monitoring
- ✅ Automatic reconnection
- ✅ Scalable design for future enhancements
