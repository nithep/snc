---
title: "github-copilot-snc"
type: raw
tags: [knowledge]
---

สรุปสั้นๆ — โครงงาน nithep/snc มีโครงสร้างชัดเจนและส่วนประกอบหลักครบ (API, PBX listener, Frontend, docs, ops) และสามารถรันเป็น PoC ได้ทันที แต่พบปัญหาทางเทคนิคและความปลอดภัยที่ต้องแก้ก่อนนำไปรันในสภาพแวดล้อม production (รายการข้อบกพร่องสำคัญและคำแนะนำอยู่ด้านล่าง)

ผมได้ตรวจอ่าน README, ไฟล์หลักของแต่ละคอร์ (api/server.py, api/services/*, pbx/snc_pbx_listener.py, pbx/test_smdr_parser.py, app/index.html) และรายการไฟล์ต้นทางเพื่อตรวจความสมบูรณ์และจุดเสี่ยง

## What this is
ระบบ Smart Nurse Call (SNC) — โซลูชัน PoC ที่จับ SMDR จากตู้ Phonik PBX ผ่าน Telnet แล้วแปลงเป็น FHIR-like JSON → ส่งไปยัง FastAPI backend ที่เก็บลง SQLite และกระจายเรียลไทม์ไปยัง Nurse Dashboard (WebSocket). เหมาะสำหรับทดสอบใช้งานบน Raspberry Pi 4 และผสานกับ UI บนเบราว์เซอร์เพื่อการตอบสนองเหตุฉุกเฉินในโรงพยาบาล

### Stack
- Language(s): Python (หลัก), HTML/JS (frontend), Shell scripts (ops)
- Framework / runtime: FastAPI (backend) + uvicorn; asyncio / aiohttp in PBX listener; static single-file HTML/JS frontend
- Notable libraries: aiohttp (PBX → HTTP), fastapi, pydantic, sqlite3 (builtin). (Gemini service present for AI summary integration.)

## How it's organized
Annotated top-level tree (สำคัญ):
```
api/                FastAPI server, DB schema, WebSocket, ai/gemini integration, Dockerfile, cloudbuild
  ├─ server.py      HTTP + WebSocket endpoints, DB init, SLA logic (main backend)
  ├─ requirements.txt
  └─ services/      gemini_direct_service.py (AI integration)
app/                Self-contained Nurse Dashboard (index.html, dashboard-status.html)
pbx/                Phonik PBX Telnet SMDR listener, proxy (snc_pbx_listener.py), parser tests
doc/                Documentation / runbooks / blueprint (OKF)
ops/                DevOps scripts (deploy, quick_start.sh, backup, burn-in monitor)
.gitignore, README.md, MIGRATION_RUNBOOK.md, LICENSE, AGENTS.md
```

How it fits together:
- pbx/snc_pbx_listener.py: เชื่อม Telnet → subscribe SMDR/RDSS → แปลงเป็น event payload (FHIR-like) → POST ไปที่ backend /api/events/trigger
- api/server.py: รับ trigger, บันทึกลง SQLite (WAL), คำนวณ SLA, ให้ REST API (events, analytics, demo), และ WebSocket /ws/nurse-station เพื่อ broadcast ไปยัง frontend
- app/index.html: single-page dashboard (i18n ไทย/อังกฤษ) เชื่อม WebSocket + poll /api/events และมีปุ่ม Ack / Clear ที่เรียก API เขียน

## Quick findings — ปัญหาสำคัญ (prioritized)
1. Bug — admin reset-kpi ฟังก์ชันใช้ตัวแปร request แต่ไม่ได้ประกาศรับพารามิเตอร์
   - ใน api/server.py ฟังก์ชัน reset_kpi_stats() เรียก request.headers แต่ลายเซ็นเป็น def reset_kpi_stats(): → จะทำให้เกิด NameError / 500 เมื่อเรียก
   - แก้: เปลี่ยนเป็น def reset_kpi_stats(request: Request): หรือใช้ Depends เพื่อรับ Request

2. Blocking I/O ใน async context (performance / scalability)
   - server.py เรียก sqlite3 แบบ synchronous ภายใน FastAPI async endpoints (เช่น get_recent_events, ack/clear, kpi) — sqlite3 เป็นบล็อกคอลล์ อาจบล็อก event loop ภายใต้โหลด
   - แก้แนะนำ: ย้ายการเข้าถึง SQLite ไปใช้ aiosqlite หรือรันคำสั่ง DB ใน threadpool (starlette.run_in_threadpool / asyncio.to_thread) เพื่อไม่ให้บล็อก loop

3. DB path & permissions / deployment concern
   - DB_PATH = "nurse_call_events.db" เป็น path คงที่ใน working dir — ควรทำให้ configurable ผ่าน env var (e.g., SNC_DB_PATH) และกำหนดโฟลเดอร์มาตรฐาน (/var/lib/snc) พร้อมสิทธิ์ที่เหมาะสม
   - แนะนำให้ ops สร้าง systemd service ที่ตั้ง WorkingDirectory, user และ umask ที่เหมาะสม

4. FHIR compliance / payload field names
   - โครงสร้าง payload เป็น "FHIR-like" แต่มีฟิลด์ที่ไม่ตรงมาตรฐาน เช่น occurrenceDateTimeField (ชื่อฟิลด์ไม่ใช่ occurrenceDateTime) และ extension รูปแบบอาจไม่สมบูรณ์หากต้องส่งไปยัง GCP Healthcare API ในอนาคต
   - แก้: ปรับให้สอดคล้อง HL7 FHIR (เช่น ใช้ occurrenceDateTime) และเพิ่ม unit tests/JSON schema validation

5. Robustness of save_event_to_db
   - save_event_to_db() assumes extension และ keys (extension["roomId"], payload[0]["contentString"]) มีอยู่จริง — อาจเกิด KeyError เมื่อ payload ต่างรูปแบบ
   - แก้: ตรวจสอบ/validate ก่อนบันทึก และบันทึก raw line/diagnostic เมื่อ payload ขาดหาย

6. SQL / query issues and missing limits
   - ใน server.py พบว่าบาง SELECT ในไฟล์ที่ดาวน์โหลดมีการตัด/ellipsis (น่าจะเป็นผลจากการแสดงไฟล์) — แต่โปรดตรวจสอบ SELECT ORDER BY timestamp และ LIMIT เพื่อให้ frontend ไม่ดึงข้อมูลเกินจำเป็น
   - เพิ่ม pagination/limit และ index บน timestamp, room_id เพื่อประสิทธิภาพ

7. Security: transport & secrets
   - PBX listener และ frontend → backend ใช้ HTTP/ws (plain) ตามค่าเริ่มต้น ถ้าใช้งานข้ามเครือข่าย ควรบังคับ HTTPS/WSS และป้องกันการดักฟัง
   - .env ที่เก็บ PBX_PASS / SNC_API_KEY ต้องถูกป้องกัน (ไฟล์ .gitignore ควรระบุแบบเจาะจงตามกฎของโปรเจกต์ — ห้ามใช้ pattern กว้างเช่น *key*)
   - แนะนำ rotation guide (doc/wiki/SNC_API_KEY_ROTATION_GUIDE.md) ตามกฎโครงการ (หากยังไม่มี ให้สร้าง)

8. Blocking broadcast to many WebSocket clients
   - ConnectionManager.broadcast ส่งข้อความแบบรอทีละ client อาจช้าภายใต้จำนวน client มาก ๆ — ควรพิจารณาส่งแบบ concurrent หรือ catch per-client exceptions มี retry/backoff

9. Tests & CI
   - มี test_smdr_parser.py (ดี) และ integration_test.py แต่ควรเพิ่ม CI (unit tests, lint, docker build) ถ้ายังไม่มี workflow
   - เพิ่ม test coverage สำหรับ DB migrations, ack/clear flows, และ edge cases ของ parser

## Recommended immediate fixes (actionable)
- Fix reset_kpi_stats signature to accept Request (or use dependency) — high priority
- Replace blocking sqlite3 calls in async handlers with aiosqlite or run_in_threadpool — medium-high priority
- Harden save_event_to_db with validation (try/except, schema checks)
- Make DB path configurable via env var; document backup/restore and WAL checkpointing in ops
- Align FHIR fields to HL7 FHIR standard; add JSON schema and validation step before DB write
- Enforce TLS for backend (or document requirement to run behind reverse proxy with TLS)
- Review .gitignore and ensure sensitive files are excluded by specific patterns, and add key rotation doc if missing
- Add systemd service unit in ops (example) and ensure single-user for running services on Pi

## How to run it (shortest path)
From a fresh clone on a Raspberry Pi (example steps):
1. API
   ```
   cd api
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   uvicorn server:app --host 0.0.0.0 --port 8000
   ```
   - Or build Docker image using api/Dockerfile and run container.

2. PBX listener (separate process on same Pi or another host):
   ```
   cd pbx
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   python snc_pbx_listener.py
   ```
   - Configure pbx/.env with PBX_IP, PBX_PASS, BACKEND_API_URL, SNC_API_KEY

3. Frontend:
   - Option A (served by backend): ensure api/ mounts ../app and open http://<pi-ip>:8000/
   - Option B (static): open app/index.html in browser (configure backend host in Settings)

Health check:
   ```
   curl http://localhost:8000/health
   ```

Quick Start (from README):
   ```
   ./ops/quick_start.sh   # if present and executable — verify contents before running
   curl -s http://localhost:8000/health
   ```

## Low-risk improvements & hardening
- Add schema migrations (alembic or simple migrations scripts) instead of runtime ALTER TABLE checks
- Add request/response logging with configurable level and redact secrets
- Add rate limiting per API key and per IP (middleware exists but review logic under proxies/load balancers)
- Improve WebSocket scalability (use broadcast tasks or channel layers if scaling horizontally)
- Add automated backup & WAL checkpoint ops (ops/ already mentions scripts — review and harden)

## Try asking (follow-up questions)
1. ต้องการให้ผมแก้โค้ดตัวอย่าง (PR) สำหรับปัญหา reset_kpi_stats และเปลี่ยนการเข้าถึง SQLite เป็นแนวทาง non-blocking (aiosqlite / run_in_threadpool) ให้หรือไม่ — ถ้าใช่ ผมจะเสนอ diff พร้อมคำอธิบาย
2. คุณต้องการยืนยันรูปแบบ FHIR แบบเข้มงวด (strict HL7 FHIR v4) สำหรับ payload หรือพอใช้ FHIR-like แบบปัจจุบันก่อน เพื่อเราจะตัดสินใจว่าจะสร้าง JSON schema validator อย่างไร
3. เป้าการ deploy เป็นแบบ “รันบน Pi โดยตรง (systemd)” หรือ “containerized (Docker / Cloud Run)” — ผมจะแนะนำ service unit / Dockerfile และการตั้งค่า TLS ตามที่คุณต้องการ

หากต้องการ ผมสามารถ:
- สร้าง PR ที่แก้ไข bug สำคัญ (reset_kpi_stats) และตัวอย่างการปรับ sqlite ให้ไม่บล็อก event loop
- เพิ่มตัวอย่าง systemd unit และตัวอย่างการตั้งค่ env ที่ปลอดภัย
แจ้งผมว่าต้องการให้ผมเริ่มทำส่วนไหนก่อน (แก้โค้ด PR / เขียน runbook ops / เขียน JSON schema FHIR)