# 🔄 คู่มือหมุนเวียน SNC_API_KEY (Rotation Guide)

> **เวอร์ชัน:** 1.0 | **อัปเดตล่าสุด:** 16 ส.ค. 2569
> **ใช้กับ:** Smart Nurse Call (SNC) PoC — โครงสร้าง 5-Core (`doc/BLUEPRINT_5CORE.md`)

---

## 📌 ควร rotate เมื่อไหร่

| กรณี | ความเร่งด่วน |
|---|---|
| Key รั่วใน git history / เอกสาร / ถูกเผยแพร่ | 🔴 เร่งด่วนสุด |
| สงสัยว่ามีคนนอกทราบ key | 🔴 เร่งด่วน |
| ทีมมีคนออก / สิทธิ์เปลี่ยน | 🟡 เร็วที่สุด |
| หมุนเวียนประจำ (ทุก 90 วัน) | 🟢 ตามกำหนด |

**ตัวอย่างจริง (15 ส.ค. 2569):** key `340e28ca...` ถูก commit ใน `doc/wiki/POST_BURNIN_FIELD_TEST_PLAN.md` → ต้อง rotate + purge จาก git history (`git filter-repo`)

---

## ⚙️ หลักการสำคัญ

1. **key เดียวกันทั้งระบบ** — backend `.env` กับ listener `.env` ต้องตรงกันเป๊ะ ไม่งั้นเหตุการณ์จาก PBX จะโดน 401 ทิ้งเงียบๆ
2. **ห้าม hardcode ลงโค้ด/เอกสาร** — key อยู่ใน `.env` (chmod 600) เท่านั้น
3. **ห้าม commit `.env` ลง git** — `.gitignore` ครอบคลุมอยู่แล้ว
4. **key เก่าต้องทิ้งทันที** — หลัง rotate เสร็จ key เก่าไร้ค่า

---

## 📍 ตำแหน่ง key ทั้งระบบ (5-Core)

| Component | ตำแหน่ง | วิธีอ่าน |
|---|---|---|
| Backend (Pi4) | `/home/ecs-agent/snc-poc/api/.env` | `grep SNC_API_KEY api/.env` |
| Listener (Pi4) | `/home/ecs-agent/snc-poc/pbx/.env` | `grep SNC_API_KEY pbx/.env` |
| Cloud Run | env var `SNC_API_KEY` | `gcloud run services describe snc-cloud-backend --region asia-southeast1` |
| Dashboard (เบราว์เซอร์) | `localStorage` ของแต่ละเครื่อง | ⚙️ ตั้งค่า → API Key |

---

## 🔄 ขั้นตอน rotate (ฉบับสมบูรณ์)

### Step 1: สร้าง key ใหม่

```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
# หรือ (Windows ไม่มี python)
openssl rand -hex 32
```

ผลลัพธ์: 64 ตัวอักษร hex (32 bytes) เช่น `48bc5efd...` — **เก็บไว้ในที่ปลอดภัยก่อน**

### Step 2: Backup .env เดิมบน Pi4 (กันพลาด)

```bash
ssh pi4 "cd /home/ecs-agent/snc-poc && ts=\$(date +%Y%m%d%H%M%S) && \
  cp api/.env backups/api.env.\$ts && cp pbx/.env backups/pbx.env.\$ts && \
  echo \"Backup: backups/*.\$ts\""
```

### Step 3: อัปเดต key บน Pi4 (ทั้ง 2 ไฟล์ ต้อง key เดียวกัน)

```bash
NEW_KEY="<key ที่สร้างใน Step 1>"

ssh pi4 "cd /home/ecs-agent/snc-poc && \
  sed -i 's|^SNC_API_KEY=.*|SNC_API_KEY=$NEW_KEY|' api/.env pbx/.env && \
  chmod 600 api/.env pbx/.env && \
  grep '^SNC_API_KEY' api/.env pbx/.env | sed 's/=\(.\{6\}\).*/=\1.../'"
```

> ⚠️ **ถ้า `pbx/.env` ไม่มีอยู่** — สร้างใหม่ (ต้องมี `SNC_API_KEY` เท่านั้น):
> ```bash
> ssh pi4 "echo 'SNC_API_KEY=$NEW_KEY' > /home/ecs-agent/snc-poc/pbx/.env && chmod 600 /home/ecs-agent/snc-poc/pbx/.env"
> ```

### Step 4: Restart services

```bash
ssh pi4 "sudo systemctl restart snc-backend.service snc-pbx-listener.service && \
  sleep 3 && systemctl is-active snc-backend.service snc-pbx-listener.service"
```

### Step 5: ตั้ง key ที่ Cloud Run

รันใน **Cloud Shell** หรือเครื่องที่มี gcloud:

```bash
gcloud run services update snc-cloud-backend \
  --project hotel-ecs-nithep \
  --region asia-southeast1 \
  --set-env-vars "SNC_API_KEY=<key ใหม่>"
```

> ℹ️ ถ้า Cloud Run รัน image เก่า (ไม่มี routes API) ให้ redeploy พร้อมกัน:
> ```bash
> gcloud builds submit --config api/cloudbuild.yaml --project hotel-ecs-nithep .   # context = repo root (image ต้องมี app/ ด้วย)
> gcloud run deploy snc-cloud-backend --image gcr.io/hotel-ecs-nithep/snc-cloud-backend:latest \
>   --platform managed --region asia-southeast1 --allow-unauthenticated \
>   --project hotel-ecs-nithep --set-env-vars "SNC_API_KEY=<key ใหม่>"
> ```
> *(หรือใช้ `ops/deploy_gcp_cloudrun.ps1` ซึ่งตั้ง key อัตโนมัติจาก `$env:SNC_API_KEY`)*

### Step 6: ตรวจสอบ auth (ไม่สร้างข้อมูล — ใช้ room 9999)

```bash
# key เก่า → ต้อง 401
curl -s -o /dev/null -w 'old key → HTTP %{http_code}\n' \
  -X POST http://localhost:8000/api/events/acknowledge/9999 \
  -H "X-API-Key: <key เก่า>"

# key ใหม่ → ต้อง 200
curl -s -o /dev/null -w 'new key → HTTP %{http_code}\n' \
  -X POST http://localhost:8000/api/events/acknowledge/9999 \
  -H "X-API-Key: <key ใหม่>"

# ไม่มี key → ต้อง 401
curl -s -o /dev/null -w 'no key → HTTP %{http_code}\n' \
  -X POST http://localhost:8000/api/events/acknowledge/9999
```

### Step 7: แจ้งทีม/อัปเดตแดชบอร์ด

- เบราว์เซอร์พยาบาลที่เคยกรอก key เก่า → จะเจอ 401 → เปิด ⚙️ ตั้งค่า → กรอก key ใหม่
- (ระบบจะเด้งหน้าตั้งค่าให้อัตโนมัติเมื่อเจอ 401)

---

## ✅ Checklist หลัง rotate

- [ ] `api/.env` และ `pbx/.env` มี key ใหม่ **ตรงกัน** (chmod 600)
- [ ] Services ทั้ง 2 active + `/health` healthy
- [ ] Cloud Run env var อัปเดต (ถ้าใช้งาน)
- [ ] key เก่า → 401, key ใหม่ → 200, ไม่มี key → 401
- [ ] เหตุการณ์จาก PBX เข้าระบบปกติ (ดู `backend.log` ไม่มี 401 จาก listener)
- [ ] ไม่มี key เก่าหลงเหลือใน repo/เอกสาร (grep ตรวจ)

---

## ↩️ Rollback (ถ้าจำเป็น)

```bash
ssh pi4 "cd /home/ecs-agent/snc-poc && \
  cp backups/api.env.<ts> api/.env && cp backups/pbx.env.<ts> pbx/.env && \
  sudo systemctl restart snc-backend.service snc-pbx-listener.service"
```

---

## 🔍 กรณี key รั่วใน git history

1. rotate key ตามคู่มือนี้ก่อน (สำคัญที่สุด — key เก่าไร้ค่าทันที)
2. purge จาก history:
   ```bash
   # สร้างไฟล์ rules (อยู่ .freebuff/ ที่ gitignored)
   echo "OLD_KEY==>SNC_API_KEY_REDACTED" > .freebuff/replace.txt
   git filter-repo --replace-text .freebuff/replace.txt --force
   git remote add origin https://github.com/nithep/snc.git
   git push --force origin main
   ```
3. sync Pi4 clone:
   ```bash
   ssh pi4 "cd /home/ecs-agent/snc-poc && git fetch origin && git reset --hard origin/main"
   ```

---

*จัดทำโดย: Senior Software Engineer — 16 ส.ค. 2569*
