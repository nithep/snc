---
title: "🏥 SNC Health Monitoring — /health schema + Telegram เมนูตรวจระบบ"
type: wiki
tags: [snc, monitoring, health, telegram, alerting, systemd]
updated: 2026-09-02
---

# 🏥 SNC Health Monitoring — /health + เมนูตรวจระบบผ่าน Telegram

> มาตรฐานใหม่ (commit `1755202`): ทุกข้อความตรวจสอบ/แจ้งเตือนต้องมี
> **สถานะรวม + รายการตรวจราย service + สาเหตุ + เมนูถัดไป** — ห้ามมีข้อความกำกวม
> แบบ `services: active, active` อีก

---

## 1. `/health` Response Schema

`GET /health` คืนผลตรวจราย service เสมอ:

```json
{
  "status": "healthy",
  "service": "snc-backend",
  "db": "sqlite",
  "timestamp": "2026-09-02T01:13:34",
  "checked_at": "2026-09-02T01:13:34",
  "reason": "ไม่พบความผิดปกติจาก Backend health check",
  "checks": {
    "backend":      {"status": "healthy", "message": "ตอบสนองปกติ"},
    "database":     {"status": "healthy", "message": "เชื่อมต่อได้ (sqlite)"},
    "pbx_listener": {"status": "active",  "message": "systemd active"},
    "websocket":    {"status": "healthy", "message": "พร้อมรับการเชื่อมต่อ"},
    "cloud_run":    {"status": "ready",   "message": "พร้อมให้บริการ"}
  }
}
```

### สถานะรวม (aggregate)

| เงื่อนไข | `status` |
|---|---|
| ไม่มี check ใด down/degraded/unknown | `healthy` |
| มี check เป็น `degraded` หรือ `unknown` | `degraded` |
| มี check เป็น `down` หรือ `failed` | `down` |

### ความหมายสถานะ `pbx_listener` ตามสภาพแวดล้อม

| สภาพแวดล้อม | วิธีตรวจ | สถานะที่เป็นไปได้ |
|---|---|---|
| **Edge Pi4** (production) | `systemctl is-active snc-pbx-listener.service` จริง | `active` / `degraded` / `down` |
| **Cloud Run** (container) | ไม่มี systemd → ข้าม | `skipped` (ไม่นับเป็นปัญหา) |
| **Windows dev** | ไม่มี systemctl → ข้าม | `skipped` |

> ⚠️ `skipped` **ไม่ใช่ failure** — ออกแบบเพื่อกัน false alarm: uptime check ของ GCP
> และ `deploy-snc-one-shot.sh` (grep `"status":"healthy"`) ต้องได้ `healthy` บน Cloud Run เสมอ

---

## 2. เมนูคำสั่ง Telegram (@snc2569_bot)

| คำสั่ง | หน้าที่ |
|---|---|
| `/health` | ผลตรวจราย service + สาเหตุ + เมนูถัดไป |
| `/status` | เหมือน `/health` |
| `/cloudrun` | สรุป Cloud Run + db backend |
| `/uptime` | ข้อมูล uptime check endpoint |
| `/logs` | journalctl ล่าสุด 20 บรรทัด (เฉพาะบน Pi — ที่อื่นตอบ graceful) |
| `/kpi` `/rooms` `/burn` `/alerts` | เดิม — KPI/สายค้าง/burn-in/ledger |
| `/help` | เมนูทั้งหมด |

ตัวอย่าง `/health` เมื่อปกติ:

```text
✅ ผลตรวจสุขภาพระบบ SNC
เวลา: 2026-09-02T01:36:28
สถานะรวม: HEALTHY

รายการตรวจสอบ:
✅ Backend API: ตอบสนองปกติ
✅ Database: เชื่อมต่อได้ (sqlite)
✅ PBX Listener: systemd active
✅ WebSocket: พร้อมรับการเชื่อมต่อ
✅ Cloud Run: พร้อมให้บริการ

สาเหตุที่ตรวจพบ: ไม่พบความผิดปกติจาก Backend health check

เมนูถัดไป: /cloudrun | /logs | /uptime
```

กรณี backend ล่ม ข้อความเป็น `DOWN` + สาเหตุ (HTML-escaped) + แนะนำ `/logs` `/cloudrun`

---

## 3. Template Alert (ops/alerting.py)

ทุก alert มี 4 ส่วนตามที่ผู้ดูแลร่วมกันตกลง:

```text
🚨 ระบบ SNC พบความผิดปกติ
สถานะรวม: CRITICAL
เวลา: 2026-09-02 01:09:47
รหัส: SNC-AL-CLOUD-20260902-010947

รายการตรวจสอบ:
❌ Service ที่เกี่ยวข้อง: Cloud Run uptime check /health failed

สาเหตุที่ตรวจพบ:
Uptime check snc-cloud-run-health ล้มเหลวต่อเนื่อง 120 วินาที

หลักฐาน/วิธีตรวจสอบ:
curl https://snc-cloud-backend-...run.app/health

เมนูถัดไป: /health | /cloudrun | /logs | /uptime

📋 ขั้นตอนกู้คืน: (ตาม type: POWER/TUNNEL/BACKEND/CLOUD)
```

ทดสอบ template โดยไม่ส่งจริง:

```bash
python3 ops/alerting.py --dry-run --severity CRITICAL --type CLOUD \
  --summary "ทดสอบ" --details "..." --verify "..."
```

---

## 4. หมายเหตุ: Cloudflare WAF บล็อก python-urllib

- `https://snc.nithep.com` **บล็อก UA `Python-urllib*` ด้วย 403** (WAF bot rule)
- `snc_telegram_agent.py` จึงตั้ง `User-Agent: SNC-Telegram-Agent/1.0` ทุก request
- Production บน Pi ใช้ `http://localhost:8000` อยู่แล้ว — ไม่กระทบ
- สคริปต์ Python ตัวใหม่ที่ยิงเข้า tunnel ตรง ๆ ต้องตั้ง UA เองด้วย

---

## 5. การทดสอบ

```bash
# unit tests (ไม่ต้องมี pytest)
python -m unittest tests.test_health_monitoring -v
```

ครอบคลุม: mapping สถานะ systemd, `skipped` บนเครื่องไม่มี systemd,
ฟอร์แมตข้อความ agent (ห้าม `active, active`), HTML-escape, graceful `/logs`,
template alert 4 ส่วน

---

## 6. ไฟล์ที่เกี่ยวข้อง

| ไฟล์ | บทบาท |
|---|---|
| `api/server.py` | `/health` + `_systemd_service_status()` |
| `ops/snc_telegram_agent.py` | คำสั่ง/เมนู Telegram + `SNC-Telegram-Agent/1.0` UA |
| `ops/alerting.py` | template alert + ledger `logs/alerts.log` |
| `ops/setup_cloud_monitoring.sh` | uptime check → webhook → bridge → Telegram |
| `tests/test_health_monitoring.py` | unit tests |
