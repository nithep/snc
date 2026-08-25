---
title: "SNC Architecture — Academic View (มุมมองเชิงวิชาการของสถาปัตยกรรมระบบ)"
type: architecture
tags: [architecture, iot, edge-cloud, reference-model, academic]
---

# 🎓 SNC Architecture — Academic View

> จัดโครงสร้างระบบ SNC ตามกรอบอ้างอิงวิชาการ — ใช้ประกอบการอธิบายเชิงวิชาการ/เขียนรายงาน
> ฉบับปฏิบัติการอยู่ที่ [[ARCHITECTURE_FLOW]] · [[ARCHITECTURE_DIAGRAM]] · topology ฉบับเต็ม [[0008-system-topology-interconnection]]

## 📛 ชื่อเรียกทางวิชาการ

- **ระบบ:** ระบบเฝ้าระวังเหตุการณ์เรียกพยาบาลเรียลไทม์ บนสถาปัตยกรรม Edge–Cloud แบบไฮบริด
  *(Real-time Nurse Call Event Monitoring System on a Hybrid Edge–Cloud Architecture)*
- ลักษณะสำคัญ: เป็น **Digital Twin** ของระบบ nurse call แบบ legacy PBX — แปลงสัญญาณโทรศัพท์เดิม (SMDR) เป็นเหตุการณ์ดิจิทัลที่วัดผลได้ (SLA/KPI)
- **เอกสารตรวจรับการเชื่อมโยง:** End-to-End Connectivity Verification Matrix
  (ตามแนว *Service Validation & Testing* — ITIL 4 / ISO/IEC 20000)

## 🏗️ โครงสร้างแบบแบ่งชั้น — อ้างอิง ISO/IEC 30141 (IoT Reference Architecture)

| ชั้น | องค์ประกอบใน SNC | ศัพท์เทคนิค | โค้ด/หลักฐาน |
|---|---|---|---|
| **1. Perception / Device** (ชั้นรับรู้) | ตู้ Phonik DX-32C/80C/144C, ปุ่ม NCX-CORD / สวิทช์ฉุกเฉิน NCX-PULL | Legacy field devices; SMDR telemetry source | ฮาร์ดแวร์ — ดู [[phonik_nurse_call_knowledge]] |
| **2. Edge** (ชั้นขอบ) | Pi 4: SMDR listener, TCP proxy :2323, Outbox (SQLite WAL) | Edge gateway; protocol translation; durable local buffer | `pbx/snc_pbx_listener.py`, `pbx/event_outbox.py` |
| **3. Network** (ชั้นขนส่ง) | Telnet :23 (single-session ตู้), TCP :2323 mirror, HTTPS/TLS outbound, Cloudflare Tunnel (inbound) | Southbound legacy transport; northbound secure egress; reverse-proxy ingress | `Cloudflare_Tunnel_Setup`, tunnel systemd |
| **4. Platform / Cloud** | Cloud Run (serverless container), Firestore (NoSQL), IAM/Secrets, Cloud Build | CaaS/FaaS; DBaaS; control plane | `api/Dockerfile`, `api/cloudbuild.yaml` |
| **5. Application** | FastAPI REST+WebSocket, FHIR-like event schema, Dashboard, SLA/KPI analytics | Event-driven service; pub-sub broadcast; analytics | `api/server.py`, `app/index.html` |

> ทางเลือกกรอบอ้างอิงอื่น: แบบ 4 ชั้น (Perception–Network–Middleware–Application) และ ITU-T Y.2060 ให้ผลการจัดกลุ่มสอดคล้องกัน

## 🔬 Design Patterns ที่ระบบใช้

| Pattern | จุดใช้งาน | ผลเชิงสถาปัตยกรรม | ADR/ร่องรอย |
|---|---|---|---|
| Transactional Outbox | คิวส่ง event ฝั่ง Pi | At-least-once delivery กัน data loss ตอน backend ล่ม | [[0004-outbox-idempotency]] |
| Idempotent Consumer | dedup ด้วย `event_id` (INSERT OR IGNORE) | กัน duplicate → SLA วัดแม่น | [[0004-outbox-idempotency]] |
| Critical-path Isolation | local = critical, cloud = best-effort fan-out | ความล้มเหลวปลายทางรองไม่ propagate กลับ | `snc_pbx_listener.py:_flush_outbox` |
| Protocol Gateway / Message Translator | SMDR → FHIR-like JSON | Legacy modernization + เตรียม HL7 FHIR/GCP Healthcare | AGENTS.md ข้อ 3 |
| Fail-closed Deployment Verification | verify `db=firestore` ทั้งสอง script + code guard `K_SERVICE` | กัน silent degradation (บทเรียน incident) | [[SNC_CLOUDRUN_DATALOSS_INCIDENT_2026-08-25]] |
| Observer / Pub-Sub | WebSocket broadcast ไป nurse station | Real-time push หลายผู้รับพร้อมกัน | `api/server.py` |
| Self-healing Keep-alive | Heartbeat 30s + watchdog 60s + auto-reconnect | รักษา session ตู้ PBX 24/7 | `snc_pbx_listener.py` |

## 📐 Topology — Hub-and-Spoke สองระนาบ (Control Plane / Data Plane)

```
[Control Plane]  mbd2019 (ops/dev) ──── git/GitHub (nithep/snc)
                        │  deploy (cloudbuild)      │  clone/pull (sync)
                        ▼                           ▼
[Data Plane]   PBX ตู้สาขา ──:23──▶ pi4 (edge hub) ──HTTPS──▶ Cloud Run ──▶ Firestore
                     ╲                │    ▲                      │
                      ╲──:2323 mirror─┘    └── WebSocket ────────┤
                                             (dashboard)         ▼
                                                          KPI/SLA analytics
```

- **Pi = local hub ฝั่ง data** — จุดเดียวที่จับ SMDR (ตู้รับ 1 session) แล้วกระจายทั้ง local backend และ cloud
- **GitHub = hub ฝั่ง control** — source of truth ของโค้ด/เอกสาร; deploy เข้า cloud ผ่าน Cloud Build เท่านั้น
- ธรรมชาติการไหลข้อมูล: **Event-Driven Architecture (EDA)** — capture → normalize → persist → broadcast → analyze

## 🔗 เส้นเชื่อม 6 เส้น (ผลตรวจยืนยันล่าสุด 26 ส.ค. 2569)

| เส้นเชื่อม | ผล | วิธีตรวจ |
|---|---|---|
| mbd2019 → git | ✅ | local = origin = `0830caa` |
| git → pi4 | ✅ | ff-merge clone บน Pi (`~/snc`) |
| pi4-pbx → ตู้ PBX | ✅ | `Connected successfully` + heartbeat 30s |
| pi4 → cloud | ✅ | Outbox dual-target, key hash ตรงกัน |
| mbd2019 → pi4-pbx (:2323) | ✅ | TCP connect + server-side log |
| cloud internal/public | ✅ | `/health` db=firestore, auth 401 |

## 📚 คำศัพท์เทียบมาตรฐาน (Glossary Bridge)

| ศัพท์ในระบบ | ศัพท์วิชาการ/มาตรฐาน |
|---|---|
| Listener | Protocol Gateway / Edge Collector |
| Outbox | Transactional Outbox (durable queue) |
| SMDR | Station Message Detail Recording (telephony CDR variant) |
| Nurse Station Dashboard | Situational Awareness Console |
| SLA/KPI | Service Level Objective (SLO) measurement |
| Cloud Run + Firestore | Serverless Container + Managed NoSQL (DBaaS) |
| Digital Twin | Virtual representation synchronized with physical process |

## 🗂️ เอกสารเกี่ยวข้อง

- การตัดสินใจเชิงสถาปัตยกรรม: [[0001-record-architecture-decisions]] · [[0003-firestore-over-sqlite-cloud]] · [[0004-outbox-idempotency]] · [[0006-broker-dual-pi]] · [[0008-system-topology-interconnection]]
- ฉบับปฏิบัติการ: [[ARCHITECTURE_FLOW]] · [[BLUEPRINT_5CORE]]
- บทเรียนความทนทาน: [[SNC_CLOUDRUN_DATALOSS_INCIDENT_2026-08-25]]

*จัดทำ: 26 ส.ค. 2569 — Senior Software Engineer (opencode)*
