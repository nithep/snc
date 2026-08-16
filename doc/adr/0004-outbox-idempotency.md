---
title: "ADR 0004 — Outbox + Idempotency สำหรับการส่ง event (กัน data loss / duplicate)"
type: adr
tags: [architecture]
---

# ADR 0004 — Outbox + Idempotency สำหรับการส่ง event (กัน data loss / duplicate)

- สถานะ: **Proposed → Accepted** (implement ใน `pbx/event_outbox.py` + `api/server.py`)
- วันที่: 2026-08-17

## บริบท
เดิม listener (`snc_pbx_listener.py`) ส่ง HTTP POST ตรงไป backend ไม่มีคิว/retry →
ถ้า backend down ชั่วขณะ event หาย และ backend สร้าง id ใหม่ทุก POST (server.py:193)
→ ส่งซ้ำได้ event ซ้ำ (SLA นับผิด) และ `INSERT OR REPLACE` ทำลาย ack/clear เดิม

## การตัดสินใจ
1. **Outbox (durable queue)** บน Pi: ก่อนส่ง เก็บ event ลง SQLite (`snc_event_outbox`) เป็น pending
   แล้วค่อยส่ง; มี retry แบบ backoff; ส่งสำเร็จแล้ว mark `sent`
2. **Idempotency**: listener ส่ง `event_id` (id ของ event) ไปด้วย → backend dedup
   (`store.event_exists(id)` → ข้ามถ้ามีอยู่แล้ว) + `save_event` เปลี่ยนเป็น `INSERT OR IGNORE` (เก็บชุดแรก ไม่ clobber ack/clear)

## ผลกระทบ
- (+) event ไม่หายตอน backend down (retry จนได้) — at-least-once
- (+) event ซ้ำถูกกำจัดโดย id (idempotent) — SLA นับถูก
- (+) กัน `REPLACE` ทำลายสถานะ ack/clear
- (-) รอ ack จาก backend ก่อน mark sent (เพิ่ม latency เล็กน้อย)
- (-) outbox โตถ้า backend down นาน (มีค่า config/cleanup ที่ควรทำ)

## ทางเลือกที่ไม่ได้เลือก
- Message broker (MQTT/Redis) ตั้งแต่ตอนนี้ — ดู ADR 0006 (กัน over-engineering ก่อน scale จริง)
- ไม่ทำ idempotency — ไม่ได้ เพราะ SLA ต้องแม่น

## อ้างอิง
- `pbx/event_outbox.py`, `pbx/snc_pbx_listener.py`, `api/server.py`, `api/storage.py`