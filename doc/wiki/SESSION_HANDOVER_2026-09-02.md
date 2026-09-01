---
title: "SESSION_HANDOVER_2026-09-02 — ระบบ Monitoring ใหม่: /health ราย service + เมนู Telegram + Dedupe/Recovery"
type: handover
tags: [status, pi4, cloud-run, monitoring, telegram, alerting, health]
---

# SESSION_HANDOVER_2026-09-02 — ระบบ Monitoring ใหม่ครบวงจร

> จัดทำ: 2 ก.ย. 2569 | ต่อจาก [[SESSION_HANDOVER_2026-09-01]]
> ครอบคลุม: /health ตรวจราย service (systemd จริง), เมนูคำสั่ง Telegram ใหม่,
> alert template มาตรฐาน 4 ส่วน, dedupe, auto-RECOVERY — deploy ครบ Pi4 + Cloud Run + GitHub

## สรุปผู้เบิกจ่าย (Deploy Status)

| สภาพแวดล้อม | สถานะ | หลักฐาน |
|---|---|---|
| **Pi4** (backend + pbx-listener + tg-agent + cloudflared) | ✅ active ทั้ง 4 | `/health` healthy + `pbx_listener: systemd active` |
| **Cloud Run** (snc-cloud-backend) | ✅ serving | `/health` healthy + `db: firestore` + `pbx_listener: skipped` |
| **GitHub** (origin/main) | ✅ synced | commit `a56bd2d` |

## งานที่ทำ

### 1. `/health` ใหม่ — ตรวจราย service (`api/server.py`)

- คืน `checks` ราย service: backend / database / **pbx_listener** / websocket / cloud_run
  พร้อม `reason` สรุปสาเหตุและ `checked_at`
- `pbx_listener` อ่านสถานะ **`systemctl is-active` จริงบน Pi** (ไม่ใช่ hardcode)
- บนเครื่องไม่มี systemd (Cloud Run / Windows dev) → `skipped` **ไม่นับเป็นปัญหา**
  — กัน false alarm กับ GCP uptime check และ `deploy-snc-one-shot.sh` (grep `"status":"healthy"`)
- Aggregate: down/failed → `down`, degraded/unknown → `degraded`, else `healthy`

### 2. เมนูคำสั่ง Telegram (`ops/snc_telegram_agent.py`)

- คำสั่งใหม่: `/health` `/cloudrun` `/uptime` `/logs` `/recovery`
- ทุกข้อความมี 3 ส่วน: **สถานะ + สาเหตุ + เมนูถัดไป** — เลิกใช้ `services: active, active`
- Graceful ทุกเคส: backend ล่ม (DOWN + สาเหตุ HTML-escaped), ไม่มี journalctl/systemd
- **Cloudflare WAF บล็อก UA `Python-urllib*` (403)** → agent ตั้ง UA
  `SNC-Telegram-Agent/1.0` — สคริปต์ Python ตัวใหม่ที่ยิง tunnel ตรง ๆ ต้องทำเหมือนกัน
- ผู้ใช้ตอบข้อความ HTML ต้อง escape เสมอ (`html_escape`)

### 3. Alert Template มาตรฐาน (`ops/alerting.py`)

- ทุก alert 4 ส่วน: สถานะรวม + รายการตรวจ + สาเหตุ/หลักฐาน + เมนูถัดไป
- `--dedupe-minutes N`: มี alert type เดียวกันใน N นาที → ไม่ส่ง Telegram ซ้ำ
  (ยังเขียน ledger พร้อม `deduped: true`; entry ที่โดน dedupe **ไม่ขยาย window**)
- `send_recovery()` + `pending_incidents()`: state คำนวณจาก ledger ทั้งหมด
  (ไม่มีไฟล์ state แยก) — type ไหน alert ล่าสุดใหม่กว่า RECOVERY ล่าสุด = ยังไม่ปิด
- `--review [hours]`: สรุปปริมาณ alert/recovery/dedupe + เวลากู้ตัวเฉลี่ย

### 4. Auto-RECOVERY บน Pi (cron)

- `ops/alert-recovery-check.sh` — cron ทุก 10 นาที (ติดตั้งแล้ว):
  `/health` healthy + มี incident ค้าง → ส่ง 💚 RECOVERY อ้างรหัสเดิม + ระยะเวลา
  cron-safe (exit 0 เสมอ, ระบบยังล่ม → เงียบ)
- **ผลจริงวันแรก:** ปิด incident ค้างจาก 26 ส.ค. 2 รายการ (FORMAT, POWER)
  ส่ง RECOVERY สำเร็จ — ledger ยืนยัน `SENT OK` ทั้งคู่

### 5. Cron เดิม opt-in dedupe

- `ws-tunnel-cron.sh`: `--dedupe-minutes 30` (กันซ้ำซ้อนกับ GCP uptime alert)
- `verify-daily.sh`: ย้ายจาก `notify-telegram.sh` ดิบ → `alerting.py`
  (`--type BACKEND`, `--dedupe-minutes 720`) — เข้า ledger + template เดียวกัน

### 6. Deploy จริง

- Pi: backup → scp → md5 verify → restart ทั้ง 3 services → synthetic test ห้อง 999 (ack 1s, ไม่ breach)
- Cloud Run: Cloud Shell `ops/deploy_cloudrun_cloudshell.sh` (SNC_API_KEY จาก Secret Manager)
  — verify fail-closed: `db=firestore` ✅ auth 401 ✅ Firestore write 200 ✅

## เอกสาร / Tests

- **[[SNC_HEALTH_MONITORING]]** — เอกสารรวม: health schema + alerting 3 ชั้น
  + dedupe/recovery usage + cron example (อัปเดตให้ตรงโค้ดแล้ว)
- `tests/test_health_monitoring.py` — **23 tests OK** รันด้วย
  `python -m unittest tests.test_health_monitoring` (ไม่ต้องมี pytest)
  ครอบคลุม: systemd mapping, skipped semantics, agent ฟอร์แมต, dedupe window,
  recovery ledger, review summary

## บั๊กที่เจอและแก้ระหว่างทาง

| อาการ | สาเหตุ | วิธีแก้ |
|---|---|---|
| `/logs` crash บน Windows | `journalctl` ไม่มี → FileNotFoundError | try/except → ตอบ graceful |
| `/health` = degraded บน Cloud Run | ไม่มี systemd → unknown นับเป็นปัญหา | `skipped` semantics |
| Tunnel 403 จาก python | Cloudflare WAF บล็อก python-urllib UA | custom UA ใน agent |
| verify-daily ส่ง alert นอก ledger | ใช้ notify-telegram.sh ดิบ | ย้ายไป alerting.py |

## ค้างสำหรับวันหน้า

- [ ] ทบทวนปริมาณ alert/recovery หลังใช้งาน 24–48 ชม.:
      `python3 ops/alerting.py --review 48` (ดู false alarm rate จาก dedupe ข้าม)
- [ ] พิจารณาเปิด lockdown `/api/admin/*` ช่วงกลางคืน (Tier-2 endpoints) — ยังไม่ได้ทำ
- [ ] GCP alert policy ฝั่ง Cloud Run อาจยิงซ้ำกับ Pi cron — ถ้า `--review` เห็นซ้ำเยอะ
      ให้เพิ่ม dedupe ฝั่ง bridge (`api/bridge_server.py`) หรือลด policy ความถี่

## คำสั่งกู้ฉุกเฉิน

```bash
# มองภาพรวม
python3 ops/alerting.py --review 48
ssh pi4 '/home/ecs-agent/snc/ops/alert-recovery-check.sh http://localhost:8000/health'

# Rollback ระบบแจ้งเตือน (Pi)
ssh pi4 'cd /home/ecs-agent/snc && cp ops/alerting.py.bak.20260902011256 ops/alerting.py && \
  cp ops/snc_telegram_agent.py.bak.20260902011256 ops/snc_telegram_agent.py && \
  sudo systemctl restart snc-backend snc-pbx-listener snc-tg-agent'

# Deploy Cloud Run ซ้ำ (Cloud Shell)
bash ops/deploy_cloudrun_cloudshell.sh   # SNC_API_KEY จาก: gcloud secrets versions access latest --secret=snc-api-key
```
