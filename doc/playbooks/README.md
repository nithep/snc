# doc/playbooks/ — Skills Layer (SOPs & Action Guides)

> ตามสถาปัตยกรรม ADR 0013 — ชั้น **Skills Layer** สำหรับเอกสารปฏิบัติ (SOP / Action Guide)
> ที่ผ่านการกลั่นจาก Fabric Patterns และ **การอนุมัติโดยมนุษย์ (Human Review)** แล้วเท่านั้น

## วัตถุประสงค์

- เก็บเอกสารปฏิบัติที่พร้อมใช้งาน: SOP, Action Guide, Runbook ขั้นตอน
- ต่างจาก `doc/wiki/` (ความรู้/บริบท/อธิบาย) — playbooks คือ **"ทำอย่างไรเมื่อเกิด X"**
  ที่กลั่นจากข้อมูลจริง (traces) เช่น คู่มือแก้ SLA bottleneck, ขั้นตอนตรวจ ward/bed context
- เป็นผลผลิตปลายทางของ Knowledge Loop: `RAW → FAB → (WIKI | PLAYBOOKS)`

## กระบวนการเข้าไฟล์ (บังคับ)

1. **Antigravity Orchestrator** ร่าง artifact (PR draft) จาก Fabric Patterns
2. **มนุษย์ (Head Nurse / System Operator)** review & approve PR
3. หลัง merge → ไฟล์จึงจะถือเป็น playbook ทางการ

> ⚠️ ไฟล์ในไดเรกทอรีนี้ = ผ่าน Human Approval แล้วเท่านั้น
> ห้าม commit artifact ที่ Fabric สร้างแบบไม่ผ่าน review — ดู ADR 0013

## สถานะ

- ไดเรกทอรีใหม่ (Phase 1 — Scaffolding) — ยังไม่มี playbook จริง
- จะมี playbooks แรกเมื่อ Phase 2–4 (Fabric Tools → Raw Traces → Nightly Loop) เสร็จ

## Conventions

- ตั้งชื่อไฟล์ตาม wiki: `SCREAMING_SNAKE_CASE.md` (เช่น `SLA_BOTTLENECK_ACTION_GUIDE.md`)
- ภาษาไทยทางการ, UTF-8 เสมอ (ตาม AGENTS.md)
- ทุก playbook ควรมี: สัญญาณที่ trigger / ขั้นตอน / เกณฑ์ตัดสินใจ / ผู้รับผิดชอบ