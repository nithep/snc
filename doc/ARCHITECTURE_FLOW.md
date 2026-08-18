---
title: "SNC — ผังสถาปัตยกรรมและการไหลของข้อมูล (รวม Edge + Cloud)"
type: doc
tags: [architecture]
---

# SNC — ผังสถาปัตยกรรมและการไหลของข้อมูล (รวม Edge + Cloud)

> ผังนี้ครอบคลุมการเชื่อมสัมพันธ์ครบทุกส่วน: **D:\snc (MateBook)**, **GitHub**,
> **Raspberry Pi 4 (Edge)**, **Cloudflare Tunnel/DNS**, **GCP Cloud Run**, และ
> **GCP services** (Firestore / Secret Manager / Cloud Monitoring).
> ดูรายละเอียดส่วน Edge เดิมได้ที่ [[ARCHITECTURE_DIAGRAM]]

```mermaid
flowchart TB
    subgraph DEV["เครื่องพัฒนา (MateBook)"]
        A["D:\\snc<br/>(โค้ด + สคริปต์ deploy)"]
    end

    subgraph GIT["Version Control"]
        GH["GitHub: nithep/snc"]
    end

    subgraph EDGE["Edge (โรงพยาบาล)"]
        PBX["Phonik PBX<br/>192.168.1.91:23"]
        PI["Raspberry Pi 4 (192.168.1.94)<br/>snc_pbx_listener + snc-backend:8000<br/>(SQLite WAL) + Telegram agent"]
        CF["cloudflared<br/>Cloudflare Tunnel (outbound)"]
    end

    subgraph CLOUD["Cloudflare"]
        CFE["Cloudflare Edge<br/>HTTPS TLS 1.3"]
    end

    subgraph GCP["GCP (hotel-ecs-nithep)"]
        CS["Cloud Shell<br/>(build gcr.io + deploy)"]
        RUN["Cloud Run<br/>snc-cloud-backend<br/>(Firestore, SNC_API_KEY)"]
        BRIDGE["Cloud Run<br/>snc-alert-bridge"]
        MON["Cloud Monitoring<br/>(uptime check)"]
        SM["Secret Manager<br/>(bot token, webhook token)"]
        FS[("Firestore<br/>persistent DB")]
    end

    subgraph USER["ผู้ใช้"]
        DASH["Nurse Dashboard<br/>snc.nithep.com"]
        TG["Telegram @snc2569_bot"]
    end

    A -->|git push| GH
    GH -->|git pull| CS
    CS -->|build image| RUN
    CS -->|deploy digest| BRIDGE
    RUN --> FS
    RUN --> SM
    BRIDGE --> SM

    PBX -->|SMDR Telnet| PI
    PI -->|WebSocket/HTTP| CF
    CF -->|outbound tunnel| CFE
    CFE -->|https| DASH

    MON -->|uptime fail /health| BRIDGE
    BRIDGE -->|webhook token| SM
    BRIDGE -->|sendMessage| TG
    RUN -->|uptime target| MON
```

## เส้นทางหลัก 3 สาย

### A) สาย Edge (on-prem) — ผ่าน Cloudflare Tunnel
```mermaid
flowchart LR
    P["ผู้ป่วยกดปุ่ม/ดึงสาย"] --> PBX["Phonik PBX<br/>192.168.1.91:23"]
    PBX -->|"SMDR ==SMDX..."| LIS["Pi4: snc_pbx_listener<br/>(parse → FHIR JSON)"]
    LIS --> BE["Pi4: snc-backend :8000<br/>SQLite WAL"]
    BE -->|WebSocket| CF["cloudflared (outbound)"]
    CF -->|HTTPS TLS1.3| CFE["Cloudflare Edge"]
    CFE --> DASH["Dashboard<br/>snc.nithep.com"]
```
จุดสำคัญ: Tunnel เป็น **ขาออก (Zero Open Ports)** — `snc.nithep.com` ชี้ไป `http://172.17.0.1:8000` (เกตเวย์ Docker bridge) หา `snc-backend.service` พอร์ต 8000

### B) สาย Cloud (GCP Cloud Run)
```mermaid
flowchart LR
    A["D:\\snc"] -->|git push| GH["GitHub"]
    GH -->|git pull| CS["Cloud Shell"]
    CS -->|build| GCR["gcr.io/hotel-ecs-nithep"]
    GCR -->|deploy ด้วย digest| RUN["Cloud Run: snc-cloud-backend<br/>(auth SNC_API_KEY)"]
    RUN --> FS[("Firestore<br/>persist ตอน scale-to-zero")]
    RUN --> URL["https://snc-cloud-backend-...run.app"]
```

### C) สาย Alert/Telegram (วงจรเฝ้าระวัง)
```mermaid
flowchart LR
    MON["Cloud Monitoring<br/>uptime check GET /health (ทุก 300s)"] -->|fail 120s| POL["Alerting policy"]
    POL -->|webhook| BRIDGE["snc-alert-bridge<br/>(service แยก)"]
    BRIDGE -->|"token จาก Secret Manager"| TG["Telegram"]
```
Bridge อยู่คนละ service กับ backend หลัก → alert ส่งถึงแม้ backend หลัก down

## ตารางความสัมพันธ์

| ส่วน | บทบาท | จุดเชื่อม |
|------|--------|-----------|
| D:\snc (MateBook) | ต้นทางโค้ด + สคริปต์ deploy | `git push` → GitHub |
| GitHub `nithep/snc` | version control กลาง | Cloud Shell / Pi ดึงจากที่นี่ |
| Pi 4 (192.168.1.94) | Edge — ฟังสัญญาณจริงจาก PBX | ดึงจาก git, รัน backend+listener+cloudflared |
| Cloudflare | Tunnel + DNS | `cloudflared` ขาออก → `snc.nithep.com` |
| Cloud Run | main backend + bridge | deploy จาก Cloud Shell, URL `*.run.app` |
| GCP services | Firestore, Secret Manager, Monitoring | uptime → webhook → bridge |

## ไฟล์อ้างอิง (deploy scripts)
- `ops/deploy_cloudrun_cloudshell.sh` — deploy backend หลัก (Firestore, digest)
- `ops/deploy_bridge_cloudshell.sh` — deploy bridge + Secret Manager (bot/webhook token)
- `ops/setup_cloud_monitoring.sh` — uptime check + alert → Telegram (กัน stale-token)
- `ops/deploy_gcp_cloudrun.ps1` — PowerShell one-shot deploy (Windows/MateBook)
- `ops/deploy-to-pi.bat` — scp สคริปต์ไป Pi (Windows)
- `ops/verify-projects.conf` — สรุปสถานะโครงการแต่ละตัว