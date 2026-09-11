---
title: "SESSION_HANDOVER_2026-09-11 — API Key Rotation + .gitignore + Pi4 Sync"
type: handover
tags: [status, pi4, security, api-key, rotation, sync]
---

# SESSION_HANDOVER_2026-09-11 — API Key Rotation + .gitignore + Pi4 Sync

> จัดทำ: 11 ก.ย. 2569 | ต่อจาก [[SESSION_HANDOVER_2026-09-01]]
> ครอบคลุม: rotate API Key, เพิ่ม .gitignore rules, sync Pi4, ตรวจสอบระบบ

## งานที่ทำ

### 1. Sync Pi4 ↔ GitHub

- **ผลการตรวจสอบ:** Pi4 (`a072194`) ตรงกับ D:\snc (`a072194`) แล้ว — ไม่มี commit ค้าง
- **action:** ไม่ต้องทำอะไร เพิ่มเติม

### 2. เพิ่ม .gitignore Rules

- เพิ่ม `*.bak` และ `*.bak.*` ใน `.gitignore` เพื่อกัน backup files ไม่ให้ถูก track
- ตรวจสอบแล้วไม่มี .bak files ถูก track อยู่ใน repo
- Commit: `0aa05b0` — Push สำเร็จ + Pi4 pull สำเร็จ

### 3. Rotate API Key

- **Key ใหม่:** `47ad2259...` (64 chars, openssl rand -hex 32)
- **Pi4 backend `.env` + listener `.env`:** อัปเดตสำเร็จ + chmod 600 ✅
- **Services restart:** `snc-backend` + `snc-pbx-listener` = active ✅
- **Auth test:**
  - No key → 401 ✅
  - New key → 200 ✅
- **Backup:** `backups/api.env.*` + `backups/pbx.env.*` บน Pi4

### 4. Cloud Run Secret Manager

- **status:** ค้าง — gcloud บน D:\snc ต้อง re-authenticate (`gcloud auth login`)
- **action ที่ต้องทำ:** รันจาก Cloud Shell:
  ```bash
  echo "47ad225955435d48b5ce34f7914e6f99f20b2203e5dec6ab8a543c98bc7f2a92" | \
    gcloud secrets versions add snc-api-key --data-file=- --project hotel-ecs-nithep
  ```
- **Cloud Run status:** 503 (scale-to-zero หรือ service หยุดทำงาน — ตรวจสอบเพิ่มเติม)

## สถานะปัจจุบัน

| ระบบ | สถานะ |
|------|-------|
| D:\snc (MateBook) | ✅ `0aa05b0` |
| GitHub (origin/main) | ✅ `0aa05b0` |
| Pi4 (Edge) | ✅ `0aa05b0` + API key ใหม่ |
| Pi4 Backend | ✅ healthy (sqlite) |
| Pi4 Listener | ✅ active |
| Cloud Run | ⚠️ 503 — ต้องตรวจสอบ + อัปเดต Secret Manager |

## สิ่งค้าง

1. **Cloud Run Secret Manager** — อัปเดต key ใหม่ผ่าน Cloud Shell (gcloud re-auth needed)
2. **Cloud Run service** — ตรวจสอบสถานะ 503 (scale-to-zero หรือ service หยุด)
3. **แจ้งทีม** — key ใหม่ใช้บน Pi4 แล้ว เบราว์เซอร์พยาบาลต้องกรอก key ใหม่ใน ⚙️ ตั้งค่า

## Key ใหม่ (เก็บในที่ปลอดภัย)

```
47ad225955435d48b5ce34f7914e6f99f20b2203e5dec6ab8a543c98bc7f2a92
```

## อ้างอิง

- Rotation Guide: [[SNC_API_KEY_ROTATION_GUIDE]]
- Previous handover: [[SESSION_HANDOVER_2026-09-01]]
- Deploy script: `ops/deploy_cloudrun_cloudshell.sh`
