---
title: "SESSION_HANDOVER_2026-09-12 — Cloud Run Cleanup + Vault Update + GCP Project Shutdown"
type: handover
tags: [status, cleanup, cloud-run, vault, gcp, shutdown]
---

# SESSION_HANDOVER_2026-09-12 — Cloud Run Cleanup + Vault Update + GCP Project Shutdown

> จัดทำ: 12 ก.ย. 2569 | ต่อจาก [[SESSION_HANDOVER_2026-09-11]]
> ครอบคลุม: ลบ Cloud Run ออกจากโค้ดทั้งหมด, อัปเดต vault, Shut Down GCP project

## งานที่ทำ

### 1. Clean Code — ลบ Cloud Run ออกจาก Active Code

| ไฟล์ | สิ่งที่แก้ |
|------|-----------|
| `api/storage.py` | ลบ FirestoreStore class ทั้งหมด (557→313 บรรทัด) — เหลือ SQLite only |
| `api/server.py` | ลบ Cloud Run comment + health check `cloud_run: "removed"` |
| `pbx/snc_pbx_listener.py` | ลบ `CLOUD_RUN_API_URL` + cloud send logic ทั้งหมด |
| `ops/snc_telegram_agent.py` | ลบ `/cloudrun` command + `cloudrun_reply()` function |
| `ops/deploy_cloudrun_cloudshell.sh` | ⚠️ DEPRECATED header |
| `ops/deploy_gcp_cloudrun.ps1` | ⚠️ DEPRECATED header |

### 2. Clean Documentation — อัปเดต Vault ทั้งหมด

| ไฟล์ | สิ่งที่แก้ |
|------|-----------|
| `README.md` | ลบ Cloud Run ออกจาก architecture diagram + features |
| `AGENTS.md` | ลบ "Cloud Run" จาก rotate key guide |
| `SECURITY.md` | แก้ cross-border + investigation ไม่อ้าง Cloud Run |
| `.opencode/skills/snc/SKILL.md` | ADR 0002/0003 → deprecated, ลบ Cloud Services section |
| `app/landing.html` | ลบ Cloud Run ออกจาก arch diagram + features |

### 3. Commit + Push + Sync

```
345ef5a refactor: remove Cloud Run — Pi4 is sole production system
11 files changed, 56 insertions(+), 340 deletions(-)
```

### 4. Verify — Pi4 ยังทำงานปกติ

```json
{
  "status": "healthy",
  "db": "sqlite",
  "cloud_run": {"status": "removed", "message": "Cloud Run ถูกลบแล้ว — ระบบทำงานบน Pi4 เท่านั้น"}
}
```

### 5. Shut Down GCP Project

- **`hotel-ecs-nithep`** → ถูกลบแล้ว ✅
- **Cloud Run services** (hotel-ecs-backend, portal, snc-alert-bridge) → 0 items ✅
- **Folder `apps-script`** (ID: 756607151005) → ค้าง (Google Workspace-managed projects `sys-*` ที่ลบไม่ได้) — ไม่มีค่าใช้จ่าย

## สถานะปัจจุบัน

| ระบบ | สถานะ |
|------|-------|
| D:\snc (MateBook) | ✅ `345ef5a` |
| GitHub (origin/main) | ✅ `345ef5a` |
| Pi4 (Edge) | ✅ `345ef5a` + services active |
| GCP Cloud Run | ❌ ถูกลบแล้ว |
| GCP Project | ❌ ถูกลบแล้ว |
| Folder apps-script | ⚠️ ค้าง (ไม่มีค่าใช้จ่าย) |

## Architecture ปัจจุบัน (Lean)

```
Phonik PBX (192.168.1.91:23)
    ↕ Telnet (RDSS Poll ทุก 3 วินาที)
Pi 4 Edge (192.168.1.94)
    ├── snc-backend.service → FastAPI + SQLite WAL
    ├── snc-pbx-listener.service → PBX Listener + Outbox
    ├── TCP Proxy :2323 → Room Manager mirroring
    └── Cloudflare Tunnel → https://snc.nithep.com
         ↕ WebSocket real-time
    Nurse Station Dashboard (Dark Mode, i18n TH/EN)

Cloud Run — ❌ ไม่มีแล้ว
GCP — ❌ ไม่มีแล้ว
```

## Key Learnings

1. **Pi4 ทำหน้าที่ครบ** — ไม่ต้องพึ่ง Cloud สำหรับ Nurse Call System
2. **Cloud Run มีความเสี่ยง** — data loss จาก scale-to-zero, billing ซับซ้อน
3. **LEAN = ดี** — ระบบเดียว ดูแลง่าย ค่าใช้จ่าย 0 บาท
4. **Google Workspace-managed projects** (`sys-*`) ลบไม่ได้ผ่าน gcloud CLI — ต้องปล่อยไว้

## อ้างอิง

- Previous handover: [[SESSION_HANDOVER_2026-09-11]]
- Cloud Run deletion: [[SESSION_HANDOVER_2026-09-11]]
- Timeline: [[project_timeline]]
