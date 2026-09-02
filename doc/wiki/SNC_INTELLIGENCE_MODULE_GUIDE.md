---
title: "SNC Intelligence Module — Phase 1 Guide"
type: guide
tags: [snc, intelligence, operations, self-healing, safety]
---

# SNC Intelligence Module — Phase 1–3 Guide

คู่มือนี้อธิบาย `OpsSelfHealingAgent` ซึ่งเป็น worker แบบ rule-based สำหรับงานนอก Critical Path
ของ SNC ตาม [ADR 0011](../adr/0011-snc-intelligence-module.md)

## ขอบเขต

### Phase 1 — Ops Self-Healing

Agent ตรวจสอบแบบ read-only:

- PBX `PBX_IP:PBX_PORT` และ TCP proxy `PROXY_HOST:PROXY_PORT`
- Backend `/health`
- SQLite database, WAL/SHM และพื้นที่ดิสก์

การกู้คืนอัตโนมัติในเฟสนี้ทำได้เพียงสร้างไฟล์คำขอ reconnect ให้ Listener เป็นผู้จัดการ socket
Agent **ไม่** restart service, ไม่แก้ไข/ลบ Nurse Call Alert และไม่ส่ง payload เหตุการณ์ผู้ป่วยออกภายนอก

## การทดสอบบนเครื่องพัฒนา

```bash
python3 -m api.services.intelligence.ops_agent
```

หรือรันหนึ่งรอบผ่าน Python:

```python
import asyncio
from api.services.intelligence.ops_agent import OpsSelfHealingAgent

print(asyncio.run(OpsSelfHealingAgent().run_once()))
```

## การตั้งค่า

| ตัวแปร | ค่าเริ่มต้น | ความหมาย |
|---|---:|---|
| `SNC_OPS_POLL_INTERVAL` | `30` | รอบตรวจสอบ (วินาที) |
| `SNC_OPS_AUTO_RECONNECT` | `false` | เปิดคำขอ reconnect แบบ bounded |
| `SNC_OPS_ALERT_ENABLED` | `false` | เปิด alert ผ่าน `ops/alerting.py` เมื่อเชื่อมต่อ hook แล้ว |
| `SNC_OPS_WAL_WARNING_BYTES` | `67108864` | threshold WAL (bytes) |
| `SNC_OPS_DISK_WARNING_PERCENT` | `85` | threshold พื้นที่ดิสก์ (%) |
| `SNC_OPS_RECONNECT_COOLDOWN` | `300` | cooldown คำขอ reconnect (วินาที) |
| `SNC_OPS_MAX_RECONNECT_REQUESTS` | `3` | จำนวนคำขอสูงสุดต่อ process |
| `SNC_RECONNECT_REQUEST_FILE` | `api/.snc-reconnect-request.json` | hand-off file ระหว่าง Agent กับ Listener |

## เปิดใช้งานบน Pi 4

การเปิดใช้งานมี 2 สวิตช์แยกกัน:

1. `SNC_INTELLIGENCE_ENABLED=true` ใน `api/.env` — เปิด Dynamic Intelligence API routes ของ Backend
2. `snc-intelligence.service` — เปิด worker สำหรับ Ops Self-Healing

ตั้งค่า route plugin ก่อน แล้ว restart Backend:

```text
SNC_INTELLIGENCE_ENABLED=true
```

จากนั้นติดตั้งและเปิด worker:

```bash
sudo cp ops/snc-intelligence.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl restart snc-backend.service
sudo systemctl enable --now snc-intelligence.service
systemctl status snc-intelligence.service
curl -s http://localhost:8000/api/intelligence/clinical
journalctl -u snc-intelligence.service -f
```

ค่าใน unit ปิด `SNC_OPS_AUTO_RECONNECT` และ `SNC_OPS_ALERT_ENABLED` ไว้ก่อน ต้องทดสอบสภาพแวดล้อมจริงและอนุมัติการเปลี่ยนค่าอย่างชัดเจน
หากต้องการรัน Core-only ให้คง `SNC_INTELLIGENCE_ENABLED=false` และไม่ต้องเปิด worker service

## การเปิด bounded reconnect

ตั้งค่าใน environment ของ service หรือไฟล์ environment ที่ผู้ดูแลระบบควบคุม:

```text
SNC_OPS_AUTO_RECONNECT=true
SNC_OPS_RECONNECT_COOLDOWN=300
SNC_OPS_MAX_RECONNECT_REQUESTS=3
```

เมื่อ PBX health check ล้มเหลว Agent จะเขียนคำขอ JSON ที่กำหนดไว้ Listener จะอ่านคำขอ ลบไฟล์ และปิด socket ของตัวเองเพื่อเข้าสู่ reconnect loop
การกระทำนี้ไม่ฆ่า process และไม่ส่งคำสั่งเปลี่ยนสถานะไปยัง PBX

### Phase 2 — Clinical Analytics & Shift Handover

เรียกใช้ API แบบ read-only:

```bash
curl "http://localhost:8000/api/intelligence/clinical?window_hours=24"
curl "http://localhost:8000/api/intelligence/handover?shift=morning"
```

`ClinicalAnalyticsAgent` ตรวจหาห้องที่มีการเรียกซ้ำใน 4 ชั่วโมงและเปรียบเทียบค่าเฉลี่ย Ack/Resolution กับ baseline 7 วัน
`ShiftHandoverAgent` สรุปจำนวนเคส, เคสฉุกเฉิน, SLA breach, ห้องที่ควรเฝ้าระวัง และเคสที่ยังเปิดอยู่
ข้อมูลที่อ่านเป็น `source=real` เท่านั้น ผลลัพธ์เป็น insight/draft ไม่เปลี่ยนแปลง event และต้องมีเจ้าหน้าที่ตรวจทานก่อนใช้งาน

### Phase 3 — Modular Plugin & Nurse Dashboard Integration

The Intelligence Module is an optional plugin. Core SNC starts without importing this package.
Set `SNC_INTELLIGENCE_ENABLED=true` to dynamically load `services.intelligence.routes` and register the Intelligence API routes.
The default is `false`; when disabled, the Core API remains available and the dashboard shows a non-blocking unavailable state.


หน้า `app/index.html` แสดงผลจาก Phase 2 แบบไม่บล็อก Critical Alert Path:

- Smart Insight Panel เรียก `GET /api/intelligence/clinical` แบบ asynchronous และแสดงสถานะ SLA trend กับห้องที่เรียกบ่อย
- ปุ่ม **Shift Handover** เปิด modal ให้เลือกกะและดูร่างรายงาน
- ปุ่ม **Copy summary text** คัดลอกข้อความสำหรับนำไปตรวจทาน/วางในระบบงานภายใต้การควบคุมของเจ้าหน้าที่
- หาก API ใช้งานไม่ได้ UI แสดงสถานะเตือน โดยไม่ปิดกั้นการรับ Emergency Alert และยังคงใช้ WebSocket เดิม

## การตรวจสอบความปลอดภัย

- ตรวจว่า service ยังแยกจาก `snc-backend.service` และ `snc-pbx-listener.service`
- ตรวจว่าไม่มีการส่ง `event`, `rawSmdrLog`, ห้อง หรือข้อมูลผู้ป่วยใน report/alert
- ตรวจว่า `SNC_OPS_AUTO_RECONNECT=false` เป็นค่าเริ่มต้นใน production
- ตรวจว่า Handover มี `status=draft` และ `safety.filed=false`
- ตรวจ `SNC_INTELLIGENCE_ENABLED=false` เมื่อไม่ต้องการโหลด plugin
- ทดสอบ Core ได้แม้ไม่มี `api/services/intelligence/`
- ห้ามเพิ่มการ restart service หรือแก้ไขสถานะ alert โดยไม่มี ADR และ human approval flow ใหม่
