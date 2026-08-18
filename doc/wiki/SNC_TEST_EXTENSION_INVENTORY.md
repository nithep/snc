---
title: "ทะเบียนเบอร์ทดลอง / Extension Inventory — Smart Nurse Call (SNC)"
type: wiki
tags: [knowledge]
---

# ทะเบียนเบอร์ทดลอง / Extension Inventory — Smart Nurse Call (SNC)

**วันที่จัดเก็บข้อมูล:** 2026-08-14 ~17:20 น.
**แหล่งข้อมูล:** ระบบ Live ผ่าน Public Tunnel — `https://snc.nithep.com` (`/api/analytics/kpi`, `/api/events`)
**ผู้จัดเก็บ:** Buffy (Freebuff Desktop) — อ้างอิง SESSION_HANDOVER_2026-08-13 (Pre-Release Go-Live)

---

## 1. หลักการ Mapping เบอร์ PBX → Dashboard

| ชั้น | ค่า | ตัวอย่าง |
|---|---|---|
| **Station จริงบนตู้ PBX** (SMDR `station_ext`) | 3 หลัก | `400`, `401`, `405`, `777` |
| **Room ID ในระบบ** (`room_id`) | 4 หลัก (zero-padded) | `0400`, `0401`, `0405`, `0777` |
| **แสดงบน Dashboard** (`roomDisplayName`) | "ห้อง XXX" | "ห้อง 400" |

กฎยืนยัน (SKILL.md, fixed 2026-08-12): สำหรับเหตุการณ์ `e.{room}` ต้องใช้ **`station_ext`** เป็นห้อง (ไม่ใช่ `event_code`) เช่น กดจาก station `401` → แสดง "ห้อง 0401" เสมอ Dashboard แสดงห้องแบบไดนามิกจากเหตุการณ์จริง (ไม่ hardcode) จึงตรงกับ PBX อยู่แล้ว

---

## 2. สถานะระบบ ณ เวลาจัดเก็บ (Burn-in 48 ชม.)

| รายการ | สถานะ |
|---|---|
| `/health` (Public Tunnel) | healthy — 2026-08-14T17:17:14 |
| Burn-in 48 ชม. | เริ่ม 13 ส.ค. 2569 03:03 → **สิ้นสุด 15 ส.ค. 2569 03:03** (ณ วันที่จัดเก็บ ~38 ชม. ผ่าน, 0 FAIL ตาม handover) |
| ตรวจสอบขั้นสุดท้าย | ต้องรันบน Pi: `burnin-monitor.sh --report` หลัง 15 ส.ค. 03:03 (ดูข้อ 6) |

---

## 3. KPI ณ เวลาจัดเก็บ + การตรวจสอบความสอดคล้อง

| ตัวชี้วัด | ค่าจาก API | ตรวจสอบจากข้อมูลรายเหตุการณ์ | ผล |
|---|---|---|---|
| จำนวนเหตุการณ์ทั้งหมด | 24 | 24 (นับจริง) | ตรง |
| แยกตามประเภท | CALL_BEDSIDE: 1, CALL_TRIGGERED: 23 | CALL_BEDSIDE 1 (0405) + CALL_TRIGGERED 23 | ตรง |
| SLA Compliance Rate | 83.33% | (24 - 4 breach) / 24 = 83.33% | ตรง |
| เกิน SLA (breach) | — | 4 เหตุการณ์ (ทั้งหมดที่เบอร์ 0401) | ตรง |
| เวลาตอบรับเฉลี่ย (Ack) | 0s | ไม่มีเหตุการณ์ใดมี `ack_time_seconds` เลย (AVG → 0) | ระวัง: = "ไม่มีข้อมูล" ไม่ใช่ "เร็วมาก" |
| เวลาเคลียร์เฉลี่ย (Resolution) | 1026.72s | รวม res / 18 รายการ = 18481 / 18 = 1026.72s | ตรง |

> **สรุป:** ตัวเลข KPI บน dashboard **สอดคล้องกับข้อมูลในฐานข้อมูล 100%** — ยกเว้นข้อควรระวังเรื่อง "0s" ที่เป็นค่าไม่มีข้อมูล (ดูข้อ 5)

---

## 4. ทะเบียนเบอร์ทดลองทั้งหมด (แยกรายละเอียดต่อเบอร์)

| เบอร์ | จำนวนเหตุการณ์ | ประเภท | สถานะ | SLA breach | Ack Time | Resolution (นาที:วินาที) | ช่วงเวลา (2026) |
|---|---|---|---|---|---|---|---|
| **0101** | 2 | CALL_TRIGGERED 2 | active 2 | 0 | — | — | 08 ส.ค. 02:53 → 09 ส.ค. 01:42 |
| **0400** | 3 | CALL_TRIGGERED 3 | active 1, acknowledged 2 | 0 | — | — | 04 ส.ค. 00:47 → 08 ส.ค. 02:56 |
| **0401** | 7 | CALL_TRIGGERED 7 | resolved 7 | **4** | — | min 0:08 / avg 43:18 / max 1:15:34 | 08 ส.ค. 02:56 → 12 ส.ค. 20:46 |
| **0405** | 10 | CALL_BEDSIDE 1, CALL_TRIGGERED 9 | resolved 10 | 0 | — | min 0:02 / avg 0:29 / max 1:24 | 12 ส.ค. 20:47 → 14 ส.ค. 16:24 |
| **0777** | 1 | CALL_TRIGGERED 1 | active 1 | 0 | — | — | 11 ส.ค. 18:08 |
| **0778** | 1 | CALL_TRIGGERED 1 | resolved 1 | 0 | 0s | 0s | 11 ส.ค. 18:26 |
| ~~0999~~ | ~~1~~ | CALL_TRIGGERED | resolved | 0 | 2s | 4s | 11 ส.ค. 17:49 — scratch test (ถูกลบออกระหว่างจัดระเบียบข้อมูล) |

**รวม: 24 เหตุการณ์ / 6 เบอร์ที่ใช้งานจริง** (0999 = scratch สำหรับทดสอบ tunnel ตาม handover: `room_id 999`)

---

## 5. ข้อค้นพบและข้อควรปฏิบัติ (จากการจัดระเบียบข้อมูล)

1. **3 สายค้างที่ยังไม่เคลียร์ (0101, 0400, 0777) — ค้างมา 158 / 256 / 71 ชม.**
   - เป็นเหตุการณ์ทดสอบเก่าที่ถูกทิ้งไว้โดยไม่ได้กด "เคลียร์สาย" → ขึ้นเป็น banner "สายค้าง" และบิดเบือนหน้าแรก
   - ยังมีสถานะ `sla_breached = 0` (flag ถูกตั้งตอน ack/clear เท่านั้น) → **ถูกนับเป็น "ผ่านเกณฑ์" ทั้งที่เกิน 180s ไปมาก** ทำให้ SLA Compliance 83.33% สูงเกินจริง (ถ้านับรวมจะได้ (24-7)/24 = 70.8%)
   - **แนะนำ:** เคลียร์สายค้างทั้ง 3 เบอร์ (หรือรอ 15 ส.ค. 03:03 หลังจบ burn-in แล้วล้างข้อมูลทดสอบ เพื่อเริ่มเก็บข้อมูลจริงให้สะอาด)

2. **4 เคส breach ทั้งหมดอยู่ที่เบอร์ 0401** (res = 1:15:34 นานสุด) — บ่งชี้ว่าการทดสอบนั้นไม่ได้กดเคลียร์ตามขั้นตอน (หรือทดสอบเงื่อนไข SLA breach) ควรบันทึกเจตนาไว้ใน test log

3. **ค่าเฉลี่ยเวลารับเรื่อง = 0s** เป็น "ไม่มีข้อมูล" (ไม่มีเหตุการณ์ไหนเคยถูก ack ด้วยการกดรับเรื่องจริง — มีแค่ 0778/0999 ที่เป็นอัตโนมัติ) ควรแสดง `—` แทน 0

4. **หลัง burn-in จบ (15 ส.ค. 03:03):** ตรวจ `burnin-monitor.sh --report` (ต้อง 0 FAIL + services active) แล้วเริ่มเก็บข้อมูลชุดใหม่โดยเคลียร์ข้อมูลทดสอบเก่า เพื่อให้ KPI สะท้อนการใช้งานจริงของวอร์ด

---

## 6. Command Reference (รันบน Pi — `ssh pi4`)

```bash
# ตรวจสอบ burn-in ครบ 48 ชม. (หลัง 15 ส.ค. 03:03)
ssh pi4 '/home/ecs-agent/snc-poc/burnin-monitor.sh --report'

# ดูสายค้าง / เคส breach จากฐานข้อมูลโดยตรง
ssh pi4 "sqlite3 /home/ecs-agent/snc-poc/api/nurse_call_events.db \"SELECT room_id, status, timestamp FROM nurse_call_events WHERE status IN ('active','acknowledged');\""
ssh pi4 "sqlite3 /home/ecs-agent/snc-poc/api/nurse_call_events.db \"SELECT room_id, COUNT(*) FROM nurse_call_events WHERE sla_breached = 1 GROUP BY room_id;\""

# เริ่มเก็บข้อมูลชุดใหม่ (หลังจบ burn-in + สำรอง DB ก่อน)
ssh pi4 '/home/ecs-agent/snc-poc/backup-snc-db.sh --pi'
```
