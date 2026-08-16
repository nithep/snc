---
title: "คู่มือตั้งค่า API Key (X-API-Key) และการจัดการสายค้าง — Smart Nurse Call (SNC)"
type: guide
tags: [security]
---

# คู่มือตั้งค่า API Key (X-API-Key) และการจัดการสายค้าง — Smart Nurse Call (SNC)

**อัปเดตล่าสุด:** 2026-08-14
**ไฟล์ที่เกี่ยวข้อง:** `api/server.py` (backend) · `pbx/snc_pbx_listener.py` (listener) · `app/index.html` (dashboard)
**⚠️ ช่วง Burn-in (จนถึง 15 ส.ค. 2569 03:03):** ห้ามแก้ `.env` / เปลี่ยน API key (ข้อห้ามข้อ 7 ใน 8 ข้อ) — **ส่วนที่แตะเซิร์ฟเวอร์ (ข้อ 2) ให้ทำหลัง burn-in จบเท่านั้น** ส่วนการกรอก key ที่แดชบอร์ด + กดรับเรื่อง/เคลียร์ (ข้อ 3–4) ทำได้ทันที

---

## 1. หลักการทำงาน (อ่านก่อน)

| คำขอ | ต้องใช้ Key? |
|---|---|
| GET — ดู dashboard, KPI, รายการเหตุการณ์, health | ❌ ไม่ต้อง (เปิดเสมอ) |
| POST/PUT/DELETE — trigger, รับเรื่อง (ack), เคลียร์ (clear) | ✅ ต้องใช้ **ถ้า** เซิร์ฟเวอร์ตั้ง `SNC_API_KEY` ไว้ |

- ตรวจที่ `api/server.py` (middleware `guard_write_endpoints`): เทียบ header `X-API-Key` กับค่า `SNC_API_KEY` ใน `.env` — ไม่ตรง/ไม่มี → ตอบ `401 invalid or missing X-API-Key`
- **ถ้าเซิร์ฟเวอร์ไม่ตั้ง `SNC_API_KEY` = ไม่ต้องกรอก key ที่แดชบอร์ดเลย**
- แดชบอร์ดเจอ 401: แสดง toast แจ้งเตือน + เปิดหน้าต่างการตั้งค่าให้กรอก key อัตโนมัติ

---

## 2. ตั้งค่าฝั่งเซิร์ฟเวอร์ (บน Pi) — หลัง Burn-in

### 2.1 สร้าง key ใหม่ (สุ่ม 64 ตัวอักษร hex)

```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

### 2.2 ใส่ใน `.env` ของ Backend (อยู่ข้าง `server.py`)

```bash
find /home/ecs-agent/snc-poc -maxdepth 2 -name .env 2>/dev/null   # หาตำแหน่ง .env ก่อน
nano /home/ecs-agent/snc-poc/api/.env                              # แก้ไฟล์ backend
# เพิ่ม/แก้บรรทัด:  SNC_API_KEY=<key ที่สร้างใน 2.1>
```

### 2.3 ใส่ key เดียวกันใน `.env` ของ PBX Listener (สำคัญมาก)

Listener ส่ง key ผ่าน header ตอน trigger — **ถ้า backend ตั้ง key แต่ listener ไม่ตั้ง → เหตุการณ์จาก PBX จะโดน 401 ทิ้งทั้งหมด**

```bash
nano /home/ecs-agent/snc-poc/pbx/.env
# เพิ่ม/แก้:  SNC_API_KEY=<key เดียวกันเป๊ะกับ 2.2>   (ตรวจ PBX_PASS ว่ายังอยู่ครบ)
```

### 2.4 ตั้งสิทธิ์ + restart

```bash
chmod 600 /home/ecs-agent/snc-poc/api/.env /home/ecs-agent/snc-poc/pbx/.env
sudo systemctl restart snc-backend.service
sudo systemctl restart snc-pbx-listener.service
systemctl is-active snc-backend.service snc-pbx-listener.service    # ต้อง active ทั้งคู่
```

### 2.5 ตรวจสอบ auth (ไม่สร้างข้อมูล — ใช้ ack กับห้องที่ไม่มี)

```bash
curl -s -o /dev/null -w "%{http_code}\n" -X POST http://localhost:8000/api/events/acknowledge/9999
# 401 = key ผิด/ไม่ส่ง  ·  ตัวเลขอื่น (404/200) = key ผ่าน
```

---

## 3. ตั้งค่าฝั่งแดชบอร์ด (ทำได้เลย ไม่แตะเซิร์ฟเวอร์)

1. เปิดหน้า dashboard → คลิก **⚙️** (มุมขวาบน)
2. ช่อง **API Key (X-API-Key)** → วาง key (เฉพาะถ้าเซิร์ฟเวอร์ตั้งไว้)
3. กด **บันทึก**
   - ค่าเก็บใน `localStorage` ของเบราว์เซอร์ (จำเฉพาะเครื่องนี้ ไม่ส่งไปเซิร์ฟเวอร์)
   - ทางเลือก: ใส่ผ่าน URL `https://nursecall.nithep.com/?api_key=xxxx`
4. ทดสอบ: กดปุ่ม "รับเรื่อง" ที่ห้องใดก็ได้ — ถ้าไม่เจอ toast 401 = ผ่าน

---

## 4. ขั้นตอนแก้ "สายค้าง" (เช่น ห้อง 400, 101, 777)

**สาเหตุ:** เหตุการณ์ทดสอบถูก trigger แล้วไม่มีใครกดรับเรื่อง/เคลียร์ — ระบบไม่มี auto-timeout สายค้างติดสถานะ `active` ไปเรื่อยๆ และจะถูกนับเป็น SLA breach เมื่อกด ack/clear เท่านั้น

1. กรอก API Key ให้ถูกต้อง (ข้อ 3) — ถ้าไม่กรอก กดรับเรื่องจะได้ 401
2. เปิดการ์ดห้องที่ค้าง → กด **📞 รับเรื่อง**
3. กด **เคลียร์** (ปุ่มจะเปลี่ยนหลังรับเรื่อง) — ระบบคำนวณ SLA breach ให้อัตโนมัติ
4. ทำซ้ำจนการ์ดทุกห้องกลับเป็น "ปกติ" และ banner "สายค้าง" หาย
5. ตรวจ KPI หลังเคลียร์ — จำนวนเกิน SLA / compliance จะปรับเป็นค่าจริง (สายค้าง 157+ ชม. จะถูกนับ breach ทันที)

> ทางเลือกบน Pi: เคลียร์ตรงจาก SQLite ได้ แต่ **แนะนำให้ใช้ปุ่มบน dashboard** เพื่อให้ระบบตั้ง flag `sla_breached` เอง (bypass API = ต้องตั้ง flag เอง มึนง่าย)

---

## 5. ปัญหาที่พบบ่อย

| อาการ | สาเหตุ | วิธีแก้ |
|---|---|---|
| กดรับเรื่อง/เคลียร์ไม่ได้ + toast 401 | ไม่กรอก key หรือกรอกผิด | เปิด ⚙️ กรอก key ใหม่ (เทียบกับค่าใน `.env` บน Pi) |
| เหตุการณ์จาก PBX ไม่เข้าหลังตั้ง key | key ใน backend `.env` กับ listener `.env` ไม่ตรงกัน | แก้ให้เป็นค่าเดียวกัน (ข้อ 2.3) แล้ว restart ทั้งคู่ |
| Dashboard อ่านได้ปกติแต่เขียนไม่ได้ | เป็นพฤติกรรมตั้งใจ — GET เปิด, POST ปิด | กรอก key |
| ไม่รู้ว่า Pi ตั้ง key หรือไม่ | — | `grep SNC_API_KEY /home/ecs-agent/snc-poc/api/.env` — ไม่มีบรรทัด = ไม่ต้องกรอก |

---

## 6. สรุป Flow

```
กด "รับเรื่อง" ที่แดชบอร์ด
  → POST /api/events/acknowledge/{room}
    → header X-API-Key: <จาก localStorage หรือ ?api_key=>
      → server ตรวจเทียบ SNC_API_KEY ใน .env (บน Pi)
          ├─ ไม่ตั้ง key → ผ่านตลอด
          └─ ตั้งแล้ว → ตรง = ack สำเร็จ  /  ไม่ตรง = 401
```

**แหล่งอ้างอิง:** `doc/wiki/SNC_TEST_EXTENSION_INVENTORY.md` (ทะเบียนเบอร์ทดลอง) · `doc/wiki/SESSION_HANDOVER_2026-08-13.md` (ข้อห้าม burn-in) · `api/server.py` (middleware auth)
