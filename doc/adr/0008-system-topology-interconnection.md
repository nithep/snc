---
title: "ADR 0008 — โครงสร้างความเชื่อมโยงทั้งระบบ (System Topology & Interconnection)"
type: adr
tags: [architecture, topology, deployment, cloud]
---

# ADR 0008 — โครงสร้างความเชื่อมโยงทั้งระบบ (System Topology & Interconnection)

- สถานะ: **Accepted**
- วันที่: 2026-08-20

## บริบท
SNC มีส่วนประกอบเชื่อมโยงกันหลายชั้น — Edge (Pi4), Repo (GitHub), Cloud (GCP + Cloudflare) —
และมีสคริปต์ deploy/หมุน secret จำนวนมาก การตัดสินใจของแต่ละชิ้น (ADR 0002/0003/0005)
บันทึกไว้แล้ว แต่ยังไม่มี ADR ฉบับเดียวที่อธิบาย **แผนผังความเชื่อมโยงทั้งระบบ + วิธี sync/deploy**
ทำให้ผู้มาใหม่/ทีม ops สับสนว่าอะไรคุยกับอะไร และเหตุใดแต่ละสคริปต์/secret จึงมีอยู่

## การตัดสินใจ
กำหนด **topology 3 ชั้น (3-tier)** + **cloud layer** เป็นโครงสร้างความเชื่อมโยงมาตรฐานของ SNC
และบันทึกเป็นแผนที่อ้างอิงฉบับเดียว ดังนี้:

### 1. ชั้น Repo / Sync (GitHub เป็นจุดเชื่อมกลาง)
```
MateBook (Dev, D:/snc)          GitHub (nithep/snc)            Pi4 (Production)
┌────────────────────┐          ┌─────────────────┐           ┌──────────────────┐
│ main (local dev)   │──push──→ │ origin/main     │──pull──→  │ /home/ecs-agent/ │
│ (git-cloud)        │←─pull──  │ (source of truth)│──rsync──  │  snc/            │
│                    │          │                 │  api/     │  (systemd)       │
└────────────────────┘          │                 │  app/     │  ssh pi4         │
                                │                 │  pbx/     │  192.168.1.94    │
                                └─────────────────┘  restart  └──────────────────┘
```
- **GitHub `nithep/snc`** = แหล่งโค้ดเดียว (single source of truth)
- **Pi4** รับโค้ดผ่าน `git pull` + `rsync` เฉพาะส่วนจำเป็น (api/, app/, pbx/) แล้ว restart service
- Git remote ที่รัน push ต้องมี credential (Windows credential manager) — WSL git ไม่มี push credential
- **Nomenclature:** ใช้ `snc` / `/home/ecs-agent/snc` เท่านั้น (ห้าม `snc-poc`) — ดู ADR 0007

### 2. ชั้น Edge — Pi4 (Raspberry Pi, 192.168.1.94, alias `pi4`)
| service (systemd) | บทบาท | พอร์ต/ต้นทาง |
|---|---|---|
| `snc-backend` | FastAPI backend | `:8000` (LAN + via tunnel) |
| `snc-pbx-listener` | อ่าน SMDR จากตู้ Phonik PBX | PBX `192.168.1.91:23` |
| `snc-cloudflared` | Cloudflare Tunnel (outbound เท่านั้น) | → `localhost:8000` |
| `snc-tg-agent` | Telegram alert agent | Chat `7346817215` |

### 3. ชั้น Cloud — GCP (project `hotel-ecs-nithep`, region `asia-southeast1`)
- **Cloud Run `snc-cloud-backend`** — backend บน Firestore (`SNC_DB_BACKEND=firestore`), auth ด้วย `SNC_API_KEY`
- **Cloud Run `snc-alert-bridge`** — webhook → Telegram (แยก service ตาม ADR 0002)
- **Firestore** — collections `nurse_call_events`, `room_state` (persistent, deletion_protection)
- **Secret Manager** — `snc-api-key`, `snc-telegram-bot-token`, `snc-monitor-webhook-token` (mount, ไม่ใช้ plaintext — ADR 0005)
- **Cloud Monitoring** — uptime check `/health` → alert policy → notification channel → bridge → Telegram
- **Cloudflare** — domain `snc.nithep.com`, tunnel outbound → Pi4 `localhost:8000`, TLS 1.3, zero open port

### 4. Auth / Secret ที่แชร์ข้ามชั้น (ต้องตรงกัน)
| Secret | ใช้ที่ไหน | สถานะ |
|---|---|---|
| `SNC_API_KEY` | Pi `api/.env` + Pi `pbx/.env` + Cloud Run `snc-cloud-backend` | ต้องตรงกันทั้ง 3 จุด ไม่งั้น 401 (key เก่า→401) |
| `TELEGRAM_BOT_TOKEN` | Pi `api/.env` + Cloud `snc-telegram-bot-token` | หมุนพร้อมกัน 2 ฝั่ง |
| `MONITOR_WEBHOOK_TOKEN` | Cloud Monitoring channel URL + bridge | กัน spoofing |
| Cloudflare Tunnel token | `/etc/snc/cloudflared.env` (Pi, chmod 600) | หมุนผ่าน `setup-cloudflared.sh` |

### 5. IaC / Deploy (ตาม ADR 0005)
- `ops/terraform/` = **initial reference** — resource ถูกสร้างด้วยมือจาก `deploy_*.sh` ก่อน ต้อง `terraform import` ก่อน apply
- สคริปต์ deploy/ops: `deploy_cloudrun_cloudshell.sh`, `deploy_backend_cloudshell.sh`, `deploy_bridge_cloudshell.sh`, `setup_cloud_monitoring.sh`, `cleanup_cloud_monitoring.sh`, `rotate_telegram_token.sh`, `setup-cloudflared.sh`, `deploy-snc-one-shot.sh`

## ผลกระทบ
- มีแผนที่อ้างอิงฉบับเดียวสำหรับการเชื่อมโยงทุกชั้น → ลดสับสน, onboard เร็วขึ้น
- ชัดเจนว่า secret ไหนต้อง sync กับที่ไหน (กัน auth หาย/เดาไม่ออกว่ามีผลที่ใด)
- การเปลี่ยน topology (เพิ่ม Pi, ย้าย cloud) ต้องอัปเดต ADR นี้เป็นลำดับแรก
- ยังมีจุดที่จัดการด้วยมือ (terraform import, cleanup channel เก่า) — ต้องไล่ทำตาม Roadmap

## ทางเลือกที่ไม่ได้เลือก
- **บันทึก topology ไว้ที่ wiki อย่างเดียว** → ไม่มีสถานะ "decision" ผูกกับสถาปัตย์, เลือนหายได้
- **ให้ Pi4 เป็น dev/worktree หลัก** → เสี่ยง production รวน; ปล่อยให้ GitHub เป็นศูนย์กลาง
- **ใส่ secret เป็น plaintext env แทน Secret Manager** → ขัด ADR 0005; เลือก mount secret

## ADR ที่เกี่ยวข้อง
- `0001` โครงสร้าง ADR / `0002` แยก bridge / `0003` Firestore / `0005` IaC / `0007` Nomenclature
- เอกสาร: `doc/BLUEPRINT_5CORE.md`, `doc/wiki/SNC_SYSTEMD_SERVICES_SUMMARY.md`, `doc/ARCHITECTURE_FLOW.md`

## การตรวจสอบ
```bash
# 3 ชั้น HEAD ตรงกัน
git log --oneline -1                    # MateBook
git ls-remote origin main               # GitHub
ssh pi4 "cd /home/ecs-agent/snc && git log --oneline -1" 2>/dev/null || echo "Pi4 ไม่ใช่ git clone (rsync)"
# SNC_API_KEY ตรงกันทั้ง 3 จุด (ข้ามชั้น)
grep '^SNC_API_KEY=' /home/ecs-agent/snc/api/.env /home/ecs-agent/snc/pbx/.env   # Pi (mask แล้ว)
# Cloud: gcloud run services describe snc-cloud-backend --format="value(spec.template.spec.containers[0].env)"  # ตรวจ mount secret
# Edge services active
ssh pi4 "systemctl is-active snc-backend snc-pbx-listener snc-cloudflared snc-tg-agent"
```