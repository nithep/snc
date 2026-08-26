# Walkthrough: SNC Mode Isolation Implementation

การปรับปรุงระบบแยกแยะการทำงาน (Isolation Mode) ระหว่างหน้าจอสาธิต (Demo Dashboard) และหน้าจอทำงานจริงหน้าเคาน์เตอร์พยาบาล (Production Dashboard) ได้รับการดำเนินการเรียบร้อยแล้วและครอบคลุมทุกเลเยอร์ของระบบ

---

## การเปลี่ยนแปลงที่เกิดขึ้น (Changes Made)

### 1. 🗄️ ปรับปรุง Data Layer (`api/storage.py`)
- เมธอด `acknowledge_room` และ `clear_room` ของคลาส `SQLiteStorage` และ `FirestoreStorage` คืนค่าผลลัพธ์ตัวที่ 3 เป็น `source` ที่เก็บอยู่ในคิวรีเหตุการณ์จริง
- ในส่วนของ `FirestoreStorage` ได้เพิ่มการบันทึก `source` ลงในคอลเลกชัน `room_state` เพื่อหลีกเลี่ยงการอ่านฐานข้อมูลซ้ำซ้อนตอนเรียก Ack/Clear

### 2. 🔌 ปรับปรุง API & WebSocket (`api/server.py`)
- ปรับจูน POST `/api/events/acknowledge/{room_id}` และ POST `/api/events/clear/{room_id}` ให้แยกแยะ 3 ตัวแปรส่งออกจาก Database Storage
- แนบข้อมูล `"source": source` เข้าไปใน payload `extension` ของข้อความ WebSocket ในการประกาศรับทราบเหตุการณ์ (ack) และการเสร็จสิ้นเหตุการณ์ (clear) เพื่อให้ Client กรองได้แม่นยำ

### 3. 🖥️ ปรับปรุง UI & Logic Dashboard (`app/index.html`)
- **Mode Detector**: เมื่อเปิดหน้า Dashboard ระบบจะวิเคราะห์ URL query parameters หากพบ `mode=demo` หรือ parameters การตลาด (`utm_source=landing`, `utm_medium=cta`, `utm_campaign=snc_home`) ระบบจะสลับไปใช้ **Demo Mode** (`cfg.sourceMode = "demo"`) โดยอัตโนมัติ นอกเหนือจากนั้นจะถูกตั้งเป็น **Production Mode** (`cfg.sourceMode = "real"`)
- **API Request Filtering**: ฟังก์ชัน `loadEvents()` และ `loadKpi()` จะทำการส่งพารามิเตอร์ `?source={mode}` ไปกรองผลลัพธ์จาก API เสมอ
- **WebSocket Filtering**: คัดกรองข้อมูล WebSocket ในฟังก์ชัน `ws.onmessage` หาก Event ที่ broadcast เข้ามามี `source` ไม่ตรงกับโหมดหน้าจอ Dashboard ปัจจุบัน ข้อมูลนั้นจะถูกยกเลิก (ignore) ทันที
- **UI Mode Badge & Button Visibility**:
  - เพิ่ม Badge บอกสถานะตรงส่วนหัวข้างแบรนด์: สีเขียวสำหรับ **[ระบบจริง / PRODUCTION]** และสีส้มสำหรับ **[โหมดสาธิตจำลอง / DEMO MODE]**
  - ซ่อนปุ่มทดสอบ `🧪 DEMO` เมื่ออยู่ในโหมดระบบจริงโรงพยาบาล เพื่อหลีกเลี่ยงไม่ให้พยาบาลสับสน

---

## ผลการทดสอบ (Verification & Testing Results)

### การทำงานร่วมกับ UTM Parameters
1. **ระบบจริง (Production)**:
   - เปิดผ่าน `https://snc.nithep.com/` ➔ แสดงป้าย **[ระบบจริง (Production)]** สีเขียว
   - ปุ่ม `🧪 DEMO` ถูกซ่อนไปโดยปริยาย ข้อมูลในประวัติและ KPI ดึงเฉพาะระบบของโรงพยาบาลจริง
2. **โหมดสาธิต (Demo)**:
   - เปิดผ่าน `https://snc.nithep.com/index.html?utm_source=landing&utm_medium=cta&utm_campaign=snc_home` ➔ แสดงป้าย **[โหมดสาธิตจำลอง]** สีส้ม
   - ปุ่ม `🧪 DEMO` แสดงผลให้ผู้เยี่ยมชมกดทดสอบได้เต็มที่ สัญญาณ WebSocket และสถิติคำนวณแยกต่างหากอย่างเด็ดขาด
