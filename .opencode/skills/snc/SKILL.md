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

## Public website, SEO & content marketing (added 2026-08-20)

The public site lives at **`https://snc.nithep.com`** (Cloudflare Tunnel → `localhost:8000`
on Pi4 `pi4`, `SNC_ROOT=/home/ecs-agent/snc`). Used for **lead generation + monetization**.

### Routes (in `api/server.py`)
- `/` → Landing (`app/landing.html`) · `/dashboard` + `/index.html` → Nurse Dashboard
- `/landing.html`, `/roi.html`, `/snc-vs-imported.html`, `/how-to-phonik.html` → content pages
- Generic **`/@app.get("/{page}.html")`** serves any `app/*.html` safely (realpath-checked, blocks `..`).
  Add a new article page by dropping an `.html` in `app/` + linking it; no new route needed.
- `GET /robots.txt`, `GET /sitemap.xml` (lists `/`, `/landing.html`, `/roi.html`,
  `/snc-vs-imported.html`, `/how-to-phonik.html`, `/dashboard`).
- `POST /api/ai/snc-bot` (SNC-Bot, Gemini free tier, **exempt from X-API-Key**, rate-limited 5/min/IP,
  off-topic guard + fallback + answer cache) · `POST /api/contact` (stores `contacts.jsonl` +
  Telegram notify, rate-limited, exempt from key).

### SEO implemented (On-page)
- **JSON-LD**: `SoftwareApplication` (landing) + `FAQPage` + `LocalBusiness`
  (name `nithep.com`, founder นิเทพ เชิญสวัสดิ์, address `47 ม.6 ต.ป่าสัก อ.เชียงแสน จ.เชียงราย 57150`,
  tel `+66819508950`, `geo` lat 20.2807338 lng 100.0156355, `hasMap`) +
  `Article` JSON-LD on every content page.
- `canonical` + Open Graph + Twitter Card on all pages. `robots.txt` + `sitemap.xml`.
- **LocalBusiness phone is masked** in visible footer (links to SNC-Bot/contact modal) but
  kept in `LocalBusiness` JSON-LD for NAP consistency.
- After any change: register **Google Search Console** + submit `/sitemap.xml`; resubmit on new pages.

### Landing page sections (`app/landing.html`)
hero → stats → features → workflow → arch → history (3-row event table) → tech →
**`#care` (เฮลท์แคร์ผู้สูงอายุ + รีพอร์ตพรีเมี่ยม)** → CTA. Footer has NAP + article links.

### Content articles (drive SEO + leads)
- `roi.html` — คำนวณ ROI (ต้นทุน vs ระบบเดิม, สูตร ROI, กรณีศึกษา 50 เตียง)
- `snc-vs-imported.html` — เปรียบเทียบ SNC vs ระบบนำเข้า (8 มิติ)
- `how-to-phonik.html` — วิธีติดตั้งบน Phonik PBX + **ระบบ SOS CALL** (ดูข้อด้านล่าง)

### Monetization model
Free self-host (Pi 4) + Managed Cloud/SLA + **Premium Service Reporting** (AI Executive
Summary, SLA reports) for elderly-care / long-term care. Lead capture via SNC-Bot + contact form.

### SOS CALL integration (Emergency Call)
Phonik **SOS CALL** (DX-SOS station, NCX-LED lamp, NCX-BUZ buzzer, PI-32G Master Console,
NCX-N-DSP/NCX-B-DSP displays, MDF90/180; capacity 24+2 / 48+2 / 64 for DX-32C/80C/144C,
DX-SERIES V.6.4rl). SNC captures the SMDR `e.{room}` **EC** event → Dashboard blinks red +
times **Response Time** until Clear at Master Console → logged as FHIR/SQLite → feeds Premium
reports. Documented in `doc/wiki/phonik_nurse_call_knowledge.md` §7.1.

### Deploy & caching notes
- `ops/deploy-snc-one-shot.sh` (5-Core). **Add every new `app/*.html` to the `FILES=(...)`
  array** or it won't be uploaded. Drift-check backs up before overwrite.
- Cloudflare may cache HTML → a `no-store, max-age=0` `Cache-Control` middleware was added
  for `text/html` responses so content edits appear immediately (hard-refresh if stale).
- Test pattern: write Python to `C:\Users\Nithep\AppData\Local\Temp\opencode\`, `scp` to
  `pi4:/tmp`, run with `python3`. PowerShell `curl`/`grep` are unreliable — use `bash` or Python.

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