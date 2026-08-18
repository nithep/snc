---
title: "SESSION_HANDOVER_2026-08-19 — ย้ายโดเมน nursecall→snc + แก้ backend crash-loop + ตั้งค่า Obsidian/Remotely Save"
type: handover
tags: [status]
---

# SESSION_HANDOVER_2026-08-19 — ย้ายโดเมน + แก้ crash-loop + ตั้งค่า Obsidian/Remotely Save

> จัดทำ: 19 ส.ค. 2569 | ต่อจาก handover 17 ส.ค. (CORS restrict + cloud deploy + offsite backup)

---

## 📊 สถานะระบบ ณ สิ้น session

| ระบบ | สถานะ | หมายเหตุ |
|---|---|---|
| **โดเมนสาธารณะ** | ✅ ใช้ `snc.nithep.com` แล้ว | ย้ายจาก `nursecall.nithep.com` (DNS เก่าถอดแล้ว) |
| **Backend** | ✅ `active` + `/health` 200 (LAN+public) | แก้ crash-loop ได้แล้ว |
| **Cloudflare Tunnel** | ✅ ทำงาน (ผ่านชื่อ service เก่า) | ยังไม่ได้ติดตั้ง unit ใหม่ `snc-cloudflared` ตามมาตรฐาน repo |
| **เอกสาร rotate key** | ✅ ครบ 3 ฉบับ (API/Telegram/Cloudflare) | commit `1bdd3db` |
| **Nomenclature cleanup** | 📄 แผน + ADR 0007 ทำแล้ว | ชื่อ OS/GCP project คงไว้ตาม decision |
| **Obsidian vault** | ✅ ตั้ง root vault + Excluded files | เห็นเฉพาะ `doc/` |
| **Remotely Save (WebDAV)** | ✅ ลบโค้ดออกจาก remote แล้ว | เหลือแค่ `doc/` — ต้องตั้ง regex กันซ้ำ |

---

## ✅ งานที่เสร็จใน session นี้

### 1. ย้ายโดเมน `nursecall.nithep.com` → `snc.nithep.com` (commit `c1c68e6`)
- แทนที่ 62 จุด / 22 ไฟล์ ทั่ว repo (api/ops/docs/packaging)
- Cloudflare + DNS ฝั่งระบบจริงเสร็จ (ตรวจ live: `snc.nithep.com` → 200, `nursecall.nithep.com` → Non-existent)
- บันทึก: `doc/wiki/SNC_DOMAIN_MIGRATION_NOTE.md`

### 2. แก้ backend crash-loop (commit `e6bebe9`)
- **อาการ:** หลัง pull โค้ดใหม่ Pi เกิด `ModuleNotFoundError: No module named 'core'` → restart 81+ ครั้ง → 502
- **สาเหตุ:** `api/server.py` import `core.*` (repo root) แต่ systemd ตั้ง `WorkingDirectory=api` → Python หา `core/` ไม่เจอ
- **แก้:** เพิ่ม repo root เข้า `sys.path` ใน `server.py` (ไม่ยุ่ง WorkingDirectory ที่มีผลต่อ import `services`/`storage`)
- **ผล:** backend `active` + `/health` 200 ทั้ง LAN และ public

### 3. Push commit ค้าง + ตั้งค่า repo
- Push 4 commit ค้างขึ้น origin/main (รวม commit แก้โดเมน) → Pi pull ได้โค้ดใหม่
- Pi ติดตั้ง unit `snc-cloudflared` ยังไม่ได้ (ใช้ service เก่า)

### 4. คู่มือ rotate key + แผน cleanup ชื่อ legacy
- เพิ่ม `SNC_TELEGRAM_ROTATION_GUIDE.md`, `SNC_CLOUDFLARE_ROTATION_GUIDE.md` (commit `1bdd3db`)
- `SNC_NOMENCLATURE_CLEANUP.md` + `ADR 0007` (แยก SNC ออกจาก Hotel-ECS) + บทเรียนวางแผน naming ตั้งแต่เริ่ม (commit `fac1022`, `105dc52`)

### 5. ตั้งค่า Obsidian
- เปิด `D:\snc` เป็น root vault (ชื่อ `snc`, ไม่ชนกับ "doc" ของโปรเจกต์อื่น)
- `Excluded files` (userIgnoreFilters) ซ่อนโฟลเดอร์โค้ด เห็นเฉพาะ `doc/`
- ลบ `doc/.obsidian` (nested vault) เหลือ vault เดียว

### 6. Remotely Save (WebDAV Infini-cloud) — ลบโค้ดออกจาก remote
- **เจอปัญหา:** `Regex Of Paths To Ignore` ไม่กันโค้ดที่ sync ไปแล้ว — `/dav/snc/` มี api/app/ops/... เต็ม
- **ทำ:** ลบโค้ดทั้งหมดบน remote (14 รายการ, ทุกตัว 204) → `/dav/snc/` เหลือแค่ `doc/` (เอกสารครบ: wiki/adr/raw + INDEX/NOMENCLATURE/BLUEPRINT)
- WebDAV connection: `https://hakata.infini-cloud.net/dav/` user `2ndBrain` (Basic header ตรง ถึงได้ 207/204 — `-u` ของ curl ได้ 401)

---

## ⏳ สิ่งค้าง / next steps

### 1. Remotely Save — ตั้ง regex + verify กันโค้ดกลับมา (สำคัญ)
- ไปที่ Settings → Remotely Save → "Regex Of Paths To Ignore" วาง:
  ```
  ^api/  ^app/  ^core/  ^ops/  ^packaging/  ^pbx/  ^Phonik/  ^surfaces/  ^tests/
  ^\.agents/  ^\.venv/  ^\.git/  ^\.github/  ^\.freebuff/  ^\.opencode/  ^\.obsidian/
  ^README\.md$  ^AGENTS\.md$  ^MIGRATION_RUNBOOK\.md$  ^LICENSE$  ^run2\.log$
  ```
- sync ใหม่ + verify `doc/` ยังครบ และไม่มีโค้ดกลับมา

### 2. 🔒 เปลี่ยนรหัส WebDAV `2ndBrain` (สำคัญ — ถูกแชร์ในแชท)
- rotate รหัสหลังจบ session เพื่อความปลอดภัย

### 3. ลบไฟล์ temp รหัสผ่าน
- `C:\Users\Nithep\AppData\Local\Temp\opencode\wdav.xml` มีรหัสผ่าน — ควรลบ

### 4. ติดตั้ง unit `snc-cloudflared` ตามมาตรฐาน repo
- `sudo ./ops/setup-cloudflared.sh --token <TOKEN>` (จาก `SNC_ROOT=/home/ecs-agent/snc`) — ปัจจุบัน tunnel ทำงานผ่านชื่อเก่า ยังไม่เร่ง

### 5. งาน rename `snc-poc` → `snc` (ค้างจาก ADR 0007 / Nomenclature Cleanup)
- แยกเป็นงานเฉพาะ มี maintenance window + backup + rollback (ดู `MIGRATION_RUNBOOK.md`, `SNC_NOMENCLATURE_CLEANUP.md`)

### 6. ตรวจ CORS origins บน Cloud Run (`SNC_ALLOWED_ORIGINS`)
- ให้มี `snc.nithep.com` (เฉพาะเมื่อใช้งาน Cloud Run)

---

## 📌 หมายเหตุการเชื่อมต่อ WebDAV (สำหรับครั้งหน้า)
- Server ที่ถูกต้อง: `https://hakata.infini-cloud.net/dav/`, user `2ndBrain`
- **ต้องส่ง Basic auth เป็น header ตรง** (`Authorization: Basic <b64>`) — ใช้ `curl -u`/pre-auth ได้ 401
- โครงสร้าง remote: `/dav/` มี `snc/`, `2ndBrain/`, `Digital Second Brain/`, `Hotel-ECS/`

---

## 🔍 สถานะ commit (branch `main`, origin synced)
- งานโดเมน: `c1c68e6`, `a799227`, `e6bebe9`
- งาน rotate key: `1bdd3db`
- งาน nomenclature: `fac1022`, `105dc52`

---

*จัดทำโดย: Senior Software Engineer — 19 ส.ค. 2569*