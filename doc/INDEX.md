---
title: "INDEX — สารบัญหลัก SNC Wiki"
type: index
tags: [index, snc, toc]
---

# 🗂️ SNC Wiki — สารบัญหลัก

> นี่คือจุดเริ่มต้นของ Obsidian vault (`doc/`) — ใช้ค้นหัวข้อที่ต้องการศึกษา
> ภาษา/คำศัพท์อ้างอิงตาม [[NOMENCLATURE|NOMENCLATURE — มาตรฐานการเรียกขาน]]
> โครงสร้าง: `wiki/` (ความรู้กลั่นแล้ว) · `adr/` (การตัดสินใจ) · `raw/` (เอกสารเก่า ย้อนดู) · `playbooks/` (SOP/ปฏิบัติ ผ่าน Human Approval)

---

## 📚 ควรเริ่มจากตรงนี้ (ความรู้แกนระบบ)

| หมวด | เอกสาร |
|---|---|
| **มาตรฐานการเรียกขาน** | [[NOMENCLATURE]] |
| **Blueprint 5-Core** | [[BLUEPRINT_5CORE]] |
| **Roadmap — Knowledge Loop** | [[ROADMAP_ANTIGRAVITY_FABRIC]] · [[0013-antigravity-fabric-wikiskill-loop|ADR 0013]] |
| **ผังสถาปัตยกรรม** | [[ARCHITECTURE_FLOW]] · [[ARCHITECTURE_DIAGRAM]] |
| **สรุปเชิงสถาปัตยกรรมล่าสุด** | [[ARCHITECTURE_FLOW#Knowledge Header]] · [[SESSION_HANDOVER_2026-09-01]] |
| **ฐานความรู้ Phonik** | [[phonik_nurse_call_knowledge]] |
| **แผนโครงการ** | [[smart_nurse_call_project_plan]] |

---

## 🔍 หัวข้อที่ควรศึกษา (โดยหมวด)

### 🔄 Knowledge Loop (Vault Distillation)
- **คู่มือใช้งาน Knowledge Loop**: [[SNC_KNOWLEDGE_LOOP_GUIDE]] — export traces → Fabric 3 patterns → draft → Human Review

### ⚙️ ระบบ & ปฏิบัติการ
- **Deploy บน Pi4**: [[DEPLOYMENT_PI4]] · [[DEPLOYMENT_CHECKLIST]]
- **Systemd Services**: [[SNC_SYSTEMD_SERVICES_SUMMARY]]
- **Cloudflare Tunnel**: [[SNC_CLOUDFLARE_TUNNEL_SUMMARY]] · [[SNC_CLOUDFLARE_SETUP_SUMMARY]]
- **API Key / Secrets**: [[SNC_API_KEY_SETUP_GUIDE]] · [[SNC_API_KEY_ROTATION_GUIDE]]
- **Cloud Run Incident (data loss)**: [[SNC_CLOUDRUN_DATALOSS_INCIDENT_2026-08-25]]
- **Telegram Alerts**: [[SNC_TELEGRAM_ALERTS]]
- **Health & Monitoring (3 ชั้น)**: [[SNC_HEALTH_MONITORING]] — /health schema + เมนูตรวจระบบ + alert/dedupe/recovery
- **SNC Intelligence Module**: [[SNC_INTELLIGENCE_MODULE_GUIDE]] — Ops Self-Healing เฟสที่ 1 และ Safe Execution Gate
- **Email / SMTP Contact Alerts**: [[SNC_SMTP_EMAIL_SETUP]]

### 📡 PBX / Listener
- **แก้ปัญหาเชื่อมต่อ PBX**: [[SNC_PBX_CONNECTIVITY_TROUBLESHOOTING]]
- **ช่องทาง RDSS Real-time**: [[SNC_PBX_RDSS_REALTIME_CHANNEL]]
- **Power Cycle ตู้ PBX**: [[PBX_POWER_CYCLE_SOP]]

### 🧪 ทดสอบ & หน้างาน
- **Plan หลัง Burn-in**: [[SNC_POST_BURNIN_FIELD_TEST_PLAN]]
- **Field Test Checklist / Day Plan**: [[FIELD_TEST_CHECKLIST]] · [[FIELD_TEST_DAY_PLAN]]
- **ทะเบียนเบอร์ทดลอง**: [[SNC_TEST_EXTENSION_INVENTORY]]
- **คู่มือพนักงาน**: [[STAFF_GUIDE_TH]]
- **คู่มือสาธิต & Go-Live**: [[SNC_GO_LIVE_MANUAL]]

### 🏛️ สถาปัตยกรรม & ยุทธศาสตร์
- **มุมมองเชิงวิชาการ (ISO/IEC 30141)**: [[SNC_ARCHITECTURE_ACADEMIC_VIEW]]
- **Sovereign AI Blueprint**: [[SNC_SOVEREIGN_AI_BLUEPRINT]]

### 📅 Timeline & Handover
- **ไทม์ไลน์เต็ม**: [[project_timeline]]
- **Index Timeline (ย่อ)**: [[INDEX_TIMELINE]]
- **Handover ล่าสุด**: [[SESSION_HANDOVER_2026-09-03]] · [[SESSION_HANDOVER_2026-09-02]] · [[SESSION_HANDOVER_2026-09-01]]

---

## 🏛️ ADR — Architecture Decision Records
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
| [[0009-opencode-agent-tunnel|0009]] | แยก OpenCode agent + tunnel เฉพาะกิจ |
| [[0010-websocket-heartbeat|0010]] | WebSocket heartbeat (ping/pong) ตรวจจับสายค้าง |
| [[0011-snc-intelligence-module|0011]] | SNC Intelligence Module — Non-Critical Autonomous Operations |
| [[0012-deploy-verify-markers-backup-retention|0012]] | Deploy Verify Markers + Backup Retention |
| [[0013-antigravity-fabric-wikiskill-loop|0013]] | Antigravity Orchestrator + Fabric + WikiSkill Knowledge Loop |

---

## 🗄️ เอกสารเก่า / Legacy (`raw/` — ย้อนดู ไม่ใช่ reference หลัก)
> ไฟล์เหล่านี้มีคำ legacy (`snc-poc`, `hotel-ecs`) เก็บไว้ย้อนประวัติ — ตามหลัก NOMENCLATURE ห้ามอ้างเป็น standard

- [[IMPLEMENTATION_SUMMARY]] · [[README_DEPLOYMENT]] · [[PHASE1_IMPLEMENTATION]] · [[PHASE1_COMPLETION_SUMMARY]]
- [[DASHBOARD_EVENTS_FIX]] · [[SMDR_PARSING_FIX]] · [[snc_analysis_report]] · [[github-copilot-snc]]

---

## 📖 Playbooks — Skills Layer (`playbooks/` — SOPs & Action Guides)
> เอกสารปฏิบัติที่ผ่าน **Human Review & Approve (PR → merge)** แล้วเท่านั้น — ดู [[0013-antigravity-fabric-wikiskill-loop|ADR 0013]]

- ยังไม่มี playbook ทางการ — อยู่ระหว่าง Phase 2–4 ของ [[ROADMAP_ANTIGRAVITY_FABRIC|Roadmap Knowledge Loop]]

---

## 🚀 Quick Start
```bash
# รันระบบบน Pi4
./ops/quick_start.sh
curl -s http://localhost:8000/health
# ดูสถานะบริการ
ssh pi4 "systemctl status snc-backend snc-pbx-listener"
```

*จัดทำ: 17 ส.ค. 2569*