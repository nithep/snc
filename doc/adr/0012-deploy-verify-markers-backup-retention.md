---
title: "ADR 0012 — Deploy Verify Markers + Backup Retention ใน One-Shot Deploy"
type: adr
tags: [architecture, deploy, verification, backup, drift-detection]
---

# ADR 0012 — Deploy Verify Markers + Backup Retention ใน One-Shot Deploy

- สถานะ: **Accepted**
- วันที่: 2026-09-03

## บริบท

`ops/deploy-snc-one-shot.sh` คือเครื่องมือ deploy หลักขึ้น Raspberry Pi 4 (22 ไฟล์/รอบ)
พบปัญหา 2 ประการจากการใช้งานจริง:

1. **Verify marker หมดอายุแบบเงียบ** — step 7 (verify) เคย grep `"SNC v2.0"` ใน
   `app/index.html` ที่ deploy ไป แต่ข้อความนี้ไม่มีอยู่ในไฟล์ปัจจุบันแล้ว
   ผลคือทุก deploy รายงาน `v2 markers found: 0` โดยไม่มีใครรู้ว่าหมายถึง
   "ไฟล์เก่า" หรือ "marker หมดอายุ" — ตรวจพบจริงเมื่อ verify หลัง deploy
   kiosk fit-to-screen v2 (commit `3c4463f`) แสดง 0 ทั้งที่ deploy สำเร็จ
2. **Backup สะสมไม่จำกัด** — ทุกรอบ deploy สร้าง `*.bak.<timestamp>` ใหม่
   3 ไฟล์ (server.py / index.html / snc_pbx_listener.py) โดยไม่มีการเก็บกวาด
   สะสมจริง **27 ไฟล์** บน Pi ก่อนทำ cleanup เมื่อ 3 ก.ย. 2569

ปัญหาทั้งสองมีลักษณะเดียวกัน: **กลไกป้องกันความเสี่ยงเองกลายเป็น dead code
โดยไม่มีสัญญาณเตือน** (marker ที่ grep ไม่เจออะไรเลย = ไม่เคย fail = ไม่มีประโยชน์)

## การตัดสินใจ

### 1) Verify markers ผูกกับเวอร์ชันจริงของไฟล์

- Step 7 ตรวจด้วย marker ที่**มีอยู่จริงในโค้ดปัจจุบัน**:
  ```bash
  FTS_V2=$(grep -cE "Math\.min\(1\.3|usableHf|--scale-origin" "${REMOTE_ROOT}/app/index.html" 2>/dev/null || true)
  echo "fitToScreen v2 markers: ${FTS_V2:-0} (คาดหวัง >= 3)"
  # WARN เมื่อ 0 → ไฟล์บน Pi อาจยังเป็นเวอร์ชันเก่า
  ```
- เลือก grep **นับจำนวน marker ในไฟล์ปลายทางบน Pi** (ไม่ใช่เทียบ md5 ทั้งไฟล์)
  เพราะ: ตรวจสอบได้ทันทีว่า "ไฟล์ที่บินขึ้นไป" คือเวอร์ชันที่มีฟีเจอร์ที่ต้องการ
  โดยไม่พึ่ง git บน Pi (Pi ไม่มี working clone)

### 2) Backup retention ในตัว deploy script

- หลังสร้าง backup ของรอบ (step 3) ทำ pruning ทันทีต่อไฟล์:
  ```bash
  for p in "$REMOTE_BASE/server.py" "$REMOTE_BASE/../app/index.html" \
           "$REMOTE_BASE/../pbx/snc_pbx_listener.py"; do
    ls -t "$p".bak.* 2>/dev/null | tail -n +3 | xargs -r rm -f
  done
  ```
- **เก็บล่าสุด 2 ไฟล์ต่อ base file** — เพียงพอสำหรับ rollback ทันที 1 ขั้น
  (backup ก่อนหน้า + backup ก่อนโค้ดปัจจุบัน) โดยไม่สะสมไม่จำกัด
- **จำกัดขอบเขต glob เฉพาะ base file** — ไฟล์อื่น เช่น `storage.py.bak.*`,
  `.env.bak.*` (dotfile, glob ไม่ประทับ) และ one-off backup ไม่ถูกแตะ
- ทดสอบ: `bash -n` (syntax), local simulation (5 backups → เหลือ 2 + ไฟล์แปลกปลอมไม่ถูกลบ),
  no-op บน Pi ภายใต้ `set -e` (glob ว่างต้องไม่ทำ deploy fail — pipeline สุดท้ายคือ `xargs -r` ซึ่ง exit 0)

## ผลกระทบ (Consequences)

- ✅ ผู้ deploy เห็นตัวเลข markers ที่มีความหมายทุกรอบ (`3` = ปกติ, `< 3` = ต้องตรวจ)
- ✅ Backup บน Pi ไม่เกิน 2 ไฟล์ × 3 base file = 6 + one-off เดิม — ไม่ต้องเก็บกวาดมืออีก
- ⚠️ **Marker ผูกกับเนื้อโค้ด** — ครั้งถัดไปที่แก้ `fitToScreen` ต้องอัปเดต grep ใน
  deploy script ด้วย (แลกกับความหมายที่ชัดเจน) — บันทึกใน handover แล้ว
- ⚠️ Retention ทำงานเฉพาะตอน deploy — ถ้ามีกระบวนการอื่นสร้าง `*.bak.*` ใน path เดียวกัน
  จะไม่โดน prune จนกว่า deploy ถัดไป
- ℹ️ ทางเลือกที่พิจารณาแล้วไม่ใช้:
  - *เทียบ md5 ทั้งไฟล์กับ git* — Pi ไม่มี git working clone, เพิ่ม dependency ฟรี
  - *logrotate* — เกินจำเป็นสำหรับไฟล์ 3 ตัว, เพิ่ม moving part บน Pi
  - *ไม่ prune, เขียน cron แยก* — แยกสถานที่เกิดเหตุกับตัวการ (backup เกิดตอน deploy
    ควร prune ตอน deploy), เสี่ยงลืมติดตั้ง cron บนเครื่องใหม่

## ไฟล์ที่เกี่ยวข้อง

- `ops/deploy-snc-one-shot.sh` — step 3 (backup + retention) และ step 7 (verify markers)
- `app/index.html` — ตัว marker ที่ถูกตรวจ (`fitToScreen` v2)
- Commits: `3c4463f` (dashboard v2) · `7c5c696` (markers) · `13d2532` (retention)
