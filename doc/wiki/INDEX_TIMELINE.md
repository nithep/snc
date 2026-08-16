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

---

## 📦 Handover ล่าสุด (Session ต่อเนื่อง — อ่านตัวนี้ก่อน)
- **[[SESSION_HANDOVER_2026-08-16|Handover 16 ส.ค.]]** — ล่าสุด: Cloud Run + Firestore + Monitoring
- **[[SESSION_HANDOVER_2026-08-15|Handover 15 ส.ค.]]** — Burn-in Complete + แผนชั้น 11
- **[[SESSION_HANDOVER_2026-08-13|Handover 13 ส.ค.]]** — Pre-Release → Go-Live

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