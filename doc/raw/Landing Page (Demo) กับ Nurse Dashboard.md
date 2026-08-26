จัดการตรวจสอบการใช้งาน LandingPage เชื่อมข้อมูล demo แยกการใช้งานจาก dashboard ของจริง ออกแบบการใช้งานให้เชื่อมกันเป็นระบบที่ใช้งานจริงได้ไหม เราควรสร้างบน เครื่องdev - บน pi4- บน cloud แบบไหนดีที่สร้าง-จำลอง-ดู-commit-deploy ตามลำดับแบบนี้ได้ไหมอย่่างไร 


การออกแบบและวางระบบแบ่งแยกการใช้งานระหว่าง **Landing Page (Demo)** กับ **Nurse Dashboard (Production จริง)** รวมถึงการวาง Workflow **สร้าง $\rightarrow$ จำลอง $\rightarrow$ ดู $\rightarrow$ Commit $\rightarrow$ Deploy** ข้ามสภาพแวดล้อม (Dev $\rightarrow$ Pi 4 $\rightarrow$ Cloud) มีแนวทางเชิงสถาปัตยกรรมระดับ Senior Software Engineer & Healthcare IoT Specialist ดังนี้ครับ:

---

### 1. การออกแบบเชื่อมต่อ Landing Page (Demo) กับ Nurse Dashboard (ระบบจริง)

เพื่อให้ระบบสามารถรองรับทั้ง **ผู้เยี่ยมชมทั่วไป/ฝ่ายบริหาร (ทดลองเล่นบน Landing Page)** และ **เจ้าหน้าที่พยาบาลหน้างานจริง (ใช้งานผ่านเคาน์เตอร์)** โดยไม่ส่งผลกระทบต่อข้อมูลทางการแพทย์:

mermaid

flowchart TD

    subgraph Public_Internet["1. สาธารณะ / ลูกค้าทั่วไป (Public Layer)"]

        Landing["Landing Page (landing.html)<br/>- ROI Calculator<br/>- Interactive Simulator Widget"]

        DemoBtn["ปุ่มทดสอบจำลอง (Demo Button)"]

    end

    subgraph Edge_Hospital["2. เครือข่ายโรงพยาบาลจริง (Hospital LAN / Pi 4)"]

        Hardware["ตู้ Phonik PBX + บอร์ด Help Call<br/>(สวิทช์หัวเตียง / ห้องน้ำ)"]

        Listener["snc_pbx_listener.py<br/>(Telnet Edge Capture)"]

        Dashboard["Nurse Station Dashboard (index.html)<br/>(เคาน์เตอร์พยาบาล)"]

    end

    subgraph Backend_Layer["3. ระบบประมวลผล (Backend API & Data Store)"]

        DemoAPI["POST /api/demo/trigger<br/>(tag: source='demo')"]

        RealAPI["POST /api/events/trigger (Outbox)<br/>(tag: source='real', FHIR Standard)"]

        DB[(SQLite WAL / Cloud Firestore)]

        WS["WebSocket Dispatcher<br/>broadcast: events"]

    end

    Landing --> DemoBtn --> DemoAPI

    Hardware --> Listener --> RealAPI

    DemoAPI --> DB

    RealAPI --> DB

    DB --> WS

    WS -->|channel: real/demo| Dashboard

#### ยุทธศาสตร์การแยกข้อมูล (Data & Traffic Isolation)

1. **Data Tagging (`source: "real" | "demo"`)**:
    - ทุก Event ที่ส่งผ่านระบบจะถูกประทับตราระบุแหล่งที่มา
    - ข้อมูลจากตู้ Phonik PBX ทางสายโทรศัพท์/บอร์ดห้องพักจริง $\rightarrow$ บังคับ `source: "real"`
    - ข้อมูลจากปุ่มทดลองเล่นบนหน้า Landing Page $\rightarrow$ ยิงเข้า `/api/demo/trigger` และบังคับ `source: "demo"` เสมอ
2. **การรักษาความถูกต้องของ SLA/KPI ทางการแพทย์**:
    - การประมวลผล Response Time, SLA Dashboard, และรายงานสถิติของโรงพยาบาล จะกรองเฉพาะ `WHERE source = 'real'` เท่านั้น
    - การทดสอบหรือการกดเล่นจากภายนอกจะไม่ทำให้สถิติเวลาเข้าช่วยเหลือผู้ป่วยจริงผิดเพี้ยน
3. **การแสดงผลบน Dashboard**:
    - **เคาน์เตอร์พยาบาลจริง**: ตั้งค่า Default Filter ให้รับเฉพาะสัญญาณจริง (หรือมีป้ายกำกับ `[DEMO SIMULATION]` สีส้มสดใส เพื่อให้พยาบาลไม่สับสนกับเหตุฉุกเฉินจริง)
    - **หน้าจำลองบนเว็บ (Live Demo)**: ผู้สนใจสามารถกด "Live Interactive Demo" จากหน้า Landing Page เพื่อเปิดหน้า Dashboard จำลองที่เชื่อมกับข้อมูล `source=demo` ได้อย่างสมบูรณ์

---

### 2. ยุทธศาสตร์สภาพแวดล้อม (Dev Machine vs Pi 4 vs Cloud)

|สภาพแวดล้อม|บทบาทหลัก (Role)|สิ่งที่รันบนนี้|Data Storage|
|---|---|---|---|
|**1. Dev Machine** (Windows/MateBook)|**Sandbox & Development**  <br>(พัฒนา UI, Logic, จำลอง PBX)|- FastAPI Backend (`server.py`)  <br>- Mock PBX Telnet Server / Generator  <br>- Dashboard & Landing Page|SQLite (Local / In-memory)|
|**2. Pi 4** (Edge Hardware)|**Production Edge Appliance**  <br>(เชื่อมตู้โทรศัพท์ Phonik จริง)|- `snc-backend` (systemd)  <br>- `snc-pbx-listener` (จับพอร์ต PBX LAN)  <br>- `snc-cloudflared` (Tunnel ปลอดภัย)|SQLite WAL Mode (`nurse_call_events.db`)|
|**3. Cloud** (GCP / Cloudflare)|**Public Portal & Global Dashboard**  <br>(เผยแพร่ Landing Page & สำรองข้อมูล)|- GCP Cloud Run (`snc-cloud-backend`)  <br>- Alert Bridge (ส่ง Telegram แจ้งเตือน)  <br>- Cloudflare DNS / CDN Caching|Google Cloud Firestore|

---

### 3. Workflow มาตรฐาน: "สร้าง $\rightarrow$ จำลอง $\rightarrow$ ดู $\rightarrow$ Commit $\rightarrow$ Deploy"

[1. สร้างบน Dev] ──> [2. จำลอง Mock Event] ──> [3. ดูผลลัพธ์บน Browser]

        │

        ▼

[4. Commit & Push ขึ้น GitHub] (Single Source of Truth)

        │

   ┌────┴────────────────────────┐

   ▼                             ▼

[5a. Deploy สู่ Pi 4 Edge]    [5b. Deploy สู่ GCP Cloud Run]

(ดึงโค้ด + รันระบบหน้างาน)     (รัน Landing Page + Demo สาธารณะ)

#### รายละเอียดขั้นตอนทีละสเต็ป:

#### ขั้นที่ 1: สร้าง (Build & Code บน Dev Machine)

- พัฒนาโครงสร้าง Landing Page (`app/landing.html`), Dashboard (`app/index.html`), หรือ Backend API (`api/server.py`) บนเครื่อง Dev
- จัดการ Design System, CSS Dark Mode, Interactive Charts ให้สวยงามระดับพรีเมียม

#### ขั้นที่ 2: จำลอง (Simulate บน Dev Machine)

- ไม่จำเป็นต้องยกตู้ PBX มาต่อกับเครื่อง Dev ตลอดเวลา โดยใช้ชุดจำลอง:
    
    powershell
    
    # รัน Backend แบบ Local
    
    python api/server.py
    
    # รัน Mock PBX Telnet หรือสคริปต์ยิง Event ทดสอบ
    
    python api/integration_test.py
    
- ทดสอบการกดปุ่มบน Landing Page เพื่อตรวจสอบว่า Event ยิงเข้า `/api/demo/trigger` พร้อมแท็ก `source=demo` ถูกต้อง

#### ขั้นที่ 3: ดู (Inspect & Verify UI/UX)

- เปิด Web Browser ตรวจสอบ:
    - Landing Page: `http://localhost:8000/landing.html` หรือ `http://localhost:8000/`
    - Nurse Dashboard: `http://localhost:8000/` (ดูการตอบสนอง Real-time WebSocket, เสียง Alarm, การจับเวลา SLA)
- ตรวจสอบ Unit Test ผ่านคำสั่ง `pytest` เพื่อความมั่นใจว่า Logic ไม่พัง

#### ขั้นที่ 4: Commit (Version Control ผ่าน Git)

- บันทึกการเปลี่ยนแปลงและ Push ขึ้น GitHub:
    
    bash
    
    git add api/ app/ doc/
    
    git commit -m "feat(landing): connect interactive demo widget with isolated source tagging"
    
    git push origin main
    

#### ขั้นที่ 5: Deploy (การปล่อยขึ้นระบบจริง)

- **สำหรับ Pi 4 (Edge Station)**:
    - ดึงโค้ดผ่าน Git หรือรันสคริปต์ซิงค์:
        
        bash
        
        ssh pi4 "cd /home/ecs-agent/snc && git pull origin main && sudo systemctl restart snc-backend snc-pbx-listener"
        
- **สำหรับ Cloud (Landing Page / Demo Public)**:
    - Deploy ขึ้น GCP Cloud Run ด้วยสคริปต์ใน `ops/`:
        
        bash
        
        bash ops/deploy_backend_cloudshell.sh
        
    - เว็บไซต์ Landing Page จะพร้อมให้บริการแก่สาธารณะผ่านโดเมน เช่น `https://snc.nithep.com` ปลอดภัยด้วย HTTPS ของ Cloudflare

---

### สรุปคำแนะนำ

1. **การแยกข้อมูล**: ระบบปัจจุบันรองรับการแยก `source=demo` และ `source=real` อยู่ในระดับ Schema แล้ว ทำให้สามารถเชื่อมต่อ Landing Page กับ Dashboard ได้ทันทีอย่างปลอดภัย
2. **การทำงานข้ามสภาพแวดล้อม**: ลำดับการทำงาน **"สร้างบน Dev $\rightarrow$ จำลอง Mock $\rightarrow$ ดูผลลัพธ์ $\rightarrow$ Commit ขึ้น GitHub $\rightarrow$ Deploy แยกสาย (Pi4 / Cloud)"** เป็น Best Practice ที่มั่นคง ปลอดภัยต่อระบบปฏิบัติการของโรงพยาบาล และสะดวกต่อการพัฒนาอย่างต่อเนื่องครับ