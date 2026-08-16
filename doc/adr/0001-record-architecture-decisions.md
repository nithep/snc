---
title: "ADR 0001 — บันทึกสถาปัตยกรรม (Architecture Decision Records)"
type: adr
tags: [architecture]
---

# ADR 0001 — บันทึกสถาปัตยกรรม (Architecture Decision Records)

- สถานะ: **Accepted**
- วันที่: 2026-08-17

## บริบท
โปรเจกต์ SNC มีการตัดสินใจเชิงสถาปัตยกรรมหลายอย่าง (แยก bridge, Firestore, tunnel, ฯลฯ)
ที่กระจัดกระจายอยู่ตามสคริปต์/เอกสาร โดยไม่มีหลักฐานเหตุผล+"ทางเลือกที่ไม่ได้เลือก" → รีวิว/สืบค้นย้อนหลังยาก

## การตัดสินใจ
นำ **ADR (Architecture Decision Record)** มาใช้เป็นมาตรฐาน บันทึกการตัดสินใจสำคัญแต่ละรายการ
เป็นไฟล์แยก `doc/adr/NNNN-<title>.md` ตามโครงสร้าง:
- บริบท (Context) / การตัดสินใจ (Decision) / ผลกระทบ (Consequences) / ทางเลือก (Alternatives)

## ผลกระทบ
- การตัดสินใจใหม่ทุกครั้งที่กระทบสถาปัตย์ต้องมี ADR
- Reviewer/ผู้มาใหม่เข้าใจ "ทำไม" โดยไม่ต้องเดาจากโค้ด
- ป้องกันการทำซ้ำ/สวนทางกับ decision เดิม

## ADR ที่เกี่ยวข้อง
- `0002` แยก alert bridge / `0003` Firestore / `0004` Outbox+idempotency / `0005` IaC / `0006` broker+dual-Pi