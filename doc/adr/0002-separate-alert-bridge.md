---
title: "ADR 0002 — แยก SNC Alert Bridge เป็น service ต่างหาก"
type: adr
tags: [architecture]
---

# ADR 0002 — แยก SNC Alert Bridge เป็น service ต่างหาก

- สถานะ: **Accepted** (ได้ implement แล้ว)
- วันที่: 2026-08-17

## บริบท
ต้องการให้การแจ้งเตือน (alert) ถึง Telegram ยังทำงานแม้ backend หลัก (`snc-cloud-backend`)
จะ down — ถ้า webhook ชี้ไปที่ backend หลัก จุดพังเดียวกันก็จะพังพร้อมกัน

## การตัดสินใจ
สร้าง Cloud Run service แยกชื่อ `snc-alert-bridge` (จาก `api/bridge_server.py` +
`api/Dockerfile.bridge`):
- เป็น service จิ๋ว ไม่ import `storage/server` เลย (ไม่มีจุดพังร่วมกับ service หลัก)
- รับ webhook จาก Cloud Monitoring → ส่ง Telegram
- Auth fail-closed ด้วย `MONITOR_WEBHOOK_TOKEN` (จาก Secret Manager)

## ผลกระทบ
- (+) availability ดีขึ้น: alert รอดแม้ backend หลัก down
- (+) ไร้จุดพังร่วม (no shared fate)
- (-) ต้นทุน +1 service, มี env/token แยกชุดที่ต้องดูแล (โซลูชัน: Secret Manager — ADR 0005)

## ทางเลือกที่ไม่ได้เลือก
- webhook ไป backend หลัก (ไม่เอาครับ — shared failure)
- alert ผ่าน Cloud Function (ได้ แต่เพิ่ม dependency อีกตัว)

## อ้างอิง
- `ops/deploy_bridge_cloudshell.sh`, `ops/setup_cloud_monitoring.sh`