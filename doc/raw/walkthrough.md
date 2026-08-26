# Walkthrough: SNC Mode Isolation & Simulation Bar

การปรับปรุงระบบแยกแยะการทำงาน (Mode Isolation) ฉบับสมบูรณ์ ระหว่างหน้าจอสาธิต (`app/demo.html`) และหน้าจอทำงานจริงหน้าเคาน์เตอร์พยาบาล (`app/index.html`) ได้รับการดำเนินการเรียบร้อยแล้ว โดยยกเลิกกลไกตรวจจับโหมดผ่าน URL parameters เดิม และเปลี่ยนมาใช้ **ไฟล์หน้าจอแยกกันโดยสมบูรณ์** พร้อมแถบจำลองขั้นตอนจริง (Simulation Bar) สำหรับงานสาธิต

---

## การเปลี่ยนแปลงที่เกิดขึ้น (Changes Made)

### 1. 🧪 หน้าจอสาธิตใหม่ `app/demo.html`
- คัดลอกโครงสร้างหลักทั้งหมดจาก `app/index.html` (Dashboard v2.x self-contained: KPI, Room Grid, Event History, i18n ไทย/อังกฤษ, Settings Modal)
- กำหนด `cfg.sourceMode = 'demo'` แบบถาวรในโค้ด — **ตัดการตรวจสอบ UTM params / `?mode=demo` ออกทั้งหมด**
- Badge สถานะสีส้ม **[โหมดสาธิตจำลอง / Demo Simulation Mode]** แสดงถาวรข้างโลโก้แบรนด์
- **Simulation Bar** ติดอยู่ด้านล่างสุดของจอ (sticky bar, Glassmorphism) ประกอบด้วยปุ่มสีจัดตาม mockup:
  - 🔴 **กด STA (ห้อง 400)** — POST `/api/demo/trigger` (`CALL_BEDSIDE`)
  - 🔴 **ดึงสายห้องน้ำ (ห้อง 400)** — POST `/api/demo/trigger` (`CALL_BATHROOM_EMERGENCY`)
  - 🟠 **พยาบาลยกหูรับสาย (Ack)** — POST `/api/events/acknowledge/0400`
  - 🟢 **พยาบาลกดล้างสาย (Clear)** — POST `/api/events/clear/0400`
  - 🟣 **Fast SLA Test** — รันลูปอัตโนมัติ Trigger ➔ หน่วง 4 วินาที ➔ Ack ➔ หน่วง 5 วินาที ➔ Clear พร้อมแจ้งความคืบหน้าทีละขั้นผ่าน Toast และล็อกปุ่มทั้งแถบระหว่างรัน (กันกดซ้ำ)

### 2. 🖥️ Dashboard ระบบจริง `app/index.html`
- กำหนด `cfg.sourceMode = 'real'` แบบถาวร — ตัดโค้ดตรวจสอบ UTM params / query params สำหรับสลับโหมดออกทั้งหมด
- ลบปุ่มจำลองเดิม `#demoTestBtn` ออกจาก HTML แล้ว (ไม่มี handler ตกค้าง)
- Badge แสดงผลเป็นป้ายสีเขียว **[ระบบจริง (Production)]** ถาวร ฟังก์ชัน `updateModeIndicator()` ไม่มีเงื่อนไขสลับโหมดอีกต่อไป

### 3. 🌐 ลิงก์แนะนำสินค้า `app/landing.html` และ `app/roi.html`
- ลิงก์ Call to Action ทั้ง 3 จุดของ Landing Page ("เปิด Nurse Station Dashboard", "ดู Dashboard ตัวอย่าง", "เปิด Dashboard ทดลองใช้") เปลี่ยนจาก `index.html?utm_source=...` ไปชี้ที่ **`demo.html`** ตรง ๆ
- ปุ่ม "ดู Dashboard ตัวอย่าง" ในบทความ ROI (`app/roi.html`) ปรับชี้ `demo.html` เช่นเดียวกันเพื่อความสม่ำเสมอของ Funnel การตลาด

### 4. 🗄️ Data Layer & API (รักษาเดิมจาก iteration ก่อน — ใช้งานได้จริง)
- Event ทุกประเภทประทับตรา `source` (`"real"` | `"demo"`):
  - `/api/demo/trigger` (สาธารณะ ไม่ต้องใช้ API Key) → **บังคับ `source="demo"` เท่านั้น**
  - `/api/events/trigger` (Edge Listener, ต้องมี `X-API-Key`) → `source="real"`
- GET `/api/events?source=` และ GET `/api/analytics/kpi?source=` กรองตามโหมด — **KPI เริ่มต้นนับเฉพาะ `real` เสมอ**
- POST acknowledge/clear แนบ `extension.source` ลง WebSocket broadcast เพื่อให้ Client กรองได้แม่นยำ

---

## ผลการทดสอบ (Verification & Testing Results)

1. **Syntax สคริปต์ฝั่ง Client**: extract inline `<script>` จากทั้ง 2 ไฟล์ parse ด้วย Node.js — **ผ่านทั้งคู่ ไม่มี syntax error**
2. **Parser Tests**: รัน `python pbx/test_smdr_parser.py` — **ผ่าน 28/28 OK** (SMDR/RDSS/watchdog/proxy emulation)
3. **API Smoke Test (Fast SLA Loop จำลองตาม demo.html)**:
   - POST `/api/demo/trigger` (ไม่ใช้ Key) → response `extension.source = "demo"` ✅
   - Ack หลัง 4 วินาที → `ack_time_seconds` ถูกคำนวณ ✅
   - Clear หลัง 5 วินาที → `resolution_time_seconds` + `sla_breached=false` ครบ, Event สถานะ `resolved` ✅
   - GET `/api/events?source=demo` เห็นเหตุการณ์ / `?source=real` = 0 รายการ (**isolation สมบูรณ์**) ✅
   - GET `/api/analytics/kpi` (default `real`) → `total_events=0` — เหตุการณ์ demo **ไม่บิดเบือน KPI ระบบจริง** ✅
   - WebSocket client เชื่อมต่อ `/ws/nurse-station` รับ broadcast ทันทีพร้อม `extension.source="demo"` — filter ใน `ws.onmessage` ของทั้ง 2 หน้าทำงานถูกต้อง ✅

## สรุป Flow การใช้งาน (Usage Flow)

```
Landing Page ──CTA──► demo.html  [โหมดสาธิตจำลอง] ──► /api/demo/trigger ──► source="demo"
หน้างานโรงพยาบาล ────► index.html [ระบบจริง]      ◄── PBX Listener ─────► source="real"
```

- ผู้เยี่ยมชม/การตลาด: ใช้ `demo.html` กดจำลองทีละขั้นหรือรัน Fast SLA Test — ข้อมูลแยกจากระบบจริงเด็ดขาด
- พยาบาลหน้างาน: ใช้ `index.html` — ไม่มีปุ่มทดสอบหลงเหลือ, เห็นเฉพาะสัญญาณจากตู้ Phonik PBX
