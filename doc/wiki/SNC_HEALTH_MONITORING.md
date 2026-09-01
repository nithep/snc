---
title: "🏥 SNC Health Monitoring — /health + การแจ้งเตือน 3 ชั้น (Pi4 · GCP · Telegram)"
type: wiki
tags: [snc, monitoring, health, telegram, alerting, systemd, cloud-run]
updated: 2026-09-02
---

# 🏥 SNC Health Monitoring — /health + การแจ้งเตือน 3 ชั้น

> มาตรฐานใหม่ (commit `1755202`): ทุกข้อความตรวจสอบ/แจ้งเตือนต้องมี
> **สถานะรวม + รายการตรวจราย service + สาเหตุ + เมนูถัดไป** — ห้ามมีข้อความกำกวม
> แบบ `services: active, active` อีก

เอกสารนี้บูรณาการ 2 เรื่องเข้าด้วยกัน:

1. **Health Check** — `/health` schema + เมนูตรวจระบบผ่าน Telegram
2. **การแจ้งเตือน (Alerting)** — เส้นทาง alert 3 ชั้น: Pi4 local, GCP Cloud Monitoring,
   และ Telegram — พร้อม template/dedupe/recovery มาตรฐานเดียวกัน

---

# ส่วนที่ 1 — Health Check

## 1.1 `/health` Response Schema

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

## 1.2 เมนูคำสั่ง Telegram (@snc2569_bot)

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

## 1.3 หมายเหตุ: Cloudflare WAF บล็อก python-urllib

- `https://snc.nithep.com` **บล็อก UA `Python-urllib*` ด้วย 403** (WAF bot rule)
- `snc_telegram_agent.py` จึงตั้ง `User-Agent: SNC-Telegram-Agent/1.0` ทุก request
- Production บน Pi ใช้ `http://localhost:8000` อยู่แล้ว — ไม่กระทบ
- สคริปต์ Python ตัวใหม่ที่ยิงเข้า tunnel ตรง ๆ ต้องตั้ง UA เองด้วย

---

# ส่วนที่ 2 — การแจ้งเตือน (Alerting Architecture)

## 2.1 ภาพรวมเส้นทาง alert 3 ชั้น

```mermaid
flowchart LR
    subgraph Pi4["🖥️ Pi4 (Edge) — local monitor"]
        CR1[cron: verify-daily.sh] --> HC[/health ตรวจเอง/]
        CR2[cron: ws-tunnel-cron.sh] --> TC[tunnel/WS check]
    end
    subgraph GCP["☁️ GCP Cloud Monitoring"]
        UP1[uptime check: Cloud Run /health ทุก 300s]
        UP2[uptime check: Pi tunnel /health ทุก 300s]
        AP[alert policy: fail 120s → OPEN]
    end
    subgraph TG["📣 Telegram @snc2569_bot"]
        MSG[ข้อความมาตรฐาน 4 ส่วน + เมนู]
    end
    HC -->|"notify-telegram.sh"| MSG
    TC -->|"alerting.py + ledger"| MSG
    UP1 -->|webhook| BR[snc-alert-bridge<br/>(Cloud Run แยก service)]
    UP2 -->|webhook| BR
    BR --> MSG
```

จุดประสงค์ของการมี 2 แหล่งตรวจ (Pi เอง + GCP):

- **Pi local**: ตรวจสิ่งที่ตัวเองเห็น — service, PBX, tunnel client
- **GCP uptime**: ตรวจจับกรณี **Pi แจ้งเองไม่ได้** — ไฟดับ / เน็ตหลุด / ตู้ล่ม
  (`snc-pi-tunnel-health` ตรวจ `snc.nithep.com/health` จากภายนอก)

## 2.2 องค์ประกอบแต่ละชั้น

### ชั้นที่ 1: Pi4 local monitoring

| ส่วน | ไฟล์ | บทบาท |
|---|---|---|
| ตรวจรายวัน | `ops/verify-daily.sh` (cron) | health + service + key |
| ตรวจ tunnel/WS | `ops/ws-tunnel-cron.sh` (cron) | WS ผ่าน tunnel, ตาย 2 ครั้งติด → alert |
| ส่ง Telegram | `ops/notify-telegram.sh` | ส่งข้อความดิบ (ใช้กับข้อความง่าย ๆ) |
| ส่ง + บันทึก ledger | `ops/alerting.py` | **ทางหลัก** — template มาตรฐาน + รหัสอ้างอิง |
| ตอบคำถาม | `ops/snc_telegram_agent.py` | คำสั่ง `/health` `/logs` ฯลฯ (pull) |

### ชั้นที่ 2: GCP Cloud Monitoring

| ส่วน | ไฟล์ | บทบาท |
|---|---|---|
| ตั้งค่าทั้งหมด | `ops/setup_cloud_monitoring.sh` | uptime check ×2 + alert policy ×2 + webhook |
| รับ webhook | `api/bridge_server.py` (Cloud Run `snc-alert-bridge`) | แปล incident → Telegram |
| Deploy bridge | `ops/deploy_bridge_cloudshell.sh` | แยก service — alert ถึงแม้ backend หลัก down |

### ชั้นที่ 3: Telegram

- **alert (fail)**: template "สถานะ + รายการตรวจ + สาเหตุ + เมนูถัดไป"
- **recovery (กลับมาปกติ)**: template "ระบบกลับมาปกติแล้ว" แยกชัดเจน (ดู 2.4)

## 2.3 Template มาตรฐาน (ใช้ร่วมทุกแหล่ง)

ทุก alert มี 4 ส่วนเหมือนกัน ต่างแค่เนื้อหา — `ops/alerting.py` เป็นจุดกลาง:

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

- ทุก alert มีรหัสอ้างอิง `SNC-AL-<TYPE>-<YYYYMMDD>-<HHMMSS>` และเขียนลง ledger
  `logs/alerts.log` — ค้นย้อนได้ด้วย `/alerts <คำค้น>` ใน Telegram
- ทดสอบ template โดยไม่ส่งจริง:

```bash
python3 ops/alerting.py --dry-run --severity CRITICAL --type CLOUD \
  --summary "ทดสอบ" --details "..." --verify "..."
```

## 2.4 Recovery Message (แยกจาก alert)

เมื่อระบบกลับมา healthy ให้ส่งข้อความ recovery แยกเป็นอีกประเภท — แนะนำ type
`RECOVERY` + severity `INFO`:

```text
💚 ระบบ SNC กลับมาปกติแล้ว

สถานะรวม: HEALTHY
เวลา: 2026-09-02 02:10:00
รหัส: SNC-AL-RECOVERY-20260902-021000

กู้คืนจาก:
SNC-AL-CLOUD-20260902-010947 (Cloud Run uptime check /health failed)

ระยะเวลาผิดปกติ: ~60 นาที

เมนูถัดไป: /health | /status
```

วิธีทำงานจริง: cron ตรวจซ้ำ (เช่น `verify-daily.sh` หรือ ws-tunnel-cron) เมื่อเจอ
healthy หลังเคยส่ง alert → เรียก `alerting.py --severity INFO --type RECOVERY`
พร้อมอ้างรหัส alert เดิม (ledger เก็บรหัสไว้ค้นได้)

**อัตโนมัติ (แนะนำ)** — `ops/alert-recovery-check.sh` + `--recovery-auto`:
state คำนวณจาก ledger ทั้งหมด (ไม่มีไฟล์ state แยก) — type ใดถือว่า "ค้าง"
ถ้า alert ล่าสุดของ type นั้นใหม่กว่า RECOVERY ล่าสุด

```bash
# ทดสอบนอก cron
ops/alert-recovery-check.sh http://localhost:8000/health

# cron ตรวจทุก 10 นาที (บน Pi)
*/10 * * * * /home/ecs-agent/snc/ops/alert-recovery-check.sh >> /home/ecs-agent/snc/logs/recovery-check.log 2>&1

# ส่ง recovery แบบ manual อ้างรหัสเดิม
python3 ops/alerting.py --recovery-from SNC-AL-TUNNEL-20260902-010000 \
  --type TUNNEL --downtime "~45 นาที"
```

## 2.5 Dedupe — กัน alert ซ้ำจากหลายแหล่ง

กรณี cron บน Pi และ GCP uptime เจอปัญหาเดียวกันพร้อมกัน อาจได้ alert ซ้ำ 2 ฉบับ
key = `service + status + time bucket` — **implement แล้วใน `alerting.py`**:

```bash
# ไม่ส่ง Telegram ซ้ำถ้ามี alert TUNNEL ใน 10 นาทีล่าสุด (ยังบันทึก ledger พร้อม deduped: true)
python3 ops/alerting.py --severity CRITICAL --type TUNNEL \
  --summary "WS Tunnel ตาย 2 ครั้งติด" --dedupe-minutes 10
```

- entry ที่โดน dedupe จะมี `deduped: true` ใน ledger และ **ไม่ขยายหน้าต่าง dedupe**
  (ต่อให้ยิงซ้ำกี่ครั้ง ก็ยังนับ window จาก alert จริงฉบับแรก)
- RECOVERY จะยังทำงานถูกต้องเพราะ `pending_incidents()` ใช้ alert ล่าสุดใน ledger
  รวมฉบับที่โดน dedupe ด้วย

## 2.6 สรุปการไหลเมื่อเกิดเหตุ

```text
เกิดเหตุ (เช่น Cloud Run down)
    ├─ GCP uptime ตรวจไม่ผ่าน 120s → policy OPEN → webhook → bridge → 📣 Telegram
    └─ (ถ้า Pi ยังรัน) cron ตรวจเจอ → alerting.py → ledger + 📣 Telegram (dedupe ข้าม)
ผู้ดูแลกด /health → เห็นรายการตรวจราย service + สาเหตุ
ผู้ดูแลกด /logs หรือ /cloudrun → รายละเอียดเพิ่ม
ระบบกลับมาปกติ → RECOVERY message อ้างรหัส alert เดิม
```

---

# ภาคผนวก

## A. การทดสอบ

```bash
# unit tests (ไม่ต้องมี pytest)
python -m unittest tests.test_health_monitoring -v
```

ครอบคลุม: mapping สถานะ systemd, `skipped` บนเครื่องไม่มี systemd,
ฟอร์แมตข้อความ agent (ห้าม `active, active`), HTML-escape, graceful `/logs`,
template alert 4 ส่วน

## B. ไฟล์ที่เกี่ยวข้องทั้งหมด

| ไฟล์ | บทบาท |
|---|---|
| `api/server.py` | `/health` + `_systemd_service_status()` |
| `ops/snc_telegram_agent.py` | คำสั่ง/เมนู Telegram + `SNC-Telegram-Agent/1.0` UA |
| `ops/alerting.py` | template alert + ledger + dedupe + RECOVERY (`--recovery-auto`) |
| `ops/alert-recovery-check.sh` | cron wrapper ส่ง RECOVERY อัตโนมัติเมื่อกลับมา healthy |
| `ops/notify-telegram.sh` | ส่ง Telegram แบบเรียบง่าย (shell) |
| `ops/verify-daily.sh` | cron ตรวจรายวันฝั่ง Pi |
| `ops/ws-tunnel-cron.sh` | cron ตรวจ WS/tunnel ฝั่ง Pi |
| `api/bridge_server.py` | webhook bridge (Cloud Run แยก service) |
| `ops/setup_cloud_monitoring.sh` | ตั้งค่า uptime check + policy + webhook |
| `tests/test_health_monitoring.py` | unit tests |

## C. เอกสารที่เกี่ยวข้อง

- [[SNC_TELEGRAM_ALERTS]] — คู่มือ Telegram bot + การ rotate token
- [[SNC_CLOUDFLARE_TUNNEL_SUMMARY]] — tunnel + WS heartbeat
- [[SNC_API_KEY_ROTATION_GUIDE]] — key ที่ใช้ใน alert chain
