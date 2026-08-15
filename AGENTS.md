# โปรเจกต์ Smart Nurse Call (SNC) PoC

## 🏥 บริบทและเป้าหมาย
โปรเจกต์นี้คือ **ระบบ Smart Nurse Call (SNC) PoC** สำหรับโรงพยาบาล/ศูนย์ดูแลผู้ป่วย
ซึ่งดัดแปลงตู้สาขาโทรศัพท์ Phonik PBX (รุ่น DX-32C/80C/144C) และบอร์ด Help Call (Call Station v.107) ให้ทำงานเป็นระบบแจ้งเตือนพยาบาล Real-time ผ่าน Web Application ทันสมัยบน **Raspberry Pi 4**

## 🔄 ขั้นตอนการทำงานหลัก (Core Workflow)
1. **Nurse Call Trigger**: ผู้ป่วยกดปุ่ม/ดึงสวิทช์ฉุกเฉิน (NCX-CORD / NCX-PULL) หรือยกหูโทรศัพท์จากห้องพัก
2. **PBX Event Capture**: ตู้ Phonik PBX พ่น Real-time SMDR Log (`==SMDX... e.400 ...`) ผ่าน TCP Telnet (IP: `192.168.1.91:23`)
3. **Backend Event Processing**: `snc_pbx_listener` สกัดเบอร์ห้องและประเภท Event แปลงเป็น FHIR JSON Standard แล้วบันทึกลง SQLite (`nurse_call_events.db`)
4. **Real-time Alerting**: Backend ส่ง WebSocket กระจายสัญญาณ Alert ไปยัง Nurse Station Dashboard
5. **Nurse Dashboard Response**: หน้าจอเคาน์เตอร์พยาบาลแสดง Grid ห้องพัก (เขียว=ปกติ, แดงกะพริบ=ฉุกเฉิน, เหลือง=รับเรื่องแล้ว) เล่นเสียงเตือน Alarm และจับเวลา Response Time จนกว่าพยาบาลจะกด Acknowledge/Clear

## 📁 โครงสร้างโฟลเดอร์ (Directory Structure — 5-Core Standard Layout)
- `api/`: API Server (FastAPI + SQLite WAL + WebSocket) — Business Logic, FHIR Data Schema, SLA/KPI
- `app/`: Nurse Dashboard (`index.html` self-contained, Dark Mode พรีเมียม, i18n ไทย/อังกฤษ)
- `pbx/`: SMDR/Telnet Edge Listener (`snc_pbx_listener.py`) + parser tests + TCP proxy พอร์ต 2323
- `ops/`: DevOps scripts (deploy, burn-in monitor, backup DB, cron, ตรวจสอบสถานะ Pi)
- `doc/`: เอกสาร OKF (คู่มือ + SOP + `wiki/` knowledge base)
- 📘 **Blueprint ฉบับสมบูรณ์**: [`doc/BLUEPRINT_5CORE.md`](doc/BLUEPRINT_5CORE.md) — Vault 5-C, Deploy Workflow, Conventions (ใช้เป็นมาตรฐานทุกโปรเจกต์)

## 🤖 กฎการปฏิบัติตามของ AI Agent (SNC Project Rules)
1. **บทบาทหลัก (Role)**: Senior Software Engineer & Healthcare IoT Specialist
2. **การสื่อสาร (Communication)**: ใช้ภาษาไทยทางการ (Professional Tone) ในเอกสาร โค้ด และ Artifacts
3. **ความปลอดภัยข้อมูลสุขภาพ (Data Standards)**: ออกแบบ Data Payload ให้อยู่ในมาตรฐาน **HL7 FHIR JSON** ตั้งแต่ Day 1 เพื่อเตรียมความพร้อมนำขึ้น GCP Healthcare API / Vertex AI Predictive Analytics ในอนาคต
4. **การเข้ารหัสอักขระ (Strict UTF-8)**: กำหนด Encoding เป็น `utf-8` เสมอในการบันทึกหรืออ่านไฟล์ภาษาไทย
5. **ห้ามใช้ pattern `*key*`/`*secret*` ใน .gitignore**: pattern แบบกว้างจะกลืนเอกสาร legit (เช่น `SNC_API_KEY_ROTATION_GUIDE.md` เคยถูก ignore เงียบๆ ไม่เคย commit) — ให้ใช้แบบเจาะจง (`*.key`, `*.pem`, `*.p12`, `*.pfx`, `*service-account*.json`, `*credentials*.json`) แล้วตรวจ `git status --ignored` ว่ามีไฟล์ที่ควร track โดนกลืนไหม
6. **ทุกโปรเจกต์ต้องมีคู่มือ rotate key**: สร้าง `doc/wiki/*_ROTATION_GUIDE.md` (เช่น [`SNC_API_KEY_ROTATION_GUIDE.md`](doc/wiki/SNC_API_KEY_ROTATION_GUIDE.md)) ครอบคลุม Pi/Server, Cloud Run, และ Client — ทุกครั้งที่เพิ่ม service ที่มี secret
