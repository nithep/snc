---
title: "ADR 0010 — WebSocket Heartbeat (ping/pong) ตรวจจับสายค้างบน Nurse Dashboard"
type: adr
tags: [architecture, websocket, realtime, dashboard]
---

# ADR 0010 — WebSocket Heartbeat (ping/pong) ตรวจจับสายค้างบน Nurse Dashboard

- สถานะ: **Accepted**
- วันที่: 2026-08-26

## บริบท
Dashboard Nurse Station รับเหตุการณ์ real-time ผ่าน WebSocket (`/ws/nurse-station`)
โดยมี fallback เป็น poll ทุก 10 วินาที กลไก reconnect เดิมอาศัย `onclose` + exponential backoff (1s→30s)

จุดอ่อนที่พบ (พิสูจน์จากการทดสอบ):
1. **Zombie socket** — ถ้า TCP ครึ่งเดียวตาย (ครึ่งทางที่ client) `onclose` อาจไม่ fire
   → pill สถานะค้าง "เชื่อมต่อสด" ทั้งที่สายตาย ข้อมูลเข้าตารางช้าลงเหลือ 10 วินาที (poll)
2. **Cloudflare Tunnel** (free plan) มี idle timeout สำหรับ WebSocket — สายเงียบเกิน
   อาจถูกตัดฝั่ง edge (แม้ uvicorn ping ทุก 20 วิ จะช่วยอยู่แล้ว แต่ไม่มีหลักประกัน 100%)
3. การพึ่ง uvicorn protocol-level ping เพียงอย่างเดียว ทำให้ฝั่ง browser
   (JavaScript) มองไม่เห็นหลักฐานว่าสายมีชีวิต — ไม่สามารถ "บังคับ" reconnect เองได้

## การตัดสินใจ
เพิ่ม **application-level heartbeat** แบบ ping/pong บน WebSocket:

1. **Client (dashboard `app/index.html` + `app/demo.html`)**
   - ส่ง `{"type":"ping"}` ทุก **15 วินาที** (กัน Cloudflare drop สาย idle + ตรวจความมีชีวิต)
   - นับ `wsLastMsgAt` จากทุกข้อความที่ได้รับ (รวม pong/ข้อความที่ถูก filter)
   - เงียบเกิน **60 วินาที** → บังคับ `initWebSocket()` reconnect ทันที (ไม่รอ onclose)
   - **เงื่อนไขปลอดภัย**: บังคับ reconnect เฉพาะเมื่อเคยเห็น `pong` แล้ว (`wsPongSeen`)
     — ถ้า server เก่ายังไม่มี echo จะพึ่งกลไกเดิม (uvicorn ping + onclose + backoff) ไม่เกิด churn
2. **Server (`api/server.py`)**
   - `websocket_endpoint` ตอบ `{"type":"pong"}` ให้ข้อความ `{"type":"ping"}`
   - backward-compatible: ข้อความอื่นยัง log ตามปกติ, client เก่าไม่ส่ง ping ก็ไม่มีผล
3. **เครื่องมือตรวจสอบ**: `ops/ws-tunnel-test.py` (ผ่าน Cloudflare WAF — ต้องมี browser UA)
   - โหมดเต็ม: เชื่อม WS → ยิง demo trigger → รอ broadcast ตรวจ payload
   - `--check-only`: เชื่อม WS แล้วปิด (ไม่ยิง event) — ใช้ cron ทุก 15 นาทีบน Pi

## ผลกระทบ (Consequences)
- ✅ Dashboard ตรวจพบสายค้างเองและ reconnect โดยไม่ต้องโหลดหน้า — พิสูจน์แล้ว:
  kill backend กลางคัน → pill เปลี่ยนเป็น "กำลังเชื่อมต่อใหม่" ภายใน **500 ms**
  → กลับมา "เชื่อมต่อสด" เองภายใน **4,000 ms** → เหตุการณ์ใหม่หลัง reconnect
  เข้าตารางภายใน **300 ms**
- ✅ เหตุการณ์ใหม่รีเรนเดอร์ Recent Events ทันทีผ่าน WS (พิสูจน์ใน Chrome headless:
  เหตุการณ์ใหม่ขึ้นแถวแรกตารางภายใน **358 ms** — น้อยกว่า poll 10 วิมาก)
- ✅ Multi-client 15 ตัว × 10 เหตุการณ์ = **150/150 broadcast ครบ ไม่สูญหาย** —
  ping/pong ไม่รบกวน broadcast (avg 223 ms / p95 422 ms)
- ⚠️ ค่าโสหุ้ย: ข้อความ ping 1 ครั้ง/15 วิ/client — เล็กน้อยมากเทียบกับ payload เหตุการณ์
- ⚠️ ต้อง deploy `api/server.py` และ `app/index.html`/`app/demo.html` พร้อมกัน
  (ออกแบบให้ deploy ไม่พร้อมกันได้ปลอดภัยอยู่แล้ว — ดูข้อ "เงื่อนไขปลอดภัย")
- 🔁 ตั้ง cron บน Pi แล้ว: `*/15 * * * * /usr/bin/python3 ops/ws-tunnel-test.py --check-only`
  → log ที่ `logs/ws-tunnel-check.log` — ถ้า tunnel/WSS ตาย จะเห็นใน log และกลับมาเมื่อ tunnel ฟื้น

## ทางเลือก (Alternatives)
- **พึ่ง uvicorn ping (protocol-level) อย่างเดียว**: ปัดตก — browser ตรวจไม่ได้/บังคับ reconnect
  เองไม่ได้ (เป็นที่มาของ ADR นี้)
- **Heartbeat client-only (ไม่แก้ server)**: ปัดตก — client จะแยกไม่ออกว่า "server เก่า
  ไม่ตอบ pong" กับ "สายค้างจริง" → เสี่ยง churn reconnect ทุก 60 วิ
- **Message Broker (MQTT/Redis Stream)**: ปัดตก ณ ตอนนี้ — เกินความจำเป็นสำหรับ PoC
  (ดู ADR 0006 เปิดใหม่เมื่อมี consumer หลายประเภท)
- **ปรับ poll ให้ถี่ขึ้น (เช่น 3 วิ)**: ปัดตก — แก้ที่อาการไม่ใช่ต้นเหตุ และโหลด server เพิ่ม

## ADR ที่เกี่ยวข้อง
- `0004` outbox/idempotency — durable delivery ของ event (ชั้นบันทึก)
- `0006` broker/dual-Pi — แนวทางเมื่อต้อง life-safety จริง
- `0008` system topology — WebSocket ตรงจาก backend บน Pi4 + Cloudflare Tunnel
- `0009` tunnel self-heal — กลไกคืนชีพ tunnel (เส้นทางเชื่อมถึง dashboard)
