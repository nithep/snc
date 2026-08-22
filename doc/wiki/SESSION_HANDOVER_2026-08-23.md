---
title: "SESSION_HANDOVER_2026-08-23 — Pi4 Cleanup + SHC/SNC Separation"
type: handover
tags: [status, pi4, shc, snc, cloud]
---

# SESSION_HANDOVER_2026-08-23 — Pi4 Cleanup + SHC/SNC Separation

> จัดทำ: 23 ส.ค. 2569 | สรุปการตรวจสอบ Pi4, การจัดระเบียบ runtime และการวางสถาปัตยกรรม SHC แยกจาก SNC

## สรุปการตัดสินใจ

- **SNC** คือระบบเรียกพยาบาล ใช้ Pi4 เดิมและรันด้วย systemd
- **SHC** คือระบบโรงแรม Smart Hotel Check-in แยกเป็นอีกระบบหนึ่ง
- แนวทางเป้าหมายของ SHC: ใช้ **Raspberry Pi Zero 2 W เป็น Edge Node** และย้าย API/UI หลักไปรันบน Cloud
- ห้ามนำ SHC code, database หรือ listener มาปะปนกับ SNC
- หาก SHC และ SNC ใช้ตู้ PBX เดียวกัน ต้องออกแบบ session/command broker เพิ่ม เพราะ PBX รองรับการเชื่อมต่อจำกัด ไม่ให้เปิด connection แยกชนกัน

## สถานะ SNC บน Pi4

Host: `ecs-agent@hotel-gateway` · LAN: `192.168.1.94`

| Component | สถานะ | รายละเอียด |
|---|---|---|
| `snc-backend.service` | active | `/home/ecs-agent/snc/api/server.py`, port `8000` |
| `snc-pbx-listener.service` | active | `/home/ecs-agent/snc/pbx/snc_pbx_listener.py`, proxy port `2323` |
| `snc-cloudflared.service` | active | Tunnel สำหรับ `snc-opencode.nithep.com` |
| SNC health | healthy | `GET http://127.0.0.1:8000/health` ตอบ `200` |
| OpenCode | active | port `4096`, public endpoint ป้องกันด้วย Basic Auth |

ฐานข้อมูลที่ใช้งานจริง:

```text
/home/ecs-agent/snc/api/nurse_call_events.db
/home/ecs-agent/snc/pbx/snc_event_outbox.db
```

## งานที่ดำเนินการบน Pi4 แล้ว

1. ลบ Docker container เก่า `snc-backend` ที่ crash loop จาก SQLite path ผิด
2. ลบโปรเจกต์เก่า `/home/ecs-agent/snc-project`
3. ยืนยันว่า SNC หลักใช้ systemd จาก `/home/ecs-agent/snc`
4. ย้ายไฟล์ `.bak*` และ root database ที่ไม่ได้ใช้งานไปยัง:

```text
/home/ecs-agent/snc/backups/legacy-archive-20260822/
```

5. ลบ directory ว่าง `frontend/` และ `docs/` ภายใน SNC
6. ลบ PM2 process เก่า `hotel-backend` ซึ่งชี้ไป legacy path `/home/ecs-agent/Hotel-ECS/backend`
7. ลบไฟล์ว่าง `/home/ecs-agent/ping` และ `package-lock.json` ระดับ `/home/ecs-agent`
8. บันทึก PM2 state ใหม่แล้ว (`pm2-clean`)

ไม่มีการลบฐานข้อมูลใช้งานจริงหรือไฟล์ source หลักของ SNC

## ผลการตรวจสอบ SHC (`nithep/shc`)

Repository ที่ตรวจสอบ: `https://github.com/nithep/shc`  
HEAD ที่ตรวจสอบ: `a1bef2169bca7b810442c043eb496457bf5072fa`

SHC เป็นระบบโรงแรม ไม่ใช่ SNC โดยมีองค์ประกอบหลัก:

- Node.js API ใน `api/`
- React/Vite UI ใน `app/`
- PBX connector ใน `pbx/`
- Cloud/ops configuration ใน `ops/`
- เอกสาร migration ระบุ deployment path ใหม่ของ SHC

ข้อจำกัดที่พบ:

- `api/server.js` ยังเป็นโครงเริ่มต้นและ endpoint event ยังเพียง log/ตอบรับ
- PBX relay code บางส่วนยังเป็นตัวอย่าง ต้องยืนยัน protocol/ACK-NACK ก่อนใช้ hardware จริง
- SHC config เดิมใช้ port `3000` ซึ่งชนกับ `hotel-app` บน Pi4 ปัจจุบัน
- SHC ยังไม่ได้ติดตั้งบน Pi4 หรือ Pi Zero 2 W ใน session นี้

## สถาปัตยกรรมเป้าหมายของ SHC

```text
Phonik PBX ของโรงแรม
        │
        ▼
Raspberry Pi Zero 2 W
  - SHC Edge Agent
  - PBX connector
  - local queue / offline retry
  - Cloudflare Tunnel หรือ HTTPS outbound
        │
        ▼
SHC Cloud
  - API
  - Web UI / Check-in
  - Database กลาง
  - Audit / notification / analytics
```

Pi Zero 2 W เหมาะกับงาน Edge listener และ queue แต่ไม่ควรรันชุด Cloud/UI/build ขนาดเต็ม เพราะมี RAM 512MB และมี Wi-Fi 2.4GHz เป็นหลัก ควรใช้ USB Ethernet หากต้องเชื่อม PBX แบบมีสาย

## งานถัดไป

1. ยืนยันว่า SHC ใช้ตู้ PBX แยกจาก SNC หรือไม่
2. เตรียม Pi Zero 2 W เฉพาะสำหรับ SHC โดยไม่ติดตั้ง SNC
3. เลือก Cloud runtime และ database สำหรับ SHC
4. แยก hostname, secret, database, service และ Cloudflare Tunnel ของ SHC
5. ทดสอบ SHC ด้วย PBX simulator ก่อนเชื่อม hardware จริง
6. หากใช้ PBX เดียวกับ SNC ต้องออกแบบ command/session broker ให้ชัดเจนก่อน deploy

## ข้อควรระวัง

- ห้ามให้ SHC เปิด TCP session ไป PBX port `23` ซ้อนกับ SNC โดยตรง
- ห้ามใช้ SNC port `2323` เป็นช่องส่งคำสั่ง relay ของ SHC
- ห้ามคัดลอก `.env`, API key, tunnel token หรือ database ระหว่าง SHC กับ SNC
- การย้าย SHC ขึ้น Cloud ต้องยังมี local queue และ retry เมื่อ Internet ขัดข้อง

