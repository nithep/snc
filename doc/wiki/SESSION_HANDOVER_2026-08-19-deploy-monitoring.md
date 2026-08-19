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
- ✅ สคริปต์หมุนเสร็จ (`ops/rotate_telegram_token.sh`, commit `350758d`) — auto-detect ssh/gcloud, สร้าง secret version ใหม่ + redeploy bridge + อัปเดต `api/.env` บน Pi4 + ทดสอบส่งจริง
- token `8857966053:...` (len 46) ใช้อยู่ใน (a) Secret Manager `snc-telegram-bot-token:latest` → bind `snc-alert-bridge` (b) `api/.env` บน Pi4 — ทั้งหมดถูกแสดงในแชท/ประวัติ debug → **ต้องหมุน (revoke ที่ @BotFather)**
- **ขั้นตอน (2 สภาพแวดล้อม — เครื่องเดียนมีทั้ง ssh+gccoud ไม่คล่ะ):**
  ```bash
  # (1) เครื่อง dev ที่มี `ssh pi4` — หมุน Pi4 เท่านั้น:
  NEW_TELEGRAM_BOT_TOKEN="<token ใหม่จาก @BotFather>" bash ops/rotate_telegram_token.sh --skip-cloud

  # (2) Cloud Shell (มี `gcloud`) — หมุน Secret Manager + redeploy bridge:
  NEW_TELEGRAM_BOT_TOKEN="<token ใหม่เดียวกัน>" bash ops/rotate_telegram_token.sh --skip-pi
  ```
  หลังทำ → ตรวจ `webhook bridge → {"status":"sent"}` + `notify-telegram.sh` บน Pi ส่งจริง
- ⚠️ **อย่าลืม Revoke token เก่า** ที่ @BotFather (`/mybots` → @snc2569_bot → API Token → Revoke) ก่อน/หลัง deploy — token เก่าจะไร้ค่าทันที

### 2. ลบ channel เก่าที่ไม่ใช้ (กันความรก/สับสน) — ยังไม่ได้ลบ
- เก็บเฉพาะล่าสุด `6246499446847685992` (ACTIVE — อยู่ใน alerting policy)
- ตัวเก่าที่สร้างซ้ำระหว่าง debug: `12417720015775998846`, `276357567739982957`, `3584692914350070116`, `9802072087643608996`
- **วิธีลบ (Cloud Shell) — ใช้สคริปต์ที่พร้อมแล้ว:**
  ```bash
  # 1) ดูก่อน (ไม่ลบจริง) — ควรได้ 4 รายการจาก STALE_CHANNEL_IDS
  DRY_RUN=1 bash ops/cleanup_cloud_monitoring.sh

  # 2) ลบจริง (มี guard ป้องกันลบ ACTIVE channel + เตือนถ้า channel ยังผูกกับ policy)
  bash ops/cleanup_cloud_monitoring.sh
  ```
  - ใช้ API ตรง (`curl` → `monitoring.googleapis.com`) — ระวัง: ถ้า channel ยังถูก alerting policy ผูกอยู่ API คืน `400` → ต้อง `unbind` ที่ policy ก่อน (ดู terraform `import` ข้างบน)
  - active channel `6246499446847685992` อยู่ใน `alertPolicies[0].notificationChannels` → อย่าลบก่อนเปลี่ยน policy

### 3. ตั้ง `SNC_ALLOWED_ORIGINS` + ลบ `TEST_MARKER=ok` บน Cloud Run backend
- **สถานะ ณ 19 ส.ค. (ต่อ):** env จริงบน `snc-cloud-backend` **ยังไม่มี `SNC_ALLOWED_ORIGINS`** (มีแค่ `SNC_API_KEY` plaintext + `SNC_DB_BACKEND`) และมี `TEST_MARKER=ok` ค้างอยู่ (revision 00016)
- **สาเหตุเดิม:** คำสั่ง `--set-env-vars` ตรงหนี `,` ของ comma-separated origins ไม่ได้ → deploy พัง
- **วิธีแก้ (แนะนำ) — redeploy ด้วยสคริปต์ที่แก้แล้ว (commit `ea397f7`):**
  ```bash
  # มี SNC_API_KEY ตรงกับ api/.env บน Pi4 (เดียวกับที่ใช้กับ Firestore)
  export SNC_API_KEY="<key ตรงกับ api/.env บน Pi4>"
  bash ops/deploy_backend_cloudshell.sh
  ```
  สคริปต์นี้ทำครบ:
  - build image ผ่าน Cloud Build (multi-stage + nonroot + HEALTHCHECK)
  - เก็บ `SNC_API_KEY` ลง Secret Manager `snc-api-key` (ไม่ใช่ plaintext env — ตาม ADR 0005) แล้ว mount เป็น secret → **ลบ `SNC_API_KEY` plaintext เก่าอัตโดมัติ**
  - deploy พร้อม `^@^` delimiter (หนี comma ของ origins) ตั้ง `SNC_DB_BACKEND` + **`SNC_ALLOWED_ORIGINS`** ใหม่
  - `--set-env-vars` เป็น *full replace* → **`TEST_MARKER=ok` ถูกลบออกอัตโดมัติ** (ไม่อยู่ใน env ใหม่)
  - verify `/health` (db=firestore) + auth fail-closed (POST ไม่มี key → 401)
- ⚠️ **อย่าใช้คำสั่ง manual ในหมายเหตุเดิม** (มี `SNC_API_KEY` ใน plaintext JSON) — ใช้สคริปต์แทนเพื่อความปลอดภัย + ตรวจสอบอัตโนมัติ
- ตรวจสอบหลัง deploy:
  ```bash
  gcloud run services describe snc-cloud-backend --region=asia-southeast1 \
    --format='yaml(spec.template.spec.containers[0].env,spec.template.spec.containers[0].env[].valueSource)'
  # คาดหวั่ง: มี SNC_DB_BACKEND + SNC_ALLOWED_ORIGINS; ไม่มี TEST_MARKER; SNC_API_KEY เป็น secret mount
  ```

---

## 🔍 สถานะ commit (branch `main`, origin synced ✅)

| commit | งาน | สถานะ |
|---|---|---|
| `350758d` | feat(ops): เพิ่ม `rotate_telegram_token.sh` (หมุน TELEGRAM_BOT_TOKEN แบบกึ่งอัตโนมัติ) | ✅ สคริปต์พร้อม — รอหมุน token จริง (revoke ที่ @BotFather) |
| `ea397f7` | fix(ops): ตั้ง `SNC_ALLOWED_ORIGINS` ด้วย `^@^` delimiter + เพิ่ม `cleanup_cloud_monitoring.sh` | ✅ สคริปต์พร้อม — รอรันบน Cloud Shell |
| `923eb0d` | docs(handover): อัปเดตสถานะจริง (SNC_ALLOWED_ORIGINS ยังไม่ตั้ง / channel เก่า / TEST_MARKER) | ✅ commit — แก้ต่อใน handover นี้แล้ว |
| `c4c53ce` | fix(monitoring): อ่าน secret เป็น plaintext + comment project id legacy | ✅ live |
| (ก่อนหน้า) `837fe18` / `ad7e917` | bridge แยก service + fix container start | ✅ live |

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