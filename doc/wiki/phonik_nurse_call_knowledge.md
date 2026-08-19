---
title: "📚 ฐานความรู้ระบบ Phonik Nurse Call (Help Call) — Hardware, Wiring, Config"
type: wiki
tags: [knowledge]
---

# 📚 ฐานความรู้ระบบ Phonik Nurse Call (Help Call) — Hardware, Wiring, Config

**จัดทำ:** 2026-08-14 · **ที่มา:** เอกสารคู่มือใน `Phonik/` (Install Manual, Programming Manual, ManualConfig Builder 150, help-call-m2335, Nurse Call Manager Manual, PC Operator manual) + ผังการเชื่อมสาย `ผัง-NC.jpg` + ใบแจ้งหนี้จริง `ราชเวช_IV3781.pdf` + ไฟล์โปรเจกต์ Config Builder (`*.pnk`)
**ขอบเขต:** ระบบ Nurse Call / Help Call ของ Phonik (Main Control DX-32C/80C/144C + Call Station v.107) สำหรับใช้อ้างอิงงานออกแบบ-ติดตั้ง-ตั้งค่า และบูรณาการกับ Smart Nurse Call (SNC) — ดูเพิ่ม `.agents/skills/Phonik_SNC_Hardware_Spec/SKILL.md`

---

## 1. 🏥 ภาพรวมระบบ (System Overview)

ระบบ Help Call / Nurse Call ของ Phonik ประกอบด้วย 3 ส่วนหลัก:

```
[ ห้องผู้ป่วย ]                 [ ตู้ Main Control ]             [ เคาน์เตอร์พยาบาล ]
  Call Station v.107   ──►   DX-32C / DX-80C / DX-144C   ──►   Master Console (PI-32G)
  (DX-STATION)                  + DX-CPA (CPU)                  Display (NCX-M-DSP / NCX-B-DSP)
  NCX-CORD (ข้างเตียง)          + DX-8ATI (สายสัญญาณ)           (จอแสดงเบอร์ห้อง/คิว)
  NCX-PULL (ห้องน้ำ)            + DX-P128 (PSU + แบตสำรอง)
  NCX-LED / LAMP EM (ไฟหน้าห้อง)
  NCX-BUZZER
```

- ผู้ป่วยกดปุ่ม `CALL` / ดึงสายฉุกเฉิน (NCX-PULL) → ตู้ Main Control ประมวลผล → ไฟหน้าห้องติด + จอเคาน์เตอร์พยาบาลแสดงเบอร์ห้อง + เรียก Master Console
- ตู้ส่ง Log เหตุการณ์ออกทาง **LAN/RS-232 (SMDR)** ซึ่ง SNC (`pbx/snc_pbx_listener.py`) ดักจับได้แบบ Real-time

---

## 2. 🔩 ตู้ Main Control (DX Series)

| รุ่น | สล็อต | DX-8ATI สูงสุด | ความจุสถานี (STA) | หมายเหตุ |
|---|---|---|---|---|
| **DX-32C** | 3 Slots | 3 | 24+2 | ติดผนัง 28×37×23 cm, 100VA |
| **DX-80C** | 6 Slots | 6 | 48+2 | 250VA |
| **DX-144C** | 10 Slots | 8 | 64 | 28×50×23 cm, 400VA, Non-Blocking |

- การ์ด ATI (สายสัญญาณ) รองรับ: **DX-STA** (Call Station) หรือ NCX-M-DSP / NCX-B-DSP (Display) หรือ PI-32G (Master Console)
- การ์ด 1 ใบ (DX-8ATI) ให้ **8 พอร์ตเสียง (EXT Port) + 8 พอร์ตข้อมูล (Data Port)**
- การจัดสล็อต/พอร์ต (DX-32C): SLOT1 = EXT 1-8 / Data 1-8, SLOT2 = EXT 17-24 / Data 9-16, SLOT3 = EXT 33-40 / Data 17-24 (Data Port ของ DX-CPA = 61-62)

### 2.1 DX-CPA (Central Processor Unit + Attendance Console Interface Card)
- 32-bit CPU + DSP, Flash, RAM + แบตสำรอง (Memory Backup), SD Card (Config/Backup)
- พอร์ต: **ATI Data 2 Port** (ATI1/ATI2), Paging 2 Port (PAG1/PAG2), Relay 4 Port (RLY1-4), LAN Port, Serial RS-232 (Printer 2 port, Con RJ11), Digital Switch
- LED: LED1 (เขียว Happy Lamp), LED2 (แดง Warning), LED3 (แดง Backup/Restore), LED4 (แดง Serial), LED_DSP (แดง DSP ทำงาน)

### 2.2 DX-8ATI (8 EXT Port + 8 Data Port Interface Card)
- ต่อกับ DX-STA, NCX-B-DSP, PI-32G — ระยะสาย: **26AWG (0.40mm) < 200m / 24AWG (0.50mm) < 300m / 22AWG (0.65mm) < 500m**

### 2.3 DX-P128 (Power Supply Unit)
- Switch Mode 28Vdc 6A, Input 180-260Vac/50Hz, จ่าย +5V/-5V/+24V/+28V/+100V, Fuse 5A
- ชาร์จแบตสำรอง (12V 7Ah) — ใช้ `JS-BATTI 12V 7AH` ตามใบแจ้งหนี้จริง

---

## 3. 🛏️ อุปกรณ์ในห้องผู้ป่วย (Room Equipment)

| อุปกรณ์ | หน้าที่ | การต่อ |
|---|---|---|
| **Call Station v.107 / DX-STATION** (Dual Port) | สถานีข้างเตียง สนทนา 2 ทาง ปุ่ม CALL / CLEAR | RJ-11 4Pin ไป EXT Port |
| **NCX-CORD** (Bed Side Switch / Call Cord) | สายกดเรียกข้างเตียง | ต่อเข้า DX-STATION |
| **NCX-PULL** (Emergency Call Switch) | สวิทช์ดึงฉุกเฉินในห้องน้ำ — **ยกเลิกที่จุดเกิดเหตุเท่านั้น** | ต่อเข้า DX-STATION (26AWG < 40m / 24AWG < 60m / 22AWG < 80m) |
| **NCX-LED / LAMP EM** (Corridor Lamp / Emergency Lamp) | ไฟสัญญาณหน้าห้อง | ต่อเข้า DX-STATION RJ-11 6Pin (ใช้ 4Pin) |
| **NCX-BUZZER** | เสียงบัซเซอร์เตือน | — |
| **PI-32G** (Master Console) | คอนโซลเคาน์เตอร์พยาบาล 32 ปุ่ม + ไฟสถานะ 2 สี, Hand Free, MUTE, CAMP+ | RJ-11 4Pin ไป EXT Port |
| **NCX-M-DSP / NCX-B-DSP** (Caller ID Display) | จอ LED แสดงเบอร์ห้อง/คิว (M = 4 หลัก, B = 1 หลัก) | RJ-11 4Pin |

**หลักการทำงานของ DX-STATION:** กด `CALL` (Call Cord 1/2 หรือ Emergency Switch) → ไฟ LED/LAMP EM ติดที่ห้อง + แจ้งตู้ → กด `CLEAR` ที่จุดเกิดเหตุยกเลิก — ยกเว้น **Emergency Switch ต้องยกเลิกที่ Master Console**

---

## 4. 🔌 การเดินสาย (จากผัง-NC.jpg + Install Manual)

### 4.1 สายจากตู้ → ห้อง (ต่อสถานี)
สถานีแต่ละห้องใช้สายคู่เกลียว 4 เส้น (2 คู่) ต่อแบบ **L / T / R / H** (ขั้ว 1-4):

| ขั้ว | สัญญาณ | สีสาย (ตามผัง) |
|---|---|---|
| **L** | DATA− | ขาว/ฟ้า (คู่ DATA) |
| **H** | DATA+ | ขาว/ฟ้า (คู่ DATA) |
| **T** | TIP (เสียง) | แดง/เขียว (คู่ VOICE) |
| **R** | RING (เสียง) | แดง/เขียว (คู่ VOICE) |

- เส้นทาง: **ตู้ DX-8ATI (EXT+Data Port) → MDF → ห้อง** โดย Data Port ไปยัง DX-STATION, เสียง (TIP/RING) ไปยังลำโพง/ไมค์สถานี
- **KEY station** (ปุ่มเรียกฉุกเฉิน) ใช้สายคู่ **เหลือง/ดำ** (DATA-KEY) แยกต่างหาก

### 4.2 โครงสร้างผังการเชื่อมสายจริง (ผัง-NC.jpg — ตัวอย่างห้อง 11xx)
```
DX-8ATI การ์ดใบที่ 1-4 (ATI-1..4)  แต่ละการ์ด: P1-P8 (EXT พอร์ต)
  ├─ P1..P8 → เบอร์สถานีห้อง (เช่น 1101-1108, 1109-1116, 1117-1124, 1125-1127)
  ├─ DATA-STA ต่อเนื่องทุกพอร์ต (สาย DATA คู่ ขาว/ฟ้า)
  ├─ DATA-KEY (KEY station, สาย เหลือง/ดำ)
  ├─ VOICE → JACK1/2, JACK3/4 (RJ45, สาย PVC-4C)
  └─ DATA-CPA1 / DATA-CPA2 → ไป DX-CPA (ข้อมูลสถานะห้อง/คิว)
Master Console (PI-32G) + Display (NCX-M-DSP) → ต่อกับตู้ (RJ-11 4Pin)
```

### 4.3 หมายเหตุการติดตั้ง
- สาย ATI → สถานี: 26AWG < 200m (0.40mm) / 24AWG < 300m / 22AWG < 500m
- สาย DX-STATION → NCX-PULL/NCX-LED: 26AWG < 40m / 24AWG < 60m / 22AWG < 80m
- ใช้อุปกรณ์ MDF (เช่น MDF-90) เป็นจุดรวมสายระหว่างตู้กับห้อง

---

## 5. 🎛️ เลขหมาย (Numbering — P001)

- หมายเลขสถานี: **1-512** (4 หลัก) หรือ Operator **941-948** / Function Port **801-900** / Hunting Port **901-940**
- ตัวอย่างเลขหมายจริงในงานราชเวช: ห้องชั้น 11 ใช้ **1101-1127** (ชั้น+ห้อง) — ตามผังการเชื่อมสาย `ผัง-NC.jpg`
- หมายเลข Operator (P002/P003): ตัวอย่าง 100 = 1, 101 = 2, ... (Console port)
- การตั้งค่าเลขหมาย: `*001#<Port>#<Number>#` (Port 0 = ว่าง, 1-512, 941-948)

---

## 6. ⚙️ การตั้งค่า Config Builder (`.pnk`)

- **`.pnk`** = ไฟล์โปรเจกต์ (Project) ของโปรแกรม **Phonik Config Builder v1.5.0** — เก็บ Global Data (P0XX-P4XX, P8XX, P9XX) ใช้สำหรับ Offline เตรียมคอนฟิก หรือ Online Download/Upload กับตู้
- โหมด: Offline / Online Manual RW / Online Auto Read / Online Read Only
- โครงสร้าง P-page ที่เกี่ยวข้องกับ Nurse Call:

| P-code | หน้าที่ | หมายเหตุ |
|---|---|---|
| **P001** | Numbering Assignment (กำหนดหมายเลขสถานี/พอร์ต) | 1-512, 941-948 Operator |
| **P002 / P003** | Operator Assignment (Day / Night) | คอนโซลเคาน์เตอร์ |
| **P020** | Key & DSS (Attendance Console Assignment) | กำหนดสถานีที่ปรากฏบนคอนโซล (ATI 1-64) |
| **P021** | Attendance Page Assignment | หน้า/กลุ่มการแสดงผล 64 ปุ่ม |
| **P022** | Key Pad Assignment | KEY station 1-4 / 01-32 |
| **P091** | Extension Group Assignment | กลุ่ม 1-32 |
| **P092** | Extension Name | ตั้งชื่อสถานี (เช่น "1101", "ห้อง 1101") |
| P012/P013 | Hunting Type/Group | — |
| P006/P007 | Restriction | — |
| P028/P029 | Department | — |
| P049 | System Name | ชื่อระบบ (Default: PHONIK PBX) |
| P905/P906 | Import/Export SD/CF | `.dat` (Native format) |

- งานราชเวชมีไฟล์โปรเจกต์จริง: `27072567-F1-2-v3.0.0.pnk`, `27072567-F3-v3.0.0.pnk`, `27072567-F4-v3.0.0.pnk` (โครงสร้าง Dictionary<"Pxxx", Object> — .NET BinaryFormatter, Version v51r0, ค่า HType/สถานี 1001-1160 ฯลฯ)
- ตั้งค่าระบบผ่านโทรศัพท์ (SP-PHONE): `*0123#1234#` = เข้า System Program (Password 1234), `*015#` = เปลี่ยนรหัสผ่าน

---

## 7. 📡 SMDR / การเชื่อมต่อกับ SNC

- ตู้ Phonik ส่ง Log เหตุการณ์ออกทาง Telnet (Port 23) / RS-232: `==SMDX2005=03/08/26 18:59 401 e.400 EC 0:00'09 0 #1`
- รหัสเหตุการณ์: `e.{room_id}` = เรียกฉุกเฉิน/กดเรียก, `onM -9` / `onto -1` = พยาบาลรับสาย, `offM =0` / `offx -0` = เคลียร์สาย
- SNC ใช้ `station_ext` (เช่น `401`) เป็น room_id (ดู `doc/wiki/SMDR_PARSING_FIX.md`, `doc/wiki/SNC_TEST_EXTENSION_INVENTORY.md`)
- ⚠️ ตู้จริง: **DX-COMPACT V5.4r1 (V5.1r0)** — ยืนยันจาก `..VERS=` จริงบน LAN

---

## 7.1 🚨 ระบบ SOS CALL (Emergency Call / ระบบเรียกขอความช่วยเหลือฉุกเฉิน)

ระบบเรียกขอความช่วยเหลือฉุกเฉิน (SOS CALL) เหมาะสำหรับพื้นที่ที่ต้องการรักษาความปลอดภัย เช่น หน่วยงานราชการ ห้องตรวจรักษาพยาบาล ลานจอดรถ — มี both ไฟเตือนและเสียงเตือน

### 7.1.1 อุปกรณ์หลัก (จากสเปก SOS)
| อุปกรณ์ | หน้าที่ | หลักการทำงาน |
|---|---|---|
| **DX-SOS** (SOS Station) | เครื่องเรียกขอความช่วยเหลือฉุกเฉิน มีปุ่มกดเรียก + ไฟแสดงสถานะ สนทนากับ Master Console ได้ | กดเรียก → แจ้ง Master Console |
| **NCX-LED** (LED Lamp) | ไฟแอลอีดีหน้าจุดเกิดเหตุ | ติดค้างเมื่อมีการเรียก จนกว่าห้องควบคุมจะสั่งปิด |
| **NCX-BUZ** (Buzzer) | ตัวบัซเซอร์ส่งเสียงดัง | ดังเมื่อมีการเรียก และ **หยุดเมื่อห้องควบคุมรับสายสนทนา** (ไม่รบกวนการสนทนา) |
| **PI-32G** (Master Console) | มาสเตอร์คอนโซล ตอบรับ/เรียกแต่ละเครื่อง | มีไฟติดค้างที่หน้าเครื่องเตือนจนกว่าจะ "ดับไฟ" เมื่อเสร็จงาน |
| **NCX-N-DSP** (4-Line Display) | จอแสดงผล 4 บรรทัด แสดงหมายเลขสเตชั่นที่เรียกมา | แสดงที่ Master Console |
| **NCX-B-DSP** (1-Line Display) | จอแสดงผล 1 บรรทัด แสดงหมายเลขสเตชั่น | แสดงที่ Master Console |
| **MDF90 / MDF180** | กล่องพักและกระจายสาย (MDF) | จุดรวมสายระหว่างตู้กับห้อง |
| **DX-8ATI** | แผงสายสัญญาณ | สูงสุด 3 / 6 / 8 แผง สำหรับ DX-32C / DX-80C / DX-144C |

- **DX-SERIES Version:** V.6.4rl · สินค้าพร้อมจำหน่าย 1 กุมภาพันธ์ 2567
- **ความจุสูงสุด (สถานี):** `(PI-32G) + (DX-SOS) + (NCX-B-DSP) + (NCX-M-DSP)` = **24+2 / 48+2 / 64** สำหรับ DX-32C / DX-80C / DX-144C

### 7.1.2 บูรณาการวัดผลกับ SNC
- เมื่อเกิด SOS CALL ตู้ Phonik จะพ่น SMDR เหตุการณ์ `e.{room_id}` แบบ **EC (Emergency Call)** — SNC จับ timestamp วินาทีที่เกิดเหตุ
- SNC (Dashboard) แสดงสถานะ **แดงกะพริบ** ทันที และเริ่มจับ **Response Time** จนกว่าพยาบาล/เจ้าหน้าที่จะ **Acknowledge/Clear** ที่ Master Console (`offM`/`offx`)
- ผลลัพธ์การเรียก (เวลาตอบสนอง, SLA Level 1–3, อัตราครบ/ไม่ครบ) ถูกบันทึกลง SQLite (FHIR JSON) และนำไปทำ **รีพอร์ตพรีเมี่ยมรายวัน/รายเดือน** ได้ทันที
- จุดนี้ตอบโจทย์ "เพิ่มบูรณาการกับระบบ SOS วัดผลการเรียก" — SNC เปลี่ยนสัญญาณ SOS ให้เป็นข้อมูลวัดผลได้โดยไม่ต้องเดินสายเพิ่ม

---

## 8. 🧾 บันทึกงานจริง รพ.ราชเวช (อ้างอิง IV3781 — 15/09/66)

| ลำดับ | อุปกรณ์ | Qty | ราคา/หน่วย |
|---|---|---|---|
| 1 | DX5-80C Super (Main Control DX-80C) | 1 | 9,555.00 |
| 2 | DX5-8AT1 V5 (DX-8ATI V5) | 7 | 6,541.50 |
| 3 | DX6-8SLT/C V6 (SLT 8 พอร์ต) | 1 | 4,226.25 |
| 4 | JS-BATTI 12V 7AH (แบตสำรอง) | 4 | 787.50 |
| 5 | PI-32G Digital Hybrid Key Telephone (Master Console) | 4 | 2,520.00 |
| 6 | NCX-M-DSP (Display 4 หลัก) | 4 | 3,570.00 |
| 7 | NCX (อื่น ๆ) | 2 | 1,554.00 |
| 8 | DX-STATION Call Station Dual Port (s/n 96211002, 96305011, 96308001-02) | 18 | 1,417.50 |
| 9 | NCX-CORD Call Cord | 20 | 1,050.00 |
| 10 | MDF-90 (40 ห้อง/MDF, Terminal 10 ห้อง/MDF ฯลฯ) | — | — |

> รวม 177,073.05 + VAT 12,395.11 = **189,468.16 บาท** · หมายเหตุ: ตัวเลขจากใบแจ้งหนี้จริง — งานชั้น 11 (F11) ตามใบเสนอ 3629 ต้องนับอุปกรณ์ใหม่อีกครั้งตามผัง

---

## 9. 📄 แหล่งอ้างอิง (ใน `Phonik/`)

- `Install Manual.pdf` — สเปก/การติดตั้งตู้และอุปกรณ์
- `Programming Manual.pdf` — การโปรแกรม P0XX-P9XX ทั้งหมด
- `ManualConfig Builder 150.pdf` — คู่มือ Config Builder v1.5.0 (`.pnk`)
- `help-call-m2335.pdf` — คู่มือระบบ Help Call (Main Control DX5.4r1 + Call Station v.107)
- `Nurse Call Mamager Manual.pdf`, `PC Operator manual.pdf` — โปรแกรมจัดการ/โอเปอเรเตอร์
- `ผัง-NC.jpg` — ผังการเชื่อมสาย NURSE CALL SYSTEM (แผนผังการเชื่อมสายจริง)
- `ราชเวช_IV3781.pdf` — ใบแจ้งหนี้/ส่งของจริง (อ้างอิงฮาร์ดแวร์ชุดราชเวช)

---

*จัดทำโดย Buffy (Freebuff Desktop) — อัปเดตตามไฟล์จริงในโฟลเดอร์ Phonik · UTF-8 · ภาษาไทยทางการ*
