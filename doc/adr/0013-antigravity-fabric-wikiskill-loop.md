---
title: "ADR 0013 — Antigravity Orchestrator + Fabric + WikiSkill Knowledge Loop"
type: adr
tags: [architecture, knowledge, fabric, wiki, playbooks, nightly, human-in-the-loop]
---

# ADR 0013 — Antigravity Orchestrator + Fabric + WikiSkill Knowledge Loop

- สถานะ: **Accepted**
- วันที่: 2026-09-04

## บริบท

SNC ผลิตข้อมูล runtime จำนวนมากทุกวัน (SMDR events, SLA timing, telemetry) แต่ความรู้
ที่ได้จากข้อมูลจริงยังกระจายอยู่ตาม session handover / wiki ที่เขียนด้วยมือ — ไม่มีกลไก
**กลั่นข้อมูล → ความรู้** แบบอัตโนมัติที่ต่อเนื่อง และไม่มีช่องทางให้ทีมปฏิบัติการ (Head Nurse /
System Operator) review ก่อนความรู้ขึ้นเป็นมาตรฐาน

เป้าหมาย: สร้าง **Enriched Intelligence Layer** ที่ไม่แตะ Critical Path (PBX → Listener →
Outbox → API → Dashboard) โดย:
1. Dump traces แบบ **Non-PHI** (event + telemetry) ให้ Fabric ใช้เป็นวัตถุดิบ
2. **Antigravity Orchestrator** รัน Nightly Batch (ผ่าน `/schedule` + Sub-agents)
   กลั่น traces ด้วย **Fabric Patterns** เป็นความรู้ (Wiki Layer) และเอกสารปฏิบัติ (Skills Layer)
3. **มนุษย์เป็น Gate สุดท้าย** — artifact ทุกชิ้นต้องผ่าน PR review + approve ก่อน merge

## การตัดสินใจ

### 1) โครงสร้างไดเรกทอรีใหม่ 3 จุด (ตาม 5-Core)

| Path | บทบาท | Git policy |
|---|---|---|
| `ops/raw/` | Non-PHI Trace Dump (event + telemetry traces) — วัตถุดิบ | **gitignore เนื้อหา** (runtime artifacts, อาจสะสม) |
| `ops/fabric/patterns/` | Fabric Patterns — นิยามวิธีกลั่น traces | **commit** (ออกแบบโดยคน/Agent, เป็นมาตรฐาน) |
| `doc/playbooks/` | Skills Layer — SOPs & Action Guides หลัง Human Approval | **commit** (ผ่าน review แล้วเท่านั้น) |

- `doc/wiki/` (เดิม) = Wiki Layer — ความรู้/บริบท/คำอธิบาย
- `doc/playbooks/` (ใหม่) = Skills Layer — "ทำอย่างไรเมื่อเกิด X" — แยกหน้าที่กับ wiki
- เพิ่มรายละเอียดใน `ops/raw/README.md`, `ops/fabric/patterns/README.md`, `doc/playbooks/README.md`

### 2) นโยบาย Trace: Non-PHI เท่านั้น + ไม่แตะ Critical Path

- แหล่ง traces: สำเนาจาก `pbx/event_outbox.py` (Non-PHI trace dump) + telemetry ระบบ
- ห้ามข้อมูล PHI/PDPA-sensitive: ไม่มีชื่อ-นามสกุลผู้ป่วย, HN, อาการ, FHIR Patient resource ดิบ
- อนุญาต: event type, room ID (ตัวเลขห้อง), SLA timing, aggregate ระดับกลุ่มห้อง
- เส้นทางข้อมูล Critical Path (outbox → API → dashboard) ไม่ถูกดัดแปลงเพื่อรองรับ trace dump

### 3) กระบวนการ Knowledge Loop (WikiSkill Loop)

```
outbox/telemetry ──► ops/raw/ (non-PHI) ──► Fabric Patterns (ops/fabric/patterns/)
                                              │
                                              ├─► doc/wiki/ (กลั่นความรู้/บริบท/SLA bottlenecks)
                                              └─► doc/playbooks/ (ร่าง SOP/Action Guide)
                                              │
                                              ▼
                                    PR draft (มนุษย์: Head Nurse / System Operator)
                                              │
                                    review & approve ──► merge ──► playbooks เป็นทางการ
```

- **Antigravity Orchestrator** (รันผ่าน `/schedule` + Sub-agents) ทำ Nightly Batch:
  กลั่น traces ด้วย Fabric CLI → สร้าง PR draft
- **Human Approval Gate บังคับ**: Agent ไม่ merge เอง — ทุก PR ต้องมีคน approve
  (สอดคล้องกับ Safe Execution Gate ของ ADR 0011)
- ไฟล์ใน `doc/playbooks/` ที่ยังไม่ผ่าน approve = draft — merge แล้วเท่านั้นจึงเป็นทางการ

### 4) Roadmap 5 เฟส (บันทึกเต็มใน `doc/ROADMAP_ANTIGRAVITY_FABRIC.md`)

| เฟส | งาน | วันที่ |
|---|---|---|
| 1 (เฟสนี้) | Scaffolding: ไดเรกทอรี + `.gitignore` + ADR 0013 | 2026-09-04 |
| 2 | ติดตั้ง Fabric CLI + ออกแบบ 3 Patterns | after p1 |
| 3 | สคริปต์ Export Traces (Non-PHI) | after p2 |
| 4 | Nightly Batch + Human Review Flow | after p3 |
| 5 | Verification: Browser Subagent + Pi Load Test | after p4 |

## ผลกระทบ (Consequences)

- ✅ ความรู้จากข้อมูลจริง (SLA bottlenecks, ward/bed context) กลั่นต่อเนื่องแบบอัตโนมัติ
- ✅ มนุษย์ยังเป็นผู้ตัดสินใจสุดท้าย — เหมาะกับระบบ life-safety และสอดคล้อง PDPA
- ✅ Critical Path ไม่ถูกรบกวน — trace dump เป็น side-path ที่มี policy ชัดเจน
- ⚠️ ต้องมีวินัย Non-PHI ในการเขียน export script (Phase 3) — ผิดพลาด = ข้อมูลรั่วใน repo
- ⚠️ Nightly Batch ต้องมี monitor (ถ้า loop ตายเงียบ ความรู้จะเก่า) — ตรวจใน Phase 5
- ⚠️ repo อาจโตจาก playbooks/wiki ที่เพิ่มขึ้น — ยอมรับได้ (เอกสาร, ขนาดเล็ก)

## ทางเลือกที่พิจารณาแล้วไม่ใช้ (Alternatives)

- **Auto-merge ไม่มี human gate** — ปฏิเสธ: ความรู้ที่ผิดพลาดในระบบ nurse call มีผลต่อ
  ความปลอดภัยผู้ป่วย; ต้องมีคนรับผิดชอบ (Head Nurse/Operator)
- **เก็บ traces ใน DB อย่างเดียว ไม่มี flat file** — ปฏิเสธ: Fabric ทำงานกับ flat files/
  text ได้ดีที่สุด และ flat file แยกสิทธิ์/cleanup ง่ายกว่า
- **รวม wiki กับ playbooks เป็นที่เดียวกัน** — ปฏิเสธ: คนละประเภท (ความรู้ vs ปฏิบัติ)
  แยกกันเพื่อค้นหา/อนุมัติที่ต่างกัน (playbooks ต้อง human-approved, wiki กลั่นต่อเนื่อง)
- **ไม่ dump traces เลย (ใช้เฉพาะ dashboard KPI)** — ปฏิเสธ: ข้อมูล granular ที่จำเป็น
  สำหรับวิเคราะห์ bottleneck จะหายไป

## ADR ที่เกี่ยวข้อง

- `0004` Outbox + idempotency — แหล่งที่มาของ trace dump (side-path จาก outbox)
- `0011` SNC Intelligence Module — หลักการ Safe Execution Gate / autonomous ops
- `0007` Nomenclature — ทุก path/ชื่อ ต้องเป็นมาตรฐาน SNC/5-Core

## ไฟล์ที่เกี่ยวข้อง

- `ops/raw/README.md` · `ops/fabric/patterns/README.md` · `doc/playbooks/README.md` — โครงสร้างใหม่
- `.gitignore` — นโยบาย ignore `ops/raw/*` (ADR 0013)
- `doc/ROADMAP_ANTIGRAVITY_FABRIC.md` — แผน 5 เฟส (flowchart + gantt)