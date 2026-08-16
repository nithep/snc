---
title: "ADR 0005 — Infrastructure-as-Code ด้วย Terraform สำหรับ GCP"
type: adr
tags: [architecture]
---

# ADR 0005 — Infrastructure-as-Code ด้วย Terraform สำหรับ GCP

- สถานะ: **Proposed**
- วันที่: 2026-08-17

## บริบท
GCP ทั้งหมดถูกสร้างด้วยสคริปต์ imperative (`deploy_*.sh/ps1/bat`) → รันซ้ำผลไม่ deterministic,
รีวิว/reproduce ยาก, ไม่มี single source of truth สำหรับ Cloud Run / Firestore / Secret Manager / Monitoring

## การตัดสินใจ
ใช้ **Terraform** (GCP provider) ครอบทรัพยากรหลัก: Cloud Run 2 ตัว (backend+bridge),
Firestore, Secret Manager, uptime check + alerting policy, IAM binding
- เก็บ state ไว้ใน GCS bucket (backend)
- สคริปต์ deploy เดิมค่อยๆ เลิกใช้/กลายเป็น wrapper ที่เรียก `terraform apply`

## ผลกระทบ
- (+) declarative + reproducible, review ผ่าน PR, drift ตรวจได้ (`terraform plan`)
- (+) secret ผ่าน Secret Manager + IAM ชัดเจน
- (-) ต้องเรียนรู้ Terraform; เพิ่ม dependency (terraform CLI, state bucket)
- (-) ต้อง migrate จาก resource ที่สร้างด้วยมือก่อน (import)

## ทางเลือกที่ไม่ได้เลือก
- ใช้ `gcloud` สคริปต์ต่อ — ง่ายแต่ไม่ reproducible (เป็น status quo ที่เราต้องการแก้)
- Cloud Deployment Manager — ยังนิยมน้อยกว่า Terraform ในองค์กร

## อ้างอิง
- `ops/terraform/` (สร้างตาม ADR นี้)