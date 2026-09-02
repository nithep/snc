---
title: "🗂️ Index Timeline — SNC (Smart Nurse Call)"
type: wiki
tags: [knowledge]
---

# 🗂️ Index Timeline — SNC (Smart Nurse Call)

> ดัชนีนำทางเรียงตามเวลา (Timeline Index) ของระบบ SNC ใช้เพื่อหางาน/สถานะ/เอกสารได้รวดเร็ว
> เนื้อหาเป็นเพียงจุดยึด (anchors) — รายละเอียดอยู่ที่ไฟล์ที่ link แต่ละบรรทัด กรองให้เฉพาะที่จำเป็นเพื่อกัน noise/ซ้ำซ้อน

---

## 🧭 แผนที่ดัชนี
- **ไทม์ไลน์เต็ม (ประวัติทุก Milestone)**: [[project_timeline|ดู project_timeline.md]]
- **แผนงานโครงการ (Project Plan ฉบับเป็นทางการ)**: [[smart_nurse_call_project_plan]]
- **การตัดสินใจเชิงสถาปัตย์ (ADR)**: [[0001-record-architecture-decisions|ADR 0001–0006]]
- **รายงานวิเคราะห์ระบบ**: [[snc_analysis_report]]

---

## 📅 Timeline Index (เรียงตามวัน)

### 🔧 ฐานราก & พื้นฐาน (01–03 ส.ค. 2569)
- **01–02 ส.ค.** — Edge Serial/TCP Phonik Listener + Vertex AI Payload, Dashboard เบื้องต้น, Deploy Pi Zero 2W → **สเปคฮาร์ดแวร์**: [[phonik_nurse_call_knowledge|Phonik Knowledge]]
- **03 ส.ค.** — เริ่มโปรเจกต์แยก `snc` (SNC PoC Strategy), SMDR Listener, Backend, Nurse Dashboard ตัวแรก

### 🧠 สถาปัตยกรรม & ยุทธศาสตร์ (04–06 ส.ค. 2569)
- **04 ส.ค.** — Sovereign AI / Private Network Blueprint → [[SNC_SOVEREIGN_AI_BLUEPRINT]]
- **04–05 ส.ค.** — MVP Validation, EMER + Digital Twin, Intercom Call Baseline (Zero-Hardware SLA)
- **05 ส.ค.** — Field Go-Live Verification, SLA Real Hardware Test & Cost Plan
- **06 ส.ค.** — Hybrid Cloud Package → GCP Cloud Run Deploy, Executive Demo/Go-Live Manual, Gemini Direct REST (Zero-Cost AI)

### ⚙️ การพัฒนาแกนระบบ & การติดตั้งจริง (08–12 ส.ค. 2569)
- **08 ส.ค.** — SQLite WAL/Hotfix, Integration Test 9/9, Frontend Dynamic UI
- **09 ส.ค.** — **Live End-to-End ครั้งแรกบน Pi 4** (192.168.1.94)
- **10 ส.ค.** — SMDR Field Diagnostic, Auth Handshake & Event Subscription Fix → [[SNC_PBX_CONNECTIVITY_TROUBLESHOOTING|PBX Troubleshooting]]
- **11 ส.ค.** — SSH/switch/API key hardening, **X-API-Key auth**, Systemd Services + **Cloudflare Tunnel Go-Live** → [[SNC_SYSTEMD_SERVICES_SUMMARY|Systemd]] · [[SNC_CLOUDFLARE_TUNNEL_SUMMARY|Cloudflare Tunnel]] · [[SNC_API_KEY_ROTATION_GUIDE|API Key Rotation]]
- **11–12 ส.ค.** — **PBX Power Cycle** (session lock), RDSS Real-time Channel, TCP Proxy 2323 + Handshake Emulation → [[PBX_POWER_CYCLE_SOP|Power Cycle SOP]] · [[SNC_PBX_RDSS_REALTIME_CHANNEL|RDSS Channel]]

### 🚀 Go-Live & Release (13 ส.ค. 2569)
- **13 ส.ค.** — **Dashboard v2.0** + `sourceEventType`, WS Resilience, Deploy One-Shot script, Security Hardening, **Burn-in 48 ชม. เริ่ม**, คู่มือพนักงาน → [[SNC_API_KEY_SETUP_GUIDE|API Key Setup]]
- **13 ส.ค.** — SOP Power Cycle + Field Test Checklist, Rollback Drill, แผนวันทดสอบหน้างาน → [[FIELD_TEST_CHECKLIST|Field Checklist]]
- **13 ส.ค.** — แยกโครงสร้าง **5-Core** (`api/`/`app/`/`pbx/`/`ops/`/`doc/`) บนแบรนด์ nithep

### ✅ หลัง Burn-in & วางจำหน่าย (14–16 ส.ค. 2569)
- **14 ส.ค.** — Extension Inventory, Executive Report Upskill, API Key Setup Guide
- **15 ส.ค.** — **Burn-in 48 ชม. Complete (0 FAIL)**, เตรียม Go-Live รพ.ราชเวช ชั้น 11, Post-Burnin Field Test Plan → [[SNC_POST_BURNIN_FIELD_TEST_PLAN|Field Test Plan]]
- **16 ส.ค.** — Cloud Run Deploy + Verify/Monitoring Hardening + **Firestore Persistent DB** (ADR 0003)

### 🔁 Production Hardening & Field Config (24–25 ส.ค. 2569)
- **24–25 ส.ค.** — Dashboard Overhaul (History redesign + แยก Real/Demo + KPI Views + Status Strip), Deploy Infra Fixes (Dockerfile `core/`, deploy script env-safe), **AI บน Cloud ผ่าน OpenRouter**, เก็บกวาด DB ทดสอบ, ผังพอร์ตตู้ as-built → [[SESSION_HANDOVER_2026-08-25|Handover 25 ส.ค.]] · [[PBX_PORT_ROOM_MAPPING|Port→Room Map]]

### 🎭 Mode Isolation & Simulation Bar (26 ส.ค. 2569)
- **25–26 ส.ค.** — **Cloud Run Data Loss Incident** (rev ไร้ `SNC_DB_BACKEND` → event หายเมื่อ scale-to-zero) แก้รากปัญหา deploy script + code guard → [[SNC_CLOUDRUN_DATALOSS_INCIDENT_2026-08-25|Incident Report]]
- **26 ส.ค.** — คู่มือ Workflow 5 ขั้น (สร้าง→จำลอง→ดู→Commit→Deploy) + Source Tagging `demo|real` → [[SNC_DEVELOPMENT_WORKFLOW_GUIDE|Workflow Guide]]
- **26 ส.ค.** — **Mode Isolation ฉบับ File-based**: `app/demo.html` (Simulation Bar: STA/ห้องน้ำ/Ack/Clear + Fast SLA Test ลูปอัตโนมัติ) แยกจาก `index.html` (Production ถาวร), CTA Landing/ROI ชี้ `demo.html`, ผ่าน smoke test วงจร SLA + isolation + WS filter

### 🖥️ Kiosk v2 & Deploy Hardening (2–3 ก.ย. 2569)
- **2 ก.ย.** — SNC Intelligence Module (Phase 1–3) deploy แบบ Staged Rollout + Monitoring ใหม่ (`/health` ราย service + Telegram dedupe/recovery) → [[SESSION_HANDOVER_2026-09-02|Handover 2 ก.ย.]]
- **3 ก.ย.** — **Kiosk Fit-to-Screen v2** (visualViewport + cap scale 1.3 + media queries) ขึ้น Production พร้อม deploy script hardening: verify markers v2 (จับไฟล์เก่าบน Pi) + backup retention 2 ไฟล์ต่อไฟล์ (เดิมสะสม 27 ไฟล์) → [[SESSION_HANDOVER_2026-09-03|Handover 3 ก.ย.]] · [[0012-deploy-verify-markers-backup-retention|ADR 0012]]

---

## 📦 Handover ล่าสุด (Session ต่อเนื่อง — อ่านตัวนี้ก่อน)
- **[[SESSION_HANDOVER_2026-09-03|Handover 3 ก.ย.]]** — ล่าสุด: Kiosk Fit-to-Screen v2 + Deploy Script Hardening
- **[[SESSION_HANDOVER_2026-09-02|Handover 2 ก.ย.]]** — Monitoring ใหม่: /health ราย service + Telegram Menu + Dedupe/Recovery
- **[[SESSION_HANDOVER_2026-08-25|Handover 25 ส.ค.]]** — Dashboard Overhaul + Real/Demo Separation + As-built PBX Mapping

> ⚠️ **อ่านเฉพาะ handover ล่าสุด** สำหรับงาน Ops/Deploy — handover เก่าครอบคลุมหัวข้ออื่น ให้ดูเฉพาะเมื่อต้องการย้อนประวัติ

---

## 🗄️ เอกสารอ้างอิงจำแนกตามหัวข้อ
| หัวข้อ | เอกสาร |
|---|---|
| **Deploy / Ops** | [[DEPLOYMENT_PI4|Deploy Pi4]] · [[DEPLOYMENT_CHECKLIST|Deploy Checklist]] · [[SNC_SYSTEMD_SERVICES_SUMMARY|Systemd]] |
| **Cloudflare Tunnel** | [[SNC_CLOUDFLARE_TUNNEL_SUMMARY]] · [[SNC_CLOUDFLARE_SETUP_SUMMARY]] |
| **PBX / Hardware** | [[phonik_nurse_call_knowledge|Phonik Knowledge]] · [[SNC_PBX_CONNECTIVITY_TROUBLESHOOTING|Connectivity]] · [[SNC_PBX_RDSS_REALTIME_CHANNEL|RDSS]] |
| **API Key / Secrets** | [[SNC_API_KEY_SETUP_GUIDE|Setup]] · [[SNC_API_KEY_ROTATION_GUIDE|Rotation]] |
| **ทดสอบ / หน้างาน** | [[FIELD_TEST_CHECKLIST]] · [[FIELD_TEST_DAY_PLAN]] · [[SNC_POST_BURNIN_FIELD_TEST_PLAN]] · [[SNC_TEST_EXTENSION_INVENTORY|Extension Inventory]] |
| **สาธิต / คู่มือ** | [[SNC_GO_LIVE_MANUAL|Demo & Go-Live]] · [[STAFF_GUIDE_TH|คู่มือพนักงาน]] |
| **Alerts** | [[SNC_TELEGRAM_ALERTS|Telegram]] |

---

## 🏛️ ADR (Architecture Decision Records)
| ADR | เรื่อง |
|---|---|
| [[0001-record-architecture-decisions|0001]] | มาตรฐานการบันทึก ADR |
| [[0002-separate-alert-bridge|0002]] | แยก Alert Bridge เป็น service อิสระ |
| [[0003-firestore-over-sqlite-cloud|0003]] | Firestore แทน SQLite บน Cloud Run |
| [[0004-outbox-idempotency|0004]] | Durable delivery via Outbox + idempotency |
| [[0005-iac-terraform|0005]] | IaC ด้วย Terraform |
| [[0006-broker-dual-pi|0006]] | Broker บน Dual Pi |
| [[0007-nomenclature-separation|0007]] | แยกชื่อ SNC ออกจาก Hotel-ECS |
| [[0008-system-topology-interconnection|0008]] | โครงสร้างความเชื่อมโยงทั้งระบบ (topology) |