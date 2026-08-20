# 🔀 SNC — Migration Runbook (5-Core Restructure)

> ✅ **สถานะจริง (อัปเดต 20 ส.ค. 2569):** การย้ายโครงสร้าง 5-Core **เสร็จสมบูรณ์แล้ว** —
> production ปัจจุบันอยู่ที่ `/home/ecs-agent/snc` (systemd, cron, DB ทั้งหมดชี้มาที่นี่ และจัดโครงสร้าง 5-Core แล้ว)
> ยืนยันจากการปฏิบัติจริงใน session นี้ (ได้ restart `snc-opencode`/`snc-cloudflared` ที่ `/home/ecs-agent/snc` สำเร็จ)
> เอกสารนี้เก็บเป็น **ประวัติการย้าย (historical)** — อ่านเพื่อทำความเข้าใจการแมป path เดิม→ใหม่ ไม่ใช่คู่มือ deploy ปัจจุบัน
>
> เอกสารนี้บันทึกการย้ายโครงสร้าง SNC จาก `snc-poc/` (monorepo `hotel-ecs-checkin`)
> มาอยู่ในโครงสร้าง 5-Core มาตรฐาน — ใช้เป็นคู่มือสำหรับการ Deploy
> หลัง Burn-in ผ่าน (15 ส.ค. 2569 03:03) และการอ้างอิง path ใหม่ทุกครั้ง

---

## 1. ภาพรวมการเปลี่ยนแปลง (Overview)

| เดิม (monorepo) | ใหม่ (nithep/snc) | รายละเอียด |
|---|---|---|
| `snc-poc/backend/` | `api/` | FastAPI Server, services/, Dockerfile, health_check |
| `snc-poc/backend/public/index.html` | `app/index.html` | Nurse Dashboard v2.0 (เสิร์ฟจาก app/) |
| `snc-poc/dashboard-status.html` | `app/dashboard-status.html` | Status Dashboard |
| `snc-poc/pbx-connector/` | `pbx/` | SMDR Edge Listener + Parser Tests |
| `snc-poc/deploy-snc-one-shot.sh` + ฯลฯ | `ops/` | Deploy / Burn-in / Backup / Cron tooling |
| `snc-poc/docs/` + STAFF_GUIDE + SOP | `doc/` (+ `doc/wiki/`) | เอกสาร OKF ฉบับ SNC |
| `snc-poc/AGENTS.md` | `AGENTS.md` (root) | กฎ Agent ฉบับ SNC |
| — | `README.md` (ใหม่) | README ฉบับ SNC |

## 2. Path บน Pi (Server) — ใหม่ทั้งหมด

| รายการ | เดิม | ใหม่ |
|---|---|---|
| Root โครงการ | `/home/ecs-agent/snc-poc` | `/home/ecs-agent/snc` |
| Backend (systemd) | `.../snc-poc/backend` | `.../nithep/snc/api` |
| Dashboard (static) | `.../snc-poc/backend/public` | `.../nithep/snc/app` |
| Listener (systemd) | `.../snc-poc/pbx-connector` | `.../nithep/snc/pbx` |
| Logs | `.../snc-poc/logs` | `.../nithep/snc/logs` |
| DB (event) | `.../snc-poc/backend/nurse_call_events.db` | `.../nithep/snc/api/nurse_call_events.db` |
| venv | `.../snc-poc/venv` | `.../nithep/snc/venv` |

## 3. ไฟล์ที่อัปเดต path แล้ว (ใน branch นี้)

| ไฟล์ | การแก้ไข |
|---|---|
| `api/server.py` | `static_dir` → `../app` (เดิม `public`) |
| `ops/deploy-snc-one-shot.sh` | `REMOTE_ROOT=/home/ecs-agent/snc`, FILES → `api/` + `app/` |
| `ops/burnin-monitor.sh` / `burnin-reminder.sh` / `backup-snc-db.sh` | path → `nithep/snc`, DB → `api/` |
| `ops/monitor-snc-status.sh` / `verify-installation.sh` / `view-logs.sh` / `start-snc-system.sh` | logs dir + scripts |
| `ops/quick_start.sh` / `quick_start.ps1` / `setup_pi.sh` | path → `app/`, `api/`, `~/nithep/snc` |
| `ops/gcp_harness_evaluator.py` / `deploy_gcp_cloudrun.ps1` | path → `ops/`, `api/` |
| `doc/wiki/SYSTEMD_SERVICES_SUMMARY.md` | systemd WorkingDirectory → `api/` + `pbx/` |
| `doc/DEPLOYMENT_PI4.md` | path + systemd units |
| `AGENTS.md` / `api/health_check.py` / `ops/monitor-snc-status.sh` | path + แก้ bug quoting |

## 4. 🚧 Deploy หลัง Burn-in ผ่าน (วันที่ 15 ส.ค. 2569 03:03 ขึ้นไป)

> ⚠️ **ห้ามทำก่อน Burn-in ครบ 48 ชม. เด็ดขาด** — ดู SESSION_HANDOVER ข้อ 3 (Pi Freeze)

### ขั้นตอนที่ 1: จัดโครงสร้างใหม่บน Pi
```bash
ssh pi4
sudo systemctl stop snc-backend.service snc-pbx-listener.service
# Backup ระบบเดิมก่อนย้าย (สำคัญมาก)
sudo cp -r /home/ecs-agent/snc-poc /home/ecs-agent/snc-poc.bak.$(date +%Y%m%d)
# สร้างโครงสร้างใหม่
mkdir -p /home/ecs-agent/snc/{api,app,pbx,ops,doc,logs}
```

### ขั้นตอนที่ 2: ย้าย/คัดลอกไฟล์
```bash
cd /home/ecs-agent
mv snc-poc/backend/* nithep/snc/api/
mv snc-poc/backend/public/index.html nithep/snc/app/
mv snc-poc/dashboard-status.html nithep/snc/app/
mv snc-poc/pbx-connector/* nithep/snc/pbx/
mv snc-poc/*.sh snc-poc/*.py snc-poc/*.ps1 snc-poc/*.bat nithep/snc/ops/ 2>/dev/null
mv snc-poc/docs nithep/snc/doc
mv snc-poc/venv nithep/snc/venv  # หรือสร้างใหม่
mv snc-poc/backend/nurse_call_events.db nithep/snc/api/
chown -R ecs-agent:ecs-agent nithep/snc
```

### ขั้นตอนที่ 3: อัปเดต systemd units
```bash
sudo nano /etc/systemd/system/snc-backend.service
# WorkingDirectory=/home/ecs-agent/snc/api
sudo nano /etc/systemd/system/snc-pbx-listener.service
# WorkingDirectory=/home/ecs-agent/snc/pbx
sudo systemctl daemon-reload
sudo systemctl start snc-backend.service snc-pbx-listener.service
systemctl is-active snc-backend.service snc-pbx-listener.service
curl -s http://localhost:8000/health
```

### ขั้นตอนที่ 4: cron เดิม (ย้าย path)
```bash
crontab -e
# 0 3 * * * /home/ecs-agent/snc/ops/backup-snc-db.sh --pi
# */5 * * * * /home/ecs-agent/snc/ops/... (pbx_watchdog)
# 7 * * * * /home/ecs-agent/snc/ops/burnin-reminder.sh --check
```

### ขั้นตอนที่ 5: Verify
```bash
# Deploy จาก repo ใหม่ (local) — dry-run ก่อน
./ops/deploy-snc-one-shot.sh --dry-run
./ops/deploy-snc-one-shot.sh --check-tunnel
```

## 5. Rollback (ถ้าจำเป็น)

```bash
sudo systemctl stop snc-backend.service snc-pbx-listener.service
sudo rm -rf /home/ecs-agent/snc   # ระวัง! ลบเฉพาะถ้าต้องการคืนทั้งหมด
sudo cp -r /home/ecs-agent/snc-poc.bak.$(date +%Y%m%d) /home/ecs-agent/snc-poc
sudo systemctl start snc-backend.service snc-pbx-listener.service
```

## 6. Git History (การแยก repo ในอนาคต)

เมื่อพร้อม push เป็น repo แยก (`github.com/nithep/snc`):
```bash
# จาก repo hotel-ecs-checkin (branch split/snc)
git filter-repo --path api --path app --path pbx --path ops --path doc \
                --path AGENTS.md --path README.md --path LICENSE --path .gitignore \
                --path .agents --force
git remote add origin https://github.com/nithep/snc.git
git push -u origin main
```
> หมายเหตุ: `git filter-repo` ต้องรันใน clone สำรอง ไม่ใช่ repo หลัก (ลบ remote เดิมออก)

---
*บันทึกโดย: Senior Software Engineer — 13 ส.ค. 2569, branch `split/snc`*
