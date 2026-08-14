# 🏥 การวิเคราะห์และข้อเสนอแนะเชิงลึกสำหรับระบบ Smart Nurse Call (SNC)

บทวิเคราะห์ฉบับนี้จัดทำขึ้นโดยทีมวิศวกรอาวุโส (Ant/Cur) เพื่อสรุปแนวทางการวิเคราะห์ความถูกต้องและวิธีแก้ไขปัญหาทางเทคนิคสำคัญ 4 ด้านของระบบ **Smart Nurse Call (SNC)** บน Raspberry Pi 4 ตามข้อสั่งการและข้อจำกัดเครือข่ายหน้างาน

---

## 1. 📡 ปัญหาการเชื่อมต่อตู้ PBX (Phonik PBX Telnet Connection)

### 🔍 การวิเคราะห์ทางเทคนิค (Analysis & Root Causes)
1. **การตรวจสอบพอร์ต 23 (Telnet/SMDR)**:
   - ตู้สาขา Phonik DX Series มีคุณสมบัติการส่งบันทึกเหตุการณ์ (SMDR) ผ่านพอร์ต LAN (TCP Port 23) แต่ในทางปฏิบัติ **มักจะถูกปิดไว้เป็นค่าเริ่มต้น (Disabled by default)** หรือต้องระบุ **IP ปลายทางที่อนุญาตให้ส่งข้อมูล (Target IP Bound)** ในการตั้งค่าของตู้
   - การรันคำสั่ง `telnet 192.168.1.91 23` จากเครื่อง Raspberry Pi 4 (`192.168.1.94`) เป็นเครื่องมือวิเคราะห์ที่เร็วที่สุด:
     - หากขึ้น `Connection refused` แสดงว่าพอร์ต 23 บนตู้ไม่ได้เปิดใช้งาน หรือพอร์ตถูก Firewall บล็อก
     - หากขึ้น `Connected` แต่ไม่มีข้อมูลไหลเข้ามาเลยแม้ว่าจะกดเรียกจากเตียงคนไข้ แสดงว่าตู้ PBX ไม่ได้เปิดสตรีมข้อมูล SMDR หรือมีการล็อค IP ปลายทางที่ตู้ (ต้องไปเพิ่ม IP `192.168.1.94` ในตู้)
2. **ความยืดหยุ่นของ Regex Parser (`SMDR_PATTERN`)**:
   - รูปแบบที่ใช้อยู่: `r"==SMDX\d+=\d{2}/\d{2}/\d{2}\s+\d{2}:\d{2}\s+(\d+)\s+([\w\.\=\-]+)"`
   - ตู้ Phonik บางรุ่นส่งสัญญาณโดยมีเว้นวรรคไม่เท่ากัน หรือไม่มีเครื่องหมาย `=` ระหว่าง `==SMDX` กับหมายเลขลำดับ 
   - ข้อความที่บกพร่องทางโครงสร้างจะไม่ตรงกับ Pattern นี้ ส่งผลให้ `parse_smdr_line` คืนค่า `None`
   - สังเกตจากโค้ดสำรอง (Fallback) บรรทัดที่ 39-44 ที่ดักจับเฉพาะ `e.room_id` โดยไม่สนใจโครงสร้างท่อนแรก ซึ่งช่วยให้ระบบทนทานขึ้น แต่จะเสียข้อมูล `station_ext` และอาจสับสนได้เมื่อมีการยกหูตอบรับ (`onM`) หรือวางสาย (`offM`)

### 💡 แนวทางแก้ไขและพัฒนา (Actionable Recommendations)
- **การทดสอบจริง**: ให้รันคำสั่งทดสอบการเปิดพอร์ตจาก Pi:
  ```bash
  nc -zv -w5 192.168.1.91 23
  # หรือ
  telnet 192.168.1.91 23
  ```
- **ปรับปรุง Regex ใน [snc_pbx_listener.py](file:///c:/Users/Nithep/ไดรฟ์ของฉัน%20(cnithep@gmail.com)/Hotel-ECS/snc-poc/pbx-connector/snc_pbx_listener.py#L18-L20)**:
  ใช้รูปแบบที่ยืดหยุ่นขึ้นเพื่อจับกลุ่มข้อความแบบทนทานต่อรูปแบบเว้นวรรค (Whitespace-insensitive):
  ```python
  # ปรับเป็นรองรับทั้งมีและไม่มีเครื่องหมาย = รวมถึงจำนวนเว้นวรรคที่ไม่เท่ากัน
  SMDR_PATTERN = re.compile(r"==SMDX\s*\d*\s*=?\s*\d{2}/\d{2}/\d{2}\s+\d{2}:\d{2}\s+(\d+)\s+(\S+)")
  ```
- **การจัดการ Welcome Banner**: เนื่องจาก PBX Connectors ในอดีตพบว่าตู้ Phonik PBX จริงมี Welcome Banner ส่งมาบล็อกบัฟเฟอร์ในตอนแรก ให้เพิ่ม logic ใน `start_listening()` เพื่ออ่านค่าทิ้งจนหมด (Flush Buffer) ในช่วง 1 วินาทีแรกหลังเปิดการเชื่อมต่อ

---

## 2. 🗄️ ความเสถียรของ Database (SQLite Optimization)

### 🔍 การวิเคราะห์ทางเทคนิค (Analysis & Root Causes)
1. **File Locking บน Docker Volume**:
   - การ Mount SQLite Database ผ่าน Docker Volume Mount ไปยัง Host OS (Debian) มีความเสี่ยงในการเกิดข้อผิดพลาด `database is locked` หรือ `unable to open database file` หาก Backend หรือ Worker มีการสร้าง Thread เขียนฐานข้อมูลพร้อมกัน
   - พฤติกรรมของ SQLite เมื่อเปิดโหมดเริ่มต้น (Rollback Journal Mode) จะทำการล็อคทั้งไฟล์แบบ Exclusive Lock เมื่อเริ่มเขียนข้อมูล ทำให้ Thread อื่นๆ อ่าน/เขียนไม่ได้ชั่วคราว
2. **พิกัดที่แท้จริง**:
   - ใน `server.py` มีการกำหนด `DB_PATH = "nurse_call_events.db"` ซึ่งอยู่ใน Path ทำงานปัจจุบัน หากมีการ Mount โฟลเดอร์จากภายนอก ให้ตรวจสอบว่าได้ย้ายไฟล์ DB ไปอยู่ในโฟลเดอร์ย่อยที่ Mount ถาวรแล้วหรือไม่

### 💡 แนวทางแก้ไขและพัฒนา (Actionable Recommendations)
- **เปิดโหมด WAL (Write-Ahead Logging)**:
  ช่วยให้ระบบสามารถเขียนและอ่านข้อมูลไปพร้อมๆ กันได้โดยไม่ต้องล็อคไฟล์ทั้งหมด เหมาะสำหรับการประมวลผลที่มีการบันทึกสถานะและสถิติพร้อมกับการคิวข้อมูล
  ```python
  def init_db():
      conn = sqlite3.connect(DB_PATH)
      # เปิด WAL Mode
      conn.execute("PRAGMA journal_mode=WAL;")
      conn.execute("PRAGMA synchronous=NORMAL;")
      # ... สร้าง Table ...
  ```
- **ปรับปรุง Connection Timeout (Retry Logic)**:
  กำหนด timeout ที่สูงขึ้น (เช่น 15 วินาที) เมื่อ SQLite ตรวจพบการล็อค จะช่วยให้ระบบรอจนกว่า lock จะหลุดแทนที่จะ Crash ทันที
  ```python
  conn = sqlite3.connect(DB_PATH, timeout=15.0)
  ```

---

## 3. 🖥️ การแจ้งเตือนแบบ Real-time (Frontend Dynamic UI)

### 🔍 การวิเคราะห์ทางเทคนิค (Analysis & Root Causes)
1. **การใช้งาน WebSocket ในปัจจุบัน**:
   - ในหน้าจอ [index.html](file:///c:/Users/Nithep/ไดรฟ์ของฉัน%20(cnithep@gmail.com)/Hotel-ECS/snc-poc/frontend/index.html) ได้มีการเชื่อมโยง WebSocket ไว้แล้ว (`ws://${BACKEND_HOST}/ws/nurse-station`) แต่ปัญหาคือตัวแปร `BACKEND_HOST` กำหนดค่าปลายทางเป็น `192.168.1.20:8000` (เป็นค่าคงที่) เมื่อระบบไปรันอยู่บน IP จริงของ Pi คือ `192.168.1.94` หรือทำงานบน Cloud / โดเมนภายนอกผ่าน Cloudflare Tunnel ส่งผลให้ WebSocket ชี้ไปผิดเครื่อง (เกิด Connection Failure)
2. **การ Mapping สถานะ**:
   - สังเกตว่าใน [server.py](file:///c:/Users/Nithep/ไดรฟ์ของฉัน%20(cnithep@gmail.com)/Hotel-ECS/snc-poc/backend/server.py#L160-L187) คำสั่ง `trigger_event` จะแปลง `CALL_BEDSIDE` ไปเป็น `CALL_TRIGGERED` จากนั้นส่งผ่าน WebSocket แต่ใน `index.html` ตัวกรองพิจารณาสถานะ `CALL_TRIGGERED` ให้แสดงเป็น `handleEmergencyCall` ซึ่งถูกต้องแล้ว แต่ขาดการรองรับประเภท `CALL_BATHROOM_EMERGENCY` ทำให้การวิเคราะห์พฤติกรรมการเรียกซ้ำ (Temporal Pattern) ที่จัดหมวดหมู่ฉุกเฉินในห้องน้ำไม่ทำงานบน UI โดยตรง

### 💡 แนวทางแก้ไขและพัฒนา (Actionable Recommendations)
- **ปรับปรุงพิกัด Host Dynamic ใน JavaScript**:
  แก้ไขการกำหนด `BACKEND_HOST` ให้ใช้ IP/Domain ปลายทางจริงของ Host ที่เสิร์ฟหน้านั้นโดยอัตโนมัติ เพื่อรองรับการทำงานทั้งผ่าน LAN IP `192.168.1.94`, Localhost และ Cloudflare Tunnel:
  ```javascript
  const BACKEND_HOST = window.location.host; // ใช้ Host + Port เดียวกับที่เบราว์เซอร์เปิดโดยตรง
  // หรือในกรณีรัน Nginx แยกพอร์ต 80 และ FastAPI พอร์ต 8000
  const BACKEND_HOST = window.location.hostname + ':8000';
  ```
- **ปรับเปลี่ยนหน้าจอเป็น React/Vite (ตามแผน Phase 3/4)**:
  การสลับโครงสร้าง Frontend ไปใช้ React (เหมือนกับโค้ดฝั่ง Hotel-ECS) จะทำให้ระบบมีเสถียรภาพในการจัดการ State ของห้องพักจำนวนมาก มีการแบ่ง Component ที่ดี และรองรับการจัดการเสียงเตือน Siren ได้อย่างแม่นยำยิ่งขึ้น

---

## 🔒 4. การรักษาความปลอดภัยเครือข่ายและระบบ API Key (Security)

### 🔍 การวิเคราะห์ทางเทคนิค (Analysis & Root Causes)
1. **การบันทึกคีย์ลงระบบ**:
   - ในไฟล์ [gemini_direct_service.py](file:///c:/Users/Nithep/ไดรฟ์ของฉัน%20(cnithep@gmail.com)/Hotel-ECS/snc-poc/backend/services/gemini_direct_service.py#L13) ปรากฏการ Hardcode ตัวแปร `GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "OPENROUTER_KEY_REDACTED...")` ซึ่งมีความเสี่ยงสูงที่จะทำให้คีย์รั่วไหลเมื่อบันทึกข้อมูลเข้าระบบ Git
2. **ความปลอดภัยบนสายเครือข่าย**:
   - การส่งข้อมูลผ่าน Local LAN ไม่ได้บังคับเข้ารหัส แต่เมื่อข้อมูลวิ่งออกนอกระบบคลาวด์ เช่น ส่งขึ้น Google Cloud Run หรือยิงการ์ดแจ้งเตือน Google Chat จำเป็นต้องใช้ HTTPS 100%

### 💡 แนวทางแก้ไขและพัฒนา (Actionable Recommendations)
- **การคุมความปลอดภัยสภาพแวดล้อม (Environment Sovereignty)**:
  ลบค่า Default Key ออกจากโค้ด และบังคับให้อ่านจาก `.env` ที่กำหนดสิทธิ์การเข้าถึงรัดกุม (`chmod 600 ~/snc-project/.env`) เท่านั้น
- **การใช้ Cloudflare Tunnel สำหรับ Secure Gateway**:
  สถาปัตยกรรมที่ถูกต้องคือการรัน **Cloudflare Tunnel Container** ควบคู่ไปกับ Backend โดยชี้ HTTPS โดเมนภายนอก (เช่น `api-nurse.nithep.com`) วิ่งเข้ามาที่คอนเทนเนอร์หลังบ้านโดยตรง ซึ่งจะได้การเข้ารหัส TLS 1.3 ตั้งแต่ Edge ไปจนถึง Cloud ของ Cloudflare โดยที่ตัวบอร์ด Pi ไม่จำเป็นต้องเปิดพอร์ตใดๆ บนเราเตอร์เลย

---

## 🛠️ 5. ขั้นตอนการดำเนินการถัดไป (Action Plan & Timeline Update)

เพื่อให้เป็นไปตามกฎของโครงการ เมื่อได้รับอนุมัติแนวทางนี้แล้ว ทางทีมจะทำการบันทึกประวัติเหตุการณ์ลงใน `/doc/wiki/project_timeline.md` และอัปเดตสถานะของคลังความรู้ OKF ใน `docs/index.md` และ `docs/log.md` ต่อไป
