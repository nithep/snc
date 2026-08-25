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

- [x] Deploy Cloud Run **เฉพาะ** `ops/deploy_gcp_cloudrun.ps1` / `deploy_cloudrun_cloudshell.sh` (merge env ด้วย `--update-env-vars`)
- [x] Script verify ทั้งสองตัว fail-closed ถ้า `/health` ไม่ขึ้น `db=firestore` (เพิ่ม 26 ส.ค.)
- [ ] ห้าม `gcloud run deploy` มือโดยไม่ใส่ `--update-env-vars` ครบชุด
- [ ] หลัง deploy ทุกครั้ง: `GET /health` ต้องขึ้น `"db":"firestore"`
- [ ] Outbox ฝั่ง Pi ปกติ best-effort สำหรับ cloud (local เท่านั้นที่ gate `sent`) — ทบทวนตาม [[0004-outbox-idempotency]] หากต้องการ at-least-once ระดับ cloud

## 🔑 การหมุนเวียน SA key — `github-deployer@hotel-ecs-nithep` (staged rotation, 26 ส.ค.)

Audit log พบ SA นี้ `ReplaceService` เมื่อ 22 ส.ค. (23:06 +07) — 34 นาทีหลังสร้าง user-managed key
→ deploy channel นอกระบบ script ที่ env หาย น่าจะมาจาก key นี้ (GitHub Actions ภายนอก repo)

| Key ID | สร้าง | สถานะ |
|---|---|---|
| `cc69a06e...dc854` | 22 ส.ค. | ⛔ รอ revoke (ต้นเหตุ suspect) |
| `8c798c04...ef634` | 25 ก.ค. | ⛔ รอ revoke (เกินจำเป็น) |
| `5702c598...45e4` | 26 ส.ค. | ✅ key ใหม่ — เก็บที่ `%USERPROFILE%\.config\snc\github-deployer-newkey-20260826.json` |

**ขั้นตอนค้าง (ผู้ดูแล GitHub):**
1. นำเนื้อหา JSON ไฟล์ใหม่ไปแทน secret ใน GitHub Actions workflow (repo ภายนอก)
2. รัน workflow 1 ครั้งยืนยัน deploy ผ่าน
3. Revoke key เก่า:
   ```bash
   gcloud iam service-accounts keys delete cc69a06e022efbe84b84ffd606638841840dc854 \
     --iam-account=github-deployer@hotel-ecs-nithep.iam.gserviceaccount.com --project hotel-ecs-nithep -q
   gcloud iam service-accounts keys delete 8c798c04538d7de04a1a10bbf30aaed9606ef634 \
     --iam-account=github-deployer@hotel-ecs-nithep.iam.gserviceaccount.com --project hotel-ecs-nithep -q
   ```
4. ลบไฟล์ JSON ในเครื่องหลังย้ายเข้า secret แล้ว

> Workflow ต้องตั้ง env `SNC_DB_BACKEND: firestore` ทุกครั้ง (หรือพึ่ง code guard ใน `api/storage.py`
> ซึ่ง force firestore ให้เองบน Cloud Run — guard เป็นตาข่ายด้านล่าง ไม่ใช่ข้อแก้ตัวของ pipeline)

## 📎 ข้อมูลอ้างอิง

- Service: `snc-cloud-backend` (asia-southeast1) · Project: `hotel-ecs-nithep`
- Revision ที่เกี่ยว: `00015–00025` · Event DB: Firestore `(default)` collection `nurse_call_events`
- ไทม์ไลน์รวม: [[project_timeline]]
