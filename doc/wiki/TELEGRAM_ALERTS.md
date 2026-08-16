# 🔔 SNC Telegram Alerts — การแจ้งเตือนผ่าน @snc2569_bot

ส่งข้อความแจ้งเตือนระบบ SNC ไปที่ Telegram bot ผ่าน Bot API (curl → `sendMessage`)
โดยไม่ต้องติดตั้ง library เพิ่ม — ใช้สคริปต์ `ops/notify-telegram.sh`

## สิ่งที่จะแจ้งเตือน (wired แล้ว)

| เหตุการณ์ | เมื่อไหร่ | ผ่าน |
|---|---|---|
| 🎉 Burn-in ครบ 48 ชม. | 15 ส.ค. 03:05 (cron one-shot) | `post-burnin-finalize.sh` step 6 |
| (เพิ่มเติมได้) สถานะ burn-in ทุก 6 ชม. / สายหลุด PBX | — | ผูกต่อจาก `burnin-reminder.sh` / `pbx_watchdog.sh` ได้ |

## ตั้งค่าครั้งเดียว (ต้องมี token + chat_id)

### 1) ขอ token จาก @BotFather
1. เปิด Telegram → ค้นหา `@BotFather` → `/newbot`
2. ตั้งชื่อ bot และ username (เช่น `snc2569_bot`)
3. BotFather จะให้ **token** รูปแบบ `1234567890:AAH...` — บันทึกไว้

### 2) หา chat_id (ปลายทางที่ bot จะส่งหา)
วิธีที่ง่ายที่สุด — ส่งข้อความอะไรก็ได้ (เช่น `/start`) ไปที่ bot ของเราก่อน แล้วรัน:
```bash
curl -s "https://api.telegram.org/bot<TOKEN>/getUpdates" | python3 -m json.tool
```
ดูค่า `message.chat.id` (บุคคล = เลขบวก เช่น `123456789` / กลุ่ม = เลขติดลบ `-100...`)

> 💡 ถ้าใช้ bot ส่งหา**ตัวเอง** ต้องกด `/start` กับ bot ก่อน 1 ครั้ง (ไม่งั้น Telegram ปฏิเสธ)

### 3) ใส่ key ลง .env บน Pi (ห้าม commit ใน git)
```bash
ssh pi4
nano /home/ecs-agent/snc-poc/api/.env    # ต่อท้าย 2 บรรทัดนี้
```
```
TELEGRAM_BOT_TOKEN=1234567890:AAH...
TELEGRAM_CHAT_ID=123456789
```
บันทึกแล้ว `chmod 600 /home/ecs-agent/snc-poc/api/.env` (สคริปต์อ่านจาก env → `api/.env` → `.env` → `backend/.env` → `pbx-connector/.env` ตามลำดับ 5-Core)

### 4) ทดสอบ
```bash
ssh pi4 '/home/ecs-agent/snc-poc/ops/notify-telegram.sh "🔔 ทดสอบ SNC Telegram — OK"'
```
ควรได้ `[notify-telegram] ส่งสำเร็จ ✅` และข้อความเด้งในแอป
ถ้ายังไม่ตั้ง key → ข้ามเงียบ ๆ (`SKIP`) ไม่ทำให้ cron ผิดพลาด

## ปลอดภัย
- Token เป็นความลับ → อยู่ใน `.env` (chmod 600) เท่านั้น, ไม่เคย commit ลง git
- สคริปต์ส่งเฉพาะข้อความที่เรากำหนด — ไม่รับคำสั่ง/ไม่เปิดช่องโหว่ (Bot API ฝั่งส่งออกอย่างเดียว)
- `notify-telegram.sh` พร้อมใช้ทั่วไป: เรียกจาก cron/script อื่นได้ทุกที่ในโปรเจกต์

## บันทึกการตั้งค่าปัจจุบัน (14 ส.ค. 2569)

| รายการ | ค่า |
|---|---|
| Bot username | `@snc2569_bot` (ชื่อ "snc") |
| ปลายทางแจ้งเตือน (chat_id) | `7346817215` (บัญชี "lnw") |
| Token | เก็บใน `/home/ecs-agent/snc-poc/api/.env` → `TELEGRAM_BOT_TOKEN` (chmod 600) — **ไม่บันทึกใน wiki/git** |
| สถานะ | ✅ ทดสอบส่งสำเร็จ 14 ส.ค. 2569 |
| จุดผูก | `post-burnin-finalize.sh` step 6 — แจ้ง "Burn-in ครบ" อัตโนมัติ 15 ส.ค. 03:05 |
| Verify รายวัน | `verify-daily.sh` (cron 07:00, `VERIFY_ALWAYS=1`) — ส่งสรุปทุกเช้า + แจ้งเตือนทันทีเมื่อพบปัญหา → `verify_daily.log` |
| สคริปต์ | `ops/notify-telegram.sh` (repo) → `/home/ecs-agent/snc-poc/notify-telegram.sh` (Pi) |

### ⚠️ หมายเหตุความปลอดภัย (token rotation)
Token เคยถูกแชร์ในแชท (ตรวจแล้ว **ไม่มีการ commit ลง git**) แต่เพื่อความปลอดภัยสูงสุด
แนะนำ **rotate token** ผ่าน @BotFather หลังยืนยันว่าระบบแจ้งเตือนทำงานครบแล้ว:
1. Telegram → @BotFather → `/mybots` → @snc2569_bot → API Token → **Revoke** (สร้างใหม่)
2. อัปเดต `/home/ecs-agent/snc-poc/backend/.env` → `TELEGRAM_BOT_TOKEN=<token ใหม่>`
3. ทดสอบใหม่: `/home/ecs-agent/snc-poc/notify-telegram.sh "ทดสอบ rotate ✅"`
(chat_id ไม่เปลี่ยน — ใช้ของเดิมได้)

## ☁️ Cloud Monitoring uptime check → Telegram (bridge service แยก, ไม่พึ่ง Pi)

GCP ตรวจ `/health` ของ Cloud Run เองทุก 5 นาที (แม้ Pi ตายก็ยังเช็ค) — พบ fail 120s
→ ส่ง webhook ไปที่ **`snc-alert-bridge`** (Cloud Run service แยกจาก backend หลัก) → แจ้ง Telegram:

| รายการ | ค่า |
|---|---|
| bridge service | `snc-alert-bridge` (`api/bridge_server.py` — จิ๋ว, ไม่ import backend เลย) |
| uptime check | `snc-cloud-run-health` (GET `/health` ของ backend หลัก, 300s, ASIA_PACIFIC) |
| alert policy | `SNC Cloud Run uptime alert` (fail 120s → autoClose 3600s) |
| channel | webhook_tokenauth → `BRIDGE_URL/webhook?token=...` |
| auth | `?token=MONITOR_WEBHOOK_TOKEN` หรือ header `X-SNC-Token` (fail-closed) |
| env บน bridge | `TELEGRAM_BOT_TOKEN` / `TELEGRAM_CHAT_ID` / `MONITOR_WEBHOOK_TOKEN` |
| **ข้อดี** | bridge อยู่คนละ service กับ backend หลัก → alert ส่งถึง **แม้ backend หลัก down** |

### ตั้งค่า (ครั้งเดียว — deploy bridge ก่อน แล้วค่อยตั้ง monitoring)
```bash
# ใน Cloud Shell — 1) deploy bridge service (ต้องการ TELEGRAM env)
export TELEGRAM_BOT_TOKEN="<จาก api/.env บน Pi4>"
export TELEGRAM_CHAT_ID="7346817215"
bash ops/deploy_bridge_cloudshell.sh
# 2) ตั้ง uptime check + alert (idempotent — รันซ้ำได้, ดึง token จาก bridge อัตโนมัติ)
bash ops/setup_cloud_monitoring.sh
```
สคริปต์จะทดสอบ bridge จริงตอนท้าย — ควรเห็นข้อความ "GCP Monitoring: Cloud Run ผิดปกติ" ใน Telegram

---

## 🤖 โหมด Q&A — คุยกับ SNC Agent 2 ทาง

นอกจากแจ้งเตือน (1 ทาง) แล้ว ยังมี agent ตอบคำถามได้ (2 ทาง) ผ่าน `ops/snc_telegram_agent.py`:
- zero dependency (urllib), poll `getUpdates`, **ฟรี 100%** ไม่เรียก AI ภายนอก ไม่ต้องเปิดพอร์ตสาธารณะ
- ตอบสถานะจริงจาก backend + burnin.log

### คำสั่งที่ถามได้
| คำสั่ง | ตอบ |
|---|---|
| `/kpi` | SLA/KPI ล่าสุด |
| `/rooms` | สายเรียกค้าง + เหตุการณ์ล่าสุด |
| `/burn` | สถานะ burn-in (ผ่านไป/เหลือกี่ชม.) |
| `/status` | backend health + services |
| `/help` | รายการคำสั่ง |

พิมพ์ภาษาไทยได้ เช่น "ห้องไหนค้าง", "burn ถึงไหนแล้ว" และถามเกี่ยวกับตัว agent เองได้ เช่น
"อธิบายเกี่ยวกับ skill snc agent ทำงานที่ไหน สังกัดอะไร มีขอบเขตแค่ไหน" → ตอบที่อยู่/สังกัด/ขอบเขต/ข้อจำกัด
(trigger คำ: skill / agent / อธิบาย / เกี่ยวกับ / ขอบเขต / สังกัด / ทำงาน)

### วิธีรัน (ง่ายสุด ไม่ต้อง sudo)
```bash
ssh pi4 'cd /home/ecs-agent/snc-poc && nohup python3 ops/snc_telegram_agent.py >> tg_agent.log 2>&1 &'
```

### รันถาวร (systemd — ✅ ใช้จริงแล้ว)
ติดตั้งเป็น service `snc-tg-agent` แล้ว (รอด reboot + auto-restart) — รันจาก repo root:
```bash
sudo cp ops/snc-tg-agent.service /etc/systemd/system/
sudo systemctl daemon-reload && sudo systemctl enable --now snc-tg-agent
```

### ความปลอดภัย
- ตอบเฉพาะ chat_id ใน `SNC_TG_ALLOWED_CHAT` (ตั้งแล้ว = `7346817215`) — บัญชีอื่นได้แต่ข้อความปฏิเสธ
- ต่อยอดเป็น AI ได้: ใส่ `GEMINI_API_KEY` แล้วดัดแปลง fallback → Gemini (project มี `gemini_direct_service.py` อยู่แล้ว)

## 🌙 สรุปประจำเย็น (evening digest)

`ops/snc-evening-digest.sh` ส่งสรุปสถานะ + ทิปการใช้งานแบบหมุนเวียน 1 ข้อทุกวัน
ไปที่ Telegram อัตโนมัติ:

| รายการ | ค่า |
|---|---|
| cron (บน Pi) | `0 19 * * *` (19:00 ทุกวัน) |
| เนื้อหา | KPI + สายค้าง + ทิปประจำวัน (หมุนเวียน 7 ข้อจากคู่มือ troubleshooting) |
| log | `/home/ecs-agent/snc-poc/evening_digest.log` |
| วิธีรันเอง | `ssh pi4 '/home/ecs-agent/snc-poc/snc-evening-digest.sh'` |

สถานะปัจจุบัน: ✅ ติดตั้ง cron แล้ว (14 ส.ค. 2569) — รันจริงครั้งแรก 19:00 ของวันที่ครบ burn-in
