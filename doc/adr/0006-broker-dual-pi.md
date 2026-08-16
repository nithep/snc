---
title: "ADR 0006 — (อนาคต) Message Broker + Dual-Pi สำหรับ life-safety"
type: adr
tags: [architecture]
---

# ADR 0006 — (อนาคต) Message Broker + Dual-Pi สำหรับ life-safety

- สถานะ: **Proposed / Pending** — ยังไม่ implement รอ scale หรือข้อกำหนด life-safety จริง
- วันที่: 2026-08-17

## บริบท
เมื่อต้องการ consumer หลายตัว (dashboard + LINE + analytics) หรือต้องรองรับ failover
ระดับฮาร์ดแวร์ (life-safety) สถาปัตยกรรมปัจจุบัน (WebSocket ตรงจาก backend, Pi ตัวเดียว) อาจไม่พอ

## ข้อเสนอ (เมื่อถึงเวลา)
1. **Message Broker** (MQTT/EMQX หรือ Redis Stream) คั่นกลาง: listener → broker → consumers
   - (+) fan-out หลาย consumer, retry/durable queue จัดการในตัว, listener/backend แยกอิสระ
   - (-) เพิ่ม component + Ops; ต้นทุน/ความซับซ้อนสูงขึ้น (ADR 0004 ก็แก้ data-loss ได้ก่อนอยู่แล้ว)
2. **Dual-Pi / Failover**: 2 เครื่อง + keepalive/VIP หรือ active-standby
   - (+) ตัดจุดเดียวล้มเหลว (single point of failure) — สำคัญถ้าเป็น patient-safety
   - (-) ค่าใช้จ่าย+Ops เพิ่มเป็นเท่าตัว

## เกณฑ์ตัดสินใจเปิดงานนี้
- consumer มากกว่า 2 ประเภทจริง → broker
- ข้อกำหนด life-safety / SLA ความพร้อมใช้งานสูง (เช่น 99.9%+) → dual-Pi + FMEA

## สถานะปัจจุบัน
ยังไม่จำเป็น — ใช้ Outbox (ADR 0004) รองรับ data-loss ไปก่อน เปิด ADR นี้ใหม่เมื่อถึงเกณฑ์