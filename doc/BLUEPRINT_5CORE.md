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
│   ├── *_parser.py         # Protocol parsers
│   ├── tests/              # Parser tests
│   ├── requirements.txt    # Listener-specific deps
│   ├── .env                # 🔐 Vault: Listener credentials (gitignored)
│   └── *.db                # Edge cache (if needed)
│
├── ops/                    # 🔴 Core 4: DevOps / Operations
│   ├── deploy*.sh          # Deployment scripts
│   ├── backup*.sh          # Backup & restore
│   ├── monitor*.sh         # Health monitoring
│   ├── setup*.sh           # Initial setup / provisioning
│   ├── *.service           # systemd unit files
│   └── cron/               # Scheduled tasks
│
└── doc/                    # 🟣 Core 5: Documentation
    ├── ARCHITECTURE.md     # System architecture
    ├── DEPLOYMENT.md       # Deployment guide
    ├── API.md              # API reference
    ├── USER_GUIDE.md       # End-user manual
    └── wiki/               # Knowledge base / ADRs
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
  api/ pi4:/home/ecs-agent/snc-poc/api/

# Deploy listener
rsync -avz --exclude='.env' \
  pbx/ pi4:/home/ecs-agent/snc-poc/pbx/

# Deploy dashboard
rsync -avz app/ pi4:/home/ecs-agent/snc-poc/app/

# Restart services
ssh pi4 "sudo systemctl restart snc-backend snc-pbx-listener"
```

### Docker Deploy (Cloud Run)

```bash
# Build & push
docker build -t gcr.io/PROJECT/snc-api ./api
docker push gcr.io/PROJECT/snc-api

# Deploy with env vars
gcloud run deploy snc-api \
  --image gcr.io/PROJECT/snc-api \
  --set-env-vars "SNC_API_KEY=$KEY" \
  --region asia-southeast1
```

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

- [SNC_API_KEY_SETUP_GUIDE.md](wiki/SNC_API_KEY_SETUP_GUIDE.md)
- [DEPLOYMENT_PI4.md](DEPLOYMENT_PI4.md)
- [SESSION_HANDOVER_2026-08-15.md](wiki/SESSION_HANDOVER_2026-08-15.md)

---

*จัดทำโดย: Senior Software Engineer — 15 ส.ค. 2569*
