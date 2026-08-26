# แผนการสร้างหน้าสาธิตจำลองขั้นตอนจริง (Interactive Simulation Bar Plan)

แผนงานนี้ได้รับปรับปรุงเพื่อจำลองขั้นตอนการแจ้งเตือนพยาบาลให้คล้ายของจริงมากที่สุด โดยการนำอินเตอร์เฟส **Simulation Bar** ที่มีสีสันสวยงามตามภาพต้นแบบของผู้ใช้มาติดตั้งไว้ที่ส่วนล่างสุดของหน้าจอสาธิตตัวใหม่ (`demo.html`) และทำการแยกหน้าจอระบบจริง (`index.html`) ออกอย่างสมบูรณ์

---

## Proposed Changes

### 1. 🖥️ ปรับปรุง Dashboard ระบบจริง (`app/index.html`)
- **Lock Mode**: บังคับโหมดทำงานจริง `cfg.sourceMode = 'real'` เสมอ
- **UI Clean-up**:
  - ลบปุ่มทดสอบ `🧪 DEMO` เดิมออกจาก Header
  - ลบโค้ดตรวจสอบ UTM/Query Parameters ส่วนจำลองระบบ
  - แสดงเฉพาะป้ายสถานะ **[ระบบจริง (Production)]** สีเขียวเคียงข้างแบรนด์
  - รับสัญญาณและกรองข้อความ WebSocket เฉพาะข้อมูลสายเรียกของคนไข้จริงจากตู้ PBX (`source="real"`)

---

### 2. 🧪 สร้างหน้าจอสาธิตระบบพร้อมแถบจำลองขั้นตอนจริง (`app/demo.html`) [NEW]
- โคลนโครงสร้างหลักจาก `index.html`
- **Lock Mode**: บังคับโหมดทดสอบ `cfg.sourceMode = 'demo'` ถาวร
- **UI Mode Badge**: แสดงป้ายระบุสถานะสีส้ม **[โหมดสาธิตจำลอง / DEMO MODE]** เคียงข้างแบรนด์
- **Simulation Bar (แถบจำลองขั้นตอนส่วนท้ายของจอ)**:
  เพิ่มแถบควบคุมสไตล์พรีเมียมตามแบบ mockup ด้านล่างสุดของบอร์ด:
  - **ปุ่ม 🚨 กด STA (ห้อง 400)** [สีแดง]: ยิงเหตุการณ์เตือนภัยข้างเตียง (`CALL_BEDSIDE`) ไปที่ห้อง 400
  - **ปุ่ม 🚿 ดึงสายห้องน้ำ (ห้อง 400)** [สีแดง]: ยิงเหตุการณ์ดึงสายฉุกเฉินในห้องน้ำ (`CALL_BATHROOM_EMERGENCY`)
  - **ปุ่ม 📞 พยาบาลยกหูรับสาย (Ack)** [สีส้ม]: ยิงคำสั่งตอบรับสาย (Acknowledge) เพื่อจำลองเวลา SLA
  - **ปุ่ม ✅ พยาบาลกดล้างสาย (Clear)** [สีเขียว]: ยิงคำสั่งเคลียร์สายเรียกตัว (Clear/Resolved)
  - **ปุ่ม ⚡ ทดสอบ SLA ลูปอัตโนมัติ (Fast SLA Test)** [สีม่วง]: จำลองสเต็ปการทำงานเรียลไทม์ต่อเนื่องอัตโนมัติ:
    1. ส่งสัญญาณ Trigger `CALL_BEDSIDE` (ห้อง 400) ทันที
    2. รอ 4 วินาที ➔ ส่งสัญญาณ `NURSE_TALKING` (Ack)
    3. รอ 5 วินาที ➔ ส่งสัญญาณ `CALL_CLEARED` (Clear)
    (แสดงข้อความ Toast ชี้แจงทุกขั้นตอนความคืบหน้าแบบเรียลไทม์)

---

### 3. 🌐 อัปเดตลิงก์แนะนำสินค้า (`app/landing.html`)
- ปรับเปลี่ยนปุ่มกดและลิงก์เดิมที่ชี้ไปหา `index.html` ร่วมกับ UTM parameters ให้วิ่งตรงมาที่หน้าจำลองตัวใหม่ `demo.html`

---

## CSS & HTML Layout สำหรับ Simulation Bar (demo.html)
จะเพิ่ม CSS ที่โดดเด่นเพื่อจัดวางแถบ Simulation Bar ไว้ที่ด้านล่างสุดของหน้าจอ:
```css
.sim-bar {
  position: sticky; bottom: 0; left: 0; right: 0; z-index: 80;
  display: flex; align-items: center; justify-content: center; gap: 0.8rem;
  padding: 0.9rem 1.6rem;
  background: rgba(9, 14, 26, 0.92);
  backdrop-filter: blur(20px);
  border-top: 1px solid var(--stroke-strong);
  box-shadow: 0 -10px 40px -15px rgba(0,0,0,0.7);
  flex-wrap: wrap;
}
.sim-title { font-size: 0.85rem; font-weight: 700; color: var(--text-dim); }
.sim-btn-red { background: linear-gradient(135deg, #ef4444, #b91c1c); }
.sim-btn-orange { background: linear-gradient(135deg, #f59e0b, #d97706); }
.sim-btn-green { background: linear-gradient(135deg, #10b981, #047857); }
.sim-btn-purple { background: linear-gradient(135deg, #8b5cf6, #6d28d9); }
```

---

## Verification Plan

### Manual Verification
1. **หน้าจอสาธิต (demo.html)**:
   - เปิดหน้านี้ ตรวจสอบการแสดงผลของ **Simulation Bar** ด้านล่างสุดว่าตรงกับภาพ mockup หรือไม่
   - ทดสอบกดปุ่ม **กด STA (ห้อง 400)** ➔ ห้อง 400 ต้องกะพริบแดง และไซเรนต้องร้องเตือน
   - ทดสอบกดปุ่ม **พยาบาลยกหูรับสาย (Ack)** ➔ สถานะห้อง 400 ต้องเปลี่ยนเป็นรับเรื่อง (สีเหลือง) และเสียงไซเรนเงียบลง
   - ทดสอบกดปุ่ม **พยาบาลกดล้างสาย (Clear)** ➔ สถานะห้อง 400 ต้องกลับสู่ปกติ (สีเขียว)
   - ทดลองกด **Fast SLA Test** ➔ ต้องรันผ่านทีละขั้นตอนตามหน่วงเวลาที่กำหนดอย่างสมจริง พร้อมบันทึกผลลงตารางประวัติตามเวลาจริง
