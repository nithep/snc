---
description: ตรวจสอบสถานะ vault snc (Obsidian vault / git status / ไฟล์สกปรก / การเปลี่ยนแปลงล่าสุด)
agent: build
---

ตรวจสอบสถานะของ vault/project SNC ที่ `D:\snc` ตามคำสั่งที่ผู้ใช้ระบุ

หัวข้อการตรวจสอบ:
1. `$1` = ตรวจสอบสถานะ (action ที่ผู้ใช้พิมพ์)
2. `$2` = vault snc (เป้าหมายที่ผู้ใช้พิมพ์)

กรณีค่าเริ่มต้น (ไม่มี argument หรือ argument = `ตรวจสอบสถานะ vault snc`):
- ตรวจสอบ git status ของ repo (สาขาปัจจุบัน, ไฟล์ที่มีการแก้ไข/เพิ่ม/ลบ, ไฟล์ staged)
- แสดงไฟล์ที่ถูก ignore ซึ่งควรถูก track (ตรวจตาม `git status --ignored`) ตามกฎ SNC — ห้ามใช้ pattern `*key*`/`*secret*` แบบกว้าง
- แสดงรายการการ commit ล่าสุด (`git log --oneline -10`)
- ตรวจสอบสถานะ service/ระบบที่สำคัญ (backend port 8000, PBX listener, PBX stream) ตาม `ops/monitor-snc-status.sh`
- ตรวจสอบดูว่ามีคู่มือ rotate key ครบหรือไม่ (`doc/wiki/*_ROTATION_GUIDE.md`)

ให้ใช้เครื่องมือ bash/git ตรวจสอบจริงแล้วสรุปเป็นภาษาไทยทางการ (Professional Thai) ให้ผู้ใช้ทราบสถานะพร้อมข้อแนะนำที่ควรทำ

หมายเหตุ: ถ้าเปิดใน Obsidian vault ให้ดูว่ามีไฟล์ใหม่/ที่แก้ไขใน `.obsidian` หรือ `doc/wiki` ที่ควร commit ครบถ้วน