---
title: "🧹 คู่มือทำความสะอาด Windows Task Scheduler (Hygiene Guide)"
type: guide
tags: [windows, ops, hygiene, maintenance]
---

# 🧹 คู่มือทำความสะอาด Windows Task Scheduler (Hygiene Guide)

> **เวอร์ชัน:** 1.0 | **อัปเดตล่าสุด:** 20 ส.ค. 2569
> **ใช้กับ:** เครื่อง Windows ใดก็ได้ (โน้ตบุ๊ก/เซิร์ฟเวอร์) ที่สงสัยว่ามีงาน Schedule ทำงานโดยไม่ได้ตั้งใจ

---

## 📌 ทำไมต้องทำ

บ่อยครั้งที่ AI agent หรือสคริปต์ตั้งเครื่องมืออัตโนมัติ สร้าง **Scheduled Task** ไว้โดยที่เจ้าของเครื่องไม่ทราบ
(เช่น รันทุกวัน 02:00) → กินทรัพยากร, เรียก API นอกเวลา, หรือรันโค้ดเก่าที่ล้าสมัย
คู่มือนี้รวบรวมขั้นตอน **ตรวจหา → สืบต้นทาง → เก็บกวาดให้สะอาด** อย่างปลอดภัย

---

## 🔍 วิธีตรวจหาว่ามีงานรันตอนไหน

เปิด PowerShell (ไม่ต้อง Admin สำหรับดู, แต่ต้อง Admin สำหรับลบ) แล้วรัน:

```powershell
# หางานที่มี Trigger ตรงกับเวลาที่สงสัย (เช่น 02:00)
Get-ScheduledTask | ForEach-Object {
  $t = $_
  $t.Triggers | Where-Object { $_.StartBoundary -match 'T02:00' } | ForEach-Object {
    [PSCustomObject]@{
      TaskName      = $t.TaskName
      TaskPath      = $t.TaskPath
      State         = $t.State
      StartBoundary = $_.StartBoundary
      Author        = $t.Author
      Date          = $t.Date
    }
  }
} | Format-List
```

> เทคนิค: ถ้าไม่แน่ใจว่าเป็นกี่โมง ให้เปลี่ยน `T02:00` เป็น `T0` แล้วกรองในภายหลัง
> หรือดูงานทั้งหมดที่ชื่อ/ทางมาเกี่ยวข้อง: `$_.TaskName -match 'Brain|Memory|Evolving'` หรือ `$_.Actions.Execute -match '2ndBrain'`

---

## 🕵️ วิธีสืบต้นทางของงานนั้น (มาจากไฟล์ไหน เขียนเมื่อไหร่)

เมื่อเจองาน เช่น `X3_SelfEvolving_Memory` ให้ดู **Actions** (สิ่งที่รันจริง) และ **RegistrationInfo**:

```powershell
$t = Get-ScheduledTask -TaskName 'ชื่องาน'
$d = Get-ScheduledTaskInfo -TaskName 'ชื่องาน'

$t.Actions | Format-List          # Execute + Arguments = โปรแกรม/สคริปต์ที่รัน
$t.Triggers | Format-List         # วัน/เวลา/ความถี่
$t.Principal | Format-List        # ผู้รัน (UserId, LogonType)
$d | Format-List                  # LastRunTime, LastTaskResult, NextRunTime
Export-ScheduledTask -TaskName 'ชื่องาน'   # ดู XML ฉบับเต็ม
```

จุดสังเกตที่บอกต้นทาง:
- **`$t.Author`** → ใครสร้าง (ชื่อผู้ใช้/เครื่อง เช่น `MATEBOOKD2019\Nithep`)
- **`$t.Date`** → วันที่ลงทะเบียน → บอกว่า "เก่ามากแค่ไหน"
- **`Arguments`** → มักชี้ไปไฟล์ `.py`/`.ps1` ในโฟลเดอร์โปรเจกต์ (เช่น `D:\2ndBrain\99_System\Scripts\...`)
- **`LastTaskResult`** → `2147942402` (= `0x80041302`) แปลว่าถูกเรียกให้รันแต่มีปัญหา/ไม่พร้อม บ่อยครั้งคือสคริปต์หายหรือสิทธิ์ไม่พอ

จากนั้น **ตรวจไฟล์ต้นทาง** เพื่อประเมินว่ายังจำเป็นหรือไม่:

```powershell
Test-Path 'D:\2ndBrain\99_System\Scripts\self_evolving_memory.py'      # ไฟล์ยังอยู่ไหม
Get-Item  'D:\2ndBrain\99_System\Scripts\self_evolving_memory.py' |     # วันสร้าง/แก้ล่าสุด
  Select-Object FullName, CreationTime, LastWriteTime, Length
Get-Content '...ไฟล์.py' -TotalCount 30                                # อ่านหัวสคริปต์ว่าทำอะไร
```

---

## 🧼 วิธีเก็บกวาดให้สะอาด (ข้อควรระวังสำคัญ)

### 1) ลบ Scheduled Task (ปลอดภัย — เป็นแค่ "ตัวจุดชนวน" ไม่ใช่ข้อมูล)
```powershell
Unregister-ScheduledTask -TaskName 'ชื่องาน' -Confirm:$false
```

### 2) ลบไฟล์สคริปต์ — ต้องระวังอย่าลบทั้งโฟลเดอร์เด็ดขาด
> ⚠️ **ห้ามลบโฟลเดอร์ทั้งหมดเด็ดขาด** จนกว่าจะตรวจว่าไม่มีไฟล์อื่นที่ยังใช้อยู่

```powershell
# เช็คก่อนว่ามีไฟล์อื่นในโฟลเดอร์เดียวกันหรือไม่
Get-ChildItem 'D:\2ndBrain\99_System\Scripts' -Recurse |
  Select-Object FullName, Length, LastWriteTime

# ถ้ามีไฟล์อื่นที่ยังใช้ → ลบเฉพาะไฟล์เป้าหมาย
Remove-Item -LiteralPath 'D:\2ndBrain\99_System\Scripts\self_evolving_memory.py' -Force
```

### 3) ลบงานอื่นที่เกี่ยวข้องให้หมด
```powershell
foreach ($n in @('RemoveOldLogs_2ndBrain','2ndBrain_Cloud_Push')) {
  if (Get-ScheduledTask -TaskName $n -ErrorAction SilentlyContinue) {
    Unregister-ScheduledTask -TaskName $n -Confirm:$false
    echo "DELETED: $n"
  }
}
```

### 4) ตรวจสอบซ้ำว่าหมดแล้ว
```powershell
Get-ScheduledTask | Where-Object {
  $_.Actions.Execute -match '2ndBrain' -or $_.TaskName -match 'Brain|Memory|Evolving'
} | Where-Object { $_.TaskPath -ne '\Microsoft\Windows\MemoryDiagnostic\' } |
  Select-Object TaskName, State
# ถ้าไม่มีผลลัพธ์แสดงว่าเก็บกวาดครบถ้วน
```

---

## 📋 บันทึกเหตุการณ์ตัวอย่าง (Case Study — 20 ส.ค. 2569)

**อาการ:** สงสัยว่ามีงานรัน 02:00 ที่ไม่ได้ตั้งใจบนเครื่อง `MATEBOOKD2019` (C:)

**สิ่งที่พบ:**
| งาน | สถานะก่อน | ต้นทาง | อายุ |
|---|---|---|---|
| `X3_SelfEvolving_Memory` | Ready, รันทุกวัน 02:00 | `D:\2ndBrain\99_System\Scripts\self_evolving_memory.py` ("The Digestor" — วิเคราะห์ log ด้วย Gemini SDK) | สร้าง 9 พ.ค. 2569 (~3.5 เดือน) |
| `RemoveOldLogs_2ndBrain` | Ready | ลบออกในภารกิจเดียวกัน | 29 มี.ค. 2569 |
| `2ndBrain_Cloud_Push` | Disabled แล้ว | ลบออกในภารกิจเดียวกัน | — |

**การดำเนินการ:**
1. สืบต้นทางผ่าน `Get-ScheduledTask` / `Export-ScheduledTask` → ทราบว่าเป็นของระบบ 2ndBrain
2. ตรวจโฟลเดอร์ `Scripts` พบสคริปต์อื่นอีก 40+ ไฟล์ที่ยังใช้งาน → **คงโฟลเดอร์ไว้**
3. ลบเฉพาะ `self_evolving_memory.py` + ลบ Task ทั้ง 3 ตัว
4. ตรวจสอบซ้ำ → ไม่มีงานกลุ่ม 2ndBrain เหลือ

**บทเรียน:** งาน Schedule ที่ "ไม่ได้ตั้งใจ" มักมาจาก agent/สคริปต์ที่รันครั้งเดียวแล้วลืม
ให้ตรวจสอบเป็นระยะ และ **อย่าลบโฟลเดอร์แบบเหมารวม** เสมอเช็คก่อนลบไฟล์เดี่ยว

---

## ✅ Checklist ทำความสะอาด

- [ ] ระบุเวลาที่สงสัย (เช่น `T02:00`) ผ่าน `Get-ScheduledTask`
- [ ] ดู `Actions`/`Author`/`Date` ว่ามาจากไหน เขียนเมื่อไหร่
- [ ] ตรวจไฟล์ต้นทางว่ายังต้องการหรือไม่
- [ ] `Unregister-ScheduledTask` งานที่ไม่ต้องการ
- [ ] ลบไฟล์สคริปต์ **เฉพาะตัว** (ไม่ลบทั้งโฟลเดอร์หากมีของอื่น)
- [ ] ตรวจสอบซ้ำว่างานกลุ่มนั้นหมดแล้ว
