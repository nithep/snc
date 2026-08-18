---
title: "🧹 แผนถอนรากถอนโคนชื่อ legacy (Nomenclature Cleanup)"
type: plan
tags: [ops, nomenclature]
---

# 🧹 แผนถอนรากถอนโคนชื่อ legacy (Nomenclature Cleanup)

> **วันที่:** 19 ส.ค. 2569
> **เป้าหมาย:** ทำตามกฎ Nomenclature (AGENTS.md ข้อ 9) — เรียกระบบสม่ำเสมอว่า **SNC** / `nithep/snc` ไม่ใช้ชื่อ legacy
> **ขอบเขต:** ตรวจจาก `git grep` จริงบน repo (จำนวนจุดเป็น ณ วันที่จัดทำ)

---

## 📊 สถานะชื่อ legacy ใน repo (ตรวจ 19 ส.ค. 2569)

| ชื่อ legacy | จำนวน | ไฟล์หลัก (non-doc) | ประเภท |
|---|---|---|---|
| `ecs-agent` (Pi username) | 264 จุด / 26 ไฟล์ | `ops/*`, `packaging/build_installers.py` | runtime path |
| `hotel-ecs` / `Hotel-ECS` | 83 จุด | `api/*.yaml`, `ops/terraform`, `AGENTS.md` | GCP id + doc |
| `hotel.nithep.com` | 16 จุด | `api/server.py` CORS, `health_check`, `gemini` | runtime origin |
| `hotel-gateway` (Pi hostname) | 4 จุด | doc/ops | OS hostname |
| `api-nurse` / `liff.nithep.com` | 6 จุด | doc | legacy subdomain |

---

## 🔒 ข้อตัดสินใจ (Decision — 19 ส.ค. 2569)

อ้างอิง ADR pattern (Context/Decision/Consequences):

### D1: Hotel-ECS = ระบบโรงแรมคนละตัว → แยก snc ล้วน
- **Context:** `hotel.nithep.com` ปรากฏใน CORS origins ของ `api/server.py` (บรรทัด ~98) รวมถึง `health_check.py`, `gemini_direct_service.py`
- **Decision:** **ไม่ลบ** `hotel.nithep.com` ออกจาก CORS origins — เป็นระบบโรงแรม (Hotel-ECS) ที่ผูกกับ backend ของตัวเอง ไม่ใช่ SNC เราเพียงแค่**แยก SNC เป็นระบบของตัวเอง** อย่างชัดเจน (โดเมน `snc.nithep.com`, repo `nithep/snc`)
- **Consequences:** CORS ยังมี origin ของโรงแรมอยู่ (ไม่กระทบ security — อนุญาตเฉพาะ whitelist) แต่ต้องไม่ใช้ชื่อ `hotel-ecs`/`Hotel-ECS` ในเอกสารของ SNC

### D2: `ecs-agent` + `hotel-gateway` = ชื่อจริงบน OS ของ Pi → คงไว้
- **Context:** `ecs-agent` คือ username, `hotel-gateway` คือ hostname ของ Raspberry Pi 4 จริง
- **Decision:** **ไม่เปลี่ยน** — การ rename username/hostname บน OS ที่รัน service อยู่ เสี่ยงระบบ down และไม่คุ้มค่า
- **Consequences:** ยังเห็น `ecs-agent`/`hotel-gateway` ใน path (`/home/ecs-agent/...`) และระบบ — ต้องอธิบายใน doc ว่าเป็นชื่อ OS ที่ถูกต้องตามจริงของเครื่อง

### D3: `hotel-ecs-nithep` = GCP project id จริง → คงไว้ + บันทึก
- **Context:** `hotel-ecs-nithep` คือ **GCP Project ID** ที่ใช้ใน `ops/terraform/`, `api/cloudbuild*.yaml`, deploy scripts
- **Decision:** **ไม่เปลี่ยน** — project id บน GCP ย้าย resource ยาก เสี่ยง break deploy
- **Consequences:** คง id นี้ไว้ใน config แต่ต้องมีบันทึกชัดเจนว่าเป็น "legacy id" เพื่อไม่ให้สับสนกับชื่อ SNC

---

## ✅ งานที่ทำได้ทันที (ปลอดภัย — ไม่กระทบระบบจริง)

รายการนี้ไม่แตะ runtime ที่เสี่ยง จึงทำได้เลยใน repo:

| # | งาน | รายละเอียด |
|---|---|---|
| 1 | ลบ `hotel-ecs`/`Hotel-ECS` ออกจาก **เอกสาร wiki/doc** ของ SNC | แทนที่ด้วยชื่อที่ถูกต้อง (SNC / ระบบโรงแรม) ใน doc เท่านั้น |
| 2 | ทำ glossary ให้ชัด | `doc/NOMENCLATURE.md` ระบุว่า hotel-ecs/hotel.nithep.com เป็นระบบโรงแรม (ไม่ใช่ SNC) |
| 3 | เขียน ADR บันทึก D1–D3 | `doc/adr/NNNN-nomenclature-separation.md` |
| 4 | แก้ `AGENTS.md` | ลบ/แก้การอ้างชื่อ Hotel-ECS ในส่วนที่ไม่ใช่ระบบโรงแรม |
| 5 | บันทึก legacy id | ใน doc ระบุว่า `hotel-ecs-nithep` เป็น GCP project id เก่าที่คงไว้ |

## ⏸️ งานที่ระงับไว้ (ต้องมีแผนปฏิบัติการแยก — กระทบระบบจริง)

| # | งาน | เหตุผลที่ระงับ | ต้องทำเมื่อไหร่ |
|---|---|---|---|
| 1 | Rename Pi username `ecs-agent` / hostname `hotel-gateway` | เสี่ยง service down | เมื่อมี maintenance window + backup เต็ม |
| 2 | ย้าย GCP project `hotel-ecs-nithep` → project id ใหม่ของ snc | ย้าย resource บน GCP ใหญ่ | เมื่อวางแผน IaC ใหม่ (terraform) |
| 3 | เอาออก `hotel.nithep.com` จาก CORS origins | เป็นระบบโรงแรม ต้องประสานเจ้าของ | เมื่อยืนยันว่าระบบโรงแรมไม่ใช้ backend ร่วม |

> ⚠️ **กฎเหล็ก:** การลบชื่อจริง (OS username/hostname, GCP project id, โดเมน) **ห้ามทำในรอบแก้โค้ดปกติ**
> ต้องเป็นงานแยก (dedicated task) ที่มี **maintenance window + rollback plan + backup เต็ม** เท่านั้น
> เพราะชื่อพวกนี้ถูกฝังในระบบที่รันจริง (systemd, cron, GCP resource, tunnel) — แก้ทีละจุดไม่ได้

---

## 🎓 บทเรียนเพื่อโปรเจกต์ใหม่ (Best Practice)

> **วางแผน naming ตั้งแต่จุดเริ่มต้นของโครงการ** — ก่อน commit โค้ดบรรทัดแรก ควร:
> 1. เลือกชื่อโปรเจกต์สั้น/ชัดเจน (เช่น `snc`) — เลี่ยง `-poc`, `-v2`, `test`
> 2. กำหนด namespace ครบชุดล่วงหน้า: repo / โดเมน / path / username / hostname / GCP project / image tag
> 3. หลีกเลี่ยงคำที่ชนกับระบบอื่นในองค์กร (เช่น `hotel`) หรือแยกชื่อชัดเจนแต่ต้น
> 4. บันทึกลง **ADR** (ถ้าจำเป็น) ตั้งแต่เริ่ม
>
> **ทำไม:** ถอนรากชื่อ legacy ทีหลังแพงและเสี่ยง (ต้อง maintenance window) — วางแผน naming ก่อน = ประหยัดสุด
> ดูเพิ่ม: `NOMENCLATURE.md` §1, `ADR 0007`

---

## 🔍 วิธีตรวจสอบซ้ำ (Verify)

```bash
# นับจุดที่ยังเหลือ (ควรลดลงใน doc แต่งาน runtime คงเดิมตามการตัดสินใจ)
git grep -iE "hotel-ecs|Hotel-ECS" -- doc/ | wc -l
git grep -c "ecs-agent" | wc -l
```

---

*จัดทำโดย: Senior Software Engineer — 19 ส.ค. 2569*