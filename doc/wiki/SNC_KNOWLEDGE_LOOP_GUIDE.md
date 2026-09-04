---
title: "SNC Knowledge Loop Guide — WikiSkill + Fabric"
type: guide
tags: [fabric, wiki, knowledge-loop, playbook, nightly, adr-0013]
---

# 🔄 SNC Knowledge Loop Guide — WikiSkill + Fabric

> คู่มือการใช้งานกระบวนการกลั่นความรู้ (Vault Distillation) ตามสถาปัตยกรรม
> [[0013-antigravity-fabric-wikiskill-loop|ADR 0013]] — กลั่น Trace Dump (Non-PHI)
> จากระบบ SNC เป็น Wiki/Playbook โดยมี **Human Review เป็นด่านบังคับ** ก่อนเข้าคลังทางการ
> แผนงานเต็ม: [[ROADMAP_ANTIGRAVITY_FABRIC]]

---

## สรุปย่อ

- **Knowledge Loop** คือ pipeline กลั่นความรู้อัตโนมัติ: export traces จากฐานข้อมูล event → สรุปด้วย Fabric Patterns 3 ขั้น → สร้าง draft wiki/playbook รอ human review ก่อน merge เข้า vault
- ข้อมูลที่ป้อน LLM เป็น **Non-PHI เท่านั้น** (whitelist field — ตัด `fhir_payload` ทิ้งเสมอ) และตัวเลขสถิติใช้ค่าที่ **เครื่องคำนวณ (deterministic)** เป็นหลัก ไม่ปล่อยให้ LLM นับเอง
- รันง่ายที่สุดด้วยคำสั่งเดียว: `ops/nightly-kb-loop.sh` (บน Pi ตั้ง cron 02:30 อัตโนมัติ) — artifact ทั้งหมดลง `ops/fabric/drafts/` (gitignored) พร้อมเช็กลิสต์ `REVIEW.md`
- ทุก draft ติดป้าย **DRAFT** — ถือเป็นความรู้ทางการเมื่อผ่าน Human Review (ย้ายไฟล์ → commit → PR → merge) เท่านั้น

## ภาพรวม Pipeline

```text
api/nurse_call_events.db (SQLite WAL)
   │  ① ops/export_traces.py — whitelist Non-PHI field
   ▼
ops/raw/traces-YYYYMMDD.jsonl
   │  ② fabric -p snc-trace-summary   → รายงานสรุป SLA/คอขวด
   │  ③ fabric -p snc-wiki-distill    → ร่างบทความ wiki (DRAFT) ← ได้ stats + รายชื่อ vault ด้วย
   │  ④ fabric -p snc-playbook-draft  → ร่าง SOP/action guide (DRAFT)
   ▼
ops/fabric/drafts/<stamp>-*.md + <stamp>-REVIEW.md   (gitignored)
   │  ⑤ Human Review → ย้ายไป doc/wiki/ หรือ doc/playbooks/ → commit → PR → merge
   ▼
คลังความรู้ทางการของ vault
```

**Fabric Patterns ทั้ง 3** (อยู่ที่ `ops/fabric/patterns/` — โฟลเดอร์ละ `system.md`):

| Pattern | บทบาท (persona) | ผลลัพธ์ |
|---|---|---|
| `snc-trace-summary` | Data Analyst ศูนย์ควบคุม SNC | ภาพรวม event · ตารางสถิติ SLA (mean/p95/max) · จุดคอขวด · ความเสี่ยง |
| `snc-wiki-distill` | Librarian (OKF Protocol) | บทความ wiki กระชับ ภาษาไทยทางการ — รับสถิติอ้างอิง + **รายชื่อเอกสาร vault** ประกอบ (ห้ามเดาวันที่/ลิงก์ตาย) |
| `snc-playbook-draft` | Senior Software Engineer | Action guide: สัญญาณ trigger · ขั้นตอน · เกณฑ์ escalate · ผู้รับผิดชอบ |

## วิธีใช้งาน

### แบบสั่งเดียว (แนะนำ)

```bash
cd ops
./nightly-kb-loop.sh              # ข้อมูล 1 วันที่ผ่านมา (ค่าเริ่มต้น)
./nightly-kb-loop.sh --days 2     # ข้อมูล 2 วันที่ผ่านมา
./nightly-kb-loop.sh --dry-run    # เฉพาะขั้น export — ไม่เรียก Fabric/ไม่ใช้ key
```

- สคริปต์เลือก vendor/model อัตโนมัติจากชนิด key: `sk-or-*` → **OpenRouter** (`meta-llama/llama-3.3-70b-instruct`), key อื่น → **Gemini** (`gemini-2.0-flash`) — ปรับได้ด้วย env `FABRIC_VENDOR` / `FABRIC_MODEL`
- สภาพแวดล้อมที่ปรับได้: `PYTHON_BIN`, `EXPORT_DAYS`, `TRACES_RETENTION_DAYS`, `SNC_ROOT`, `FABRIC_BIN`
- **Housekeeping อัตโนมัติ**: ลบ `traces-*.jsonl` ใน `ops/raw/` ที่เก่ากว่า `TRACES_RETENTION_DAYS` (ค่าเริ่มต้น 14 วัน) — ตั้ง `0` เพื่อปิด auto-delete
- ถ้าไม่มี trace ในช่วง สคริปต์จบสถานะ 0 ทันที (ไม่เรียก Fabric) · ถ้ามีจะเขียน draft + `REVIEW.md` และแจ้ง Telegram (ถ้าติดตั้ง `ops/notify-telegram.sh` ไว้)
- บน Pi ตั้ง cron 02:30 ทุกคืน (ดู [[ROADMAP_ANTIGRAVITY_FABRIC]])

### แบบรันเองทีละ pattern

```bash
# 1) รายงานสรุปจาก traces (non-PHI)
cat ops/raw/traces-20260903.jsonl | fabric -V Gemini -m gemini-2.0-flash -p snc-trace-summary

# 2) กลั่นเป็นร่าง wiki
fabric -V Gemini -m gemini-2.0-flash -p snc-wiki-distill < summary.md

# 3) ร่าง playbook
fabric -V Gemini -m gemini-2.0-flash -p snc-playbook-draft < findings.md

# ตรวจ prompt ที่จะส่ง โดยไม่ต้องใช้ key (smoke test)
cat ops/fabric/samples/sample-traces-live-20260904.jsonl | fabric --dry-run -p snc-trace-summary
```

### ข้อกำหนดเบื้องต้น

1. **Fabric CLI**: `winget install danielmiessler.Fabric` (เวอร์ชันที่ใช้ 1.4.470) — บน Pi ใช้ release `linux_arm64`
2. **ชี้ไปยัง patterns ของโปรเจกต์** ใน `~/.config/fabric/.env`:
   ```
   CUSTOM_PATTERNS_DIRECTORY=D:/snc/ops/fabric/patterns
   ```
3. **API key**: `GEMINI_API_KEY` (จาก `api/.env`) หรือ `OPENROUTER_API_KEY` — key จริงมีบน Pi; ตั้งใน `~/.config/fabric/.env` หรือ env ก็ได้
4. ⚠️ **Gotcha สำคัญ**: ถ้าใช้ key `sk-or-*` (OpenRouter) ต้องใช้ vendor `OpenRouter` และ **unset `GEMINI_API_KEY`** — มิฉะนั้น fabric จะลองเรียก Gemini vendor ก่อนแล้ว error 400 หลุดมาปน stdout (สคริปต์ nightly จัดการให้อัตโนมัติ)
5. ⚠️ **Gotcha Windows**: ใน Git Bash ให้ส่ง `PYTHON_BIN=python` (alias `python3` เป็น Windows Store stub)

## กลไกความปลอดภัย (บังคับตาม ADR 0013)

1. **Non-PHI by construction** — `ops/export_traces.py` export เฉพาะ whitelist (`ts, event_type, room_id, status, ack_seconds, resolution_seconds, sla_breached, source`) · `fhir_payload` ถูกตัดทิ้งเสมอ → ข้อมูลผู้ป่วยไม่มีทางถึง LLM
2. **ตัวเลข deterministic เป็นหลัก** — บทเรียน Phase 5: LLM นับ breach จาก traces ดิบผิด (รายงาน 24–34 จากจริง 51) → แก้โดยให้ `export_traces.py --stats` คำนวณด้วยเครื่องแล้วป้อนเป็น "สถิติอ้างอิง" ส่วนหัวของ input; ทั้ง 3 pattern ถูกสั่งให้ใช้ตัวเลขนั้น ห้ามนับเอง
3. **ห้าม fabricate** — pattern ทุกตัวห้ามเดา/สร้างตัวเลข-วันที่ (ต้องอ้าง `period` จากสถิติอ้างอิง) และห้ามเขียนไฟล์เอง
4. **Human-in-the-loop** — draft ทุกชิ้นลง `ops/fabric/drafts/` (gitignored) ติดป้าย DRAFT · เป็นทางการเมื่อย้ายไป `doc/wiki/`/`doc/playbooks/` และ merge ผ่าน PR เท่านั้น

## บทเรียนจาก live run (2026-09-05) และการ harden

Live run แรกบน Pi (6 records, 1–3 ก.ย.) ตัวเลข SLA ตรง deterministic stats 100% แต่พบจุดอ่อนเชิงรูปแบบใน wiki draft 2 ข้อ จึงปรับ pattern และสคริปต์:

1. **Model เดาปีในชื่อเรื่อง** (`2023-09` ทั้งที่ข้อมูลเป็น 2026-09) → pattern ถูกบังคับให้คัดลอก `YYYY-MM` จาก `period.first` **ตามตัวอักษร** (ค.ศ. เท่านั้น ห้ามแปลง พ.ศ.) และสคริปต์ป้อนสถิติอ้างอิง (มี `period`) เข้าสู่ขั้น wiki-distill ด้วย
2. **Broken wikilink** (`[[สัญญา SLA]]` ไม่มีใน vault) → สคริปต์สร้าง **รายชื่อเอกสารจริง** จาก `doc/wiki/` + `doc/adr/` แล้วป้อนให้ pattern · กฎใหม่: wikilink ได้เฉพาะชื่อในรายการ นอกนั้นเขียนเป็น path ใน inline code
3. Reviewer ควรตรวจ 2 จุดนี้เป็นพิเศษทุกรอบ (ดูเช็กลิสต์ด้านล่าง)

## เช็กลิสต์ Human Review (ต่อรอบ nightly)

1. อ่าน draft ใน `ops/fabric/drafts/` — ตรวจความถูกต้องกับข้อมูลจริง (ตัวเลข SLA ต้องตรงกับ `--stats`)
   - **ตรวจวันที่/ปีในชื่อเรื่องและเนื้อหา** — ต้องตรงกับ `period` ของ traces (กัน model เดาปี)
   - **ตรวจ wikilink ทุกตัว** — ต้องมีไฟล์จริงใน vault (กัน broken link)
2. ถ้าผ่าน: ย้ายไฟล์ไป `doc/wiki/` (ตั้งชื่อ `SNC_<หัวข้อ>.md`) หรือ `doc/playbooks/` (ตั้งชื่อ `SCREAMING_SNAKE_CASE.md`) ตาม convention
3. commit + PR → ทีม review อีกชั้น → merge (ไฟล์ใน `doc/playbooks/` เป็นทางการหลัง merge เท่านั้น)
4. ถ้าไม่ผ่าน: แก้ pattern ใน `ops/fabric/patterns/` หรือทิ้ง draft (drafts/ ไม่ถูก track อยู่แล้ว)

## ผลทดสอบจริงบนเครื่อง dev (2026-09-05)

- `fabric --dry-run` กับ `snc-trace-summary` ผ่าน — แสดง system prompt ตรงตาม pattern, ไม่ต้องใช้ key
- `nightly-kb-loop.sh --dry-run` ผ่าน (`PYTHON_BIN=python`) — จบสถานะ "ไม่มี trace ในช่วง 1 วัน" อย่างถูกต้อง
- DB เครื่อง dev มี 37 events (2026-08-14 → 2026-08-26) · CALL_BEDSIDE 28 / CALL_BATHROOM_EMERGENCY 9 · breach 0 · ack mean 7.4s / resolution mean 15.7s (ต่ำกว่าเป้า SLA ทั้งคู่) — live run เต็มรอบทำบน Pi (key จริง)
- ประสิทธิภาพจาก Phase 5 (Pi): export 111 records < 1s · fabric ~12s/call · loop เต็ม ~38s

## เอกสารอ้างอิง

- [[0013-antigravity-fabric-wikiskill-loop|ADR 0013]] — สถาปัตยกรรม Knowledge Loop
- [[ROADMAP_ANTIGRAVITY_FABRIC]] — แผน 5 เฟส + ข้อค้นพบ Phase 5
- [[0004-outbox-idempotency|ADR 0004]] — ที่มาของ event/SLA fields ใน traces
- `ops/fabric/patterns/README.md` — การติดตั้ง Fabric CLI + มาตรฐาน patterns
- `ops/raw/README.md` — กฎ Non-PHI / นโยบาย gitignore ของ trace dump
- `doc/playbooks/README.md` — กระบวนการ Human Approval ก่อนเข้า playbooks
