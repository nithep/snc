---
title: "SESSION_HANDOVER_2026-09-07 — Deploy ADR 0013 (Remove Kiosk Scaling) + Pi Git Sync + CRLF Renormalization"
type: handover
tags: [status, pi4, dashboard, deploy, git-sync, line-endings, kiosk-removal]
---

# SESSION_HANDOVER_2026-09-07 — Deploy ADR 0013 + Pi Git Fast-Forward + CRLF Fix

> จัดทำ: 7 ก.ย. 2569 | ต่อจาก [[SESSION_HANDOVER_2026-09-05]]
> ครอบคลุม: Deploy ADR 0013 ขึ้น Production, Visual/Layout Verification, Test Suite, GitHub push, Pi git sync (`5f6e3da` → `c0df54a`), renormalize CRLF blob

## สรุปสถานะ (Deploy Status)

| สภาพแวดล้อม | สถานะ | หลักฐาน |
|---|---|---|
| **GitHub** (origin/main) | ✅ synced | `c0df54a` — push `932d90c..c0df54a` |
| **Pi4** (git checkout `~/snc`) | ✅ `c0df54a` | fast-forward + reset ครบ; `git status` สะอาด (เหลือแค่ `.bak.*` untracked ของ deploy) |
| **Live** (snc.nithep.com) | ✅ = GitHub (runtime) | `app/index.html` md5 `6df5931c…` · `api/server.py` md5 `00ecb55d…` = LF blob |
| Services | ✅ `active,active` | `snc-backend` + `snc-pbx-listener` (listener ไม่ถูก restart — สงวน session PBX) |

## งานที่ทำ

### 1. Deploy ADR 0013 — Remove Kiosk Scaling ขึ้น Production (commit `cbebdac`)

- `app/index.html`: ลบ Kiosk Scaling (`#appScale`, `fitToScreen()`, `ResizeObserver`, รองรับ `?kiosk`) — กลับสู่ responsive natural flow (`overflow-y: auto` + scroll แนวตั้ง) ตาม [[0013-remove-kiosk-scaling|ADR 0013]]
- `api/server.py`: เพิ่ม route alias `/index.htm` (คง `Cache-Control: no-store` เดิม)
- Deploy ผ่าน `ops/deploy-snc-one-shot.sh --check-tunnel`: backup `.bak.20260907191824` + retention 2 ไฟล์, md5 22/22 ตรงกันหลัง scp

### 2. Visual Check (Headless Chrome/CDP กับ `/dashboard`)

- **Desktop 1440×900**: 30 room cards render, grid 5 คอลัมน์เต็มความกว้าง (การ์ด 249×190px), doc height 2735px = scroll ธรรมชาติ, console errors 0
- **Mobile emulation 390px**: 30 cards, 1 คอลัมน์ (การ์ด 313px), doc height 7004px, console errors 0
- หมายเหตุ: `/` เสิร์ฟ `landing.html` (หน้าโปรโมชัน) — dashboard อยู่ที่ `/dashboard`, `/index.html`, `/index.htm`
- Screenshots: `logs/live_193252_desktop.png`, `logs/live_193256_mobile.png`

### 3. Test Suite

- `pytest tests/ pbx/test_smdr_parser.py` → **76 passed + 4 subtests** (รวม `test_dashboard_uses_natural_responsive_layout`)

### 4. Git Sync ฝั่ง Pi (`5f6e3da` → `c0df54a`)

- **ค้นพบ:** Pi เป็น git checkout ที่ HEAD `5f6e3da` (5 ก.ย.) — ตามหลัง local/GitHub หลาย commit
- **สาเหตุ merge abort ซ้ำ ๆ:** `.gitattributes` กำหนด `* text=auto` / `*.js eol=lf` แต่ `OLD_deployed.js` + `app/index.js` ถูก commit เก็บ CRLF ไว้ → บน Linux git เห็น phantom "modified" ถาวร → บล็อก merge ที่แตะไฟล์
- **แก้:** ลบ `app/index.js` (ถูกลบ upstream ใน `cbebdac` อยู่แล้ว) → FF สำเร็จ → renormalize `OLD_deployed.js` CRLF→LF (commit `c0df54a`) → Pi `reset --hard origin/main` (state ก่อนหน้าไร้ค่า 100%) → phantom หาย
- Commit chain ฝั่ง Git: `cbebdac` (kiosk removal + `/index.htm`) → `3a3636d` (timeline entry) → `c0df54a` (renormalize OLD_deployed.js)

### 5. Full Repo↔Pi Re-audit

- 223 tracked files: **223/223 content-identical** กับ canonical LF blob (`git cat-file`) — 0 DIFF จริง, 0 MISSING
- 218 byte-identical; 5 ไฟล์เหลือ CRLF working copy บน Pi (`app/demo.html`, `core/download_service.py`, `ops/deploy-to-pi.bat`, `ops/deploy_gcp_cloudrun.ps1`, `packaging/download_manifest.json`) — normalize แล้ว **MATCH กับ blob 100%** = EOL artifact จาก Windows scp เท่านั้น, `git status` สะอาด, ไม่กระทบ runtime

## สถานะ/ข้อควรรู้ต่อเนื่อง

1. ✅ ระบบหลัก (PBX listener, alerting, WS) ไม่ได้ถูก restart — เปลี่ยนเฉพาะ dashboard + routing + git state
2. ⚠️ ไฟล์ 5 รายการบน Pi เป็น CRLF (scp จาก Windows) — git มองว่าสะอาด (clean filter) และเนื้อหา = blob ทุกไฟล์ แต่ md5 raw ต่างกัน → deploy script ครั้งถัดไปจะเตือน drift + scp ทับเป็น CRLF ใหม่ (วัฏจักรเดิมของ workflow)
3. ⚠️ **ADR numbering collision:** มีไฟล์ `doc/adr/0013-*` สองไฟล์ (`0013-antigravity-fabric-wikiskill-loop.md` + `0013-remove-kiosk-scaling.md`) — ควร renumber เป็น 0014/0015 ใน session ถัดไป
4. 📦 backup deploy รอบนี้: `api/server.py.bak.20260907191824`, `app/index.html.bak.20260907191824`, `pbx/snc_pbx_listener.py.bak.20260907191824` (retention จะ prune อัตโนมัติ)

## ไฟล์ที่แก้ (จาก session นี้)

| ไฟล์ | Commit | เรื่อง |
|---|---|---|
| `app/index.html`, `api/server.py` | `cbebdac` | ADR 0013 kiosk removal + route `/index.htm` (deploy ขึ้น Pi รอบนี้) |
| `doc/wiki/project_timeline.md` | `3a3636d` | timeline entry 07 ก.ย. |
| `OLD_deployed.js` | `c0df54a` | renormalize CRLF→LF ตาม `.gitattributes` |
| `doc/wiki/SESSION_HANDOVER_2026-09-07.md` | — | เอกสารฉบับนี้ |

- Previous handover: [[SESSION_HANDOVER_2026-09-05]]
- ADR ที่เกี่ยว: [[0013-remove-kiosk-scaling]] · [[0012-deploy-verify-markers-backup-retention]]
