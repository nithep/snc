---
title: "SESSION_HANDOVER_2026-09-05 — Knowledge Loop Live-Run Hardening + Pi Repo Sync"
type: handover
tags: [status, pi4, knowledge-loop, fabric, adr-0013, sync, hardening]
---

# SESSION_HANDOVER_2026-09-05 — Knowledge Loop Live-Run Hardening + Pi Repo Sync

> จัดทำ: 5 ก.ย. 2569 | ต่อจาก [[SESSION_HANDOVER_2026-09-03]] (ไม่มี handover 4 ก.ย.)
> ครอบคลุม: WikiSkill + Fabric (ADR 0013) live run จริง + hardening 3 ชั้น + แก้ sync ของ repo บน Pi — sync ครบ Pi4 + GitHub

## สรุปผู้เบิกจ่าย (Deploy Status)

| สภาพแวดล้อม | สถานะ | หลักฐาน |
|---|---|---|
| **Pi4** (repo `main`) | ✅ synced ที่ `5f6e3da` | md5 `ops/nightly-kb-loop.sh` + pattern ตรงกับ local · services `active,active` · `/health` 200 |
| **GitHub** (origin/main) | ✅ synced | push `c59fe5a..5f6e3da` (3 commits) |
| **Knowledge Loop** | ✅ E2E ผ่าน 2 รอบจริงบน Pi | drafts `20260905-0201` (ก่อน harden) + `20260905-0303` (หลัง harden) |

## งานที่ทำ

### 1. คู่มือ Knowledge Loop (commit `c610b4f`)

- สร้าง [[SNC_KNOWLEDGE_LOOP_GUIDE]] — pipeline / วิธีใช้ / gotchas / เช็กลิสต์ review (หมวดใหม่ใน [[INDEX]])
- แก้ `ops/nightly-kb-loop.sh`: **auto-detect PYTHON_BIN** แบบรันทดสอบจริง (`-c 'import sys'`) — กัน Windows Store `python3` stub ที่โผล่ใน `command -v` แต่ rc≠0 เมื่อรันจริง (Git Bash ต้องใช้ `python`)

### 2. Live run จริงบน Pi + พบจุดอ่อน → Harden (commit `e40ce2e`)

รัน `./nightly-kb-loop.sh --days 3` บน Pi (6 records, 1–3 ก.ย. · breach 4 · ห้อง 0400×3, 0999×1 — 0999 คือห้อง test):
- **ตัวเลขตรง deterministic stats 100%** — กลไก `--stats` จาก Phase 5 ทำงานได้จริง
- **จุดอ่อนที่พบใน wiki draft (รอบ 0201):**
  1. Model เดาปีในชื่อเรื่อง (`2023-09` ทั้งที่ข้อมูลเป็น 2026-09)
  2. Broken wikilink (`[[สัญญา SLA]]` ไม่มีใน vault)
- **แก้ที่ pattern `snc-wiki-distill`:** input เป็น 3 ส่วน (สถิติอ้างอิง + **รายชื่อเอกสารจริงใน vault** + summary) · ชื่อเรื่องต้อง copy `YYYY-MM` จาก `period.first` **ตามตัวอักษร** (ค.ศ. เท่านั้น ห้ามแปลง พ.ศ.) · wikilink ได้เฉพาะชื่อในรายการ นอกนั้นเขียนเป็น inline code path
- **แก้ที่สคริปต์:** ป้อน stats + vault inventory เข้าขั้น wiki-distill · เพิ่ม **traces retention** `TRACES_RETENTION_DAYS` (default 14 วัน, 0 = ปิด) — ลบ `ops/raw/traces-*.jsonl` เก่าอัตโนมัติ (ทดสอบ: ไฟล์ 20 วันถูกลบ, 5 วัน+วันนี้รอด)
- **ยืนยันหลัง harden (รอบ 0303):** ชื่อเรื่อง `SNC_REPORT_2026-09` + วันที่ตรง period ✓ · ลิงก์ 2/3 จริง

### 3. ตรวจ wikilink อัตโนมัติ + ตรวจ cron + Sync Pi repo (commit `5f6e3da`)

- **Wikilink checker:** สคริปต์ตรวจทุก `[[ลิงก์]]` ใน wiki draft เทียบ inventory (`doc/wiki/` + `doc/adr/`) แบบ deterministic (ไม่ผ่าน LLM) แล้วใส่ผลใน `REVIEW.md` (⚠ ลิงก์ตาย → ห้าม merge / ✅ ผ่าน) — validate กับ draft จริง: จับ `SNC_STATUS_LOG` ตัวเดียว
- **Cron 02:30:** รอบเช้าวันนี้ทำงานสะอาด (จบสถานะ "ไม่มี trace 1 วัน" ถูกต้อง — DB ไม่มี event หลัง 3 ก.ย.) ด้วยสคริปต์เวอร์ชันก่อน harden (deploy 03:03 หลัง cron) — **คืนนี้คือรอบแรกของเวอร์ชัน harden**
- **Pi repo sync (อนุมัติแบบ backup branch → pull clean):**
  - Pi เคย **detached HEAD** (`f26e477` — root cause ที่ดูเหมือน "lag 34 commits") + drift ไม่ commit ~273 ไฟล์
  - Snapshot drift → branch **`pi-local-hotfixes-20260905`** (`2b53a8e`, อยู่บน Pi เท่านั้น) → fast-forward `main` สู่ `5f6e3da` (ตั้ง tracking ให้แล้ว)
  - เหลือ branch เก่า `master` (`f26e477`) ให้ลบภายหลัง · residual dirty = `app/index.js`/`OLD_deployed.js` CRLF-normalization noise เท่านั้น

## ⚠️ ข้อควรรู้ต่อเนื่อง (สำคัญ)

1. **Branch `pi-local-hotfixes-20260905` มีไฟล์ secret** (`api/.env.bak.*`, `backups/*.env` ที่เคย untracked บน Pi) — **ห้าม push** ถ้ายังไม่ scrub ตาม [[SNC_API_KEY_ROTATION_GUIDE]]
2. **`[[SNC_STATUS_LOG]]` ที่ model ลิงก์** — ไฟล์จริง (`doc/wiki/SNC_STATUS_LOG.md`) แต่ **untracked บน Pi** (มีใน backup branch) → ตัดสินใจได้ว่าจะ promote เป็นเอกสารจริงหรือให้ checker จับต่อ
3. **Pi drift เดิมทั้งหมดอยู่ใน backup branch** — production บน Pi ตอนนี้รับโค้ดจาก origin/main ตรง ๆ (สะอาด) — ถ้า field fix ไหนยังจำเป็น ต้อง cherry-pick กลับอย่างเป็นทางการ
4. traces ค้างใน `ops/raw/` บน Pi จะถูก retention เก็บกวาดเองตั้งแต่คืนนี้ (เก็บไว้ 14 วัน)
5. งาน dashboard/kiosk ที่ค้างจาก [[SESSION_HANDOVER_2026-09-03]] (`app/index.js` v1 dead code, ไฟล์ modified ค้างที่เครื่อง dev: `api/server.py`, `app/index.html`, ADR 0013-draft) — **ยังไม่ได้แตะ** ใน session นี้

## Commits ของ session นี้ (push แล้ว)

| Commit | เรื่อง |
|---|---|
| `c610b4f` | docs(kb): Knowledge Loop usage guide + PYTHON_BIN auto-detect |
| `e40ce2e` | fix(kb): harden wiki-distill pattern + traces retention |
| `5f6e3da` | feat(kb): auto-check draft wikilinks against vault inventory in REVIEW.md |

## ไฟล์ที่แก้ (จาก session นี้)

- **ใหม่:** `doc/wiki/SNC_KNOWLEDGE_LOOP_GUIDE.md`, `doc/wiki/SESSION_HANDOVER_2026-09-05.md` (ไฟล์นี้)
- **แก้:** `ops/nightly-kb-loop.sh` · `ops/fabric/patterns/snc-wiki-distill/system.md` · `doc/INDEX.md` · `doc/wiki/INDEX_TIMELINE.md`
- **deploy บน Pi แล้ว:** สคริปต์ + pattern (md5 ตรง local) — backup `.bak.20260905*` ค้างบน Pi 3 ไฟล์

## งานต่อไปที่ค้าง (ให้ session หน้า pick up)

- [ ] เช็ก cron 02:30 คืนนี้ (`tail /home/ecs-agent/snc/logs/nightly-kb-loop.log`) ยืนยัน harden เวอร์ชันรัน unattended ได้
- [ ] ตัดสินใจ `SNC_STATUS_LOG.md`: promote เข้า vault จริง หรือทิ้ง (checker จะจับซ้ำถ้าไม่แก้)
- [ ] Triage `pi-local-hotfixes-20260905` — cherry-pick field fix ที่ยังจำเป็นเข้า main (แบบ scrub secret ก่อน)
- [ ] ลบ branch `master` ที่ Pi (ถ้ายืนยันว่าไม่ต้องการ)
- [ ] งานค้าง dashboard จาก 3 ก.ย. + ไฟล์ modified ค้างที่เครื่อง dev
- [ ] พิจารณาแก้ pattern `snc-playbook-draft` — live run ออกบทบาท "ผู้ดูแลห้อง" ที่ไม่ใช่บทบาทมาตรฐาน SNC (ควรเป็น Head Nurse / System Operator)
