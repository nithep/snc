# Smart Nurse Call (SNC) - Phase 1 Implementation Guide

## 📋 ภาพรวม Phase 1: Integration & Signal Processing

Phase นี้มุ่งเน้นการเชื่อมต่อระบบทั้งหมดให้ทำงานร่วมกันได้อย่างสมบูรณ์:
- **PBX Listener** → ดักจับสัญญาณจากตู้ Phonik PBX
- **Backend API** → ประมวลผลและเก็บข้อมูล
- **WebSocket** → ส่งข้อมูลแบบ Real-time
- **Frontend Dashboard** → แสดงผลและแจ้งเตือน

---

## 🚀 ขั้นตอนการติดตั้งและทดสอบ

### 1. ติดตั้ง Dependencies

#### Backend (FastAPI)
```bash
cd api
pip install fastapi uvicorn aiohttp websockets
```

#### PBX Connector
```bash
cd pbx
pip install -r requirements.txt
```

### 2. เริ่ม Backend Server

```bash
cd api
python server.py
```

✅ Backend จะรันที่ `http://localhost:8000`

### 3. เริ่ม PBX Listener

```bash
cd pbx
python snc_pbx_listener.py
```

✅ PBX Listener จะเชื่อมต่อกับตู้ Phonik PBX ที่ `192.168.1.91:23`

### 4. เปิด Frontend Dashboard

เปิดไฟล์ `app/index.html` ในเบราว์เซอร์ หรือใช้ Live Server:

```bash
cd app
npx serve .
```

✅ Dashboard จะเปิดที่ `http://localhost:3000`

---

## 🧪 การทดสอบระบบ

### ทดสอบด้วย Integration Test Script

```bash
cd api
python integration_test.py
```

**การทดสอบจะครอบคลุม:**
1. ✅ Health Check Endpoint
2. ✅ Trigger Bedside Call
3. ✅ Acknowledge Call
4. ✅ Clear Call
5. ✅ Get Recent Events
6. ✅ KPI Analytics

### ทดสอบผ่าน Dashboard (Manual Testing)

1. **จำลองการเรียกข้างเตียง:**
   - กดปุ่ม "เรียกจากห้อง 400" บน Dashboard
   - ตรวจสอบว่าการ์ดเปลี่ยนเป็นสีแดงกะพริบ
   - ตรวจสอบว่ามีเสียงเตือนดังขึ้น

2. **ทดสอบการรับเรื่อง:**
   - กดปุ่ม "กดรับเรื่อง (Acknowledge)"
   - ตรวจสอบว่าการ์ดเปลี่ยนเป็นสีเหลือง
   - ตัวนับเวลาหยุดเดิน

3. **ทดสอบการเคลียร์:**
   - กดปุ่ม "เคลียร์สถานะ (Clear)"
   - ตรวจสอบว่าการ์ดกลับเป็นสีเขียว
   - ตรวจสอบ KPI อัปเดต

---

## 🔍 การตรวจสอบสถานะระบบ

### ตรวจสอบ Backend API

```bash
curl http://localhost:8000/health
```

**Expected Response:**
```json
{
  "status": "healthy",
  "service": "snc-backend",
  "timestamp": "2026-08-04T04:59:37.123456"
}
```

### ตรวจสอบ Events

```bash
curl http://localhost:8000/api/events
```

### ตรวจสอบ KPI

```bash
curl http://localhost:8000/api/analytics/kpi
```

**Expected Response:**
```json
{
  "avg_ack_time_seconds": 15.5,
  "avg_resolution_time_seconds": 120.3,
  "total_events": 25,
  "events_by_type": {
    "CALL_TRIGGERED": 20,
    "ACKNOWLEDGED": 18,
    "CALL_CLEARED": 15
  },
  "sla_compliance_rate": 96.0
}
```

---

## 📊 ตัวชี้วัดความสำเร็จ Phase 1

| ตัวชี้วัด | เป้าหมาย | วิธีการวัด |
|----------|---------|-----------|
| **Event Latency** | < 1 วินาที | วัดเวลาจาก PBX → Dashboard |
| **WebSocket Connection** | Stable | ไม่มีการหลุดระหว่างใช้งาน |
| **API Response Time** | < 500ms | วัดจาก integration test |
| **Temporal Escalation** | ทำงานถูกต้อง | ทดสอบกดซ้ำภายใน 90 วินาที |
| **KPI Calculation** | ถูกต้อง | เปรียบเทียบกับค่าจริง |

---

## ⚠️ การแก้ไขปัญหาเบื้องต้น

### ปัญหา: Backend ไม่เริ่มต้น

**อาการ:**
```
ModuleNotFoundError: No module named 'fastapi'
```

**วิธีแก้:**
```bash
pip install fastapi uvicorn aiohttp
```

### ปัญหา: PBX Listener เชื่อมต่อไม่ได้

**อาการ:**
```
ConnectionRefusedError: [Errno 111] Connection refused
```

**วิธีแก้:**
1. ตรวจสอบว่าตู้ PBX เปิดอยู่และ IP ถูกต้อง (`192.168.1.91`)
2. ตรวจสอบ Firewall ไม่ได้บล็อกพอร์ต 23
3. ทดสอบด้วย Telnet:
   ```bash
   telnet 192.168.1.91 23
   ```

### ปัญหา: WebSocket ขาดการเชื่อมต่อ

**อาการ:**
Dashboard แสดง "Disconnected (Retrying)"

**วิธีแก้:**
1. ตรวจสอบว่า Backend ยังรันอยู่
2. รีสตาร์ท Backend server
3. ตรวจสอบ Browser Console สำหรับ error messages

### ปัญหา: Database Lock

**อาการ:**
```
sqlite3.OperationalError: database is locked
```

**วิธีแก้:**
1. ปิดทุก process ที่เข้าถึง database
2. ลบไฟล์ `nurse_call_events.db` แล้วเริ่มใหม่
3. ใช้คำสั่ง:
   ```bash
   rm nurse_call_events.db
   python server.py  # จะสร้าง database ใหม่
   ```

---

## 📝 บันทึกการเปลี่ยนแปลง (Changelog)

### v1.0.0 - Phase 1 Complete

**新增功能:**
- ✅ PBX Listener ส่ง events ไปยัง Backend API ผ่าน HTTP
- ✅ Backend คำนวณ SLA metrics (Ack Time, Resolution Time)
- ✅ เพิ่ม endpoint `/api/events/clear/{room_id}` สำหรับเคลียร์สถานะ
- ✅ เพิ่ม endpoint `/api/analytics/kpi` สำหรับดูรายงาน KPI
- ✅ เพิ่ม endpoint `/health` สำหรับ health check
- ✅ Frontend แสดง KPI Summary แบบ Real-time
- ✅ Frontend รองรับปุ่ม Clear เพื่อเคลียร์สถานะ
- ✅ Integration Test Script สำหรับทดสอบระบบทั้งหมด

**ปรับปรุง:**
- ✅ Database schema เพิ่ม fields: `ack_time_seconds`, `resolution_time_seconds`, `sla_breached`
- ✅ Event type mapping จาก PBX → Dashboard
- ✅ Auto-reload KPI ทุก 30 วินาที

---

## 🎯 ขั้นตอนถัดไป (Next Steps)

หลังจาก Phase 1 สำเร็จ ให้ดำเนินการต่อด้วย:

1. **Phase 2: KPI Analytics Enhancement**
   - เพิ่มกราฟแสดงแนวโน้ม
   - Export รายงานเป็น Excel/PDF
   - ตั้งค่า Alert เมื่อ SLA breach

2. **Phase 3: Production Deployment**
   - สร้าง systemd service สำหรับ auto-start
   - ตั้งค่า PM2 สำหรับ Backend
   - ทดสอบ crash recovery

3. **Phase 5: Field Testing**
   - ทดสอบกับตู้ PBX จริง
   - วัดผล KPI กับพยาบาลจริง
   - ปรับปรุง UX/UI ตาม feedback

---

## 📞 การติดต่อสนับสนุน

หากพบปัญหาหรือมีคำถาม:
- 📧 Email: [your-email@example.com]
- 💬 Telegram: [your-telegram-handle]
- 📱 LINE: [your-line-id]

---

**เอกสารนี้จัดทำเมื่อ:** 2026-08-04  
**เวอร์ชัน:** 1.0.0  
**สถานะ:** Phase 1 Ready for Testing ✅
