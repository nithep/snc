---
title: "🏗️ 5-Core Project Blueprint"
type: wiki
tags: [knowledge]
---

# 🏗️ 5-Core Project Blueprint

> **มาตรฐานโครงสร้างโปรเจกต์สำหรับ Smart Nurse Call (SNC) และโปรเจกต์ในอนาคต**  
> **Version:** 1.0 | **Effective:** 15 ส.ค. 2569

---

## 📋 วัตถุประสงค์

กำหนดโครงสร้างโปรเจกต์มาตรฐานเดียว (Single Source of Truth) ที่ใช้ได้กับทุกโปรเจกต์ ไม่ว่าจะ deploy บน local machine, Raspberry Pi, Cloud Run, หรือ Docker

---

## 🏛️ โครงสร้าง 5-Core Layout

```
project-root/
│
├── api/                    # 🔵 Core 1: Backend API / Business Logic
│   ├── server.py           # FastAPI / Express / main entry point
│   ├── services/           # Business logic modules
│   ├── models/             # Data models / schemas (FHIR, etc.)
│   ├── tests/              # Unit & integration tests
│   ├── requirements.txt    # Python dependencies
│   ├── Dockerfile          # Container definition
│   ├── .env                # 🔐 Vault: Config + Credentials (gitignored)
│   └── *.db                # Database files (SQLite WAL mode)
│
├── app/                    # 🟢 Core 2: Frontend / Dashboard
│   ├── index.html          # Main dashboard (self-contained SPA)
│   ├── *.html              # Other pages
│   ├── assets/             # Static assets (images, fonts)
│   └── manifest.json       # PWA manifest (if applicable)
│
├── pbx/                    # 🟡 Core 3: Edge / IoT / Listener
│   ├── *_listener.py       # Edge capture service
│   ├── event_outbox.py     # Durable outbox (ADR 0004) — กัน event หาย/ซ้ำ
│   ├── *_parser.py         # Protocol parsers
│   ├── tests/              # Parser tests
│   ├── requirements.txt    # Listener-specific deps
│   ├── .env                # 🔐 Vault: Listener credentials (gitignored)
│   └── *.db                # Edge cache + snc_event_outbox.db (if needed)
│
├── ops/                    # 🔴 Core 4: DevOps / Operations
│   ├── deploy*.sh          # Deployment scripts
│   ├── backup*.sh          # Backup & restore
│   ├── monitor*.sh         # Health monitoring
│   ├── setup*.sh           # Initial setup / provisioning
│   ├── *.service           # systemd unit files
│   ├── fabric/patterns/    # Fabric Patterns — กลั่นความรู้จาก traces (ADR 0013)
│   ├── raw/                # Non-PHI trace dumps (gitignored, ADR 0013)
│   └── cron/               # Scheduled tasks
│
└── doc/                    # 🟣 Core 5: Documentation
    ├── ARCHITECTURE.md     # System architecture
    ├── BLUEPRINT_5CORE.md  # This blueprint
    ├── ARCHITECTURE_FLOW.md# รวมผัง Edge + Cloud (Mermaid)
    ├── DEPLOYMENT.md       # Deployment guide
    ├── API.md              # API reference
    ├── USER_GUIDE.md       # End-user manual
    ├── adr/                # Architecture Decision Records (ADR 0001-0013)
    ├── wiki/               # Knowledge base
    └── playbooks/          # Skills Layer — SOPs & Action Guides (human-approved, ADR 0013)
```

---

## 🔐 Vault Structure (5 C Framework)

ไฟล์ความลับต้องอยู่ใน `.env` เท่านั้น ห้าม commit ลง git

### ตำแหน่ง `.env` ตาม service

| Service | `.env` Location | ใช้กับ |
|---|---|---|
| API Server | `api/.env` | server.py, health_check.py |
| Listener | `pbx/.env` | snc_pbx_listener.py |
| Root (optional) | `.env` | deploy scripts, tunnel tokens |

### ตัวอย่าง `.env` สำหรับ API Server

```bash
# === SNC API Server Config ===

# Database
DB_PATH=./nurse_call_events.db

# Auth (rotate every 90 days)
SNC_API_KEY=<generate with: python3 -c "import secrets; print(secrets.token_hex(32))">

# AI Integration
GEMINI_API_KEY=<your-key>

# Alerts
TELEGRAM_BOT_TOKEN=<token>
TELEGRAM_CHAT_ID=<id>
GOOGLE_CHAT_WEBHOOK_URL=<url>

# Contact email notifications (SMTP)
SNC_SMTP_HOST=smtp.example.com
SNC_SMTP_PORT=587
SNC_SMTP_USERNAME=alerts@example.com
SNC_SMTP_PASSWORD=<smtp-password>
SNC_SMTP_FROM=alerts@example.com
SNC_CONTACT_EMAIL=team@example.com

# PBX Connection
PBX_HOST=192.168.1.91
PBX_PORT=23
```

### ตัวอย่าง `.env` สำหรับ Listener

```bash
# === SNC PBX Listener Config ===

# Backend connection
BACKEND_API_URL=http://localhost:8000
SNC_API_KEY=<same key as api/.env>

# PBX connection
PBX_HOST=192.168.1.91
PBX_PORT=23
PBX_PASS=<pbx-password>
```

---

## 🔄 Sync Strategy: Local ↔ Production (Pi4/Cloud)

### โครงสร้างต้องตรงกัน

```
Local Machine                 Pi4 Production
─────────────                 ──────────────
api/server.py          ←→    api/server.py
api/services/*         ←→    api/services/*
app/index.html         ←→    app/index.html
pbx/snc_pbx_listener.py ←→  pbx/snc_pbx_listener.py
ops/*.sh               ←→    ops/*.sh (paths adjusted)
```

### .env แยกกัน (ไม่ sync)

```
Local api/.env         →  Development keys (may differ)
Pi4 api/.env           →  Production keys (rotate quarterly)
Cloud Run env vars     →  Production keys (same as Pi4)
```

---

## 🚀 Deploy Workflow

### Standard Deploy (scp/rsync)

```bash
# Deploy API server
rsync -avz --exclude='.env' \
  api/ pi4:/home/ecs-agent/snc/api/

# Deploy listener
rsync -avz --exclude='.env' \
  pbx/ pi4:/home/ecs-agent/snc/pbx/

# Deploy dashboard
rsync -avz app/ pi4:/home/ecs-agent/snc/app/

# Restart services
ssh pi4 "sudo systemctl restart snc-backend snc-pbx-listener"
```

### Docker Deploy (Cloud Run)

```bash
# Build & push (context = repo root — image ต้องมีทั้ง api/ และ app/)
docker build -t gcr.io/PROJECT/snc-api -f api/Dockerfile .
docker push gcr.io/PROJECT/snc-api

# Deploy with env vars
gcloud run deploy snc-api \
  --image gcr.io/PROJECT/snc-api \
  --set-env-vars "SNC_API_KEY=$KEY" \
  --region asia-southeast1
```

---

## 🧠 Architecture Decisions (ADR) & Durable Delivery

### ADR (`doc/adr/`)
การตัดสินใจเชิงสถาปัตย์ทุกครั้งต้องบันทึกเป็น ADR แยกไฟล์ (`NNNN-<title>.md`)
ด้วยโครงสร้าง **Context / Decision / Consequences / Alternatives** — ดู ADR 0001

| ADR | เรื่อง | สถานะ |
|-----|-------|--------|
| 0001 | มาตรฐานการบันทึก ADR | Accepted |
| 0002 | แยก SNC Alert Bridge เป็น service ต่างหาก | Accepted |
| 0003 | Firestore แทน SQLite บน Cloud Run (interface เดียวใน `api/storage.py`) | Accepted |
| 0004 | Outbox + Idempotency (กัน event หาย/ซ้ำ) | Accepted |
| 0005 | Infrastructure-as-Code ด้วย Terraform | Proposed |
| 0006 | Message Broker + Dual-Pi (อนาคต/life-safety) | Proposed |

### Outbox & Idempotency (ADR 0004)
- **`pbx/event_outbox.py`**: listener เขียน event ลง SQLite (`snc_event_outbox.db`) เป็น `pending`
  ก่อนส่ง → retry แบบ backoff (15s) จนกว่า backend รับ → mark `sent`
- **Idempotency**: listener ส่ง `event_id` → backend dedup (`store.event_exists`)
  + `save_event` ใช้ `INSERT OR IGNORE` (ไม่ทำลาย ack/clear)
- **ผล**: event ไม่หายตอน backend down, ไม่ duplicate → SLA นับถูก

### Synthetic E2E (`ops/synthetic-e2e-check.sh`)
ตรวจเกิน `/health` 200: ยิง event จำลองจริง + ตรวจ idempotency + ยืนยัน event อยู่ใน `/api/events`
(ใช้ได้ทั้ง Pi/Cloud — ใช้ใน cron)

---

## 📏 Conventions

### Naming

| Type | Convention | Example |
|---|---|---|
| Services | `snc-{component}` | `snc-backend`, `snc-pbx-listener` |
| Env vars | `SCREAMING_SNAKE_CASE` | `SNC_API_KEY`, `PBX_HOST` |
| Files | `snake_case.py` | `snc_pbx_listener.py` |
| Tests | `test_*.py` | `test_smdr_parser.py` |

### Permissions (Pi4)

| Path | Permission | Owner |
|---|---|---|
| `.env` files | `600` | `ecs-agent` |
| `api/` directory | `700` | `ecs-agent` |
| `*.py` files | `644` | `ecs-agent` |
| `*.db` files | `660` | `ecs-agent` |

---

## ✅ Checklist Before Deploy

- [ ] `.env` files exist on target (with correct keys)
- [ ] `.env` permissions set to `600`
- [ ] No secrets in committed code (grep checked)
- [ ] Service files point to correct paths
- [ ] Tests pass locally
- [ ] Backup created (if updating production)

---

## 📚 References

- [[0001-record-architecture-decisions|ADR 0001-0006]] — การตัดสินใจเชิงสถาปัตยกรรม
- [[ARCHITECTURE_FLOW]] — ผังรวม Edge + Cloud
- [[SNC_API_KEY_SETUP_GUIDE]]
- [[DEPLOYMENT_PI4]]
- [[SESSION_HANDOVER_2026-08-15]]

---

*จัดทำโดย: Senior Software Engineer — 15 ส.ค. 2569*
