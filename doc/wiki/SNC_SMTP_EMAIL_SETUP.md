---
title: "SNC SMTP Email Setup — การแจ้งเตือนฟอร์มติดต่อ"
type: guide
tags: [email, smtp, alerts, security]
---

# SNC SMTP Email Setup

## ขอบเขต

ฟอร์ม `ติดต่อทีมงาน SNC` ที่ `snc.nithep.com` จะบันทึกข้อความลงระบบและส่งอีเมลแจ้งเตือนผ่าน SMTP เมื่อกำหนดตัวแปรต่อไปนี้ใน environment ของ backend:

ตัวอย่างสำหรับโดเมน `nithep.com` และ mailbox `admin@nithep.com`:

```text
SNC_SMTP_HOST=<SMTP host ของผู้ให้บริการ nithep.com>
SNC_SMTP_PORT=587
SNC_SMTP_USERNAME=admin@nithep.com
SNC_SMTP_PASSWORD=<smtp-password-or-app-password>
SNC_SMTP_FROM=admin@nithep.com
SNC_CONTACT_EMAIL=admin@nithep.com
```

> ต้องใช้ SMTP host จริงของผู้ให้บริการอีเมลสำหรับ `nithep.com` เช่น host ที่ผู้ให้บริการระบุใน control panel ห้ามเดา host เพราะอาจทำให้ TLS หรือ authentication ล้มเหลว

ใช้ SMTP submission แบบ STARTTLS บนพอร์ต 587 โดยห้ามนำ password ใส่ใน source code, Git หรือเอกสารที่ commit

## Cloud Run

ให้เก็บ `SNC_SMTP_PASSWORD` ใน Secret Manager และ mount เป็น secret environment variable ส่วนค่าที่ไม่ใช่ความลับตั้งผ่าน environment variables ของ Cloud Run

ตัวอย่างรูปแบบคำสั่งใน Cloud Shell (ไม่ใส่ค่าจริงใน repository):

```bash
gcloud run services update snc-cloud-backend \
  --project hotel-ecs-nithep \
  --region asia-southeast1 \
  --update-env-vars \
SNC_SMTP_HOST=<SMTP_HOST>,SNC_SMTP_PORT=587,SNC_SMTP_USERNAME=admin@nithep.com,SNC_SMTP_FROM=admin@nithep.com,SNC_CONTACT_EMAIL=admin@nithep.com \
  --update-secrets SNC_SMTP_PASSWORD=snc-smtp-password:latest
```

ก่อนใช้คำสั่งนี้ต้องสร้าง secret และให้ service account ของ Cloud Run มี `roles/secretmanager.secretAccessor`

## การตรวจสอบ

ส่งข้อความทดสอบจากฟอร์ม แล้วตรวจ response:

```json
{
  "status": "success",
  "notified": true,
  "email_notified": true
}
```

หาก `email_notified` เป็น `false` ให้ตรวจ Cloud Run logs โดยไม่พิมพ์ค่า password:

```bash
gcloud logging read \
  'resource.type="cloud_run_revision" AND resource.labels.service_name="snc-cloud-backend"' \
  --project hotel-ecs-nithep --limit 30
```

## ความปลอดภัย

- ใช้ mailbox สำหรับระบบโดยเฉพาะ ไม่ใช้บัญชีส่วนตัว
- ใช้ SMTP password หรือ app password แยกจากรหัสผ่านหลัก
- จำกัดผู้รับด้วย `SNC_CONTACT_EMAIL`
- rotate password ตามนโยบายผู้ให้บริการ และ restart/redeploy Cloud Run หลัง rotate
- ไม่บันทึก SMTP password ใน log, response, screenshot หรือ commit
