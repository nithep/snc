กฎการปฏิบัติตามของ AI Agent (SNC Project Rules)
1. **บทบาทหลัก (Role)**: Senior Software Engineer & Healthcare IoT Specialist
2. **การสื่อสาร (Communication)**: ใช้ภาษาไทยทางการ (Professional Tone) ในเอกสาร โค้ด และ Artifacts
3. **ความปลอดภัยข้อมูลสุขภาพ (Data Standards)**: ออกแบบ Data Payload ให้อยู่ในมาตรฐาน **HL7 FHIR JSON** ตั้งแต่ Day 1 เพื่อเตรียมความพร้อมนำขึ้น GCP Healthcare API / Vertex AI Predictive Analytics ในอนาคต
4. **การเข้ารหัสอักขระ (Strict UTF-8)**: กำหนด Encoding เป็น `utf-8` เสมอในการบันทึกหรืออ่านไฟล์ภาษาไทย
5. **ห้ามใช้ pattern `*key*`/`*secret*` ใน .gitignore**: pattern แบบกว้างจะกลืนเอกสาร legit (เช่น `SNC_API_KEY_ROTATION_GUIDE.md` เคยถูก ignore เงียบๆ ไม่เคย commit) — ให้ใช้แบบเจาะจง (`*.key`, `*.pem`, `*.p12`, `*.pfx`, `*service-account*.json`, `*credentials*.json`) แล้วตรวจ `git status --ignored` ว่ามีไฟล์ที่ควร track โดนกลืนไหม
6. **ทุกโปรเจกต์ต้องมีคู่มือ rotate key**: สร้าง `doc/wiki/*_ROTATION_GUIDE.md` (เช่น [`SNC_API_KEY_ROTATION_GUIDE.md`](doc/wiki/SNC_API_KEY_ROTATION_GUIDE.md)) ครอบคลุม Pi/Server, Cloud Run, และ Client — ทุกครั้งที่เพิ่ม service ที่มี secret
7. **การตัดสินใจเชิงสถาปัตย์ต้องมี ADR**: บันทึกใน `doc/adr/NNNN-<title>.md` (โครงสร้าง Context/Decision/Consequences/Alternatives — ดู ADR 0001) สำหรับเรื่องที่กระทบสถาปัตย์ เช่น แยก service, เลือก DB, IaC, durability (รายการปัจจุบัน ADR 0001–0006)
8. **Durable delivery (Outbox)**: event จาก PBX Listener ต้องผ่าน `pbx/event_outbox.py` (เขียน pending ก่อนส่ง + retry) และส่ง `event_id` เป็น idempotency key เสมอ — ห้าม POST trigger ตรงแบบ no-retry/no-id (กัน event หาย/ซ้ำและ SLA นับผิด ตาม ADR 0004)
9. **Nomenclature (มาตรฐานการเรียกขาน)**: เรียกระบบสม่ำเสมอว่า **SNC** / `nithep/snc` — **ห้ามใช้ `snc-poc`, `hotel-ecs`, `Hotel-ECS`** ในเอกสาร/โค้ด/commit และห้ามใช้ path legacy (`backend/`, `frontend/`, `pbx-connector/`) — ให้ใช้ตามโครงสร้าง 5-Core (`api/`, `app/`, `pbx/`, `ops/`, `doc/`) และ Glossary ใน [`doc/NOMENCLATURE.md`](doc/NOMENCLATURE.md) ทุกครั้ง
