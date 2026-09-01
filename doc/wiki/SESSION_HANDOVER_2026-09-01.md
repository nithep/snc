---
title: "SESSION_HANDOVER_2026-09-01 — Sync Pi4 + Deploy GCP Cloud Run + Fix Secret Manager"
type: handover
tags: [status, pi4, cloud-run, deploy, sync, secret-manager]
---

# SESSION_HANDOVER_2026-09-01 — Sync Pi4 + Deploy GCP Cloud Run + Fix Secret Manager

> จัดทำ: 1 ก.ย. 2569 | ต่อจาก [[SESSION_HANDOVER_2026-08-26]]
> ครอบคลุม: sync โค้ดระหว่าง D:\snc ↔ GitHub ↔ Pi4, deploy ขึ้น GCP Cloud Run, แก้ deploy script ปัญหา Secret Manager conflict

## งานที่ทำ

### 1. ตรวจสอบ Git Status (D:\snc, Pi4, GitHub)

- **D:\snc (MateBook):** branch `main`, commit `f26e477` (+1 commit ยังไม่ได้ push)
- **Pi4 (192.168.1.94):** branch `master`, commit `0830caa` — **落后 20 commits** จาก GitHub
- **GitHub (origin/main):** `fc5d14c`
- **Pi4 มี untracked files:** backup files (*.bak), burn-in status, `_backup_untracked/`

### 2. Sync Pi4 ↔ GitHub

1. `git stash` local changes บน Pi4
2. `git pull origin main` — fast-forward 20 commits (32 files, +3677 lines)
3. แก้ merge conflicts ใน `api/storage.py` + `app/index.html` (ใช้ version ใหม่จาก GitHub)
4. `git reset --hard origin/main` — บังคับให้ Pi4 ตรงกับ GitHub
5. Restart services: `snc-backend.service` + `snc-pbx-listener.service` ✅
6. Health check: `{"status":"healthy","db":"sqlite"}` ✅

### 3. Push D:\snc → GitHub

- Push commit `f26e477` (chore(dashboard): extract main Nurse Station logic to app/index.js)
- ไฟล์ใหม่: `app/index.js` (+896 lines)

### 4. Sync Pi4 อีกครั้ง

- Pull commit `f26e477` สำเร็จ ✅

### 5. Deploy GCP Cloud Run

#### 5.1 สร้าง API Key ใน Secret Manager

- สร้าง `snc-api-key` version 2 + version 3 สำเร็จบน Cloud Shell

#### 5.2 Build + Push Image

- Docker build สำเร็จ (392s, 15/15 steps)
- Push image `gcr.io/hotel-ecs-nithep/snc-cloud-backend:latest@sha256:689ee39...` สำเร็จ

#### 5.3 Deploy ล้มเหลว — Secret Manager Conflict

- **ปัญหา:** `SNC_API_KEY` ถูกตั้งเป็น **Secret Manager reference** อยู่แล้วบน Cloud Run
- **สาเหตุ:** deploy script 试图จะ set เป็น **string literal** ผ่าน `--set-env-vars`
- **ผลลัพธ์:** `ERROR: Cannot update environment variable [SNC_API_KEY] to string literal because it has already been set with a different type`

#### 5.4 แก้ Deploy Script

- แก้ `ops/deploy_cloudrun_cloudshell.sh`:
  - เอา `SNC_API_KEY` ออกจาก `EXTRA_ENV` (string literal)
  - เพิ่ม `--update-secrets "SNC_API_KEY=snc-api-key:latest"` แทน
  - แก้ `GEMINI_API_KEY` + `TELEGRAM_BOT_TOKEN` ให้ใช้ `--update-secrets` เช่นกัน
- Commit: `b502603` — Push สำเร็จ

#### 5.5 Deploy สำเร็จ

- Cloud Shell: `git reset --hard origin/main` → run deploy script
- Build image + Push สำเร็จ
- Deploy + set secrets สำเร็จ

### 6. Verify ผลลัพธ์

| รายการ | ผลลัพธ์ |
|--------|---------|
| `/health` | ✅ `healthy`, `db=firestore` |
| Auth (POST ไม่มี key) | ✅ 401 |
| Dashboard `/` | ✅ HTTP 200 |
| Firestore write | ✅ HTTP 200 |
| KPI | ✅ 41 events, SLA 100%, avg ack 0s, avg resolution 20.49s |

## สถานะปัจจุบัน

| ระบบ | Commit/Rev | สถานะ |
|------|------------|-------|
| D:\snc (MateBook) | `b502603` | ✅ |
| GitHub (origin/main) | `b502603` | ✅ |
| Pi4 (Edge) | `f26e477` | ✅ (落后 1 commit — fix deploy script) |
| GCP Cloud Run | rev 00029 | ✅ `healthy` + `firestore` |
| Secret Manager | v3 (`snc-api-key`) | ✅ |

## ไฟล์ที่แก้

| ไฟล์ | การแก้ไข |
|------|----------|
| `ops/deploy_cloudrun_cloudshell.sh` | แก้ deploy script: ใช้ `--update-secrets` แทน string literal env vars |
| `OLD_deployed.js` | เพิ่มไฟล์ (backup) |

## การตัดสินใจ/ข้อสังเกต

1. **Deploy script ต้องใช้ `--update-secrets`** สำหรับ secrets ที่มีอยู่แล้วบน Cloud Run — ห้ามใช้ `--set-env-vars` สำหรับ secret refs (Cloud Run ปฏิเสธ)
2. **Pi4 อยู่ branch `master`** ไม่ใช่ `main` — แต่ sync ผ่าน `origin/main` ได้ปกติ
3. **Untracked files บน Pi4** เป็น backup files ที่ไม่เกี่ยวกับ code หลัก — ไม่ต้อง commit
4. **Image build สำเร็จแล้ว** ครั้งถัดไป deploy จะเร็วขึ้น (ไม่ต้อง build ใหม่ถ้า code ไม่เปลี่ยน)

## สิ่งค้าง

1. **Pi4落后 1 commit** (`b502603` — fix deploy script) — ต้อง `git pull` บน Pi4
2. **Rotate API Key จริง** — ค่า key ปัจจุบันอาจเคยถูกใช้ใน plaintext → ควร rotate ตาม [[SNC_API_KEY_ROTATION_GUIDE]]
3. **Untracked files บน Pi4** — ควรเพิ่มใน `.gitignore` หรือลบ (backup files *.bak)

## อ้างอิง

- Deploy script: `ops/deploy_cloudrun_cloudshell.sh`
- Cloud Run service: `https://snc-cloud-backend-59781590359.asia-southeast1.run.app`
- Secret Manager: `snc-api-key` (v3), `snc-gemini-api-key`, `snc-telegram-bot-token`
- Previous handover: [[SESSION_HANDOVER_2026-08-26]]
