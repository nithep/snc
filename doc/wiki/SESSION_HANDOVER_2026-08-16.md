# SESSION_HANDOVER_2026-08-16 — Cloud Run Deploy + Verify/Monitoring Hardening + Firestore Persistent DB

> จัดทำ: 16 ส.ค. 2569 | แทนที่ handover ก่อนหน้าเฉพาะส่วน Ops/Deploy

---

## 📊 สถานะระบบ ณ สิ้น session

| ระบบ | สถานะ | หมายเหตุ |
|---|---|---|
| **Pi4 (production)** | ✅ ใช้งานได้ | services active, `/health` healthy, verify **PASS=14 FAIL=0** (ยังใช้ SQLite backend) |
| **Cloud Run API + auth** | ✅ ใช้งานได้ | POST ไม่มี key → 401, key ใหม่ → 200 |
| **Cloud Run dashboard** | ✅ ใช้งานได้ | `GET /` → 200 + title `SNC Nurse Station — Live Monitor`, `/static/` → 200 |
| **Cloud Run persistent DB** | ⚠️ โค้ดพร้อม — **รอ deploy ครั้งถัดไป** | `api/storage.py` + `SNC_DB_BACKEND=firestore` — event ไม่หายตอน scale-to-zero (commit `e37d5c4`) |
| **Telegram แจ้งเตือน** | ✅ | notify + agent หา token เจอ (len 46) หลังแก้ env path |

---

## ✅ งานที่เสร็จใน session นี้

### 1. verify-system.sh v2 (หลายโปรเจกต์)
- รองรับ `ops/verify-projects.conf` (1 บรรทัด/โปรเจกต์, 12 ช่องคั่น `|`)
- โหมด: default / `--all` / ระบุชื่อ + env override เดิม
- เช็ค 9 กลุ่ม: 5-Core layout, dir เก่า, cron→ops/, services, health, secrets, proxy, external conn, git sync

### 2. verify-daily.sh + cron 07:00
- ตรวจทุกเช้า + แจ้งเตือน Telegram **เฉพาะเมื่อพบปัญหา** (`VERIFY_ALWAYS=1` ให้ส่งแม้ผ่าน)
- log ที่ `<root>/verify_daily.log` — cron: `0 7 * * * VERIFY_ALWAYS=1 /home/ecs-agent/snc-poc/ops/verify-daily.sh` (ส่งสรุปทุกเช้า + แจ้งเตือนเมื่อ FAIL)

### 3. บั๊กที่เจอ + แก้ (สำคัญ)
| บั๊ก | ผลกระทบ | แก้ |
|---|---|---|
| `ops/*.sh` สูญเสีย exec bit (git เก็บ 100644) | **cron พังเงียบ** (backup 03:00, watchdog ไม่รัน) | `chmod +x` ใน git (20 ไฟล์→100755) + บน Pi4 |
| `notify-telegram.sh` + `snc_telegram_agent.py` หา `.env` ไม่เจอ (ชี้ `ops/` แทน root) | Telegram พังหลัง restructure | แก้ env resolution: ลอง parent (`api/.env`) ก่อน + legacy fallback |
| Docker image ไม่มี dashboard (build context = `api/` เท่านั้น) | Cloud Run `/` → 307 + JSON error | Dockerfile build จาก **repo root** (`COPY api/ .` + `COPY app/ app/`) + cloudbuild.yaml + .dockerignore |
| **Cloud Run cache image ตาม tag `:latest`** | deploy ใหม่แต่ยังใช้ image เก่า (GCR tag ใหม่แล้ว revision ยัง digest เก่า) | deploy ด้วย **digest `@sha256`** (ทั้ง 2 deploy scripts) |
| `static_dir` ชี้ผิดใน container: `../app` จาก `/app/server.py` = `/app` ไม่ใช่ `/app/app` | Cloud Run `/` → 307 + `/static/` 404 ทั้งที่ image มี `app/` จริง | เลือก candidate หลายตำแหน่ง (`../app` สำหรับ repo, `app` สำหรับ container) ตามว่ามี `index.html` ไหม — commit `b906c3b` (ก่อนหน้า `df07273` แค่ abspath ยังไม่พอ) |

### 4. Cloud Run deploy journey (บันทึกเพื่อกันซ้ำ)
1. default compute SA ไม่มี `logging.logWriter` → grant
2. ไม่มี `artifactregistry.repositories.createOnPush` → grant `artifactregistry.admin`
3. Cloud Shell network ไป gcr.io หลุด → docker push retry 3 ครั้งในสคริปต์
4. build context ต้อง root (ไม่งั้นไม่มี app/) → Dockerfile + cloudbuild.yaml
5. deploy ต้อง digest ไม่ใช่ tag → แก้ deploy scripts
6. `static_dir` ต้องรองรับ 2 layout (repo: `api/server.py`+`app/`, container: `/app/server.py`+`/app/app/`) → candidate หลายตำแหน่ง (commit `b906c3b`)
7. Cloud Shell network ไป gcr.io หลุดนาน (connection refused ต่อเนื่องหลายชั่วโมง) → docker push ไม่ใช่ทางเลือกที่พึ่งได้ → fallback `gcloud builds submit` (รันในเครือข่าย Google) + grant IAM ให้ SA ล่วงหน้า (`logging.logWriter` + `artifactregistry.admin`) (commit `11b4f94`)

---

## ⏳ สิ่งค้าง / next steps

_(เคลียร์แล้ว: deploy Cloud Run รอบ Firestore สำเร็จ — ดูส่วน Firestore ด้านล่าง)_

### ☁️ Cloud Monitoring uptime check → Telegram (bridge = service แยก — โค้ดพร้อม รอ deploy)
- **bridge แยก service**: `api/bridge_server.py` + `api/Dockerfile.bridge` + `api/cloudbuild-bridge.yaml` + `ops/deploy_bridge_cloudshell.sh` — alert ส่งถึงแม้ backend หลัก down (ไม่ import backend เลย ไม่มีจุดพังร่วม)
- `ops/setup_cloud_monitoring.sh`: uptime check `/health` 300s + webhook channel → **bridge** + alert policy (fail 120s) + ทดสอบ bridge จริง (idempotent, ดึง token จาก bridge env)
- server.py + deploy scripts ×2: **revert** bridge ออก (main service กลับ lean — bridge code ไม่เคยถูก deploy อยู่แล้ว)
- **รอ (Cloud Shell)**: ① `export TELEGRAM_BOT_TOKEN/CHAT_ID` + `bash ops/deploy_bridge_cloudshell.sh` ② `bash ops/setup_cloud_monitoring.sh`

---

## 🔐 Credentials

- **SNC_API_KEY ใหม่**: `SNC_API_KEY_REDACTED` (ไม่ commit)
  - Pi4: `api/.env` + `pbx/.env` (chmod 600)
  - Cloud Run: env var (ตั้งแล้ว)
  - key เก่า `340e28...` ถูกลบจาก git history (filter-repo) แล้ว
- **Telegram**: token ใน `api/.env` (`TELEGRAM_BOT_TOKEN`/`TELEGRAM_CHAT_ID`) — bot `@snc2569_bot`, chat `7346817215`

---

## 🔄 Firestore persistent DB (เพิ่มใน session)

- **สถานะ: ✅ deploy เรียบร้อย (revision `snc-cloud-backend-00015-4nj`, 16 ส.ค. ~22:48 +07)**
  - `GET /health` → `"db":"firestore"` ✅
  - ทดสอบ write/read: POST trigger → 200, KPI `total_events` 0→1 ✅
  - listener บน Pi4 forward ทั้ง local + cloud จริง (`✅ Event sent to cloud: Room 1101/1100`)
  - event เก่า (17:24) ที่ KPI=0 เป็นเพราะตอนนั้นยังใช้ SQLite ephemeral — ข้อมูลหายตอน scale-to-zero (ยืนยันว่าบั๊กเดิมมีจริง และ Firestore แก้แล้ว)
- **✅ ทดสอบ scale-to-zero จริงผ่าน (23:20 น. 16 ส.ค.)**: idle 16 นาที → cold start 2.33s (T0 warm 0.29s — พิสูจน์ว่า instance หลับจริง) + KPI `total_events=1` **คงอยู่ครบ** — ข้อมูลไม่หายอีกต่อไป (SQLite เก่าจะได้ 0)
- **ปัญหา**: Cloud Run ใช้ SQLite บน disk ชั่วคราว — event หายหมดเมื่อ instance scale-to-zero (~15 นาทีไม่มี traffic)
- **แนวทาง**: เลือก **Firestore** (serverless, มี free tier, ไม่ต้องจัดการ instance — เหมาะกับ PoC มากกว่า Cloud SQL ที่มีค่าใช้จ่ายขั้นต่ำรายเดือน)
- **การออกแบบ** (`api/storage.py`):
  - `SqliteStore` — logic เดิมทั้งหมด (Pi4 ใช้เหมือนเดิม ไม่เปลี่ยนพฤติกรรม)
  - `FirestoreStore` — collection `nurse_call_events` (doc/event) + `room_state` (doc/room ชี้ event ล่าสุด — หลีกเลี่ยง composite index ที่ต้องสร้างมือ)
  - เลือก backend ผ่าน env `SNC_DB_BACKEND` (default `sqlite`) — Pi4 ไม่ต้องติดตั้ง firestore lib (lazy import)
  - KPI คำนวณจาก stream events ในหน่วยความจำ (ปริมาณ PoC ไม่สูง — ง่ายกว่า incremental counter)
- **ไฟล์ที่แก้**: `api/storage.py` (ใหม่), `api/server.py` (ใช้ store แทน sqlite ตรง + แก้บั๊ก `reset_kpi_stats` ที่อ้าง `request` โดยไม่มีพารามิเตอร์), `api/requirements.txt` (+`google-cloud-firestore`), deploy scripts ×2 (setup Firestore + env + verify KPI), `verify-system.sh` (เพิ่ม check KPI ในส่วน Cloud Run), `health` endpoint รายงาน `db` backend
- **ทดสอบ**: SqliteStore functional test ผ่านครบ (save/ack/clear/KPI/reset/no-event) บน Pi4 ด้วย temp DB — **SQLITE STORE: ALL TESTS PASSED**

---

## 📦 Git (session นี้)

- `330c8ad` feat: Cloud Monitoring uptime check → Telegram webhook bridge + setup script (bridge ใน server.py)
- (ถัดไป) feat: bridge แยกเป็น service `snc-alert-bridge` + revert bridge ออกจาก server.py
- `11b4f94` ops: deploy fallback อัตโนมัติไป Cloud Build เมื่อ docker push ล้มเหลว + IAM grant ล่วงหน้า
- `e37d5c4` feat: Cloud Run persistent DB via Firestore (storage abstraction + deploy setup) — **deploy สำเร็จ (revision 00015, `db:firestore`)**
- `b906c3b` fix: static_dir เลือก candidate หลายตำแหน่ง (repo + container layout) — **Cloud Run dashboard จบที่ commit นี้**
- `df07273` fix: static_dir abspath (แก้ครึ่งเดียว — ไม่เพียงพอ)
- `1c35ed1` fix: deploy ด้วย digest ไม่ใช่ tag
- `d4d0993` ops: deploy script pull อัตโนมัติ + fail-fast + ตรวจ dashboard
- `9c8d02e` fix: Dockerfile context=root + app/ ใน image
- `168b5f4`/`f430252` ops: verify multi-project + cron + exec bits + Telegram env
- ทั้งหมด pushed + Pi4 synced (hotfix `gemini_direct_service.py` ถูก preserve)

> ⚠️ Pi4 มี untracked legacy files (root scripts เก่า, backups/, .burnin_*) — reset ไม่ลบ เก็บไว้ได้
