---
name: snc
description: Use when working on the SNC (Smart Nurse Call) project — a real-time nurse alerting system built on a Phonik PBX and Help Call board running on Raspberry Pi 4. Covers the 5-core layout (api/, app/, pbx/, ops/, doc/), SMDR/Telnet parsing, FHIR JSON payloads, WebSocket alerting, SQLite WAL, and the Thai-language communication conventions.
---

# SNC — Smart Nurse Call

## About the project

A hospital / care-facility nurse call system built by repurposing a Phonik PBX
cabinet (DX-32C/80C/144C) and a Help Call board (Call Station v.107) into a
real-time web-based alerting system running on **Raspberry Pi 4**, under the
brand **nithep** (`https://snc.nithep.com`).

## Core workflow

1. **Nurse Call Trigger**: patient presses the emergency button / pulls the cord
   (NCX-CORD / NCX-PULL) or lifts the room handset.
2. **PBX Event Capture**: the Phonik PBX emits real-time SMDR Logs
   (`==SMDX... e.400 ...`) over TCP Telnet (`192.168.1.91:23`).
3. **Backend Event Processing**: `snc_pbx_listener` extracts the room number and
   event type, maps it to FHIR JSON, and writes to SQLite
   (`nurse_call_events.db`).
4. **Real-time Alerting**: backend pushes alerts over WebSocket to the Nurse
   Station Dashboard.
5. **Nurse Dashboard Response**: the nurse counter screen shows a room grid
   (green=normal, blinking red=emergency, yellow=acknowledged), plays an alarm,
   and times response until the nurse Acknowledges/Clears.

## Directory structure (5-Core Standard Layout)

| Folder | Purpose |
|--------|---------|
| `api/` | FastAPI server: business logic, FHIR data schema, SLA/KPI, WebSocket, SQLite WAL |
| `app/` | Nurse Dashboard (`index.html` self-contained, premium Dark Mode, i18n Thai/English) |
| `pbx/` | SMDR/Telnet edge listener (`snc_pbx_listener.py`) + parser tests + TCP proxy on port 2323 |
| `ops/` | DevOps: deploy, burn-in monitor, DB backup, cron, Pi health checks |
| `doc/` | OKF docs: staff guide + SOP + `wiki/` knowledge base. Blueprint: `doc/BLUEPRINT_5CORE.md` |

## Project rules (AI Agent conventions)

1. **Role**: Senior Software Engineer & Healthcare IoT Specialist.
2. **Communication**: use professional Thai in docs, code, and artifacts.
3. **Data Standards**: design payloads as **HL7 FHIR JSON** from Day 1 to prepare
   for GCP Healthcare API / Vertex AI Predictive Analytics.
4. **Strict UTF-8**: always save/read Thai files as `utf-8`.
5. **Never use broad `*key*`/`*secret*` patterns in .gitignore** — they silently
   swallow legitimate docs (e.g. `SNC_API_KEY_ROTATION_GUIDE.md` was ignored and
   never committed). Use specific patterns (`*.key`, `*.pem`, `*.p12`, `*.pfx`,
   `*service-account*.json`, `*credentials*.json`) and check
   `git status --ignored` for swallowed files.
6. **Every project needs a key-rotation guide**: create
   `doc/wiki/*_ROTATION_GUIDE.md` (see `doc/wiki/SNC_API_KEY_ROTATION_GUIDE.md`)
   covering Pi/Server, Cloud Run, and Client whenever a service with a secret is
   added.

## Security notes

- All PBX control commands go through a Verifier (Safety First).
- API Key + Rate Limit against LAN attacks (`SNC_API_KEY`).
- SQLite WAL Mode + auto-backup via cron (`ops/backup-snc-db.sh`).
- Self-healing via systemd (`Restart=always`) + Burn-in Monitor
  (`ops/burnin-monitor.sh`).

## Quick start

```bash
cd ~/nithep/snc
./ops/quick_start.sh            # run API + Listener
curl -s http://localhost:8000/health
```