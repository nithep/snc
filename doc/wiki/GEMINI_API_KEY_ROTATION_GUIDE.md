---
title: "🔄 คู่มือหมุนเวียน GEMINI_API_KEY (Rotation Guide)"
type: guide
tags: [security, ai]
---

# 🔄 คู่มือหมุนเวียน GEMINI_API_KEY (Rotation Guide)

> **เวอร์ชั่น:** 1.0 | **อัปเดตล่าสุด:** 20 ส.ค. 2569
> **ใช้กับ:** Smart Nurse Call (SNC) PoC — โครงสร้าง 5-Core (`doc/BLUEPRINT_5CORE.md`)
> **เกี่ยวข้อง:** `SNC_API_KEY_ROTATION_GUIDE.md` · `doc/ADR/0005-iac-terraform.md`

---

## 📌 ควร rotate เมื่อไหร่

| กรณี | ความเร่งด่วน |
|---|---|
| Key รั่วใน git history / เอกสาร / ถูกเผยแพร่ | 🔴 เร่งด่วนสุด |
| สงสัยว่ามีคนนอกทราบ key | 🔴 เร่งด่วน |
| ทีมมีคนออก / สิทธิ์เปลี่ยน | 🟡 เร็วที่สุด |
| หมุนเวียนประจำ (ทุก 90 วัน) | 🟢 ตามกำหนด |
| โดน Free Tier Rate Limit (429) เรื้อรัง หรือสงสัย key ถูกนำไปใช้ผู้อื่น | 🟡 ควรเปลี่ยน key ใหม่ |

> **หมายเหตุ Free Tier:** `GEMINI_API_KEY` ใช้กับ **Gemini API Free Tier** (สมัครฟรีที่ Google AI Studio ไม่ต้องบัตรเครดิต)
> Key ตัวนี้ควบคุมโควต้า RPM/RPD ของบอท SNC-Bot และฟีเจอร์ AI สรุปรายวัน
> การ rotate จะ**เริ่มนับโควต้าใหม่** และตัดการใช้งานของ key เก่าทันที

---

## ⚙️ หลักการสำคัญ

1. **key ต้องตรงกันระหว่าง Edge (Pi4) กับ Cloud (Cloud Run)** — ถ้าขัดกัน อีกด้านจะได้ `401/429` และ SNC-Bot จะคืนข้อความ *"ระบบ AI ไม่พร้อมให้บริการชั่วคราว"*
2. **ห้าม hardcode ลงโค้ด/เอกสาร** — key อยู่ใน `.env` (chmod 600) หรือ Secret Manager เท่านั้น
3. **ห้าม commit `.env` ลง git** — `.gitignore` ครอบคลุมอยู่แล้ว (ดู `AGENTS.md` ข้อ 5)
4. **key เก่าต้องเพิกถอน (revoke) ทันที** — หลัง rotate เสร็จ ให้ revoke key เก่าบน Google AI Studio## 📍 ตำแหน่ง key ทั้งระบบ (5-Core)| Component | ตำแหน่ง | วิธีอ่าน ||---|---|---|| Backend (Pi4 Edge) | `/home/ecs-agent/snc/api/.env` (บรรทัด `GEMINI_API_KEY=`) | `grep GEMINI_API_KEY /home/ecs-agent/snc/api/.env` || Backend (Cloud Run) | GCP **Secret Manager** — secret `snc-gemini-api-key` (mount เป็น env เมื่อ deploy) ⚠️ **ใช้งานบังคับแล้วตั้งแต่ 26 ส.ค. 2569** | `gcloud secrets versions access latest --secret=snc-gemini-api-key` || Local dev | `api/.env` (ไม่ deploy ขึ้น Pi โดยตรง — ใช้ `ops/.env` / `.env.example` เป็นแม่แบบ) | `grep GEMINI_API_KEY api/.env` || Client | — ไม่มี (SNC-Bot เรียกผ่าน backend เท่านั้น) | — |> **สถานะ 26 ส.ค. 2569:** ย้าย `GEMINI_API_KEY` ขึ้น Secret Manager บน Cloud Run แล้ว — deploy ด้วย `--set-secrets GEMINI_API_KEY=snc-gemini-api-key:latest` + `--remove-env-vars GEMINI_API_KEY` (เลิก plaintext env บน service), ให้สิทธิ์ `roles/secretmanager.secretAccessor` แก่ Cloud Run SA แล้ว, ทดสอบ `/api/ai/snc-bot` ผ่าน (rev `00026-sbm`)

---

## 🔄 วิธี rotate (ขั้นตอน)

### ขั้นที่ 1 — สร้าง key ใหม่ (Google AI Studio)
1. เปิด https://aistudio.google.com/apikey → **Create API Key**
2. คัดลอก key ใหม่ (ขึ้นต้น `AIza...`) เก็บไว้ชั่วคราวใน password manager

### ขั้นที่ 2 — อัปเดตบน Pi4 (Edge)
```bash
# 1) backup
cp /home/ecs-agent/snc/api/.env /home/ecs-agent/snc/api/.env.bak.$(date +%Y%m%d%H%M%S)

# 2) เปลี่ยนค่า (แทนที่ทั้งบรรทัด)
sed -i "s|^GEMINI_API_KEY=.*|GEMINI_API_KEY='<KEY_ใหม่>'|" /home/ecs-agent/snc/api/.env

# 3) restart service
sudo systemctl restart snc-backend.service
sudo systemctl is-active snc-backend.service   # ต้องได้ active
```

### ขั้นที่ 3 — อัปเดตบน Cloud Run (ถ้าใช้)
```bash
gcloud secrets versions add snc-gemini-api-key --data-file=- <<< '<KEY_ใหม่>'
# แล้ว redeploy (ดู ops/deploy_gcp_cloudrun.ps1 / deploy_cloudrun_cloudshell.sh)
```

### ขั้นที่ 4 — ตรวจสอบ (Verify)
```bash
# ทดสอบ SNC-Bot endpoint บน Pi
curl -s -X POST http://localhost:8000/api/ai/snc-bot \
  -H 'Content-Type: application/json' \
  -d '{"message":"SLA ของระบบ SNC คืออะไร"}'
# ต้องได้ {"status":"success","answer":"..."}  ไม่ใช่ข้อความ "ไม่พบ API Key"

# ทดสอบผ่านสาธารณะ
curl -s https://snc.nithep.com/api/ai/snc-bot -X POST -H 'Content-Type: application/json' \
  -d '{"message":"ทดสอบ"}'
```

### ขั้นที่ 5 — เพิกถอน key เก่า
กลับไปที่ Google AI Studio → เลือก key เก่า → **Delete** (revoke) ทันที

---

## 🧪 กรณีฉุกเฉิน: ตัดการใช้งานชั่วคราว

หากสงสัย key รั่วแต่ยังเปลี่ยนไม่ทัน ให้ลบบรรทัด `GEMINI_API_KEY=` ออกจาก `.env` แล้ว restart
→ ระบบจะ degrade อย่างสวยงาม: SNC-Bot คืนข้อความ *"ระบบ AI ไม่พร้อมให้บริการชั่วคราว"* (ดู `_SNC_FALLBACK_MSG` ใน `api/services/gemini_direct_service.py`) และไม่ crash

---

## ✅ Checklist หลัง rotate

- [ ] สร้าง key ใหม่ใน Google AI Studio
- [ ] อัปเดต `api/.env` บน Pi4 + restart service
- [ ] (ถ้ามี) อัปเดต Secret Manager + redeploy Cloud Run
- [ ] ทดสอบ `/api/ai/snc-bot` ได้คำตอบจริง (ไม่ใช่ "ไม่พบ API Key")
- [ ] ทดสอบ `/api/ai/daily-summary` ได้รายงานสรุป
- [ ] Revoke key เก่าบน Google AI Studio
- [ ] ไม่มี `.env` หลุดเข้า git (`git status --ignored`)
