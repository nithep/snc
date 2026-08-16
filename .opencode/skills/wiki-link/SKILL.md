---
name: wiki-link
description: Use when working with the OKF documentation wiki — the raw markdown files under doc/wiki/ (knowledge base, SOP, guides) and Obsidian-style wiki links ([[...]]). Use when asked to filter/link wiki notes, cross-reference necessary information, reduce noise, or connect related docs in the SNC/5-Core knowledge base.
---

# OKF — Wiki Filtering & Linking

จัดการ "เอกสาร OKF" (คู่มือ + SOP + wiki / knowledge base) ใน `doc/` โดยเฉพาะไฟล์ raw markdown
ใน `doc/wiki/` และลิงก์แบบ Obsidian wikilink `[[...]]` — งานคือ **กลั่นกรองเฉพาะข้อมูลที่จำเป็น
แล้วเชื่อมโยงระหว่างเอกสาร** ไม่ให้เก็บทุกอย่างแบบตามอำเภอใจ (ลด noise / กัน link ตาย / กันซ้ำซ้อน)

## โครงสร้างที่เกี่ยวข้อง

- `doc/wiki/` — knowledge base: คู่มือ rotate key, handover, setup guide, SOP, analysis report
- `doc/adr/` — Architecture Decision Records (ADR 0001–0006)
- `doc/BLUEPRINT_5CORE.md` — มาตรฐานโครงสร้างโปรเจกต์
- `doc/ARCHITECTURE_FLOW.md` — ผังรวม Edge + Cloud
- `AGENTS.md` — กฎ AI Agent ของโปรเจกต์ (Thai, UTF-8, ADR, outbox)

## กฎการกลั่นกรอง (Filter — อะไรควรเก็บ/ตัด)

**ควรเก็บ / เชื่อมโยง (link):**
- ข้อมูลที่ช่วยให้เข้าใจระบบ: ตัวชี้สำคัญ (IP/port/endpoint), สถานะ/ผลการทดสอบ, การตัดสินใจ (ชี้ ADR)
- ข้อมูลที่อ้างอิงข้ามกันได้จริง เช่น ปัญหา→แนวทางแก้, การตั้งค่า→คู่มือ rotate key
- "จำเป็น" = เมื่อไม่รู้สิ่งนี้แล้วจะทำงาน/ตัดสินใจต่อไม่ได้

**ควรตัด / ย่อ (ไม่ทำซ้ำ):**
- รายละเอียดที่ copy มาจากไฟล์อื่น → แทนที่ด้วย wikilink `[[ชื่อไฟล์]]` แทนการวางเนื้อหาซ้ำ
- ข้อมูลล้าสมัย/ซ้ำกับ handover เก่า → ชี้ไป handover ล่าสุดเท่านั้น
- ความเห็นส่วนตัว / ประวัติที่ไม่ได้ช่วย decision → ย่อหรือตัด

## กฎการเชื่อมโยง (Link)

ใช้ **wikilink** `[[ชื่อไฟล์]]` (ไม่มี `.md` ถ้าอยู่ใน vault เดียวกัน) เพื่อ cross-reference:

- อ้างไฟล์อื่น → `[[session_handover_2026-08-16]]`
- อ้างพร้อม label → `[[SNC_API_KEY_SETUP_GUIDE|วิธีตั้ง key]]`
- อ้าง ADR → `[[0004-outbox-idempotency]]`

**ข้อปฏิบัติ:**
1. ก่อนใช้ลิงก์ ตรวจว่าไฟล์ปลายทางมีอยู่จริง (กัน "broken link") — ใช้ Glob/Grep ตรวจชื่อใน `doc/`
2. ลิงก์ไปที่ข้อมูลจำเป็นเท่านั้น — อย่าใส่ลิงก์มั่วที่ไม่ได้ช่วยต่อยอด
3. ชื่อไฟล์ใช้ตัวพิมพ์ตามไฟล์จริง (`SESSION_HANDOVER...` เป็น uppercase, `project_timeline.md` เป็น lowercase)
4. ถ้าเปิดเป็น Obsidian vault (`D:\snc`) `[[...]]` จะ resolve เอง; ถ้าไม่ใช่ ให้มั่นใจว่า path ตรง
5. ห้ามเปลี่ยนเนื้อหาต้นฉบับเพียงเพื่อให้ลิงก์ตรง — ถ้าไฟล์ปลายทางไม่มี ให้ใช้ path เต็มหรือไม่ลิงก์

## ภาษา / Encoding
- เอกสารเป็นภาษาไทยทางการ (Professional Thai) — ตาม AGENTS.md
- ต้องเป็น **UTF-8** เสมอ (บันทึก/อ่านไฟล์ภาษาไทย)

## ตัวอย่างการใช้งาน
- "เชื่อมโยง session handover กับ blueprint" → แทรก `[[BLUEPRINT_5CORE]]` + ลิงก์ ADR ที่เกี่ยวข้อง
- "ทำสรุป wiki ที่จำเป็นเท่านั้น" → กรองเฉพาะข้อเท็จจริงสำคัญ + ชี้ลิงก์ไปรายละเอียด แทนการวางยาว
- "ตรวจ link ตายใน doc/wiki" → grep หา `[[...]]` แล้วเปรียบเทียบกับไฟล์จริงใน `doc/`