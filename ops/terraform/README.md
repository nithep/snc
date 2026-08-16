# Terraform for SNC GCP (ADR 0005)

ครอบทรัพยากร GCP ของ SNC: Cloud Run (backend + bridge), Firestore, Secret Manager,
uptime check + alerting policy (→ bridge → Telegram)

## ข้อควรระวัง / วิธีใช้

1. **เป็น initial reference** — resource บางตัวอาจถูกสร้างด้วยมือจาก `ops/*.sh` ไปก่อนแล้ว
   ต้อง `terraform import` ก่อน `apply` เพื่อไม่ให้ Terraform สร้างซ้ำ/ทำลายของเดิม
   ตัวอย่าง:
   ```bash
   terraform import google_cloud_run_v2_service.backend \
     projects/<PROJECT>/locations/asia-southeast1/services/snc-cloud-backend
   terraform import google_firestore_database.snc <PROJECT>/(default)
   ```
2. **Remote state** ที่ `gs://snc-tfstate-nithep/snc` — สร้าง bucket เองก่อน (ด้วยมือครั้งเดียว):
   ```bash
   gsutil mb -l asia-southeast1 gs://snc-tfstate-nithep
   ```
   หรือแก้ `versions.tf` ให้ชี้ bucket ของคุณ
3. **Secrets ผ่าน Secret Manager** — ไม่ต้องตั้ง `TELEGRAM_BOT_TOKEN`/`MONITOR_WEBHOOK_TOKEN`
   ใน env ของ Cloud Run (mount จาก secret) ตรงกับ ADR 0002/0005
   - `SNC_API_KEY` (backend) ก็ผ่าน secret `snc-api-key` แล้ว (ไม่ใช้ plain env) — ดู main.tf
4. ตั้งค่าตัวแปร (`backend_image`, `bridge_image`, `snc_api_key`, `telegram_*`, `monitor_webhook_token`)
   ใน `terraform.tfvars` หรือ env `TF_VAR_*`
5. รัน: `terraform init` → `terraform plan` → `terraform apply`

## การแก้ hardening (ล่าสุด)
- `snc_api_key` ย้ายจาก plain env → mount จาก Secret Manager (`snc-api-key`) + IAM accessor
- `deletion_protection = true` บน Firestore (กัน destroy โดยไม่ตั้งใจใน prod)

## หมายเหตุ design
- `backend_image`/`bridge_image` ควรชี้ **digest** (ไม่ใช่ tag) เพื่อกัน Cloud Run cache tag เก่า
  (เหมือนที่ deploy script ทำด้วย `image_summary.digest`)
- uptime/alert ใช้ `uptime_check_id` อ้างอิงกัน เพื่อให้ filter `check_id` ตรงเสมอ
- `monitor_webhook_token` ฝังใน URL ของ notification channel — ถ้า rotate token
  ต้อง `terraform apply` เพื่ออัปเดต channel (กัน stale-token)

## การเปลี่ยนจากสคริปต์มือ
ค่อย ๆ ย้าย: สร้าง IaC ครอบ → import ของที่มี → เมื่อ `terraform apply` เข้ากันได้ดี
แล้วจึงเลิกใช้ `deploy_*.sh` (อาจเปลี่ยนเป็น wrapper ที่เรียก terraform แทน)