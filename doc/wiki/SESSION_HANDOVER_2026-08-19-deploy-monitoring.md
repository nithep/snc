---
title: "SESSION_HANDOVER_2026-08-19-deploy-monitoring — Deploy Alert Bridge + Cloud Monitoring สมบูรณ์"
type: handover
tags: [status]
---

# SESSION_HANDOVER_2026-08-19-deploy-monitoring — Alert Bridge + Cloud Monitoring ครบ

> จัดทำ: 19 ส.ค. 2569 | ต่อจาก handover 16 ส.ค. (Cloud Run + Firestore) — ปิดค้าง "Cloud Monitoring → Telegram bridge"

---

## 📊 สถานะระบบ ณ สิ้น session

| ระบบ | สถานะ | หมายเหตุ |
|---|---|---|
| **snc-alert-bridge** (Cloud Run) | ✅ live | revision ใหม่, `/health` healthy, deploy ด้วย token จริง |
| **webhook → Telegram** | ✅ `{"status":"sent"}` | แก้ `forbidden` (token base64) + `skipped` (TELEGRAM token placeholder) ได้แล้ว |
| **uptime check** `/health` 300s | ✅ `snc-cloud-run-health` | ตรวจ backend หลัก |
| **notification channel** → bridge | ✅ id `6246499446847685992` | webhook_tokenauth → bridge |
| **alerting policy** (fail 120s) | ✅ มีอยู่แล้ว | `17676417133185946039` |
| **GCP project ID** | ✅ คง `hotel-ecs-nithep` | ตาม ADR 0007 (legacy id) — เพิ่ม comment ใน deploy scripts |
| **เส้นทาง alert** | ✅ สมบูรณ์ | Monitoring → webhook → bridge → Telegram (แยก service — alert ส่งได้แม้ backend หลัก down) |

---

## ✅ งานที่เสร็จใน session นี้

### 1. Deploy `snc-alert-bridge` จริง (commit `837fe18`, `ad7e917` — จาก session ก่อน)
- Service แยกจาก backend หลัก (ไม่ import backend เลย — ไม่มีจุดพังร่วม)
- Deploy ผ่าน `ops/deploy_bridge_cloudshell.sh` (Cloud Build + Secret Manager + digest)
- ตรวจ live: `/health` → `{"status":"healthy","service":"snc-alert-bridge"}`

### 2. Fix bug token monitoring (commit `c4c53ce`)
- **อาการ:** webhook ทดสอบ → `{"error":"forbidden"}`
- **สาเหตุ:** `ops/setup_cloud_monitoring.sh` + `ops/deploy_bridge_cloudshell.sh` อ่าน secret ด้วย `--format='get(payload.data)'` → คืนค่า **base64** แต่ bridge env เก็บ **plaintext** → token ไม่ตรงกัน bridge ปฏิเสธ
- **แก้:** เอา `--format='get(payload.data)'` ออกจากทั้ง 2 ไฟล์ → อ่านเป็น plaintext ตรงกับ bridge env

### 3. Fix Telegram token (แก้ `skipped`)
- **สาเหตุ:** secret `snc-telegram-bot-token` เก็บ placeholder `<TOKEN>` (len 7) → bridge ส่ง Telegram ไม่ได้
- **แก้:** deploy bridge ใหม่ด้วย token จริง (len 46) → `webhook → {"status":"sent"}`

### 4. คง GCP project ID ตาม ADR 0007
- **Decision:** คง `hotel-ecs-nithep` เป็น GCP project id จริง (เป็น legacy id ตาม ADR 0007 / NOMENCLATURE)
- **ทำ:** เพิ่ม comment อธิบายใน 3 deploy scripts (`deploy_cloudrun`, `deploy_backend`, `deploy_bridge`) — ห้ามเปลี่ยน default จนกว่าจะ migrate resource
- หมายเหตุ: service names เป็น `snc-*` แล้ว (backend + bridge) — GCP project id เท่านั้นที่คง legacy ไว้

---

## 🔧 ไฟล์ที่แก้ใน commit `c4c53ce`

| ไฟล์ | การเปลี่ยนแปลง |
|---|---|
| `ops/setup_cloud_monitoring.sh` | อ่าน secret เป็น plaintext (ลบ `--format='get(payload.data)'`) |
| `ops/deploy_bridge_cloudshell.sh` | อ่าน secret เป็น plaintext + comment project id legacy |
| `ops/deploy_cloudrun_cloudshell.sh` | comment project id legacy |
| `ops/deploy_backend_cloudshell.sh` | comment project id legacy |

---

## ⚠️ สิ่งที่ต้องทำต่อ / ข้อควรระวัง

### 1. 🔒 Rotate TELEGRAM_BOT_TOKEN (สำคัญ — หลุดในแชท)
- token `8857966053:...` ถูกแสดงในแชท/ประวัติระหว่าง debug
- ดูขั้นตอน: `doc/wiki/SNC_TELEGRAM_ROTATION_GUIDE.md`
- หลัง rotate → ต้อง deploy bridge ใหม่ (update secret) แล้วเช็ค `sent` อีกครั้ง

### 2. ลบ channel เก่าที่ไม่ใช้ (กันความรก/สับสน) — ยังไม่ได้ลบ
- เก็บเฉพาะล่าสุด `6246499446847685992`
- ตัวเก่าที่สร้างซ้ำระหว่าง debug: `12417720015775998846`, `276357567739982957`, `3584692914350070116`, `9802072087643608996`
- ลบผ่าน Monitoring console หรือ API (ระวัง: ถ้าผูกกับ alerting policy ต้อง unbind ก่อน)

### 3. ตรวจ Cloudflare domain `snc.nithep.com` → Cloud Run (ยังค้าง)
- ยังค้างจาก handover 19 ส.ค. (main) — `SNC_ALLOWED_ORIGINS` ควรมี `snc.nithep.com`
- **สถานะ ณ 19 ส.ค. (ต่อ):** env จริงบน Cloud Run backend **ยังไม่มี `SNC_ALLOWED_ORIGINS`** (มีแค่ `SNC_API_KEY` + `SNC_DB_BACKEND`)
  - ตรวจ: `gcloud run services describe snc-cloud-backend --region=asia-southeast1 --format='yaml(spec.template.spec.containers[0].env)'`
  - **ยังไม่ได้ตั้งค่า** — คำสั่ง `update` ยังไม่สำเร็จ (ติด shell quoting ของ comma/URL)
  - วิธีที่เตรียมไว้ (หนี comma โดยใช้ JSON file, merge ครบ 3 env):
    ```bash
    printf '{"SNC_API_KEY":"SNC_API_KEY_REDACTED","SNC_DB_BACKEND":"firestore","SNC_ALLOWED_ORIGINS":"https://snc.nithep.com,https://hotel.nithep.com,https://snc-cloud-backend-59781590359.asia-southeast1.run.app"}' > /tmp/snc_env.json
    gcloud run services update snc-cloud-backend --region=asia-southeast1 --project=hotel-ecs-nithep --env-vars-file /tmp/snc_env.json --remove-env-vars TEST_MARKER
    ```
  - ⚠️ **หมายเหตุ:** ระหว่าง debug ได้เพิ่ม env `TEST_MARKER=ok` ไว้บน Cloud Run (revision 00016) — **ต้องลบออก** (ยังอยู่) พร้อมตั้ง `SNC_ALLOWED_ORIGINS` จริง

---

## 🔍 สถานะ commit (branch `main`, origin synced ✅)
- `c4c53ce` fix(monitoring): plaintext token + comment project id legacy
- (ก่อนหน้า) `837fe18` / `ad7e917` bridge แยก service + fix container start

---

## 📌 สรุปเส้นทาง alert (ใช้งานจริงแล้ว)
```
Cloud Monitoring uptime check (/health 300s)
   └─ fail 120s → alerting policy
        └─ notification channel (webhook_tokenauth)
             └─ snc-alert-bridge (service แยก — อยู่รอดแม้ backend หลัก down)
                  └─ Telegram bot (@snc2569_bot)
```

---

*จัดทำโดย: Senior Software Engineer — 19 ส.ค. 2569*