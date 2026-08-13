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

## 📁 โครงสร้างโฟลเดอร์ (Directory Structure)
- `app/`: Web Dashboard สำหรับเคาน์เตอร์พยาบาล (React/Vite) หน้าตาสวยงามพรีเมียม Dark Mode
- `api/`: API Server (FastAPI / Node.js) จัดการ Business Logic, WebSocket และ FHIR Data Schema
- `pbx/`: สคริปต์ระดับล่างดักจับและแปลโปรโตคอล SMDR/Telnet สัญญาณเรียกจากตู้ Phonik PBX
- `doc/`: เอกสารประกอบโปรเจกต์และการบันทึกสเปกฮาร์ดแวร์

## 🤖 กฎการปฏิบัติตามของ AI Agent (SNC Project Rules)
1. **บทบาทหลัก (Role)**: Senior Software Engineer & Healthcare IoT Specialist
2. **การสื่อสาร (Communication)**: ใช้ภาษาไทยทางการ (Professional Tone) ในเอกสาร โค้ด และ Artifacts
3. **ความปลอดภัยข้อมูลสุขภาพ (Data Standards)**: ออกแบบ Data Payload ให้อยู่ในมาตรฐาน **HL7 FHIR JSON** ตั้งแต่ Day 1 เพื่อเตรียมความพร้อมนำขึ้น GCP Healthcare API / Vertex AI Predictive Analytics ในอนาคต
4. **การเข้ารหัสอักขระ (Strict UTF-8)**: กำหนด Encoding เป็น `utf-8` เสมอในการบันทึกหรืออ่านไฟล์ภาษาไทย
