---
title: "ADR 0003 — ใช้ Firestore (แทน SQLite) บน Cloud Run"
type: adr
tags: [architecture]
---

# ADR 0003 — ใช้ Firestore (แทน SQLite) บน Cloud Run

- สถานะ: **Accepted** (ได้ implement แล้ว — `api/storage.py`)
- วันที่: 2026-08-17

## บริบท
Cloud Run scale-to-zero → ไฟล์ SQLite ใน instance จะหาย/ไม่ persist ระหว่าง instance
หากเก็บ event ในไฟล์ local จะ data loss ระหว่าง instance restart

## การตัดสินใจ
- บน **Cloud Run** ใช้ **Firestore** (native mode, collection `nurse_call_events` + `room_state`)
- บน **Pi4/Edge** ยังใช้ **SQLite WAL** (ไฟล์ `nurse_call_events.db`)
- ทั้งสองอยู่หลัง **repository interface เดียวกัน** ใน `api/storage.py`:
  `save_event / get_recent_events / acknowledge_room / clear_room / get_kpi_summary / get_room_events / reset`
  เลือกผ่าน env `SNC_DB_BACKEND` (sqlite|firestore) ด้วย factory `get_store()`

## ผลกระทบ
- (+) persistent ข้าม scale-to-zero, interface เดียว → ไม่ drift ระหว่าง Edge/Cloud
- (+) ใช้ single-field index เท่านั้น หลีกเลี่ยง composite index (Cloud Run ง่าย)
- (-) `get_room_events`/`get_kpi_summary` บน Firestore กรองใน Python (ไม่ใช้ composite index) → ช้ากว่าเมื่อข้อมูลเยอะ
- (-) Firestore คิดค่าใช้จ่ายตามการอ่าน/เขียน

## ทางเลือกที่ไม่ได้เลือก
- Cloud SQL (PostgreSQL) — แรงแต่แพง+maintenance สูงกว่า เหมาะตอน scale ใหญ่
- ไฟล์ SQLite บน Cloud Run — ไม่ persist

## อ้างอิง
- `api/storage.py`