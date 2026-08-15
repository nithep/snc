# SESSION_HANDOVER_2026-08-16 — Cloud Run Deploy + Verify/Monitoring Hardening

> จัดทำ: 16 ส.ค. 2569 | แทนที่ handover ก่อนหน้าเฉพาะส่วน Ops/Deploy

---

## 📊 สถานะระบบ ณ สิ้น session

| ระบบ | สถานะ | หมายเหตุ |
|---|---|---|
| **Pi4 (production)** | ✅ ใช้งานได้ | services active, `/health` healthy, verify **PASS=14 FAIL=0** |
| **Cloud Run API + auth** | ✅ ใช้งานได้ | POST ไม่มี key → 401, key ใหม่ → 200 |
| **Cloud Run dashboard** | ✅ ใช้งานได้ | `GET /` → 200 + title `SNC Nurse Station — Live Monitor`, `/static/` → 200 |
| **Telegram แจ้งเตือน** | ✅ | notify + agent หา token เจอ (len 46) หลังแก้ env path |

---

## ✅ งานที่เสร็จใน session นี้

### 1. verify-system.sh v2 (หลายโปรเจกต์)
- รองรับ `ops/verify-projects.conf` (1 บรรทัด/โปรเจกต์, 12 ช่องคั่น `|`)
- โหมด: default / `--all` / ระบุชื่อ + env override เดิม
- เช็ค 9 กลุ่ม: 5-Core layout, dir เก่า, cron→ops/, services, health, secrets, proxy, external conn, git sync

### 2. verify-daily.sh + cron 07:00
- ตรวจทุกเช้า + แจ้งเตือน Telegram **เฉพาะเมื่อพบปัญหา** (`VERIFY_ALWAYS=1` ให้ส่งแม้ผ่าน)
- log ที่ `<root>/verify_daily.log` — cron: `0 7 * * * /home/ecs-agent/snc-poc/ops/verify-daily.sh`

### 3. บั๊กที่เจอ + แก้ (สำคัญ)
| บั๊ก | ผลกระทบ | แก้ |
|---|---|---|
| `ops/*.sh` สูญเสีย exec bit (git เก็บ 100644) | **cron พังเงียบ** (backup 03:00, watchdog ไม่รัน) | `chmod +x` ใน git (20 ไฟล์→100755) + บน Pi4 |
| `notify-telegram.sh` + `snc_telegram_agent.py` หา `.env` ไม่เจอ (ชี้ `ops/` แทน root) | Telegram พังหลัง restructure | แก้ env resolution: ลอง parent (`api/.env`) ก่อน + legacy fallback |
| Docker image ไม่มี dashboard (build context = `api/` เท่านั้น) | Cloud Run `/` → 307 + JSON error | Dockerfile build จาก **repo root** (`COPY api/ .` + `COPY app/ app/`) + cloudbuild.yaml + .dockerignore |
| **Cloud Run cache image ตาม tag `:latest`** | deploy ใหม่แต่ยังใช้ image เก่า (GCR tag ใหม่แล้ว revision ยัง digest เก่า) | deploy ด้วย **digest `@sha256`** (ทั้ง 2 deploy scripts) |
| `static_dir` ชี้ผิดใน container: `../app` จาก `/app/server.py` = `/app` ไม่ใช่ `/app/app` | Cloud Run `/` → 307 + `/static/` 404 ทั้งที่ image มี `app/` จริง | เลือก candidate หลายตำแหน่ง (`../app` สำหรับ repo, `app` สำหรับ container) ตามว่ามี `index.html` ไหม — commit `b906c3b` (ก่อนหน้า `df07273` แค่ abspath ยังไม่พอ) |

### 4. Cloud Run deploy journey (บันทึกเพื่อกันซ้ำ)
1. default compute SA ไม่มี `logging.logWriter` → grant
2. ไม่มี `artifactregistry.repositories.createOnPush` → grant `artifactregistry.admin`
3. Cloud Shell network ไป gcr.io หลุด → docker push retry 3 ครั้งในสคริปต์
4. build context ต้อง root (ไม่งั้นไม่มี app/) → Dockerfile + cloudbuild.yaml
5. deploy ต้อง digest ไม่ใช่ tag → แก้ deploy scripts
6. `static_dir` ต้องรองรับ 2 layout (repo: `api/server.py`+`app/`, container: `/app/server.py`+`/app/app/`) → candidate หลายตำแหน่ง (commit `b906c3b`)

---

## ⏳ สิ่งค้าง / next steps

1. **tg agent เป็น systemd** — ตอนนี้รันแบบ nohup (PID บน Pi) จะหายถ้า reboot; `ops/snc-tg-agent.service` ยังชี้ path เก่า ต้องแก้เป็น `ops/snc_telegram_agent.py`
2. (optional) เพิ่ม Cloud Run health/auth/dashboard เข้า verify-daily
3. Cloud Run ยังไม่มี DB จริง — events เก็บบน Pi4 (`api/nurse_call_events.db`) Cloud Run เป็นตัว API/auth อย่างเดียว

---

## 🔐 Credentials

- **SNC_API_KEY ใหม่**: `SNC_API_KEY_REDACTED` (ไม่ commit)
  - Pi4: `api/.env` + `pbx/.env` (chmod 600)
  - Cloud Run: env var (ตั้งแล้ว)
  - key เก่า `340e28...` ถูกลบจาก git history (filter-repo) แล้ว
- **Telegram**: token ใน `api/.env` (`TELEGRAM_BOT_TOKEN`/`TELEGRAM_CHAT_ID`) — bot `@snc2569_bot`, chat `7346817215`

---

## 📦 Git (session นี้)

- `b906c3b` fix: static_dir เลือก candidate หลายตำแหน่ง (repo + container layout) — **Cloud Run dashboard จบที่ commit นี้**
- `df07273` fix: static_dir abspath (แก้ครึ่งเดียว — ไม่เพียงพอ)
- `1c35ed1` fix: deploy ด้วย digest ไม่ใช่ tag
- `d4d0993` ops: deploy script pull อัตโนมัติ + fail-fast + ตรวจ dashboard
- `9c8d02e` fix: Dockerfile context=root + app/ ใน image
- `168b5f4`/`f430252` ops: verify multi-project + cron + exec bits + Telegram env
- ทั้งหมด pushed + Pi4 synced (hotfix `gemini_direct_service.py` ถูก preserve)

> ⚠️ Pi4 มี untracked legacy files (root scripts เก่า, backups/, .burnin_*) — reset ไม่ลบ เก็บไว้ได้
