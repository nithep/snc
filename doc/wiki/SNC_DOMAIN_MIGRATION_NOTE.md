---
title: "🔄 บันทึกการย้ายโดเมนสาธารณะ nursecall → snc (Domain Migration Note)"
type: wiki
tags: [knowledge, ops]
---

# 🔄 บันทึกการย้ายโดเมนสาธารณะ `nursecall` → `snc`

> **วันที่:** 19 ส.ค. 2569
> **ผู้ดำเนินการ:** Agent SNC (ตรวจสอบ live) + วิศวกร (ปรับ Cloudflare/DNS)
> **อ้างอิง:** [`SNC_CLOUDFLARE_TUNNEL_SUMMARY.md`](SNC_CLOUDFLARE_TUNNEL_SUMMARY.md), [`SNC_CLOUDFLARE_ROTATION_GUIDE.md`](SNC_CLOUDFLARE_ROTATION_GUIDE.md)

---

## 🎯 เป้าหมาย

เปลี่ยนโดเมนสาธารณะ (Public Ingress) ของระบบ SNC จาก `nursecall.nithep.com` เป็น **`snc.nithep.com`** ทั่วทั้ง repo และระบบจริง

---

## ✅ สิ่งที่ทำไปแล้ว

### 1. ใน Repo / Vault (commit `c1c68e6`)
- แทนที่ `nursecall.nithep.com` → `snc.nithep.com` ครบ **62 จุด / 22 ไฟล์** ไม่มีจุดตกหล่น (ตรวจ `git grep` = 0)
- ครอบคลุม: `api/server.py` (CORS origins), `packaging/build_installers.py`, `surfaces/gui/service_portal.html`, `ops/*` (setup-cloudflared, setup_pi, deploy-snc-one-shot, deploy_backend_cloudshell, snc-cloudflared.service), `README.md`, และ docs/wiki ทั้งหมด
- ยังมีคู่มือ rotate key ครบ 3 ฉบับ (API Key / Telegram / Cloudflare) — commit `1bdd3db`

### 2. ในระบบจริง (ตรวจสอบ Live — 19 ส.ค. 2569 00:26 UTC)
| โดเมน | DNS | HTTP |
|---|---|---|
| `snc.nithep.com` | ✅ resolve (Cloudflare: `172.67.152.137` / `104.21.12.136`) | ✅ `/health` → **200** `{"status":"healthy","service":"snc-backend"}` |
| `nursecall.nithep.com` | ❌ Non-existent domain (ถอดออกแล้ว) | — |

**→ การตั้งค่า Cloudflare Tunnel + DNS สำหรับโดเมนใหม่เสร็จสมบูรณ์แล้ว** — backend ถูก publish ผ่าน `http://192.168.1.94:8000` → Tunnel → `https://snc.nithep.com`

---

## 🔧 Incident ที่พบและแก้ไขระหว่างการย้าย (19 ส.ค. 2569 ~01:05 UTC)

หลัง pull โค้ดใหม่บน Pi เกิด **backend crash-loop** (`ModuleNotFoundError: No module named 'core'`)

- **สาเหตุ:** `api/server.py` import `core.*` (อยู่ที่ repo root) แต่ systemd ตั้ง `WorkingDirectory=/home/ecs-agent/snc-poc/api` → Python หา `core/` ไม่เจอ → process ออก code=1 ทุกครั้ง → 502
- **การแก้ไข (commit `e6bebe9`):** เพิ่ม repo root เข้า `sys.path` ใน `server.py` (ไม่ยุ่งกับ WorkingDirectory ที่มีผลต่อ import `services`/`storage`)
- **ผล:** backend `active` + `/health` → 200 ทั้ง LAN (`localhost:8000`) และ public (`snc.nithep.com`) ✅

---

## ⏳ สิ่งที่ยังต้องทำ / ยังไม่ได้ปรับ

| # | รายการ | สถานะ |
|---|---|---|
| 1 | ~~Redeploy backend ให้ CORS origins ใหม่มีผล~~ | ✅ ทำแล้ว (backend restart ใช้ `snc.nithep.com` ได้) |
| 2 | ตรวจ CORS origins ที่ Cloud Run env (`SNC_ALLOWED_ORIGINS`) ให้มี `snc.nithep.com` | ⚠️ ตรวจ (เฉพาะเมื่อใช้ Cloud Run) |
| 3 | บุ๊กมาร์ก/ทางลัดบนเครื่องพยาบาล/เจ้าหน้าที่ — อัปเดตเป็น `https://snc.nithep.com` | ⚠️ แจ้งทีม |
| 4 | เอกสารคู่มือภายใน (STAFF_GUIDE, FIELD_TEST_CHECKLIST) — เปลี่ยนแล้วใน repo ✅ แต่อย่าลืมเผยแพร่เวอร์ชันใหม่ | ✅ repo / ⚠️ เอกสารแจกจ่าย |
| 5 | ตรวจ `deploy-snc-one-shot.sh` ตัวจริงบน Pi ที่อาจยังมี config ค้าง | ⚠️ ตรวจ |
| 6 | ลบ Public Hostname เก่า `nursecall` ฝั่ง Cloudflare Zero Trust (DNS ถอดแล้ว ยังควรลบให้สะอาด) | ⚠️ ตรวจ |

> ℹ️ **หมายเหตุ:** โดเมนเก่า `nursecall.nithep.com` ตอบ `Non-existent domain` แล้ว — DNS ฝั่งถอดออกแล้ว แต่ควรยืนยัน Public Hostname เก่าใน Zero Trust ถูกเอาออกด้วย

---

## 🧹 งานถอนรากถอนโคนชื่อ legacy (แยกเป็นงานใหม่ — ดู NOMENCLATURE)

จากการตรวจ `git grep` (19 ส.ค. 2569) ยังมีชื่อ legacy ที่ไม่ใช่ "SNC" หลงเหลือใน repo — ควรจัดการเป็นงานแยก:

| ชื่อ legacy | จำนวน | ประเภท | ความเสี่ยง |
|---|---|---|---|
| `ecs-agent` (Pi username) | 264 จุด / 26 ไฟล์ non-doc | `ops/*`, `packaging` | 🔴 สูง — เป็น username จริงบน Pi |
| `hotel-ecs` / `Hotel-ECS` | 83 จุด | `api/*.yaml`, `ops/terraform`, `AGENTS.md` | 🔴 สูง — บางจุดคือ GCP project id `hotel-ecs-nithep` |
| `hotel.nithep.com` | 16 จุด | `api/server.py` CORS, `health_check`, `gemini` | 🟠 กลาง — runtime origin |
| `hotel-gateway` (Pi hostname) | 4 จุด | doc/ops | 🟡 ต่ำ |
| `api-nurse` / `liff.nithep.com` | 6 จุด | doc | 🟢 ต่ำ |

> ⚠️ **ข้อควรระวัง:** `hotel-ecs-nithep` คือ **GCP project ID จริง** (terraform/cloudbuild) — การเปลี่ยนชื่อต้องย้าย resource บน GCP ด้วย ไม่ใช่แค่แก้โค้ด ส่วน `hotel.nithep.com` ใน CORS เป็นระบบโรงแรมเดิม (Hotel-ECS) ที่ SNC ผูกไว้ — ควรถามเจ้าของระบบก่อนเอาออก
> ดูแผนรายละเอียดใน [`SNC_NOMENCLATURE_CLEANUP.md`](SNC_NOMENCLATURE_CLEANUP.md) (จะจัดทำ)

---

## 🔍 วิธีตรวจสอบซ้ำ (Verify)

```powershell
# โดเมนใหม่ — ต้อง 200
Invoke-WebRequest -Uri "https://snc.nithep.com/health" -UseBasicParsing

# โดเมนเก่า — ควร resolve ไม่ได้ (Non-existent)
nslookup nursecall.nithep.com
```

```bash
# บน Pi — ตรวจ tunnel/config ว่าไม่มี nursecall หลงเหลือ
ssh pi4 "grep -rn nursecall /home/ecs-agent/snc-poc/ 2>/dev/null || echo 'CLEAN'"
# รีสตาร์ท cloudflared + backend หลัง redeploy
ssh pi4 "sudo systemctl restart cloudflared snc-backend.service"
```

---

*จัดทำโดย: Senior Software Engineer — 19 ส.ค. 2569*