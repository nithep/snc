---
title: "Incident — Cloud Run Data Loss (env SNC_DB_BACKEND หายจาก deploy) 19–24 ส.ค. 2569"
type: incident
tags: [incident, cloudrun, firestore, data-loss]
date: 2026-08-25
status: resolved
---

# 🚨 Incident — Cloud Run Data Loss (SNC_DB_BACKEND หายจาก deploy)

> สรุป: event จริงจาก PBX (21 + 24 ส.ค.) หายทั้งหมดบน Cloud Run เพราะ revision กลางคันรัน
> SQLite บน container (ephemeral) แทน Firestore — **ต้นตอคือ deploy ที่ไม่ได้ใส่ env**
> และบั๊กของ deploy script เองที่ทำให้ script ตายกลางทางเงียบๆ

## 📅 Timeline ของเหตุการณ์

| วันที่ (2569) | เหตุการณ์ |
|---|---|
| 16–18 ส.ค. | rev `00015–00017` — `SNC_DB_BACKEND=firestore` ✅ ข้อมูลเข้า Firestore ปกติ |
| **19 ส.ค.** | rev `00018–00019` deploy โดย**ไม่มี** `SNC_DB_BACKEND` → `get_store()` fallback เป็น **SQLite บน container** ❌ |
| 21 ส.ค. / 24 ส.ค. | Pi listener ส่ง event ห้อง 1100/1105 ขึ้น cloud — HTTP **200 OK** (เขียนลง disk ชั่วคราว) |
| ~24 ส.ค. | container scale-to-zero → **disk ถูกทำลาย = event หายถาวร** (recover ไม่ได้) |
| 24 ส.ค. | rev `00020–00024` deploy ผ่าน script → กลับมา firestore ✅ (แต่ข้อมูลช่วง 19–24 ส.ค. หายไปแล้ว) |
| 25 ส.ค. | ตรวจพบ + แก้ป้องกันซ้ำ (ดูด้านล่าง) |

## 🔍 หลักฐานที่ใช้วินิจฉัย

- Firestore REST (`listCollectionIds`) เห็นเฉพาะ collection `room_state` โดย timestamp ใหม่สุดคือ **17 ส.ค.** ทั้งที่ outbox บน Pi mark `sent` 15/15 และ log ขึ้น `✅ Event sent to cloud`
- `gcloud run revisions describe <rev>` ต่อ revision พบ env ของ `00018–00019` ไม่มี `SNC_DB_BACKEND`
- 200 OK เพราะ trigger endpoint บันทึกลง store ใดๆ ก็ได้ — HTTP layer ไม่รู้ว่า store เป็น SQLite

## 🛡️ สิ่งที่แก้ (25 ส.ค.)

1. **Code guard** (`api/storage.py` → `get_store()`): ถ้ารันบน Cloud Run (มี env `K_SERVICE`)
   แต่ backend ≠ `firestore` → force `firestore` + `logging.critical` — deploy env พังอีก
   จะเสียแค่ warning ไม่เสียข้อมูล (อิงหลัก [[0003-firestore-over-sqlite-cloud]])
2. **Deploy script bugfix** (`ops/deploy_gcp_cloudrun.ps1`): บรรทัด IAM binding ใช้ `*> $null`
   ร่วมกับ `$ErrorActionPreference="Stop"` ทำให้ PS 5.1 โยน NativeCommandError และ
   **script ตายทุกครั้งก่อนถึง step build** (เป็นแรงจูงใจให้คนไป deploy มือจน env หาย) → เปลี่ยนเป็น `| Out-Null`
3. Deploy rev `00025-jvz` ผ่าน script + verify ครบ (health=firestore, auth 401, smoke test dedup/KPI)

## ✅ Checklist ป้องกันซ้ำ

- [ ] Deploy Cloud Run **เฉพาะ** `ops/deploy_gcp_cloudrun.ps1` (merge env ด้วย `--update-env-vars` เท่านั้น)
- [ ] ห้าม `gcloud run deploy` มือโดยไม่ใส่ `--update-env-vars` ครบชุด
- [ ] ตรวจ workflow ของ SA `github-deployer@hotel-ecs-nithep` (มี `roles/run.admin`) ว่า set env ครบก่อนเปิดใช้ CI/CD
- [ ] หลัง deploy ทุกครั้ง: `GET /health` ต้องขึ้น `"db":"firestore"`
- [ ] Outbox ฝั่ง Pi ปกติ best-effort สำหรับ cloud (local เท่านั้นที่ gate `sent`) — ทบทวนตาม [[0004-outbox-idempotency]] หากต้องการ at-least-once ระดับ cloud

## 📎 ข้อมูลอ้างอิง

- Service: `snc-cloud-backend` (asia-southeast1) · Project: `hotel-ecs-nithep`
- Revision ที่เกี่ยว: `00015–00025` · Event DB: Firestore `(default)` collection `nurse_call_events`
- ไทม์ไลน์รวม: [[project_timeline]]
