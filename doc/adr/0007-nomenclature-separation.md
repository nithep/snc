---
title: "ADR 0007 — แยกชื่อ SNC ออกจากระบบ Hotel-ECS (Nomenclature Separation)"
type: adr
tags: [architecture, nomenclature]
---

# ADR 0007 — แยกชื่อ SNC ออกจากระบบ Hotel-ECS (Nomenclature Separation)

- สถานะ: **Accepted**
- วันที่: 2026-08-19

## บริบท
Repo `nithep/snc` มีชื่อ legacy ของระบบ Hotel-ECS (ระบบโรงแรมคนละตัว) ปนกับ SNC ก่อความสับสน
ตรวจ `git grep` (19 ส.ค. 2569): `ecs-agent` 264 จุด, `hotel-ecs`/`Hotel-ECS` 83 จุด, `hotel.nithep.com` 16 จุด, `hotel-gateway` 4 จุด
กฎ Nomenclature (AGENTS.md ข้อ 9) กำหนดให้เรียกสม่ำเสมอว่า SNC / `nithep/snc`

## การตัดสินใจ
1. **แยก SNC เป็นระบบของตัวเอง** — ใช้ `snc` / `nithep/snc` / `snc.nithep.com` ชัดเจน
2. **Hotel-ECS = ระบบโรงแรมคนละตัว** — คง `hotel.nithep.com` ไว้ใน CORS origins (ระบบโรงแรมผูก backend ตัวเอง)
3. **`ecs-agent` + `hotel-gateway` = ชื่อ OS จริงบน Pi → คงไว้** ไม่ rename (เสี่ยง service down)
4. **`hotel-ecs-nithep` = GCP Project ID จริง → คงไว้** + บันทึกว่าเป็น legacy id

## ผลกระทบ
- SNC มีเอกลักษณ์ชื่อชัด ไม่สับสนกับระบบโรงแรม
- ไม่เสี่ยง break ระบบจริง (ไม่ rename OS user/hostname, ไม่ย้าย GCP project)
- ยังเห็นชื่อ legacy ในโค้ด/ระบบ (จำเป็น) — ต้องอธิบายผ่าน `NOMENCLATURE.md` + `SNC_NOMENCLATURE_CLEANUP.md`

## ทางเลือกที่ไม่ได้เลือก
- **ลบ `hotel-ecs`/`hotel.nithep.com` ทุกจุด** → พัง CORS origins ระบบโรงแรม
- **Rename `ecs-agent`/`hotel-gateway` บน Pi** → เสี่ยง service down
- **ย้าย GCP project `hotel-ecs-nithep`** → งานใหญ่บน GCP เสี่ยง deploy

## ADR ที่เกี่ยวข้อง
- `0001` บันทึกสถาปัตยกรรม (โครงสร้าง ADR) / `0005` IaC Terraform

## การตรวจสอบ
```bash
git grep -iE "hotel-ecs|Hotel-ECS" -- doc/ | wc -l   # doc ควรลดลงเมื่อทำ cleanup
git grep "hotel\.nithep\.com" api/                    # ยังมี (ระบบโรงแรม) ตามการตัดสินใจ
```