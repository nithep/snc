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

1. **SNC_API_KEY ยังเป็น plaintext env บน Cloud Run** — secret `snc-api-key` **ยังไม่ถูกสร้าง** (มีแค่ชื่อใน doc/terraform แต่ไม่มีการ implement จริง) — นอกขอบงานนี้แต่ควรทำตามลำดับถัดไป (ดู "สิ่งค้าง")
2. `TELEGRAM_BOT_TOKEN` ยังเป็น plaintext env + **เป็น token ที่เคยถูก flag ว่า leak (handover 19 ส.ค.)** — ควร rotate + ย้ายขึ้น secret `snc-telegram-bot-token` (secret มีอยู่แล้ว เหลือ mount + rotate)
3. data จริง (1100/1101/1105) ที่เคยเข้า Firestore หายไปก่อนหน้าแล้วจาก incident — การเก็บกวาดครั้งนี้จึงไม่สูญข้อมูลของผู้ป่วยจริงเพิ่ม (มี backup ครบ)
4. key ถูกดึงจาก revision env เข้า temp file แล้วลบ — ไม่มี plaintext key หลุดเข้ากระแส git

## ไฟล์ที่แก้ (Doc only)

- `doc/wiki/GEMINI_API_KEY_ROTATION_GUIDE.md` — ระบุว่า Secret Manager บน Cloud Run **บังคับใช้แล้ว (26 ส.ค.)** พร้อมวิธี deploy ที่ใช้จริง

## ไฟล์ชั่วคราว/backup (gitignored ใน `.freebuff/`)

- `firestore_backup_20260826_025540.json` — backup Firestore ก่อนลบ (เก็บ 30 วันแล้วลบได้)
- `test_ai_secret.py` / `check_rev_env.py` — ชั่วคราวสำหรับ verify

## สิ่งค้าง / ข้อควรรู้ถัดไป

1. **สร้าง + mount secret `snc-api-key`** (ตอนนี้ secret ไม่มีอยู่จริง ถึง doc จะอ้าง) แล้ว `--remove-env-vars SNC_API_KEY` — พร้อม update `SNC_API_KEY_ROTATION_GUIDE.md`
2. **rotate + ย้าย `TELEGRAM_BOT_TOKEN` ขึ้น secret** (token เคย leak ตาม handover 19 ส.ค.) + ลบ plaintext env
3. หลัง deploy ทุกครั้ง: ตรวจ `/health` → `db:firestore` + POST ไม่มี key → 401 + `/api/ai/snc-bot` ยังตอบ (กัน regression หลัง mount secret)
4. `snc-gemini-api-key` ตอนนี้ชี้ `:latest` → rotate แค่ `gcloud secrets versions add` + ไม่ต้อง redeploy ใหม่ (version ใหม่จะถูก mount) — อัปเดต rotation guide ตามจริงแล้ว