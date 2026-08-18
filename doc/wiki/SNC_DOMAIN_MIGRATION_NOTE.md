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

## ⏳ สิ่งที่ยังต้องทำ / ยังไม่ได้ปรับ

| # | รายการ | สถานะ |
|---|---|---|
| 1 | Redeploy backend บน Pi/Cloud Run ให้รับ CORS origins ใหม่ (`snc.nithep.com` ใน `api/server.py`) | ⚠️ ต้อง redeploy ให้ config ใหม่มีผลจริง |
| 2 | ตรวจ CORS origins ที่ Cloud Run env (`SNC_ALLOWED_ORIGINS`) ให้มี `snc.nithep.com` | ⚠️ ตรวจ |
| 3 | บุ๊กมาร์ก/ทางลัดบนเครื่องพยาบาล/เจ้าหน้าที่ — อัปเดตเป็น `https://snc.nithep.com` | ⚠️ แจ้งทีม |
| 4 | เอกสารคู่มือภายใน (STAFF_GUIDE, FIELD_TEST_CHECKLIST) — เปลี่ยนแล้วใน repo ✅ แต่อย่าลืมเผยแพร่เวอร์ชันใหม่ | ✅ repo / ⚠️ เอกสารแจกจ่าย |
| 5 | ตรวจ `deploy-snc-one-shot.sh` ตัวจริงบน Pi ที่อาจยังมี config ค้าง (ถ้าเคย deploy ก่อน commit) | ⚠️ ตรวจ |
| 6 | ปิดการใช้งาน/ลบ tunnel เก่าที่ชี้ `nursecall` ฝั่ง Cloudflare (ถ้ายังเหลือ) | ⚠️ ตรวจ (DNS ถอดแล้ว) |

> ℹ️ **หมายเหตุ:** โดเมนเก่า `nursecall.nithep.com` ตอบ `Non-existent domain` แล้ว — แสดงว่า DNS ฝั่งถูกถอดออก (ไม่มีชื่อหลงเหลือ) แต่ควรยืนยันว่า Public Hostname เก่าใน Cloudflare Zero Trust ถูกเอาออกด้วยเพื่อความสะอาด

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