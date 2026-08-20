---
name: snc
description: >
  Smart Nurse Call (SNC) PoC orchestrator for Phonik Help Call PBX —
  Phonik PBX SMDR/RDSS edge capture, FastAPI/WebSocket nurse station,
  HL7 FHIR-like events, SLA timers, built-in TCP proxy (port 2323) for
  Room Manager mirroring, Pi deploy and field diagnostics.
  Use when the user mentions snc, snc-poc, Smart Nurse Call, nurse call,
  EMER, CALL_BEDSIDE, CALL_BATHROOM_EMERGENCY, nurse_call_events,
  snc_pbx_listener, Phonik Help Call nurse dashboard, Room Manager 2323
  proxy, handshake emulation, or runs /snc.
  Complements Phonik_SNC_Hardware_Spec, PBX_Protocol_Handler,
  State_Verifier, and Cloudflare_Tunnel_Setup.
user-invocable: true
argument-hint: "[diagnose|start|test|deploy|kpi|proxy|rotate|fix <topic>]"
when-to-use: >
  snc-poc, Smart Nurse Call, nurse call dashboard, EMER pull switch,
  SMDR listener, PBX port 23 nurse events, Room Manager 2323 proxy
  mirror, SLA ack/resolution time, RDSS poll, Cloudflare tunnel SNC,
  Telegram alert SNC, OpenCode agent SNC
---

# SNC — Smart Nurse Call Orchestrator (Distilled Knowledge Graph)

**Role:** Senior Software Engineer & Healthcare IoT Specialist
**Scope root:** repo root — 5-Core layout: `api/` `app/` `pbx/` `ops/` `doc/`
**Brand:** `nithep/snc` · `https://snc.nithep.com`
**Language:** Thai for operator-facing docs and status; code/identifiers stay English

> **Graph navigation:** อ่านแต่ละ section ตามลำดับ — แต่ละหัวข้อจะเชื่อมไปยังหัวข้อถัดไปโดยอัตโนมัติ
> เมื่อต้องการข้อมูลลึก ให้โหลด specialist skills ตามตารางด้านล่าง

---

## STEP 1 — ทำความเข้าใจระบบ (Understand the System)

### What SNC Does

ระบบ Nurse Call สำหรับโรงพยาบาล/ศูนย์ดูแลผู้ป่วย ที่ดัดแปลงตู้สาขาโทรศัพท์ Phonik PBX
(รุ่น DX-32C/80C/144C) และบอร์ด Help Call (Call Station v.107) ให้ทำงานเป็นระบบ
แจ้งเตือนพยาบาล Real-time ผ่าน Web Application บน **Raspberry Pi 4**

### Core Workflow (5 steps — จำให้แม่น)

```
[1. คนไข้กดปุ่ม/ดึงสาย] → [2. ตู้ PBX พ่น SMDR Log]
                                    ↓
[5. คำนวณ SLA] ← [4. Dashboard แสดงผล + เสียงเตือน] ← [3. Listener แปลงเป็น FHIR JSON]
```

| Step | Component | สิ่งที่เกิดขึ้น |
|------|-----------|-----------------|
| 1 | NCX-CORD / NCX-PULL / DX-STATION | คนไข้กดเรียก → ตู้ PBX บันทึกเหตุการณ์ |
| 2 | Phonik PBX `192.168.1.91:23` | พ่น SMDR Log `==SMDX... e.400 ...` ผ่าน Telnet |
| 3 | `pbx/snc_pbx_listener.py` | สกัด `station_ext` → `room_id` (zero-pad 4 หลัก) → FHIR JSON → POST backend |
| 4 | `api/server.py` (FastAPI + WebSocket) | บันทึก SQLite WAL + broadcast ไป Dashboard |
| 5 | `app/index.html` (Nurse Dashboard v2.0) | แสดง Grid ห้อง (เขียว/แดงกะพริบ/เหลือง) + เสียง Siren + จับเวลา SLA |

### Specialist Skills (โหลดเมื่อต้องการข้อมูลลึก)

| Concern | Skill |
|---------|-------|
| Phonik Help Call HW / SMDR line shapes / DX cabinets | `Phonik_SNC_Hardware_Spec` |
| CCH2 `..ROOM` / `..NAME` (hotel power, not nurse call) | `PBX_Protocol_Handler` |
| ACK/NACK/timeout self-healing | `State_Verifier` |
| Cloudflare Tunnel / 502 / Pi DHCP | `Cloudflare_Tunnel_Setup` |
| Docs vault distillation | `Librarian_OKF_Protocol` |

---

## STEP 2 — รู้จักโครงสร้างไฟล์ (Know the Layout)

### 5-Core Standard Layout

```
snc/
├── api/          # 🔵 FastAPI server + SQLite WAL + WebSocket + SLA/KPI
├── app/          # 🟢 Nurse Dashboard v2.0 (index.html self-contained, Dark Mode, i18n)
├── pbx/          # 🟡 SMDR/RDSS listener + outbox + TCP proxy 2323 + parser tests
├── ops/          # 🔴 DevOps: deploy, backup, monitor, cron, verify, tunnel-self-heal
└── doc/          # 🟣 OKF docs + wiki/ + adr/ + raw/ (Obsidian vault)
```

### Key Files (Quick Map)

| Asset | Path |
|-------|------|
| Edge listener (SMDR + RDSS + heartbeat + proxy) | `pbx/snc_pbx_listener.py` |
| Durable outbox (ADR 0004) | `pbx/event_outbox.py` |
| Parser tests (26+ tests) | `pbx/test_smdr_parser.py` |
| Outbox tests | `pbx/test_event_outbox.py` |
| Backend | `api/server.py` |
| Storage layer (SQLite/Firestore) | `api/storage.py` |
| Bridge server (ADR 0002) | `api/bridge_server.py` |
| Main dashboard | `app/index.html` (v2.0: settings modal + API key, SLA count-up, KPI bars, i18n) |
| Landing page | `app/landing.html` |
| Content articles | `app/roi.html`, `app/snc-vs-imported.html`, `app/how-to-phonik.html` |
| SNC-Bot (Gemini free) | `POST /api/ai/snc-bot` |
| Telegram alert script | `ops/notify-telegram.sh` |
| Telegram Q&A agent | `ops/snc_telegram_agent.py` |
| Tunnel self-heal | `ops/tunnel-self-heal.sh` |
| DB backup | `api/nurse_call_events.db` (SQLite WAL, created in server cwd) |

### Nomenclature Rules (ADR 0007 — ห้ามละเมิด)

| Legacy (ห้ามใช้) | SNC (ใช้แทน) |
|---|---|
| `snc-poc` | `snc` |
| `snc-poc/backend/` | `api/` |
| `snc-poc/frontend/` | `app/` |
| `snc-poc/pbx-connector/` | `pbx/` |
| `hotel-ecs` / `Hotel-ECS` | ระบบโรงแรมคนละตัว |
| `hotel.nithep.com` | ระบบโรงแรม (CORS legacy) |
| `hotel-ecs-nithep` | GCP Project ID เก่า (คงไว้) |
| `ecs-agent` / `hotel-gateway` | ชื่อ OS จริงบน Pi (คงไว้) |

> **Full glossary:** `doc/NOMENCLATURE.md` §3

---

## STEP 3 — เข้าใจ Event Flow (Event Decision Matrix)

### Signal → Event Mapping

| Physical / SMDR signal | Software event | Priority | Dashboard |
|------------------------|----------------|----------|-----------|
| First `e.{room}` call | `CALL_BEDSIDE` | `urgent` | Red flash + siren; start ack timer |
| Repeat `e.{room}` within **90s** | `CALL_BATHROOM_EMERGENCY` | `stat` | Faster alert (escalate) |
| `offM` / `offx` clear | `CALL_CLEARED` | routine | Green; stop resolution timer |
| Nurse Ack on UI | `POST /api/events/acknowledge/{room_id}` | — | Yellow; stop ack timer |

### Room Mapping Rule (fixed 2026-08-12)

- ตู้ส่ง **`event_code`** (`e.400` = group code) แต่ห้องจริงอยู่ใน **`station_ext`**
- Listener ใช้ **`station_ext`** เป็น room_id เสมอ — เช่น station `401` → ห้อง `0401`
- Room IDs zero-padded 4 หลัก: `400` → `0400`

### RDSS (Room Display Status — Real-time Channel)

ตู้ Phonik **ไม่ Push ข้อมูลสด** — ต้อง **Poll `..EVNT=ALL`** ทุก 2-3 วินาที แล้ว Parse `==RDSS`

| Pattern | Meaning |
|---------|---------|
| `==RDSS401=1` | ห้อง 401 เริ่มเรียก (ไม่ = 0 = active) |
| `==RDSS400=4>401` | สถานีกลาง 400 กำลังรับจาก 401 |
| `==RDSS401=0` | ห้อง 401 เคลียร์ (ว่าง) |

> **Full RDSS detail:** `doc/wiki/SNC_PBX_RDSS_REALTIME_CHANNEL.md`

### SMDR vs RDSS (อย่าสับสน)

| | SMDR (`==SMDX...`) | RDSS (`==RDSS...`) |
|---|---|---|
| ความหมาย | ประวัติ Call Accounting | สถานะห้องเรียลไทม์ |
| การส่ง | Push ไปยัง Target IP / เก็บในคิว | Buffer แล้ว Dump เมื่อถูกขอ |
| การใช้ | ประวัติ/SLA ย้อนหลัง | **ช่องทางเรียลไทม์หลักของ Dashboard** |

### Timestamp Naming Map

| Spec term | Code column | Notes |
|-----------|-------------|-------|
| `created_at` | `timestamp` | DB column + FHIR `occurrenceDateTime` |
| `acknowledged_at` | `acknowledged_at` | เวลาพยาบาลรับเรื่อง |
| `cleared`/`resolved` | `resolved_at` | status `resolved` |
| Computed | `ack_time_seconds`, `resolution_time_seconds`, `sla_breached` | breach: ack > 30s or resolution > 180s |

---

## STEP 4 — Network & Connectivity (Know the Connections)

### Network Defaults (override via env)

| Role | Default | Env var |
|------|---------|---------|
| Phonik PBX SMDR | `192.168.1.91:23` | `PBX_IP`, `PBX_PORT` |
| PBX password | — | `PBX_PASS` (never commit) |
| Backend | `http://localhost:8000` | `BACKEND_API_URL` |
| TCP SMDR proxy (Room Manager mirror) | `0.0.0.0:2323` | `PROXY_PORT` |
| Edge Pi (primary) | `192.168.1.94` | alias `ssh pi4` |
| Edge Pi (WiFi OOB backup) | `192.168.1.109` | WiFi, power-save disabled |
| API auth | — | `SNC_API_KEY` (all POST/PUT/DELETE require `X-API-Key`) |
| Rate limit | GET 120/min, writes 20/min | `SNC_RATE_LIMIT_GET`, `SNC_RATE_LIMIT_WRITE` |
| Public dashboard | `https://snc.nithep.com` | Cloudflare Tunnel |
| OpenCode agent | `https://snc-opencode.nithep.com` | Cloudflare Tunnel (separate) |

### TCP SMDR Proxy — Port 2323 (Room Manager Mirror)

ตู้ Phonik รับ telnet ได้ **session เดียว** — listener ถือ `:23` ไว้ 24/7
เพื่อให้ PC Room Manager อ่านประวัติได้พร้อมกัน → listener เปิด TCP server บน `:2323`

1. PC ชี้ PBX IP ไปที่ **Pi port 2323** แทนตู้ `:23`
2. Handshake emulation: `..tcmd=` → `===tcmd=1`, `..VERS=` → `===VERS=DX-COMPACT V5.4r1`, `..PASS=` → `===ACKW`, `..EVNT=` → `===EVNT=END`
3. Telnet IAC bytes stripped before matching
4. Raw SMDR lines broadcast verbatim to all proxy clients

> **Verify:** `telnet <pi-ip> 2323` → send `..VERS=` → expect `===VERS=DX-COMPACT V5.4r1 (V5.1r0)`

### Handshake Order (Listener → PBX)

```
..tcmd=1 → ..VERS= → ..PASS=… → ..EVNT=ALL
```

### Heartbeat (Anti Idle-Timeout)

PBX drops telnet session after **60s of silence**. Listener runs `_heartbeat_loop`
sending `..VERS=\r\n` every **30s** to hold the connection 24/7.

### Self-Healing Watchdog

- `_last_data_time` updates on every data received (including RDSS poll responses every 3s)
- `_watchdog_loop` checks every 10s: if silence > 60s → force-close connection → main loop reconnects
- Heartbeat/poll resilience: if `writer.write/drain()` fails → immediate reconnect

---

## STEP 5 — Security & Secrets (Never Compromise)

### Auth Model

- **`X-API-Key` header** required for all POST/PUT/DELETE when `SNC_API_KEY` is set
- GET stays open for dashboard polling
- Rate limit checked **before** auth (throttles brute-force too)

### Secret Locations (3-tier sync — must match!)

| Secret | Where | Sync? |
|--------|-------|-------|
| `SNC_API_KEY` | Pi `api/.env` + Pi `pbx/.env` + Cloud Run `snc-cloud-backend` | **ต้องตรงกันทั้ง 3 จุด** |
| `TELEGRAM_BOT_TOKEN` | Pi `api/.env` + Cloud `snc-telegram-bot-token` | หมุนพร้อมกัน 2 ฝั่ง |
| `MONITOR_WEBHOOK_TOKEN` | Cloud Monitoring channel URL + bridge | กัน spoofing |
| Cloudflare Tunnel token | `/etc/snc/cloudflared.env` (Pi, chmod 600) | หมุนผ่าน `setup-cloudflared.sh` |
| `OPENCODE_SERVER_PASSWORD` | `~/.config/opencode/opencode.env` | หมุนด้วย `openssl rand -hex 18` |

### .gitignore Rules (Critical — AGENTS.md ข้อ 5)

- **ห้ามใช้ pattern `*key*`/`*secret*`** — จะกลืนเอกสาร legit
- ให้ใช้แบบเจาะจง: `*.key`, `*.pem`, `*.p12`, `*.pfx`, `*service-account*.json`, `*credentials*.json`
- ตรวจ `git status --ignored` ว่ามีไฟล์ที่ควร track โดนกลืนไหม

### Rotation Guides (ต้องมีครบ 3 ฉบับ)

| Guide | File |
|-------|------|
| API Key | `doc/wiki/SNC_API_KEY_ROTATION_GUIDE.md` |
| Telegram Bot | `doc/wiki/SNC_TELEGRAM_ROTATION_GUIDE.md` |
| Cloudflare Tunnel | `doc/wiki/SNC_CLOUDFLARE_ROTATION_GUIDE.md` |

---

## STEP 6 — Architecture Decisions (ADR Chain)

> การตัดสินใจทุกข้อเชื่อมต่อกัน — อ่าน ADR ตามลำดับจะเห็นวิวัฒนาการ

| ADR | เรื่อง | สถานะ | เชื่อมกับ |
|-----|--------|--------|-----------|
| **0001** | บันทึกสถาปัตยกรรม (ADR pattern) | Accepted | → 0002-0009 ทั้งหมด |
| **0002** | แยก SNC Alert Bridge เป็น service ต่างหาก | Accepted | → 0003 (Firestore), 0005 (IaC) |
| **0003** | ใช้ Firestore (แทน SQLite) บน Cloud Run | Accepted | → `api/storage.py` (factory interface) |
| **0004** | Outbox + Idempotency (กัน data loss / duplicate) | Accepted | → `pbx/event_outbox.py` |
| **0005** | Infrastructure-as-Code ด้วย Terraform | Proposed | → `ops/terraform/` |
| **0006** | Message Broker + Dual-Pi (อนาคต/life-safety) | Pending | → เกณฑ์: consumer > 2 หรือ life-safety |
| **0007** | แยกชื่อ SNC ออกจาก Hotel-ECS | Accepted | → `doc/NOMENCLATURE.md` |
| **0008** | โครงสร้างความเชื่อมโยงทั้งระบบ (topology) | Accepted | → แผนที่ 3 ชั้น (Repo/Edge/Cloud) |
| **0009** | แยก OpenCode Agent เป็น headless service | Accepted | → `snc-opencode.nithep.com` |

### Key Architecture Facts

- **Edge DB:** SQLite WAL (`nurse_call_events.db`) — schema self-migrating via `ensure_column()`
- **Cloud DB:** Firestore (native mode) — collections `nurse_call_events`, `room_state`
- **Storage interface:** `api/storage.py` → `get_store()` factory, switched by env `SNC_DB_BACKEND`
- **Outbox:** `pbx/event_outbox.py` → SQLite `snc_event_outbox` table → pending → retry → sent
- **Idempotency:** listener sends `event_id` → backend dedup via `store.event_exists()` + `INSERT OR IGNORE`

---

## STEP 7 — Deploy & Operate (Edge + Cloud)

### Systemd Services (Pi4 — Production)

| Service | WorkingDirectory | Dependency |
|---------|-----------------|------------|
| `snc-backend.service` | `/home/ecs-agent/snc/api` | `After=network.target` |
| `snc-pbx-listener.service` | `/home/ecs-agent/snc/pbx` | `After=network.target snc-backend.service` |
| `snc-cloudflared.service` | — | Tunnel outbound → `localhost:8000` |
| `snc-tg-agent.service` | `/home/ecs-agent/snc` | Telegram Q&A agent |

All run as `ecs-agent` user, `Restart=always`, `RestartSec=5s`.

### Cloud Services (GCP — `hotel-ecs-nithep`)

| Service | Purpose |
|---------|---------|
| `snc-cloud-backend` (Cloud Run) | Backend on Firestore (`SNC_DB_BACKEND=firestore`) |
| `snc-alert-bridge` (Cloud Run) | Webhook → Telegram (ADR 0002, แยก service) |
| Firestore | Persistent DB (scale-to-zero safe) |
| Secret Manager | `snc-api-key`, `snc-telegram-bot-token`, `snc-monitor-webhook-token` |
| Cloud Monitoring | Uptime check `/health` → alert → bridge → Telegram |

### Cloudflare Tunnel

- **Domain:** `https://snc.nithep.com` → `http://localhost:8000` (Pi4)
- **OpenCode:** `https://snc-opencode.nithep.com` → `http://localhost:4096` (Pi4)
- **กฎเหล็ก:** ห้ามใช้ LAN IP ใน Service URL — ใช้ `localhost` เสมอ (ป้องกัน 502 จาก DHCP drift)

### Sync Strategy

```
MateBook (D:/snc) → git push → GitHub (nithep/snc) → git pull/rsync → Pi4 Production
```
- `.env` files แยกกัน (ไม่ sync) — แต่ `SNC_API_KEY` ต้องตรงกันทั้ง 3 จุด

---

## STEP 8 — Troubleshooting (Find & Fix)

### Quick Diagnosis Flow

```
症状 → ตรวจสอบ → สาเหตุ → แก้ไข
```

| อาการ | ตรวจสอบ | สาเหตุพบบ่อย | แก้ไข |
|--------|---------|-------------|--------|
| `Connection refused` on `:23` | `ping 192.168.1.91` + `telnet .91 23` | Telnet session เดียวถูกครอบ | ปิด PC Operator / ให้ใช้ proxy `:2323` |
| `Not have free PABX telnet port` | — | session ค้างเต็ม RAM ตู้ | Power Cycle ตู้ (off ~15s) |
| Idle disconnect ~60s | listener log | heartbeat หาย (รุ่นเก่า) | upgrade `snc_pbx_listener.py` |
| PC Room Manager "Authenticate Failed!!" on `:2323` | — | listener ไม่มี handshake emulation | upgrade listener |
| SMDR flows แต่ wrong room (`0400` แทน `0401`) | — | room-mapping fix หาย | ใช้ `station_ext` สำหรับ `e.` events |
| Dashboard `/` 404/blank | `app/index.html` deployed? | server ไม่เจอ static files | copy `app/index.html` จาก repo |
| 502 on `snc.nithep.com` | Cloudflare ingress rule | ชี้ไป LAN IP (DHCP drift) | เปลี่ยนเป็น `http://localhost:8000` |
| Backend crash `ModuleNotFoundError: core` | `sys.path` in server.py | WorkingDirectory ไม่เจอ repo root | เพิ่ม repo root เข้า `sys.path` |
| `Invalid tunnel secret` (Error 1033) | `cloudflared tunnel list` | credentials file stale | `cloudflared tunnel token <name>` → write new credentials |

### Full Playbooks

| Topic | File |
|-------|------|
| PBX connectivity ( Errno 111, session lock, SMDR Target IP) | `doc/wiki/SNC_PBX_CONNECTIVITY_TROUBLESHOOTING.md` |
| Power cycle SOP | `doc/PBX_POWER_CYCLE_SOP.md` |
| RDSS troubleshooting | `doc/wiki/SNC_PBX_RDSS_REALTIME_CHANNEL.md` §troubleshooting |
| Cloudflare tunnel | `doc/wiki/SNC_CLOUDFLARE_TUNNEL_SUMMARY.md` |
| Quick reference card | `doc/QUICK_REFERENCE.md` |

---

## STEP 9 — Telegram & Monitoring (Alerting Chain)

### Telegram Alert (`@snc2569_bot`)

- **Script:** `ops/notify-telegram.sh` — curl → Bot API → sendMessage (zero dependency)
- **Q&A agent:** `ops/snc_telegram_agent.py` — poll `getUpdates`, responds `/kpi`, `/rooms`, `/burn`, `/status`, `/help`
- **Evening digest:** `ops/snc-evening-digest.sh` — cron 19:00 daily, KPI + tips
- **Cloud Monitoring:** GCP uptime check `/health` every 300s → fail 120s → webhook → `snc-alert-bridge` → Telegram
- **Allowed chat:** `SNC_TG_ALLOWED_CHAT=7346817215` — other accounts get refused

### Key Crons on Pi4

| Cron | Schedule | Purpose |
|------|----------|---------|
| `verify-daily.sh` | 07:00 daily | System health + Telegram summary |
| `snc-evening-digest.sh` | 19:00 daily | KPI + tips |
| `backup-snc-db.sh` | 03:00 daily | DB backup |
| `tunnel-self-heal.sh` | every 15 min | Detect 0 connections → rotate tunnel secret |

---

## STEP 10 — KPI Targets & SLA

| Metric | Target | How Measured |
|--------|--------|-------------|
| Nurse Ack Response Time | ≤ 30 s | `ack_time_seconds` = `acknowledged_at` - `created_at` |
| Total Resolution Time | ≤ 180 s | `resolution_time_seconds` = `resolved_at` - `created_at` |
| SLA Compliance (ops goal) | ≥ 98% | events without `sla_breached=1` / total |

---

## STEP 11 — Operating Modes (Slash Commands)

### `/snc diagnose` (default if unclear)
1. Confirm cwd, check parser tests + backend health + listener defaults
2. If on network: connectivity to `:23`, `:2323`, `:8000/health`
3. Output: symptom → layer (PBX/listener/backend/UI/tunnel) → next command

### `/snc start` / ops
```bash
# On Pi (typical)
cd /home/ecs-agent/snc && ./ops/start-snc-system.sh
./ops/monitor-snc-status.sh
```

### `/snc test`
1. Parser tests: `python pbx/test_smdr_parser.py` (26+ tests)
2. Synthetic event (no PBX required):
```bash
curl -X POST http://localhost:8000/api/events/trigger \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $SNC_API_KEY" \
  -d '{"room_id":"400","event_type":"CALL_BEDSIDE"}'
```
3. Full deterministic demo:
```bash
curl -X POST http://localhost:8000/api/demo/scenario \
  -H "Content-Type: application/json" \
  -d '{"room_id":"400","ack_after":5,"clear_after":12,"include_emergency":true}'
```

### `/snc deploy`
Follow `doc/DEPLOYMENT_PI4.md` / `doc/DEPLOYMENT_CHECKLIST.md`.
On Pi: backup → scp → verify md5sum → restart systemd → verify health + synthetic test.

### `/snc kpi`
Query `/api/analytics/kpi` or read SQLite timestamps. No fake numbers — if DB empty, say so.

### `/snc proxy`
Inspect port-2323 SMDR mirror / handshake emulation.

### `/snc rotate`
Rotate secrets: API Key, Telegram token, Cloudflare tunnel credentials. Follow rotation guides.

### `/snc fix <topic>`
Implement or document a change: keep FHIR-like shape, UTF-8 for Thai, update docs/wiki only when material.

---

## STEP 12 — History & Timeline (When Things Happened)

| Date | Milestone |
|------|-----------|
| 01-02 ส.ค. | Edge Serial/TCP Listener + Vertex AI Payload + Pi Zero 2W deploy |
| 03 ส.ค. | **SNC PoC Strategy** — separate workspace, SMDR Listener, Backend, Dashboard |
| 04-05 ส.ค. | Sovereign AI Blueprint, MVP Validation, EMER + Digital Twin, Intercom Baseline |
| 05 ส.ค. | Field Go-Live Verification, Executive Approved |
| 06 ส.ค. | Hybrid Cloud → GCP Cloud Run, Go-Live Manual, Gemini REST |
| 08 ส.ค. | SQLite WAL, Hotfix Pi Zero 2W (RAM 512MB too small → migrate to Pi4) |
| 09 ส.ค. | **Live End-to-End ครั้งแรกบน Pi 4** |
| 10-11 ส.ค. | Auth hardening, Systemd Services, **Cloudflare Tunnel Go-Live**, TCP Proxy 2323 |
| 11-12 ส.ค. | PBX Power Cycle SOP, RDSS Real-time Channel, Watchdog, Proxy Fix |
| 13 ส.ค. | Dashboard v2.0, Security Hardening, **Burn-in 48h เริ่ม**, 5-Core split |
| 14 ส.ค. | Extension Inventory, Executive Report Upskill, Telegram bot live |
| 15 ส.ค. | **Burn-in 48h Complete (0 FAIL)**, Post-Burnin Field Test Plan |
| 16 ส.ค. | Cloud Run + Firestore + Monitoring Hardening |
| 17 ส.ค. | ADR 0001-0006 written, Outbox + Idempotency implemented |
| 18 ส.ค. | ADR 0007-0008, Nomenclature cleanup, Domain migration nursecall→snc |
| 19 ส.ค. | `snc.nithep.com` live, rotation guides, tunnel self-heal script |
| 20 ส.ค. | OpenCode agent tunnel (ADR 0009), Power outage incident + recovery |

> **Full timeline:** `doc/wiki/project_timeline.md`
> **Latest handover:** `doc/wiki/SESSION_HANDOVER_2026-08-19.md`

---

## STEP 13 — Safety Rules (Never Break These)

1. **No silent hardware commands** — SMDR listen is passive; CCH2 write commands need tests + explicit intent
2. **Secrets only in env** — never in committed config; server/listener load `.env` themselves
3. **Do not confuse products** — Hotel room power (`..ROOM=`) ≠ Nurse Call SMDR (`==SMDX` / `e.room`)
4. **UTF-8** for all Thai docs and scripts
5. **Prefer existing scripts** under `ops/` over greenfield process managers
6. **Never put LAN IPs in Cloudflare ingress rules** — use loopback/Docker-bridge targets
7. **Outbox first** — PBX Listener must go through `pbx/event_outbox.py` before POST (ADR 0004)
8. **ADR for architecture changes** — record in `doc/adr/NNNN-<title>.md`
9. **UTF-8 explicit** — Thai markdown files must specify encoding

---

## STEP 14 — Collaboration Map (Who Does What)

| Role | Responsibility | Touches |
|------|---------------|---------|
| SNC Agent (this skill) | Healthcare IoT engineer | All 5-Core |
| Librarian (OKF) | Vault distillation | `doc/wiki/` |
| Hotel ECS | Separate system | CORS origins only |
| Saen Barrel roles | Bridge only when user asks | Default: stay in SNC |

---

## Document Reference Map (Complete Links)

### Core Docs
| Doc | Purpose | When to read |
|-----|---------|-------------|
| `doc/BLUEPRINT_5CORE.md` | Project structure standard | Always |
| `doc/ARCHITECTURE_FLOW.md` | Full system topology (Mermaid) | Deploy/architecture questions |
| `doc/ARCHITECTURE_DIAGRAM.md` | Edge-only diagram | Pi-specific work |
| `doc/NOMENCLATURE.md` | Controlled vocabulary + glossary | Naming questions |
| `doc/QUICK_REFERENCE.md` | Cheat card for Pi4 ops | On-site / quick commands |
| `AGENTS.md` | Repo-wide agent rules | Always (root) |

### Wiki Docs (Deep Dives)
| Doc | Topic | Connects to |
|-----|-------|-------------|
| `wiki/phonik_nurse_call_knowledge.md` | Hardware catalog (Phonik DX series, wiring, numbering, SOS CALL) | STEP 1 |
| `wiki/SNC_PBX_CONNECTIVITY_TROUBLESHOOTING.md` | Errno 111, session lock, power cycle | STEP 8 |
| `wiki/SNC_PBX_RDSS_REALTIME_CHANNEL.md` | RDSS polling, watchdog, proxy fix | STEP 3 |
| `wiki/SNC_SYSTEMD_SERVICES_SUMMARY.md` | Systemd config + self-healing | STEP 7 |
| `wiki/SNC_CLOUDFLARE_TUNNEL_SUMMARY.md` | Tunnel ingress, 502 prevention | STEP 7 |
| `wiki/SNC_TELEGRAM_ALERTS.md` | Bot setup, Q&A agent, monitoring bridge | STEP 9 |
| `wiki/SNC_API_KEY_ROTATION_GUIDE.md` | API key rotation Pi/Cloud/Client | STEP 5 |
| `wiki/SNC_TELEGRAM_ROTATION_GUIDE.md` | Telegram token rotation | STEP 5 |
| `wiki/SNC_CLOUDFLARE_ROTATION_GUIDE.md` | Tunnel credentials rotation | STEP 5 |
| `wiki/SNC_API_KEY_SETUP_GUIDE.md` | First-time API key setup | STEP 5 |
| `wiki/SNC_GO_LIVE_MANUAL.md` | Executive demo script + Go-Live | STEP 11 |
| `wiki/SNC_POST_BURNIN_FIELD_TEST_PLAN.md` | Post-burnin test scenarios A/B/C | STEP 11 |
| `wiki/SNC_TEST_EXTENSION_INVENTORY.md` | Test extension mapping + KPI audit | STEP 3 |
| `wiki/SNC_SOVEREIGN_AI_BLUEPRINT.md` | Private network sovereignty | Architecture |
| `wiki/SNC_OPENCODE_SETUP_GUIDE.md` | OpenCode headless agent on Pi4 | ADR 0009 |
| `wiki/SNC_NOMENCLATURE_CLEANUP.md` | Legacy name cleanup plan | STEP 2 |
| `wiki/SNC_DOMAIN_MIGRATION_NOTE.md` | nursecall→snc domain migration | STEP 7 |
| `wiki/WINDOWS_SCHEDULED_TASK_HYGIENE.md` | Windows scheduled task cleanup | Ops |
| `wiki/project_timeline.md` | Full project history | STEP 12 |
| `wiki/INDEX_TIMELINE.md` | Timeline index (short) | STEP 12 |
| `wiki/smart_nurse_call_project_plan.md` | Project plan | Planning |

### ADR Docs
| ADR | Topic | Key files affected |
|-----|-------|-------------------|
| 0001 | ADR pattern | `doc/adr/` |
| 0002 | Alert Bridge separation | `api/bridge_server.py`, `ops/deploy_bridge_cloudshell.sh` |
| 0003 | Firestore on Cloud Run | `api/storage.py` |
| 0004 | Outbox + Idempotency | `pbx/event_outbox.py`, `api/server.py` |
| 0005 | Terraform IaC | `ops/terraform/` |
| 0006 | Broker + Dual-Pi (future) | — (pending) |
| 0007 | Nomenclature separation | `doc/NOMENCLATURE.md` |
| 0008 | System topology | `doc/ARCHITECTURE_FLOW.md` |
| 0009 | OpenCode agent tunnel | `snc-opencode.nithep.com`, `ops/snc-tg-agent.service` |

### Raw Docs (Legacy — for reference only)
| Doc | Notes |
|-----|-------|
| `raw/IMPLEMENTATION_SUMMARY.md` | Old — has `snc-poc` legacy names |
| `raw/README_DEPLOYMENT.md` | Old deployment notes |
| `raw/PHASE1_*.md` | Phase 1 completion |
| `raw/snc_analysis_report.md` | PBX analysis (SMDR Target IP) |
| `raw/โครงสร้าง SNC Pi4 Project Tree.md` | Old tree structure |

---

## Activation

* `/snc` or `/snc diagnose` → full stack triage
* `/snc test` → parser + API synthetic path
* `/snc deploy` → Pi / tunnel checklist execution
* `/snc proxy` → port-2323 Room Manager mirror / handshake emulation
* `/snc rotate` → rotate secrets (API key, Telegram, Cloudflare)
* Phrases: "snc-poc", "Smart Nurse Call", "ดึงสาย EMER", "วัด SLA nurse call", "Room Manager 2323", "RDSS poll"

*Orchestrate SNC PoC work end-to-end; defer HW catalogs and CCH2 power protocol to sibling skills.*
