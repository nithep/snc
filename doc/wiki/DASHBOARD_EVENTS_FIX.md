# SMDR Events Not Displaying on Dashboard - Diagnosis & Fix

## ปัญหา (Problem)

SMDR records จาก Phonik PBX ถูกต้องและมี prefix `==SMDX` แต่**ไม่แสดงบนหน้า dashboard**:

```
==SMDX2025=10/08/26 14:54 401 e.400 EC 0:00'05 0 #1
==SMDX2026=10/08/26 17:21 401 e.400 EC 0:00'10 0 #1
==SMDX2027=10/08/26 21:04 401 e.400 EC 0:00'08 0 #1
==SMDX2028=10/08/26 22:15 401 e.400 EC 0:00'04 0 #1
```

## สาเหตุที่เป็นไปได้ (Root Causes)

### 1. **Event ID Collision** (แก้ไขแล้ว ✅)

**ปัญหา**: Event ID ใช้ timestamp เป็นวินาที (`int(datetime.now().timestamp())`) ทำให้ events ที่เกิดขึ้นในวินาทีเดียวกันมี ID ซ้ำกัน

```python
# เดิม (มีปัญหา)
"id": f"snc-event-{formatted_room}-{int(datetime.now().timestamp())}"

# ใหม่ (แก้ไขแล้ว)
"id": f"snc-event-{formatted_room}-{int(time.time() * 1000000)}"  # microseconds
```

เนื่องจากใช้ `INSERT OR REPLACE` ใน SQL, event ใหม่จะ replace event เก่าแทนที่จะเพิ่ม record ใหม่

**ไฟล์ที่แก้ไข**: [`server.py`](file://c:\Users\Nithep\ไดรฟ์ของฉัน%20(cnithep@gmail.com)\Hotel-ECS\snc-poc\backend\server.py#L172-L215)

---

### 2. **PBX Listener ไม่ได้ส่ง events ไป backend**

อาจเกิดจาก:
- PBX listener ไม่ได้รับ SMDR stream จาก PBX
- Parsing ล้มเหลวแต่ไม่มี logging
- HTTP request ล้มเหลวแต่ error ไม่ถูก log

**การแก้ไข**: เพิ่ม comprehensive logging

**ไฟล์ที่แก้ไข**: 
- [`snc_pbx_listener.py`](file://c:\Users\Nithep\ไดรฟ์ของฉัน%20(cnithep@gmail.com)\Hotel-ECS\snc-poc\pbx-connector\snc_pbx_listener.py#L213-L235) - Enhanced send_event_to_backend logging
- [`server.py`](file://c:\Users\Nithep\ไดรฟ์ของฉัน%20(cnithep@gmail.com)\Hotel-ECS\snc-poc\backend\server.py#L172-L215) - Enhanced trigger_event logging

---

### 3. **Events ถูกบันทึกแต่ query ไม่แสดงผล**

อาจเกิดจาก:
- Database query ผิดพลาด
- Filter condition ผิด
- Limit/Order by ไม่ถูกต้อง

**การตรวจสอบ**: ใช้ script [`check_events.py`](file://c:\Users\Nithep\ไดรฟ์ของฉัน%20(cnithep@gmail.com)\Hotel-ECS\snc-poc\backend\check_events.py) เพื่อตรวจสอบ database โดยตรง

---

## การแก้ไข (Fixes Applied)

### 1. แก้ไข Event ID ให้ใช้ Microseconds

**ไฟล์**: [`server.py`](file://c:\Users\Nithep\ไดรฟ์ของฉัน%20(cnithep@gmail.com)\Hotel-ECS\snc-poc\backend\server.py)

```python
import time

# ใช้ microseconds แทน seconds
unique_id = f"snc-event-{formatted_room}-{int(time.time() * 1000000)}"
```

---

### 2. เพิ่ม Logging ที่ PBX Listener

**ไฟล์**: [`snc_pbx_listener.py`](file://c:\Users\Nithep\ไดรฟ์ของฉัน%20(cnithep@gmail.com)\Hotel-ECS\snc-poc\pbx-connector\snc_pbx_listener.py)

```python
async def send_event_to_backend(self, event_data: dict):
    try:
        await self.init_http_session()
        url = f"{self.backend_url}/api/events/trigger"
        payload = {
            "room_id": event_data["extension"]["roomId"],
            "event_type": event_data["payload"][0]["contentString"],
        }

        logging.info(f"Attempting to send event to backend: {payload}")  # NEW
        
        async with self.http_session.post(url, json=payload) as response:
            if response.status == 200:
                result = await response.json()
                logging.info(
                    f"✅ Event sent successfully: Room {payload['room_id']} - {payload['event_type']} "
                    f"(ID: {result.get('event', {}).get('id', 'unknown')})"
                )
            else:
                body = await response.text()
                logging.error(f"❌ Failed to send event. Status: {response.status} Body: {body[:200]}")

    except Exception as e:
        logging.error(f"❌ Error sending event to Backend: {e}")
        import traceback
        logging.error(traceback.format_exc())  # NEW - แสดง stack trace
```

---

### 3. เพิ่ม Logging ที่ Backend

**ไฟล์**: [`server.py`](file://c:\Users\Nithep\ไดรฟ์ของฉัน%20(cnithep@gmail.com)\Hotel-ECS\snc-poc\backend\server.py)

```python
@app.post("/api/events/trigger")
async def trigger_event(req: CallEventRequest):
    logging.info(f"📨 Received event trigger request: room_id={req.room_id}, event_type={req.event_type}")
    
    # ... processing ...
    
    logging.info(f"Mapped event type: {req.event_type} -> {mapped_event_type}")
    logging.info(f"Saving event to database: ID={unique_id}, Room={formatted_room}, Type={mapped_event_type}")
    save_event_to_db(event_payload)
    logging.info(f"✅ Event saved successfully: {unique_id}")
    
    # ... broadcast ...
```

---

### 4. สร้าง Diagnostic Script

**ไฟล์ใหม่**: [`check_events.py`](file://c:\Users\Nithep\ไดรฟ์ของฉัน%20(cnithep@gmail.com)\Hotel-ECS\snc-poc\backend\check_events.py)

Script นี้ใช้เพื่อ:
- ตรวจสอบว่ามี events ใน database หรือไม่
- ดูว่ามี duplicate IDs หรือไม่
- แสดง events แยกตาม type
- ตรวจสอบเฉพาะ Room 400

---

## ขั้นตอนการ Debug (Debugging Steps)

### ขั้นตอนที่ 1: ตรวจสอบ Database

```bash
cd /home/pi/Hotel-ECS/snc-poc/backend
python3 check_events.py
```

**ถ้าไม่เจอ events**:
- ปัญหามาจาก PBX listener ไม่ได้ส่ง events
- หรือ backend ไม่ได้รับ/ไม่บันทึก

**ถ้าเจอ events**:
- ปัญหามาจาก frontend/dashboard ไม่ดึงข้อมูลมาแสดง

---

### ขั้นตอนที่ 2: ตรวจสอบ Logs

```bash
# ตรวจสอบ PBX listener logs
tail -f /home/pi/Hotel-ECS/logs/pbx_listener.log | grep -E "(Attempting|Event sent|Error)"

# ตรวจสอบ Backend logs
tail -f /home/pi/Hotel-ECS/logs/backend.log | grep -E "(Received event|Saving event|saved successfully)"
```

**ควรเห็น**:
```
[PBX] Attempting to send event to backend: {'room_id': '0400', 'event_type': 'CALL_BEDSIDE'}
[PBX] ✅ Event sent successfully: Room 0400 - CALL_BEDSIDE (ID: snc-event-0400-1724673294123456)
[Backend] 📨 Received event trigger request: room_id=0400, event_type=CALL_BEDSIDE
[Backend] Mapped event type: CALL_BEDSIDE -> CALL_TRIGGERED
[Backend] Saving event to database: ID=snc-event-0400-1724673294123456, Room=0400, Type=CALL_TRIGGERED
[Backend] ✅ Event saved successfully: snc-event-0400-1724673294123456
```

---

### ขั้นตอนที่ 3: ทดสอบ Manual Event

```bash
# Trigger test event
curl -X POST http://localhost:8000/api/events/trigger \
  -H 'Content-Type: application/json' \
  -d '{"room_id":"400","event_type":"CALL_BEDSIDE"}'

# Check if it appears
curl http://localhost:8000/api/events | python3 -m json.tool
```

---

### ขั้นตอนที่ 4: ตรวจสอบ Dashboard

เปิด browser และตรวจสอบ:
```
http://192.168.1.94:8000/dashboard-status.html
```

หรือ API endpoint:
```
http://192.168.1.94:8000/api/events
```

---

## การ Deploy (Deployment)

```bash
# 1. Stop services บน Pi
ssh pi@192.168.1.94
pkill -f "uvicorn|snc_pbx"

# 2. Copy ไฟล์ที่แก้ไขแล้ว
cd "c:\Users\Nithep\ไดรฟ์ของฉัน (cnithep@gmail.com)\Hotel-ECS\snc-poc"
scp backend/server.py pi@192.168.1.94:/home/pi/Hotel-ECS/snc-poc/backend/
scp pbx-connector/snc_pbx_listener.py pi@192.168.1.94:/home/pi/Hotel-ECS/snc-poc/pbx-connector/
scp backend/check_events.py pi@192.168.1.94:/home/pi/Hotel-ECS/snc-poc/backend/

# 3. Restart services
./start-snc-system.sh

# 4. Monitor logs
tail -f /home/pi/Hotel-ECS/logs/pbx_listener.log
tail -f /home/pi/Hotel-ECS/logs/backend.log
```

---

## Verification Checklist

- [ ] Event ID ใช้ microseconds (ไม่ใช่ seconds)
- [ ] Enhanced logging เพิ่มในทั้ง PBX listener และ Backend
- [ ] Diagnostic script พร้อมใช้งาน
- [ ] Files deployed ไปยัง Raspberry Pi
- [ ] Services restart แล้ว
- [ ] Logs แสดงว่า events ถูกส่งและรับ
- [ ] Database มี events สำหรับ Room 400
- [ ] Dashboard แสดง events
- [ ] No duplicate IDs ใน database

---

## Files Modified

1. ✅ [`backend/server.py`](file://c:\Users\Nithep\ไดรฟ์ของฉัน%20(cnithep@gmail.com)\Hotel-ECS\snc-poc\backend\server.py)
   - Fixed event ID generation (microseconds)
   - Added comprehensive logging in trigger_event

2. ✅ [`pbx-connector/snc_pbx_listener.py`](file://c:\Users\Nithep\ไดรฟ์ของฉัน%20(cnithep@gmail.com)\Hotel-ECS\snc-poc\pbx-connector\snc_pbx_listener.py)
   - Enhanced send_event_to_backend logging
   - Added error traceback logging

3. ✅ [`backend/check_events.py`](file://c:\Users\Nithep\ไดรฟ์ของฉัน%20(cnithep@gmail.com)\Hotel-ECS\snc-poc\backend\check_events.py) (NEW)
   - Diagnostic script for database inspection

---

## Expected Outcome

หลังจาก deploy แล้ว ควรเห็น:

1. **Logs แสดง event flow ครบถ้วน**:
   ```
   PBX → Listener → Backend → Database → Dashboard
   ```

2. **Events 4 รายการปรากฏใน dashboard**:
   - Room 400, 14:54
   - Room 400, 17:21
   - Room 400, 21:04
   - Room 400, 22:15

3. **ไม่มี duplicate IDs** ใน database

4. **API endpoint `/api/events`** return events ทั้ง 4 รายการ

---

**Status**: ✅ Fixes applied, ready for deployment  
**Date**: 2024-10-08  
**Issue**: SMDR events not displaying on dashboard despite correct format
