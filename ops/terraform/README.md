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
   ดูรายการครบทุก resource (พร้อม ID จริง) ที่ส่วนด่านล่าง — **ลำดับ import ให้ถูก**
2. **⚠️ ลำดับก่อน import (สำคัญ):**
   `ops/terraform/main.tf` มักอ้างอิง env ที่มือสคริปต์ตั้ง — ให้รัน `deploy_backend_cloudshell.sh`
   ใหม่ก่อน (หลังจาก `SNC_ALLOWED_ORIGINS` + secret-mount `SNC_API_KEY` + ลบ `TEST_MARKER`
   เสร็จตาม handover 19 ส.ค.) แล้วค่อย import เส้นทางเท่ากัน ไม่งั้น Terraform จะเห็น diff
   (เช่น มี `SNC_ALLOWED_ORIGINS`/`TEST_MARKER` ที่ไม่อยู่ใน config) และอาจ overwrite ที่มีอยู่
3. **Remote state** ที่ `gs://snc-tfstate-nithep/snc` — สร้าง bucket เองก่อน (ด้วยมือครั้งเดียว):
   ```bash
   gsutil mb -l asia-southeast1 gs://snc-tfstate-nithep
   ```
   หรือแก้ `versions.tf` ให้ชี้ bucket ของคุณ
4. **Secrets ผ่าน Secret Manager** — ไม่ต้องตั้ง `TELEGRAM_BOT_TOKEN`/`MONITOR_WEBHOOK_TOKEN`
   ใน env ของ Cloud Run (mount จาก secret) ตรงตาม ADR 0002/0005
   - `SNC_API_KEY` (backend) ก็ผ่าน secret `snc-api-key` แล้ว (ไม่ใช้ plain env) — ดู main.tf
5. ตั้งค่าตัวแปร (`backend_image`, `bridge_image`, `snc_api_key`, `telegram_*`, `monitor_webhook_token`)
   ใน `terraform.tfvars` หรือ env `TF_VAR_*`
6. รัน: `terraform init` → `terraform plan` → `terraform apply`

## 📋 เสนอแผน import resource ครบ (Cloud Shell)

> PROJECT = `hotel-ecs-nithep`, REGION = `asia-southeast1`
> ใช้ `--project hotel-ecs-nithep` หรือ `gcloud config set project` ล่วงหน้า

### คำเตือนก่อน import
- import **secret** เป้นไปได้ (`google_secret_manager_secret.*`) แต่อย่า import
  `google_secret_manager_secret_version.*` ด้วยมือ — version ที่เพิ่มด้วยมือ (โดยสคริปต์ deploy)
  จะทำให้ Terraform ควบคุม version ซ้ำและ conflict กับ `versions add` ดึ่นหลัง
   - แนวทางปลอดภัย: import secret เท่านั้น → ให้ `secret_version` resource ถูก `lifecycle { ignore_changes = all }`
     (หรือ comment ทิ้ง) → ให้ deploy script ที่เพิ่ม version
- หลังจาก `terraform plan` ตรวจว่าไม่มี diff เกี่ยวกับ secret version ก่อน `apply`

### รายการ import (ลำดับที่แนะนำ)

```bash
P=hotel-ecs-nithep
R=asia-southeast1
SA=snc-run@$P.iam.gserviceaccount.com

# 0) Firestore
terraform import google_firestore_database.snc                $P/(default)

# 1) Secret Manager (เท่านั้น — ไม่ import secret_version ที่มือ)
terraform import google_secret_manager_secret.snc_api_key    $P/snc-api-key
terraform import google_secret_manager_secret.telegram_bot_token   $P/snc-telegram-bot-token
terraform import google_secret_manager_secret.monitor_webhook_token  $P/snc-monitor-webhook-token

# 2) Cloud Run services
terraform import google_cloud_run_v2_service.backend   \
  $P/$R/services/snc-cloud-backend
terraform import google_cloud_run_v2_service.bridge     \
  $P/$R/services/snc-alert-bridge

# 3) Service Account
terraform import google_service_account.run_sa          $P/snc-run@$P.iam.gserviceaccount.com

# 4) Cloud Run IAM (allUsers invoker)
terraform import google_cloud_run_v2_service_iam_member.backend_invoker \
  $P/$R/services/snc-cloud-backend/roles/run.invoker/allUsers
terraform import google_cloud_run_v2_service_iam_member.bridge_invoker \
  $P/$R/services/snc-alert-bridge/roles/run.invoker/allUsers

# 5) Secret Manager IAM (ให้กับ snc-run SA)
terraform import google_secret_manager_secret_iam_member.bridge_bot_accessor \
  $P/snc-telegram-bot-token/roles/secretmanager.secretAccessor/$SA
terraform import google_secret_manager_secret_iam_member.backend_apikey_accessor \
  $P/snc-api-key/roles/secretmanager.secretAccessor/$SA
terraform import google_secret_manager_secret_iam_member.bridge_webhook_accessor \
  $P/snc-monitor-webhook-token/roles/secretmanager.secretAccessor/$SA

# 6) Project-level IAM (Firestore datastore.user ให้กับ snc-run SA)
terraform import google_project_iam_member.run_sa_firestore \
  $P/roles/datastore.user/serviceAccount:$SA

# 7) Uptime check (display name มีอยู่แล้ว = "SNC Cloud Run /health")
terraform import google_monitoring_uptime_check_config.snc    \
  $P/uptimeCheckConfigs/snc-cloud-run-health

# 8) Notification channel (ID จริงจาก handover = 6246499446847685992)
terraform import google_monitoring_notification_channel.telegram_bridge \
  $P/notificationChannels/6246499446847685992

# 9) Alert policy (ID จริงจาก handover = 17676417133185946039)
terraform import google_monitoring_alert_policy.snc_uptime    \
  $P/alertPolicies/17676417133185946039
```

> ℹ️ หลัง import → รัน `terraform plan` ตรวจ diff ก่อน `apply`
> - channel URL มี `MONITOR_WEBHOOK_TOKEN` ฝังอยู่ — หากหมุน token แล้ว URL เก่า Terraform จะ patch อัปเดตอัตโอหลัง apply
> - uptime check filter ใช้ `uptime_check_id` — ค่าจะถูก populate อัตโอหลัง import

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