---
title: "SESSION_HANDOVER_2026-08-17 — CORS Restrict + Cloud Deploy (backend/bridge/monitoring) + Offsite Backup + Terraform"
type: handover
tags: [status]
---

# SESSION_HANDOVER_2026-08-17 — CORS Restrict + Cloud Deploy + Offsite Backup + Terraform

> จัดทำ: 17 ส.ค. 2569 | ต่อจาก handover 16 ส.ค. (Cloud Run deploy + Firestore)

---

## 📊 สถานะระบบ ณ สิ้น session

| ระบบ | สถานะ | หมายเหตุ |
|---|---|---|
| **CORS จำกัด origin** | ✅ commit `d938122` | จาก `*` → ระบุ origin จริง (`SNC_ALLOWED_ORIGINS` env) + `allow_credentials=False` — ยังต้อง redeploy backend ถึง active |
| **Cloud Monitoring uptime → Telegram** | ✅ ตั้งค่าแล้ว + **test alert ได้** | alert test (`ทดสอบจาก setup_cloud_monitoring.sh`) ส่งถึง Telegram สำเร็จ = ห่วงโซ่ Cloud Monitoring→bridge→Telegram ทำงาน |
| **Bucket offsite** `gs://snc-backup-nithep` | ✅ สร้าง + lifecycle (delete 14 วัน) | (Cloud Shell — `gsutil mb`) |
| **cron backup บน Pi** | ⚠️ **ยังไม่มี cron** | `crontab | grep backup-offsite` = ว่าง — ยังไม่ติดตั้งสำเร็จ |
| **Offsite backup ขึ้น GCS** | ⚠️ **ยังไม่มีไฟล์** | `gsutil ls gs://snc-backup-nithep/` = ว่าง — ยังไม่ push สำเร็จ |
| **Terraform IaC** | ⏳ ยังไม่ init/import/apply | ต้องสร้าง state bucket + import ของที่สร้างด้วยมือก่อน |

---

## ✅ งานที่เสร็จใน session นี้

### 1. CORS จำกัด origin (commit `d938122`)
- `api/server.py:79` — เปลี่ยน `allow_origins=["*"]` + `allow_credentials=True` → `_ALLOWED_ORIGINS` (env `SNC_ALLOWED_ORIGINS` comma-separated) + `allow_credentials=False`
  - ระบบใช้ `X-API-Key` header (ไม่ใช่ cookie) → ไม่ต้อง credentials
  - default: nursecall/hotel tunnel + Cloud Run URL + localhost + LAN Pi
  - same-origin ยังทำงานปกติ (dashboard เสิร์ฟจาก backend เอง)
- `api/.env.example` + `ops/deploy_backend_cloudshell.sh` — เพิ่ม env เอกสาร/ตั้งค่า
- **Active หลัง redeploy backend เท่านั้น**

### 2. Cloud Deploy (ทำใน Cloud Shell — ขั้นตอน 1-3 ของลิสต์)
- `deploy_backend_cloudshell.sh` ✅ (ตอนนี้ set `SNC_ALLOWED_ORIGINS` ด้วย)
- `deploy_bridge_cloudshell.sh` ✅
- `setup_cloud_monitoring.sh` ✅ + **test alert ผ่าน** (ข้อความ `Uptime check /health failed / ทดสอบจาก setup_cloud_monitoring.sh` ถึง Telegram = pipeline ทำงาน — ไม่ใช่เหตุการณ์จริง)

---

## ⏳ สิ่งค้าง / next steps

### ข้อ 4 — Offsite backup + cron (ยังไม่เสร็จ)
**ปัญหา:** บน Pi path เป็น **`/home/ecs-agent/snc-poc`** (ไม่ใช่ `~/snc`) + `--install` ตอนแรกอาจรันจาก path ผิด → cron ไม่เข้า + ไม่มีไฟล์ใน bucket

บน Pi (`ecs-agent@hotel-gateway`, **ไม่ต้อง `ssh pi4`** — alias อยู่บน Windows เท่านั้น):
```bash
cd /home/ecs-agent/snc-poc
ls -la ops/backup-offsite.sh          # ตรวจว่าไฟล์มีจริง + exec bit
bash ops/backup-offsite.sh --install  # ติดตั้ง cron
crontab -l | grep backup-offsite      # ต้องไม่ว่าง
```
ถ้า DB path ต่างจาก default ใน script (`/home/ecs-agent/snc/api/...`):
```bash
export SNC_DB_PATH=/home/ecs-agent/snc-poc/api/nurse_call_events.db
export BACKUP_DIR=/home/ecs-agent/snc-poc/backups
bash ops/backup-offsite.sh            # ทดสอบ run — ดู error ชัด (ไม่พบ DB? / ไม่พบ gsutil? / GCS push fail?)
```
Cloud Shell — เช็คไฟล์ขึ้น bucket:
```bash
gsutil ls gs://snc-backup-nithep/
```
> ⚠️ ถ้า Pi ไม่มี `gsutil` → ต้องติดตั้ง Google Cloud CLI บน Pi ก่อน (ตอนนี้ script จะข้าม offsite เงียบๆ)

### ข้อ 5 — Terraform (ยังไม่เริ่ม)
```bash
# Cloud Shell
gsutil mb -l asia-southeast1 gs://snc-tfstate-nithep   # state bucket (versions.tf ชี้ที่นี้)
cd ops/terraform
terraform init
```
- ต้อง **import** ของที่สร้างด้วยมือก่อน apply (backend/bridge/Firestore/secrets/uptime/channel/policy) — รายละเอียด + ตัวอย่างใน `ops/terraform/README.md`
- ตั้ง `terraform.tfvars` (backend_image/bridge_image ควรเป็น **digest** + sensitive จาก Secret Manager)
- ⚠️ SA drift: `main.tf` ใช้ `snc-run` SA แต่ deploy scripts ใช้ compute SA — plan จะชี้ให้เห็น

### ☁️ ตรวจ/ยืนยัน (optional)
- `curl https://snc-cloud-backend-59781590359.asia-southeast1.run.app/health` → ควรได้ `firestore` healthy
- ถ้ายังไม่ redeploy หลัง commit CORS → รัน `deploy_backend_cloudshell.sh` ใหม่ให้ `SNC_ALLOWED_ORIGINS` active

---

## 🔐 Credentials / Paths
- **Project**: `hotel-ecs-nithep` · region `asia-southeast1`
- **Pi path**: `/home/ecs-agent/snc-poc` (legacy, ไม่ใช่ `snc`)
- **Backend URL**: `https://snc-cloud-backend-59781590359.asia-southeast1.run.app`
- **Bridge URL**: `https://snc-alert-bridge-59781590359.asia-southeast1.run.app`
- **Secrets (Secret Manager)**: `snc-api-key`, `snc-telegram-bot-token`, `snc-monitor-webhook-token`
- **Telegram**: bot `@snc2569_bot`, chat `7346817215` (ใน `api/.env` บน Pi)
- **ssh**: ใช้ `pi4` alias เฉพาะบน Windows; บน Pi รันตรงๆ

---

## 📦 Git (session นี้)
- `d938122` feat(security): restrict CORS from `*` to real origins (`SNC_ALLOWED_ORIGINS` env) + `allow_credentials=False`

> ⚠️ ยังไม่ได้ push `d938122` ขึ้น origin (คอมมิตแล้วใน local) — push เมื่อพร้อม