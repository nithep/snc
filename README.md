# 🏥 SNC — Smart Nurse Call

> ระบบ Smart Nurse Call (SNC) สำหรับโรงพยาบาล/ศูนย์ดูแลผู้ป่วย — ดัดแปลงตู้สาขา Phonik PBX
> และบอร์ด Help Call (Call Station v.107) ให้เป็นระบบแจ้งเตือนพยาบาล Real-time
> รันบน **Raspberry Pi 4** ภายใต้แบรนด์ **nithep** (`https://snc.nithep.com`)

![Status](https://img.shields.io/badge/Status-Production--Ready-green) ![Platform](https://img.shields.io/badge/Platform-Raspberry%20Pi%204-red)

## 🧭 ผังสถาปัตยกรรม (รวม Edge + Cloud)

ดูผังการเชื่อมสัมพันธ์เต็มรูปแบบ (D:\snc · GitHub · Pi4 · Cloudflare · Cloud Run · GCP) พร้อม Mermaid ได้ที่
[**`doc/ARCHITECTURE_FLOW.md`**](doc/ARCHITECTURE_FLOW.md)

```
โค้ด  D:\snc ─▶ GitHub ─▶ [Cloud Shell → gcr.io] ─▶ Cloud Run (backend / bridge)
                                                                      │
                               ┌──────────────────────────────────────┤
                               ▼                                      ▼
  ฮาร์ดแวร์  PBX ─▶ Pi4(listener+backend) ─▶ cloudflared ─▶ snc.nithep.com
                                                                      │
                        Cloud Monitoring ─▶ bridge ─▶ Telegram ◀──────┘
```

## 🏛️ โครงสร้าง 5-Core (Standard Layout)

| โฟลเดอร์ | รายละเอียด |
|---------|-----------|
| `api/` | API Server (FastAPI) — จัดเก็บสถิติ, ประมวลผล SLA, WebSocket Real-time, เสิร์ฟ Dashboard |
| `app/` | Nurse Dashboard v2.0 — หน้าเคาน์เตอร์พยาบาล (Dark Mode พรีเมียม, i18n ไทย/อังกฤษ) |
| `pbx/` | SMDR Edge Listener — ถอดรหัสสัญญาณ CALL_BEDSIDE / CALL_BATHROOM_EMERGENCY ผ่าน TCP Telnet |
| `ops/` | DevOps — สคริปต์ Deploy, Burn-in Monitor, Backup WAL, cron, ตรวจสอบสถานะ Pi |
| `doc/` | เอกสาร OKF — คู่มือพยาบาล (STAFF_GUIDE), แผนและ SOP ฝ่ายเทคนิค, Knowledge Base |

## 🚀 Quick Start (บน Pi 4)

```bash
cd ~/nithep/snc
./ops/quick_start.sh            # รัน API + Listener
curl -s http://localhost:8000/health
```

## 🔄 สถาปัตยกรรม (Architecture)

```
ผู้ป่วยกดปุ่ม/ดึงสายฉุกเฉิน → Phonik PBX (192.168.1.91:23)
    → pbx/snc_pbx_listener.py (SMDR Parser → FHIR JSON)
    → api/server.py (FastAPI + SQLite WAL + WebSocket)
    → app/ (Nurse Dashboard Real-time + SLA Timer + เสียงเตือน)
```

## 🛡️ ความปลอดภัย (Security)

- ทุกคำสั่งควบคุมตู้สาขาต้องผ่านระบบ Verifier (Safety First)
- API Key + Rate Limit กันการโจมตีจาก LAN (SNC_API_KEY)
- SQLite WAL Mode + Auto-backup ผ่าน cron (`ops/backup-snc-db.sh`)
- ระบบ Self-Healing ผ่าน systemd (`Restart=always`) + Burn-in Monitor (`ops/burnin-monitor.sh`)

---
*ดำเนินการจัดทำและดูแลโดย nithep — Production-Grade Smart Systems*
