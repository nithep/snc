# แนวทางการทำงานและทดสอบระบบ Smart Nurse Call (SNC)
## (Development, Simulation, and Deployment Workflow Guide)

คู่มือนี้อธิบายสถาปัตยกรรมและขั้นตอนมาตรฐานการทำงานของทีมพัฒนาและทีมปฏิบัติการระบบ Smart Nurse Call (SNC) ตั้งแต่การเขียนโค้ด การแยกข้อมูลทดสอบ (Demo) การจำลองสัญญาณจากตู้สาขา (Phonik PBX Mock) ไปจนถึงการ Deploy ลงบนระบบจริง (Pi 4 & GCP Cloud Run)

---

## 1. การแบ่งแยกข้อมูลจำลองและข้อมูลจริง (Data & Traffic Isolation)

เพื่อรักษาระดับความน่าเชื่อถือของข้อมูลการแพทย์ (SLA/KPI Response Time) ระบบใช้หลักการประทับตราแหล่งที่มาของข้อมูล (Source Tagging) ในฟิลด์ `source` ตามมาตรฐาน HL7 FHIR-compliant schema:

```
[ข้อมูลที่เกิดขึ้นในระบบ]
       │
       ├──► ยิงเข้า /api/demo/trigger  ──► บังคับ source="demo"  ──► สำหรับทดสอบจำลอง (Sandbox/Marketing)
       │
       └──► ตู้ PBX จริงผ่าน Listener ──► บังคับ source="real"  ──► สำหรับใช้งานจริง (Production)
```

### การตั้งค่าและการใช้งาน
1. **API Endpoints**:
   - `/api/demo/trigger`: ให้บริการสาธารณะ ไม่จำเป็นต้องใช้ API Key ป้องกันความปลอดภัย อนุญาตให้เฉพาะ `source="demo"`
   - `/api/events/trigger`: ต้องมี Header `X-API-Key` ที่ถูกต้อง ใช้สำหรับยิงข้อมูลจริงจาก Edge Listener เท่านั้น
2. **Dashboard Filters**:
   - หน้าจอ Dashboard เคาน์เตอร์พยาบาล (`app/index.html`) จะกรองเฉพาะ Event ที่มี `source="real"`
   - ส่วนหน้าจำลองระบบ (Interactive Live Demo) ที่ลิงก์จาก Landing Page จะกรองเฉพาะ Event ที่มี `source="demo"` เพื่อการสาธิตโดยไม่รบกวนพยาบาลหน้างาน
3. **KPI & Statistics**:
   - การดึงข้อมูลรายงานผ่าน API ไปคำนวณสถิติความรวดเร็วในการช่วยเหลือผู้ป่วย จะรันบนเงื่อนไข `WHERE source = 'real'` เสมอ

---

## 2. ขั้นตอนการปฏิบัติงาน (The 5-Step Pipeline)

การดำเนินงานต้องผ่านขั้นตอนเรียงลำดับอย่างเคร่งครัด: **สร้าง ➔ จำลอง ➔ ดู ➔ Commit ➔ Deploy**

```
┌──────────────┐      ┌──────────────┐      ┌──────────────┐      ┌──────────────┐      ┌──────────────┐
│   1. สร้าง   │ ───► │  2. จำลอง    │ ───► │    3. ดู     │ ───► │   4. Commit  │ ───► │   5. Deploy  │
│ (Dev Machine)│      │ (Mock Event) │      │ (Web Browser)│      │   (GitHub)   │      │ (Pi & Cloud) │
└──────────────┘      └──────────────┘      └──────────────┘      └──────────────┘      └──────────────┘
```

### ขั้นที่ 1: สร้าง (Build / Develop)
* **สภาพแวดล้อม**: เครื่องพัฒนาของโปรแกรมเมอร์ (Dev Machine)
* **แนวปฏิบัติ**:
  - พัฒนา UI/UX ของ Landing Page (`app/landing.html`) หรือ Dashboard (`app/index.html`)
  - แก้ไขปรับปรุง API Server (`api/server.py`) หรือ SMDR Parser (`pbx/snc_pbx_listener.py`)
  - รักษาความเป็นระเบียบและมาตรฐานไฟล์การตั้งค่าต่างๆ (ห้ามใส่ Secret Key ลงในโค้ดตรงๆ)

### ขั้นที่ 2: จำลอง (Simulate / Test)
* **สภาพแวดล้อม**: เครื่องพัฒนาของโปรแกรมเมอร์ (Dev Machine)
* **แนวปฏิบัติ**:
  - รัน API Server จำลองบนเครื่องโลคอล:
    ```powershell
    cd d:\snc
    python api/server.py
    ```
  - จำลองข้อมูลสัญญาณฉุกเฉินยิงเข้าระบบผ่าน Integration Test Script (ยิง Mock Event ไปที่ `/api/demo/trigger`):
    ```powershell
    python api/integration_test.py
    ```
  - รัน Unit Test ตรวจสอบสลักและ parser:
    ```powershell
    pytest tests/
    ```

### ขั้นที่ 3: ดู (Inspect / Verify)
* **สภาพแวดล้อม**: เครื่องพัฒนาของโปรแกรมเมอร์ (Dev Machine)
* **แนวปฏิบัติ**:
  - เปิด Browser เข้าไปที่ `http://localhost:8000/landing.html` (สำหรับตรวจสอบหน้า Landing Page)
  - เปิด `http://localhost:8000/` (สำหรับตรวจสอบหน้า Dashboard)
  - ตรวจสอบสถานะการเชื่อมต่อ WebSocket และความถูกต้องของเสียง Alarm, สีสถานะห้องพัก (แดง/เหลือง/เขียว), การกะพริบแจ้งเตือน และการนับเวลาตอบสนอง (Response Time SLA)

### ขั้นที่ 4: Commit (Version Control)
* **สภาพแวดล้อม**: เครื่องพัฒนาของโปรแกรมเมอร์ (Dev Machine)
* **แนวปฏิบัติ**:
  - ตรวจสอบความถูกต้องของสิทธิ์ไฟล์และคีย์ลับผ่าน `git status`
  - ทำการ Commit และ Push ไปยัง Repository หลักบน GitHub ซึ่งเป็น **Single Source of Truth**:
    ```bash
    git status
    git add .
    git commit -m "feat(landing): implement isolated demo trigger connection"
    git push origin main
    ```

### ขั้นที่ 5: Deploy (Rollout)
การ Deploy ถูกแบ่งออกเป็น 2 ส่วนตามเป้าหมายปลายทาง:

#### 5.1. Deploy ขึ้นอุปกรณ์ Edge (Raspberry Pi 4 ที่ติดตั้งหน้างานโรงพยาบาล)
* **เป้าหมาย**: เพื่อรันระบบรับสัญญาณจริงจากตู้โทรศัพท์ Phonik PBX
* **คำสั่งปฏิบัติการ**:
  ```bash
  # 1. เชื่อมต่อเข้าไปยัง Raspberry Pi 4 หน้างาน
  ssh ecs-agent@192.168.1.94

  # 2. ไปยังโฟลเดอร์โปรเจกต์และดึงโค้ดเวอร์ชันล่าสุด
  cd /home/ecs-agent/snc
  git pull origin main

  # 3. รีสตาร์ทเซอร์วิสเพื่อให้การทำงานมีผล
  sudo systemctl restart snc-backend.service snc-pbx-listener.service
  ```

#### 5.2. Deploy ขึ้นระบบคลาวด์ (Google Cloud Run)
* **เป้าหมาย**: เพื่อให้บริการหน้า Landing Page และระบบ Live Demo แก่ภายนอกสาธารณะ
* **คำสั่งปฏิบัติการ**:
  ใช้สคริปต์อัตโนมัติที่จัดเตรียมไว้ใน `ops/` ผ่าน Cloud Shell หรือเครื่องที่ติดตั้ง GCP CLI:
  ```bash
  bash ops/deploy_backend_cloudshell.sh
  ```
  ระบบจะบิลด์ Docker Image และเผยแพร่ขึ้นสู่ Cloud Run และจะผูกเข้ากับ Cloudflare Tunnel / DNS โดยอัตโนมัติ

---

## 3. ความปลอดภัยและสุขอนามัยของโค้ด (Code Hygiene & Secrets)
* **ห้ามบันทึกคีย์ลับหรือ token ลงใน Git**:
  - ไฟล์ `.env` หรือไฟล์ที่มีชื่อเข้าข่าย Key/Secret ต้องถูกป้องกันไว้ใน `.gitignore` เสมอ
  - ในการทำงานบน Cloud ให้เรียกใช้จาก Google Secret Manager หรือสภาพแวดล้อมที่ปลอดภัยเท่านั้น
* **Strict UTF-8 Encoding**:
  - ไฟล์เอกสาร Markdown (.md) และโค้ด Python/Javascript ที่มีภาษาไทย ต้องบันทึกด้วยการเข้ารหัส `UTF-8` เสมอเพื่อป้องกันระบบแสดงผลเพี้ยน (Mojibake)
