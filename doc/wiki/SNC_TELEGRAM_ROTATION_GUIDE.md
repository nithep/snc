---
title: "🔄 คู่มือหมุนเวียน Telegram Token (Rotation Guide)"
type: guide
tags: [security]
---

# 🔄 คู่มือหมุนเวียน Telegram Bot Token (Rotation Guide)

> **เวอร์ชัน:** 1.0 | **อัปเดตล่าสุด:** 19 ส.ค. 2569
> **ใช้กับ:** Smart Nurse Call (SNC) PoC — โครงสร้าง 5-Core (`doc/BLUEPRINT_5CORE.md`)
> **อ้างอิง:** [`SNC_TELEGRAM_ALERTS.md`](SNC_TELEGRAM_ALERTS.md)

---

## 📌 ควร rotate เมื่อไหร่

| กรณี | ความเร่งด่วน |
|---|---|
| Token รั่วใน git history / แชท / ถูกเผยแพร่ | 🔴 เร่งด่วนสุด |
| สงสัยว่ามีคนนอกทราบ token | 🔴 เร่งด่วน |
| ทีมมีคนออก / สิทธิ์เปลี่ยน | 🟡 เร็วที่สุด |
| หมุนเวียนประจำ (ทุก 90 วัน) | 🟢 ตามกำหนด |

> **ตัวอย่างจริง:** Token เคยถูกแชร์ในแชท (ตรวจแล้วไม่มีการ commit ลง git) → แนะนำ rotate ตามคู่มือนี้เพื่อความปลอดภัยสูงสุด

---

## ⚙️ หลักการสำคัญ

1. **Bot Token ต่างจาก API Key** — ไม่ได้ยืนยัน identity ฝั่งเรา แต่เป็น "กุญแจ" ให้ bot ส่งข้อความได้ ผู้ถือ token ควบคุม bot เต็มรูปแบบ
2. **ห้าม commit token ลง git** — อยู่ใน `.env` (chmod 600) เท่านั้น
3. **chat_id ไม่ต้อง rotate** — เป็นตัวเลขปลายทาง ไม่ใช่ secret เปลี่ยนเฉพาะ token
4. **rotate แล้ว token เก่าไร้ค่าทันที** — Telegram revoke ฝั่ง @BotFather

---

## 📍 ตำแหน่ง token ทั้งระบบ (5-Core)

| Component | ตำแหน่ง | วิธีอ่าน |
|---|---|---|
| Backend (Pi4) | `/home/ecs-agent/snc-poc/api/.env` | `grep TELEGRAM_BOT_TOKEN api/.env` |
| Bridge (Cloud Run) | env var `TELEGRAM_BOT_TOKEN` | `gcloud run services describe snc-alert-bridge --region asia-southeast1` |
| TG Agent (Pi4) | service `snc-tg-agent` | อ่านจาก `api/.env` (env fallback) |

---

## 🔄 ขั้นตอน rotate (ฉบับสมบูรณ์)

### Step 1: Revoke + สร้าง token ใหม่ (ฝั่ง @BotFather)
1. เปิด Telegram → ค้นหา `@BotFather`
2. `/mybots` → เลือก `@snc2569_bot`
3. เลือก **API Token** → **Revoke current token** (สร้างใหม่)
4. คัดลอก token ใหม่ รูปแบบ `1234567890:AAH...` — **เก็บไว้ในที่ปลอดภัยก่อน**

### Step 2: Backup `.env` เดิมบน Pi4 (กันพลาด)

```bash
ssh pi4 "cd /home/ecs-agent/snc-poc && ts=\$(date +%Y%m%d%H%M%S) && \
  cp api/.env backups/api.env.\$ts && \
  echo \"Backup: backups/api.env.\$ts\""
```

### Step 3: อัปเดต token บน Pi4 (backend)

```bash
NEW_TOKEN="<token ใหม่จาก Step 1>"

ssh pi4 "cd /home/ecs-agent/snc-poc && \
  sed -i 's|^TELEGRAM_BOT_TOKEN=.*|TELEGRAM_BOT_TOKEN=$NEW_TOKEN|' api/.env && \
  chmod 600 api/.env && \
  grep '^TELEGRAM_BOT_TOKEN' api/.env | sed 's/=\(.\{10\}\).*/=\1.../'"
```

> ⚠️ **ถ้า `api/.env` ยังไม่มี `TELEGRAM_BOT_TOKEN`** — ต่อท้ายด้วย:
> ```bash
> ssh pi4 "echo 'TELEGRAM_BOT_TOKEN=$NEW_TOKEN' >> /home/ecs-agent/snc-poc/api/.env && chmod 600 /home/ecs-agent/snc-poc/api/.env"
> ```

### Step 4: อัปเดต token ที่ Cloud Run (bridge `snc-alert-bridge`)

รันใน **Cloud Shell** หรือเครื่องที่มี gcloud:

```bash
gcloud run services update snc-alert-bridge \
  --project hotel-ecs-nithep \
  --region asia-southeast1 \
  --set-env-vars "TELEGRAM_BOT_TOKEN=<token ใหม่>,TELEGRAM_CHAT_ID=7346817215,MONITOR_WEBHOOK_TOKEN=<คงเดิม>"
```

> ℹ️ หรือ redeploy bridge ผ่าน `ops/deploy_bridge_cloudshell.sh` ซึ่งอ่าน token จาก `$env:TELEGRAM_BOT_TOKEN`

### Step 5: Restart services (ถ้า TG Agent อ่าน token ฝั่ง Pi)

```bash
ssh pi4 "sudo systemctl restart snc-tg-agent && \
  sleep 2 && systemctl is-active snc-tg-agent"
```

### Step 6: ทดสอบการแจ้งเตือน

```bash
ssh pi4 '/home/ecs-agent/snc-poc/ops/notify-telegram.sh "🔔 ทดสอบ rotate Token — OK"'
```

ควรได้ `[notify-telegram] ส่งสำเร็จ ✅` และข้อความเด้งในแอป

---

## ✅ Checklist หลัง rotate

- [ ] token เก่าถูก Revoke แล้ว (ฝั่ง @BotFather)
- [ ] `api/.env` มี token ใหม่ (chmod 600)
- [ ] Cloud Run `snc-alert-bridge` env var อัปเดต (ถ้าใช้งาน)
- [ ] `notify-telegram.sh` ส่งสำเร็จ
- [ ] uptime check → Telegram ทำงาน (ดูข้อความ "GCP Monitoring: Cloud Run ผิดปกติ")
- [ ] ไม่มี token เก่าหลงเหลือใน repo/เอกสาร (grep ตรวจ)

---

## ↩️ Rollback (ถ้าจำเป็น)

```bash
ssh pi4 "cd /home/ecs-agent/snc-poc && \
  cp backups/api.env.<ts> api/.env && \
  sudo systemctl restart snc-tg-agent"
```

> ⚠️ หมายเหตุ: token เก่าถูก Revoke แล้วอาจใช้ไม่ได้ — rollback ต้องสร้าง token ใหม่แทน ไม่สามารถคืน token เดิมได้

---

*จัดทำโดย: Senior Software Engineer — 19 ส.ค. 2569*
