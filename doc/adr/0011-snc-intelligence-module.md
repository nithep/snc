---
title: "ADR 0011 — SNC Intelligence Module: Non-Critical Autonomous Operations"
type: adr
tags: [architecture, intelligence, agents, operations, safety]
---

# ADR 0011 — SNC Intelligence Module: Non-Critical Autonomous Operations

- สถานะ: **Accepted — Phase 1–3 implemented; optional plugin boundary accepted**
- วันที่: 2026-09-02

## บริบท (Context)

SNC ต้องการนำแนวคิด Agents, Loops และ Graphs มาใช้เพื่อช่วยงานวิเคราะห์และดูแลระบบ
โดยไม่เพิ่มความเสี่ยงต่อเส้นทางแจ้งเตือนฉุกเฉินแบบ deterministic ซึ่งประกอบด้วย PBX Listener,
Outbox, Backend, SQLite WAL และ Nurse Station Dashboard

บน Raspberry Pi 4 ทรัพยากรมีจำกัด และข้อมูลเหตุการณ์เป็นข้อมูลสุขภาพ จึงต้องแยกงานอัจฉริยะออกจาก
Critical Path, เริ่มจาก rule-based Python worker ที่เบาและตรวจสอบได้ ก่อนพิจารณา LLM หรือบริการภายนอก

## การตัดสินใจ (Decision)

1. สร้าง `api/services/intelligence/` เป็นโมดูลสำหรับงาน Non-Critical Path เท่านั้น
2. โหลดและ register routes ผ่าน dynamic plugin loader เฉพาะเมื่อ `SNC_INTELLIGENCE_ENABLED=true`; ค่าเริ่มต้นเป็น `false`
3. Core SNC ต้องไม่ import Intelligence ตอน module load และต้องเริ่มทำงานได้หากลบโฟลเดอร์ plugin
4. Phase 1 เริ่มด้วย `OpsSelfHealingAgent` ซึ่งทำงานแบบ polling loop และตรวจสอบ:
   - การเชื่อมต่อ PBX TCP `PBX_IP:PBX_PORT` และ proxy `PROXY_HOST:PROXY_PORT`
   - ขนาด SQLite database/WAL/SHM และพื้นที่ดิสก์
   - สถานะ Backend `/health` และ PBX listener ผ่าน health endpoint เมื่อเรียกได้
5. อนุญาตให้ทำ autonomous action เฉพาะงานที่ reversible และ bounded:
   - ตรวจสอบสถานะและจัดทำ diagnostic report
   - ขอ reconnect PBX ผ่านไฟล์คำขอ (`SNC_RECONNECT_REQUEST_FILE`) เพื่อให้ listener ตรวจพบและปิด session อย่างปลอดภัย
   - retry แบบจำกัดจำนวนและมี cooldown
6. ห้าม Agent สั่ง restart service, clear/ack/modify emergency alert, ลบฐานข้อมูล หรือส่งข้อมูลผู้ป่วยออกภายนอก
7. การแจ้งเตือนใช้ `ops/alerting.py` ที่มีอยู่แล้ว โดย default ปิดไว้ และเมื่อเปิดใช้ต้องผ่าน ledger/dedupe เดิม
8. Agent ต้องไม่ import หรือเรียกใช้ LLM ใน Phase 1 และไม่อยู่ใน request handler หรือ WebSocket loop ของ Backend
9. ทุก output เป็น diagnostic metadata เท่านั้น ไม่บรรจุ payload ผู้ป่วย และไม่ส่งข้อมูลไป endpoint ที่ไม่ได้กำหนด

### Safe Execution Gate

สถานะการกระทำใน Phase 1:

| การกระทำ | สถานะ | เหตุผล |
|---|---|---|
| TCP/HTTP health check | Auto | Read-only และ reversible |
| สร้าง reconnect request | Auto | Bounded; listener เป็นผู้ควบคุม lifecycle |
| Restart systemd service | ห้ามอัตโนมัติ | ผลกระทบภายนอกและอาจรบกวน Critical Path |
| แก้ไข/ลบ Alert | ห้าม | เป็นข้อมูล life-safety |
| ส่งข้อมูลไป Cloud/Telegram | ปิดเป็นค่าเริ่มต้น; ต้องกำหนด env | ต้องมี explicit operational opt-in |

## ผลกระทบ (Consequences)

- งานเฝ้าระวังและกู้คืนการเชื่อมต่อเบื้องต้นแยกจาก Critical Path และทดสอบได้โดยไม่ต้องมี PBX จริง
- ลดความเสี่ยงจากการให้ Agent มีสิทธิ์ restart หรือแก้ไขสถานะเหตุฉุกเฉิน
- มี diagnostic report ที่นำไปต่อยอดให้ Lead/Clinical/Shift Agent ในเฟสถัดไปได้
- การ reconnect request ต้องมี integration hook ฝั่ง listener หรือ system operator นำไปใช้; Agent จะไม่ฆ่า process หรือเขียนคำสั่งเข้าตู้ PBX
- การตรวจ TCP/HTTP เป็น best-effort และไม่ใช่หลักฐานว่า nurse call path ทำงานครบ end-to-end
- ต้องตั้งค่า threshold ให้เหมาะกับ Pi และสภาพแวดล้อมจริงก่อนเปิดเป็น systemd worker

## ทางเลือกที่ไม่ได้เลือก (Alternatives)

- **ให้ LLM อยู่ใน Critical Path** — ปัดตก เพราะ latency, hallucination และความไม่แน่นอน
- **ให้ Agent restart systemd โดยตรง** — ปัดตก เพราะเป็นการกระทำที่มีผลกระทบสูงและอาจทำให้ alert ขาดช่วง
- **ใช้ Message Broker ตั้งแต่ Phase 1** — ปัดตก ตาม ADR 0006; ยังไม่จำเป็นสำหรับ worker แบบ local polling
- **ใช้บริการ SaaS Monitoring ใหม่** — ปัดตก; ใช้ health endpoint และ `ops/alerting.py` ที่มีอยู่ เพื่อลด dependency และปกป้องข้อมูลสุขภาพ

## Phase 2 ที่ดำเนินการแล้ว

- `ClinicalAnalyticsAgent` ตรวจ Frequent Callers และคำนวณ SLA Drift แบบ deterministic
- `ShiftHandoverAgent` สร้างร่างสรุปเหตุการณ์ตามกะ morning/afternoon/night
- Read-only endpoints: `GET /api/intelligence/clinical` และ `GET /api/intelligence/handover`
- ผลลัพธ์ทุกชุดระบุ `requires_human_review` และ handover มีสถานะ `draft`/`filed: false`

## Phase 3 ที่ดำเนินการแล้ว

- Optional plugin boundary: Intelligence routes are dynamically imported only when `SNC_INTELLIGENCE_ENABLED=true`
- Core can run and be tested without the `api/services/intelligence/` directory

- Dashboard `app/index.html` แสดง Smart Insight แบบ asynchronous
- Dashboard มี Shift Handover modal, ตัวเลือกกะ และ copy-to-clipboard สำหรับ draft
- UI ระบุสถานะ read-only/draft และไม่แก้ไข Alert หรือ event data

## ขอบเขตเฟสถัดไป

- Human Review/Approval UI สำหรับการบันทึกหรือส่งต่อ draft อย่างมีผู้อนุมัติ
- การเพิ่ม LLM, Cloud API หรือ outbound notification ต้องมีการทบทวน ADR และ privacy/security review แยกต่างหาก

## ADR ที่เกี่ยวข้อง

- `0004` Outbox + Idempotency
- `0006` Broker + Dual-Pi (อนาคต)
- `0008` System Topology
- `0010` WebSocket Heartbeat
