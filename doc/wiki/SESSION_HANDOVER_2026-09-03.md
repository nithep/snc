---
title: "SESSION_HANDOVER_2026-09-03 — Kiosk Fit-to-Screen v2 + Deploy Script Hardening (Verify Markers + Backup Retention)"
type: handover
tags: [status, pi4, dashboard, kiosk, deploy, hardening, backup-retention]
---

# SESSION_HANDOVER_2026-09-03 — Kiosk Fit-to-Screen v2 + Deploy Script Hardening

> จัดทำ: 3 ก.ย. 2569 | ต่อจาก [[SESSION_HANDOVER_2026-09-02]]
> ครอบคลุม: Dashboard kiosk v2 ขึ้น Production, verify markers ใหม่, backup retention — sync ครบ Pi4 + GitHub

## สรุปผู้เบิกจ่าย (Deploy Status)

| สภาพแวดล้อม | สถานะ | หลักฐาน |
|---|---|---|
| **Pi4** (backend + pbx-listener) | ✅ `active,active` | `/health` healthy + md5 `app/index.html` ตรงกับ local |
| **GitHub** (origin/main) | ✅ synced | commit `13d2532` (+`3c4463f`, `7c5c696`, `1079c48`) |
| **Live** (snc.nithep.com) | ✅ = local = GitHub | diff ไฟล์ 0 บรรทัด · `fitToScreen v2 markers: 3` |

## งานที่ทำ

### 1. Kiosk Fit-to-Screen v2 (`app/index.html` — commit `3c4463f`)

- รวม kiosk layout เข้า `body`: `100dvh` + `overflow: hidden` — ลบ duplicate `body` block ที่ตกค้างจากการ merge
- Media queries ใหม่: `1360px` / `640px` / `480px` / `max-height: 760px`
- `fitToScreen()` v2:
  - ใช้ `window.visualViewport.height` (ถูกต้องบน mobile/kiosk ที่ URL bar หด)
  - Cap composite scale ที่ **1.3** (เดิม 2.0 — กัน blur เวลา scale เกินจอใหญ่)
  - `transform-origin` อ่านจาก CSS var `--scale-origin` (default `top center`)
- Smart Insight Panel: แสดง HTTP status/message เมื่อ `/api/intelligence/clinical` ล้มเหลว (เดิมแสดงข้อความกลาง ๆ หาสาเหตุยาก)
- **⚠️ ระวัง:** `app/index.js` ยังมีโค้ด v1 (`Math.min(2, ...)`) ตกค้าง — **ไฟล์นี้ไม่ได้ถูกโหลดโดย index.html** (self-contained) จึงไม่มีผลต่อ Production แต่ห้าม copy ทับ behavior จาก index.js

### 2. Deploy Script Hardening (`ops/deploy-snc-one-shot.sh`)

- **Verify markers (commit `7c5c696`):** grep `"SNC v2.0"` หมดอายุ (นับ 0 เสมอ) → เปลี่ยนเป็น
  `grep -cE "Math\.min\(1\.3|usableHf|--scale-origin"` — คาดหวัง ≥ 3, ต่ำกว่านั้นมี WARN
  → ใช้จับกรณีลืม deploy `app/index.html` ใหม่ (ไฟล์บน Pi ยังเก่า)
- **Backup retention (commit `13d2532`):** หลังสร้าง backup ของรอบ จะ prune
  `ls -t <base>.bak.* | tail -n +3 | xargs -r rm -f` ต่อไฟล์ (`server.py` / `index.html` / `snc_pbx_listener.py`)
  → เหลือล่าสุด 2 ไฟล์เสมอ — ทดสอบแล้วทั้ง local simulation และ no-op บน Pi
  → ไฟล์อื่น (`storage.py.bak`, `landing.html.bak`, `.env.bak`) **ไม่ถูกแตะ** (glob เฉพาะ base file)
- General cleanup ก่อนติดตั้ง retention: prune `*.bak.*` บน Pi **27 → 9 ไฟล์**

### 3. การตรวจสอบ (Verification)

- e2e deploy รอบสุดท้าย: `[OK] Backup สำเร็จ: *.bak.20260903010709 (retention: เก็บล่าสุด 2 ไฟล์ต่อไฟล์)`
- `fitToScreen v2 markers: 3` / md5 local = Pi / services `active,active` / tunnel `/health` healthy
- Headless Chrome (fresh profile = hard refresh): 31 room cards render, `appScale` = `scale(0.37465)` ที่ 1920×1080
  — kiosk พอดี 1 หน้าจอ ไม่ต้อง scroll (เจตนาของระบบ, ไม่ใช่ bug scale เล็ก)
- Screenshots: `%TEMP%\snc_1080.png`, `%TEMP%\snc_768.png` (Windows temp ของเครื่อง dev)

## สถานะ/ข้อควรรู้ต่อเนื่อง

1. ✅ ระบบหลัก (PBX listener, alerting, WS) ไม่ได้แตะ — เปลี่ยนเฉพาะ dashboard CSS/JS + deploy script
2. ⚠️ `app/index.js` (v1 ตกค้าง) — พิจารณาลบหรือ sync กับ v2 ใน session หน้า (dead code แต่เสี่ยงสับสน)
3. ⚠️ ถ้าจะแก้ `fitToScreen` อีก: อย่าลืมอัปเดต marker grep ใน deploy script step 7 ให้ตรงเวอร์ชันใหม่
4. โครงสร้าง deploy ปัจจุบัน: 22 ไฟล์/รอบ, backup auto-prune ทุกครั้ง — ไม่ต้องเก็บกวาดมืออีกต่อไป

## ไฟล์ที่แก้ (จาก session นี้)

| ไฟล์ | Commit | เรื่อง |
|---|---|---|
| `app/index.html` | `3c4463f` | kiosk fit-to-screen v2 |
| `ops/deploy-snc-one-shot.sh` | `7c5c696` | verify markers v2 |
| `ops/deploy-snc-one-shot.sh` | `13d2532` | backup retention |
| `doc/wiki/project_timeline.md` | `1079c48` + session นี้ | timeline entry |

- Previous handover: [[SESSION_HANDOVER_2026-09-02]]
- ADR ที่เกี่ยว: [[0012-deploy-verify-markers-backup-retention]]
