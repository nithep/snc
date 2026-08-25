---
title: "SESSION_HANDOVER_2026-08-26 — Firestore เก็บกวาดข้อมูลจริง + ย้าย GEMINI_API_KEY ขึ้น Secret Manager + ตรวจ deploy"
type: handover
tags: [status, firestore, secret-manager, cloud-run, ai, cleanup]
---

# SESSION_HANDOVER_2026-08-26 — Firestore Cleanup + Gemini Secret Manager + Deploy Audit

> จัดทำ: 26 ส.ค. 2569 | ต่อจาก [[SESSION_HANDOVER_2026-08-25]]
> ครอบคลุม: เก็บกวาดข้อมูลทดสอบใน Firestore, ย้าย `GEMINI_API_KEY` จาก plaintext env ขึ้น Secret Manager, ตรวจสถานะ deployment ปัจจุบัน

## งานที่ทำ

### 1. เก็บกวาด Firestore — ลบข้อมูลทดสอบ/ค้าง (Real/Demo ไม่ปนกัน)

- **ก่อนทำ:** backup ข้อมูลทั้ง 2 collection ลง `.freebuff/firestore_backup_20260826_025540.json` (gitignored) ตามกฎ "backup ก่อนลบ"
- **พบทดสอบจริง:** `nurse_call_events` เหลือ **1 doc** — event smoke-test ห้อง 0999 (`source='real'`) ที่พ่นมาจาก smoke test ของ deploy → **ปนเปื้อน real KPI** (`total_events=1`)
- **พบ room_state ค้าง (orphan):** 3 ห้อง (1100/1101/1105) ชี้ไปหา event ที่ลบ/หายไปแล้ว (ข้อมูลห้องเหล่านี้หายไปในincident 19–24 ส.ค. ตาม [[SNC_CLOUDRUN_DATALOSS_INCIDENT_2026-08-25]] — เหลือแต่ room_state เปล่า) + room_state ของ 0999
- **ลบแล้ว:** `nurse_call_events/snc-event-0999-smoke-...` + `room_state/{0999,1100,1101,1105}`
- **ผลลัพธ์:** Firestore ว่างเปล่า (0 doc ทั้ง 2 collection); `/api/analytics/kpi` → `total_events=0` ✅
- **ข้อควรรู้:** data จริงจากตู้ (pi ฝั่ง SQLite) ไม่ได้ถูกแตะ — การเก็บกวาดนี้ทำเฉพาะ Firestore (Cloud) ซึ่งเป็น map ของข้อมูลต้นทางผ่าน outbox อีกที

### 2. ย้าย GEMINI_API_KEY ขึ้น Secret Manager (เลิก plaintext env on Cloud Run)

- **ก่อน:** secret `snc-gemini-api-key` มีอยู่แล้วแต่ **0 versions** (เปล่า ไม่ถูกใช้งาน); backend รัน `GEMINI_API_KEY` เป็น **plaintext env** บน service (ขัด ADR 0005)
- **ทำ:**
  1. ดึงค่า key ปัจจุบันจาก revision env (ไม่พึ่ง source อื่น) → เพิ่มเป็น **version 1** ของ `snc-gemini-api-key`
  2. grant `roles/secretmanager.secretAccessor` ให้ Cloud Run SA `59781590359-compute@...`
  3. redeploy ด้วย image digest เดิม `sha256:748940e0...` + `--set-secrets GEMINI_API_KEY=snc-gemini-api-key:latest` + `--remove-env-vars GEMINI_API_KEY`
- **ผล:** revision ใหม่ `snc-cloud-backend-00026-sbm` — `GEMINI_API_KEY` กลายเป็น `valueFrom.secretKeyRef` (mount จาก secret) ไม่ใช่ plaintext อีกต่อไป
- **verify:** `/health` healthy + db=firestore, POST ไม่มี key → 401, **`/api/ai/snc-bot` ตอบจริง** (อ้าง SLA 30s — ไม่ใช่ fallback "ไม่พบ API Key") → กุญแจจาก Secret Manager ทำงาน ✅

### 3. ตรวจสถานะ deployment ปัจจุบัน

| ระบบ | สถานะ (ตรวจแล้ว 26 ส.ค.) |
|---|---|
| Cloud Run `snc-cloud-backend` | rev **`00026-sbm`** serving 100% (ต่อจาก `00025-jvz`) |
| `/health` | 200 healthy — `db:firestore` |
| Auth | POST ไม่มี `X-API-Key` → **401** (fail-closed) |
| Firestore | `nurse_call_events` 0 doc, `room_state` 0 doc (สะอาด) |
| AI (SNC-Bot) | ตอบผ่าน — ใช้ key จาก Secret Manager (OpenRouter `sk-or-…`) |

## การตัดสินใจ/ข้อสังเกต

1. ~~SNC_API_KEY/TELEGRAM_BOT_TOKEN ยังเป็น plaintext env~~ — **แก้แล้ว**: ขึ้น Secret Manager + mount ทั้งคู่ (rev `00027-whf`); เหลือ **การ rotate จริง** (ค่า token ยังเป็นตัวเดิมที่อาจเคย leak) — ดู "สิ่งค้างถัดไป"
3. data จริง (1100/1101/1105) ที่เคยเข้า Firestore หายไปก่อนหน้าแล้วจาก incident — การเก็บกวาดครั้งนี้จึงไม่สูญข้อมูลของผู้ป่วยจริงเพิ่ม (มี backup ครบ)
4. key ถูกดึงจาก revision env เข้า temp file แล้วลบ — ไม่มี plaintext key หลุดเข้ากระแส git

## ไฟล์ที่แก้ (Doc only)

- `doc/wiki/GEMINI_API_KEY_ROTATION_GUIDE.md` — ระบุว่า Secret Manager บน Cloud Run **บังคับใช้แล้ว (26 ส.ค.)** พร้อมวิธี deploy ที่ใช้จริง
- `doc/wiki/SNC_API_KEY_ROTATION_GUIDE.md` — ตารางตำแหน่ง Cloud Run → Secret Manager mount (secret `snc-api-key` สร้างจริงแล้ว)

## ไฟล์ชั่วคราว/backup (gitignored ใน `.freebuff/`)

- `firestore_backup_20260826_025540.json` — backup Firestore ก่อนลบ (เก็บ 30 วันแล้วลบได้)
- `test_ai_secret.py` / `verify_secrets.py` / `check_rev_env.py` / `extract_env.py` — ชั่วคราวสำหรับ verify

## Deploy History 26 ส.ค. 2569 (Cloud Run `snc-cloud-backend`)

| Revision | การเปลี่ยนแปลง |
|---|---|
| `00026-sbm` | ย้าย `GEMINI_API_KEY` ขึ้น Secret Manager (mount) + ลบ plaintext |
| `00027-whf` | ย้าย `SNC_API_KEY` + `TELEGRAM_BOT_TOKEN` ขึ้น Secret Manager (mount) + ลบ plaintext |
| `00028-8f4` | ปุ่ม 🧪 DEMO บน dashboard (room 0400, `source=demo` ไม่นับ KPI) + rebuild image ใหม่ |

**Env ที่เหลือเป็น plaintext (ไม่ใช่ secret):** `SNC_DB_BACKEND=firestore`, `TELEGRAM_CHAT_ID`

## เทียบเพิ่มเติม (เติมใน session จากคำขอต่อเนื่อง) — ย้าย SNC_API_KEY + TELEGRAM_BOT_TOKEN ขึ้น Secret Manager

- **ทำ:** สร้าง secret `snc-api-key` (value = ค่าปัจจุบันที่รันอยู่, กัน break parity กับ Pi) version 1 + grant accessor; mount `TELEGRAM_BOT_TOKEN=snc-telegram-bot-token:latest` (ค่าตรงกัน secret version 8, ไม่เพิ่ม version ซ้ำ) + grant/ยืนยัน accessor
- **redeploy:** rev `00027-whf` — `--set-secrets "GEMINI_API_KEY,SNC_API_KEY,TELEGRAM_BOT_TOKEN"` + `--remove-env-vars SNC_API_KEY,TELEGRAM_BOT_TOKEN` + `--update-env-vars SNC_DB_BACKEND,TELEGRAM_CHAT_ID`
- **ผล:** ทุก secret ผ่าน Secret Manager แล้ว — เหลือ **plaintext env เฉพาะที่ไม่ใช่ secret**: `SNC_DB_BACKEND`, `TELEGRAM_CHAT_ID`
- **verify ครบ (rev `00027-whf`):** `/health` healthy db=firestore · POST ไม่มี key → 401 · KPI ด้วย SNC_API_KEY (จาก secret) → 200 · SNC-Bot (ไทย) → 200 live_key=True
- **update doc:** `SNC_API_KEY_ROTATION_GUIDE.md` ตารางตำแหน่ง → Secret Manager mount

## สิ่งค้าง / ข้อควรรู้ถัดไป

1. **rotate `TELEGRAM_BOT_TOKEN` แท้ (สร้าง token ใหม่ที่ @BotFather)** — token ปัจจุบัน (secret version 8 และรันบน Cloud) ยังเป็นตัวที่เคย flag ว่า leak; การย้ายขึ้น Secret Manager แค่เอาออกจาก plaintext env ยังไม่ได้แก้อการถูกเผยแพร่ — หลังได้ token ใหม่: `gcloud secrets versions add snc-telegram-bot-token --data-file=-` (เพิ่ม version ใหม่ แล้ว mount `:latest` เอง) + revoke เก่าที่ @BotFather
2. **rotate `SNC_API_KEY` แท้** — ต้องอัปเดต Pi หลายจุดพร้อมกัน (`api/.env` + `pbx/.env` + Cloud Secret) เพื่อคง parity; ผมเข้าถึง Pi ไม่ได้ → ข้ามได้ แต่ควรทำเมื่อ access Pi + ใช้ `SNC_API_KEY_ROTATION_GUIDE.md` Step 1–7
3. หลัง deploy ทุกครั้ง: ตรวจ `/health` → `db:firestore` + POST ไม่มี key → 401 + `/api/ai/snc-bot` ยังตอบ (กัน regression หลัง mount secret)
4. secret ที่ mount แล้วชี้ `:latest` → rotate แค่ `gcloud secrets versions add` + เปลี่ยน `:latest` ไม่ต้อง redeploy ใหม่ (deploy เฉพาะตอนเปลี่ยน mount/ชื่อ secret) — `SNC_API_KEY`/`GEMINI_API_KEY`/`TELEGRAM_BOT_TOKEN` ตามนี้