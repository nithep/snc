---
title: "ADR 0014 — Remove Kiosk Scaling from SNC Dashboard"
type: adr
tags: [architecture, dashboard, responsive, kiosk]
---

# ADR 0014 — Remove Kiosk Scaling from SNC Dashboard

- สถานะ: **Accepted**
- วันที่: 2026-09-05

## บริบท

SNC Dashboard เคยมีโหมด Kiosk ที่ใช้ CSS `transform: scale(...)` ครอบหน้าเว็บทั้งหมด
เพื่อบังคับให้เนื้อหาพอดีหนึ่ง viewport ผลข้างเคียงคือหน้าเว็บอาจถูกย่อจนมองเหมือนหน้าเปล่า
และทำให้การใช้งานบนมือถือไม่เป็นธรรมชาติ โดยเฉพาะเมื่อความสูง viewport เปลี่ยนจาก browser chrome

## การตัดสินใจ

ยกเลิกและลบ Kiosk scaling ออกจากระบบทั้งหมด:

- ใช้ responsive CSS และ natural document flow เป็นพฤติกรรมเดียวทั้งคอมพิวเตอร์และมือถือ
- อนุญาตให้หน้าเว็บ scroll แนวตั้งตามความยาวจริงของ dashboard
- ลบ `#appScale`, `fitToScreen()`, `ResizeObserver` สำหรับ scaling และการรองรับ query `?kiosk`
- ลบไฟล์ JavaScript รุ่นเก่าที่ไม่ได้ถูกโหลดโดยหน้า production และยังมี kiosk scaling ซ้ำ
- เปลี่ยน deploy verification ให้ตรวจว่า runtime dashboard ไม่มี kiosk reference

## ผลกระทบ

- ✅ หน้า Dashboard แสดงขนาดจริง ไม่ถูกย่อจนมองไม่เห็น
- ✅ Desktop ใช้พื้นที่กว้างตาม viewport และ mobile จัด layout ตาม media queries เดิม
- ✅ Mobile scroll ดูส่วน KPI, ห้องพัก และประวัติได้ตามธรรมชาติ
- ⚠️ ผู้ใช้ที่เคยเปิด URL พร้อม `?kiosk` จะได้หน้า responsive ปกติ โดยไม่มีโหมดพิเศษ
- ⚠️ เอกสารประวัติการ deploy ที่กล่าวถึง Kiosk ยังคงเก็บไว้เป็น audit history ไม่ใช่ runtime contract

## ทางเลือกที่ไม่เลือก

- คง Kiosk ไว้แต่แก้ loop: ยังมีความเสี่ยงด้าน usability และไม่จำเป็นต่อการใช้งานบนคอม/มือถือ
- ใช้ browser zoom หรือ JavaScript ตรวจ viewport: เพิ่มความซับซ้อนและทำให้ผลลัพธ์ไม่คงที่ระหว่างอุปกรณ์
