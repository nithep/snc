---
title: "NOMENCLATURE — มาตรฐานการเรียกขานระบบ SNC"
type: doc
tags: [nomenclature, standard, snc]
---

# 📖 NOMENCLATURE — มาตรฐานการเรียกขานระบบ SNC

> เอกสารควบคุมคำศัพท์ (Controlled Vocabulary) เพื่อให้ทุกคน/ทุกเอเจนต์เรียกสิ่งเดียวกันด้วยชื่อเดียวกัน
> ป้องกันความสับสนระหว่าง `snc-poc` / `hotel-ecs` / `Hotel-ECS` / `SNC`
> **ทุกเอกสาร โค้ด commit และบทสนทนา ต้องใช้คำศัพท์ตามเอกสารนี้**

---

## 1. หลักการตั้งชื่อ (Naming Rules)

> [!IMPORTANT] บทเรียนจากโปรเจกต์ (Lesson Learned)
> **วางแผน naming ก่อนเริ่มเขียนโค้ด** — ตั้งชื่อโปรเจกต์/โดเมน/โครงสร้าง/username/hostname/GCP project อย่างจงใจตั้งแต่ **วันแรก** ก่อน commit โค้ดแรก
> ไม่งั้นต้อง "ถอนรากถอนโคน" ชื่อ legacy ทีหลัง ซึ่งแพงมาก (แก้ doc ทำได้ แต่แก้ชื่อ OS/โดเมน/GCP project ต้องมี maintenance window + เสี่ยงระบบ down)
> ตัวอย่างจริงจาก SNC: ใช้ชื่อ `hotel-ecs`/`snc-poc` ตั้งแต่ต้น → ต้องย้ายมาเป็น `snc` ใช้เวลา/ความเสี่ยงมหาศาล (ดู ADR 0007, SNC_NOMENCLATURE_CLEANUP.md)
>
> **หลักการวางแผน naming ล่วงหน้า:**
> 1. เลือก **ชื่อสั้น จำง่าย ไม่ซ้ำซ้อน** ตั้งแต่เริ่ม (เช่น `snc` แทน `snc-poc`)
> 2. กำหนด **namespace ครบชุด** ก่อนเขียนโค้ด: ชื่อโปรเจกต์ / repo / โดเมนย่อย / path / username / hostname / GCP project id / Docker image tag
> 3. **เลี่ยงคำพ้องกับระบบอื่น** ในองค์กร (เช่น `hotel`) — ถ้าจะใช้ต้องแยกชื่อให้ชัด (ADR 0007)
> 4. บันทึก decision นี้ลง **ADR** ตั้งแต่เริ่ม (ADRs ต้น ๆ ควรครอบคลุม naming)

1. **ชื่อโปรเจกต์**: เรียกสม่ำเสมอว่า **SNC** (Smart Nurse Call) หรือ **`nithep/snc`** — ห้ามใช้ `snc-poc`, `hotel-ecs`, `Hotel-ECS`, `HECS` ในบริบท SNC
2. **ไฟล์ใน `doc/wiki/`**: ขึ้นต้นด้วย **`SNC_`** (ยกเว้น handover / timeline / project plan ที่มีชื่อเฉพาะ)
3. **ตัวพิมพ์**: ใช้ **UPPER_SNAKE_CASE** สำหรับไฟล์คู่มือ/SOP (`SNC_DEPLOY_PI4`) — ยกเว้นชื่อเฉพาะ (`project_timeline`, `phonik_nurse_call_knowledge`)
4. **ห้ามใช้ legacy term** ใน vault: `snc-poc`, `hotel-ecs`, `backend/`, `frontend/`, `pbx-connector/`
5. **โครงสร้าง 5-Core** ต้องอ้างด้วยชื่อมาตรฐาน (ตารางด้านล่าง)

---

## 2. ตารางแปลคำ Legacy → SNC (ใช้แทนที่ในเนื้อหา)

| Legacy (ห้ามใช้) | SNC (ใช้แทน) |
|---|---|
| `snc-poc` | `snc` |
| `snc-poc/backend/` | `api/` |
| `snc-poc/frontend/index.html` | `app/index.html` |
| `snc-poc/pbx-connector/` | `pbx/` |
| `snc-poc/backend/services/` | `api/services/` |
| `backend/server.py` | `api/server.py` |
| `backend/storage.py` | `api/storage.py` |
| `pbx-connector/snc_pbx_listener.py` | `pbx/snc_pbx_listener.py` |
| `frontend/index.html` | `app/index.html` |
| `/home/ecs-agent/snc-poc/` | `/home/ecs-agent/nithep/snc/` |
| `hotel-ecs` / `Hotel-ECS` / `HECS` | ระบบโรงแรมคนละตัว (ไม่ใช่ SNC) — อ้างเฉพาะเมื่อพูดถึงระบบโรงแรม |
| `hotel.nithep.com` | ระบบโรงแรม (Hotel-ECS) — ปรากฏใน CORS origins, ไม่ใช่ SNC |
| `hotel-ecs-nithep` | **GCP Project ID เก่า** (terraform/cloudbuild) — คงไว้เป็น legacy id ตาม ADR |

---

## 3. Glossary — ศัพท์เฉพาะระบบ (ให้ความหมายตรงกัน)

| คำ | ความหมาย / ความสัมพันธ์ |
|---|---|
| **`station_ext`** | เลขสาย/เครื่องสถานีจริงจากตู้ PBX (เช่น `401`) |
| **`room_id`** | ห้องที่แสดงบน dashboard (zero-padded 4 หลัก เช่น `0401`) — map มาจาก `station_ext` |
| **`CALL_BEDSIDE`** | สายเรียกข้างเตียง (Normal Call) |
| **`CALL_BATHROOM_EMERGENCY`** | สายฉุกเฉินห้องน้ำ (EMER — ยกระดับจากกดซ้ำใน 90 วิ) |
| **`CALL_CLEARED`** | วางสาย/ล้างสาย — จบ lifecycle |
| **`NURSE_TALKING`** | พยาบาลยกหูรับสาย (ack) |
| **`sourceEventType`** | ประเภทเหตุการณ์ต้นทางที่เก็บใน `extension` (ใช้แยกข้างเตียง vs ห้องน้ำ) |
| **`event_type`** | ชนิดเหตุการณ์ใน DB/KPI (มาจาก `sourceEventType`) |
| **SMDR** | SMDR Log — ประวัติย้อนหลังของตู้ Phonik |
| **RDSS** | Room Display Status — สถานะห้องแบบเรียลไทม์ของตู้ (poll ทุก 3 วิ) |
| **Outbox** | `pbx/event_outbox.py` — durable delivery ก่อนส่ง + retry (ADR 0004) |
| **`X-API-Key`** | header auth สำหรับเขียนข้อมูล (trigger/ack/clear) |
| **`nurse_call_events.db`** | ฐานข้อมูล SQLite หลัก (Pi4) |
| **Ack Time** | เวลาจาก trigger → พยาบาลรับเรื่อง (เป้า ≤ 30 วิ) |
| **Resolution Time** | เวลาจาก trigger → เคลียร์สาย (เป้า ≤ 180 วิ) |
| **SLA Compliance** | อัตราผ่านเกณฑ์ (เป้า ≥ 98%) |

---

## 4. โครงสร้าง 5-Core (อ้างด้วยชื่อนี้เสมอ)

| ชื่อ | Path |
|---|---|
| **api** | `api/` — FastAPI + storage + services + WebSocket |
| **app** | `app/` — Nurse Dashboard v2.0 (`index.html`) |
| **pbx** | `pbx/` — SMDR/RDSS listener + outbox + proxy |
| **ops** | `ops/` — deploy/backup/monitor/verify/IaC |
| **doc** | `doc/` — เอกสาร OKF + wiki + adr |

---

## 5. ข้อบังคับการใช้งาน (For All Agents)

- อ้างอิงระบบด้วย **SNC** หรือ `nithep/snc` เท่านั้น
- ใช้คำศัพท์จาก Glossary ใน §3 อย่างสม่ำเสมอ (ห้ามใช้ชื่ออื่น)
- path ของโค้ด ใช้ตามโครงสร้าง 5-Core ใน §4 (ไม่ใช้ legacy path)
- ไฟล์ legacy ที่อยู่ใน `doc/raw/` เก็บไว้ย้อนดูเท่านั้น — **ไม่ใช้เป็น reference หลัก**
- ถ้าพบ term ที่ไม่อยู่ใน Glossary → เพิ่มลง §3 ก่อนใช้งาน (กันการกระจายของชื่อ)

---

*จัดทำ: 17 ส.ค. 2569 | อัปเดตเมื่อพบศัพท์ใหม่*