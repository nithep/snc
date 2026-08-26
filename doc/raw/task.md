# Task List: SNC Mode Isolation & Simulation Bar

- `[ ]` 🧪 สร้างหน้าจอสาธิตระบบพร้อมแถบจำลองขั้นตอนจริง (`app/demo.html`)
  - `[ ]` คัดลอกโครงสร้างหลักจาก `app/index.html` ไปยัง `app/demo.html`
  - `[ ]` เพิ่ม HTML โครงสร้างสำหรับ Simulation Bar ที่ส่วนล่างสุดของจอ
  - `[ ]` เพิ่ม CSS สไตล์สีสันปุ่ม (แดง, ส้ม, เขียว, ม่วง) ให้สวยงามสอดคล้องกับภาพ mockup
  - `[ ]` กำหนดค่า `cfg.sourceMode = 'demo'` แบบถาวรและเอาโค้ดตรวจสอบ UTM params ออก
  - `[ ]` อัปเดต UI Badge บอกสถานะ [โหมดสาธิตจำลอง / DEMO MODE] ด้านข้างโลโก้แบรนด์
  - `[ ]` เขียนสคริปต์ JavaScript ใน demo.html เพื่อรองรับปุ่มกดจำลองทีละขั้น (Trigger Bedside, Trigger Bathroom, Acknowledge, Clear)
  - `[ ]` เขียนสคริปต์ JavaScript ใน demo.html สำหรับปุ่ม "Fast SLA Test" (รันลูปออโต้ตามหน่วงเวลา 4 วิ -> 5 วิ) พร้อมแจ้งความคืบหน้าผ่าน toast
- `[ ]` 🖥️ ปรับปรุง Dashboard ระบบจริง (`app/index.html`)
  - `[ ]` กำหนดค่า `cfg.sourceMode = 'real'` แบบถาวรและเอาโค้ดตรวจสอบ UTM params ออก
  - `[ ]` ลบปุ่มจำลองเดิม `#demoTestBtn` ออกจาก HTML
  - `[ ]` ลบคอนฟิกและการแสดงผล Badge สำหรับโหมดสาธิต เหลือเพียงป้ายสีเขียว [ระบบจริง (Production)] ถาวร
- `[ ]` 🌐 อัปเดตลิงก์แนะนำสินค้า (`app/landing.html`)
  - `[ ]` แก้ไขลิงก์ Call to Action และปุ่มดู Dashboard ตัวอย่างให้ชี้ไปที่ `demo.html` แทน `index.html?utm_source...`
- `[ ]` 🧪 การทดสอบและบันทึกความคืบหน้า (Verification)
  - `[ ]` ตรวจสอบความถูกต้องของสคริปต์และการจำลองลูปอัตโนมัติ (Fast SLA Test)
  - `[ ]` ตรวจสอบสลักและ parser ใน API ว่าไม่มีข้อผิดพลาด
  - `[ ]` จัดทำหรืออัปเดตไฟล์ `walkthrough.md` เพื่อสรุปการเปลี่ยนแปลง
