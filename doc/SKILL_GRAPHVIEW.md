---
title: "🗺️ SNC Knowledge Graph — Visual Dependency Map for Agents"
type: doc
tags: [graphview, snc, knowledge-graph, agent-flow]
---

# 🗺️ SNC Knowledge Graph — Visual Dependency Map

> **Purpose:** แผนที่เชื่อมโยงเอกสารทั้งหมดของ SNC ให้ agent เห็นภาพรวมว่า
> ความรู้แต่ละชิ้นเชื่อมกับชิ้นไหน — อ่านเป็น flow หรือ lookup ตามต้องการ
> **Created:** 2026-08-21 · **Version:** 1.0

---

## 🔄 Agent Flow (Sequential — เรียงตามลำดับที่ agent ควรอ่าน)

```mermaid
flowchart TD
    START["🤖 Agent Loads SKILL.md"] --> S1
    S1["STEP 1: Understand System<br/>What SNC does, 5-step workflow"] --> S2
    S2["STEP 2: Know the Layout<br/>5-Core structure + Nomenclature"] --> S3
    S3["STEP 3: Event Flow<br/>Signal→Event matrix + RDSS"] --> S4
    S4["STEP 4: Network & Connectivity<br/>Ports, proxy 2323, handshake"] --> S5
    S5["STEP 5: Security & Secrets<br/>Auth model, .env sync, rotation"] --> S6
    S6["STEP 6: Architecture Decisions<br/>ADR chain 0001→0009"] --> S7
    S7["STEP 7: Deploy & Operate<br/>Systemd + Cloud + Tunnel"] --> S8
    S8["STEP 8: Troubleshooting<br/>Find & fix by symptom"] --> S9
    S9["STEP 9: Telegram & Monitoring<br/>Alerting chain"] --> S10
    S10["STEP 10: KPI Targets<br/>SLA compliance"] --> S11
    S11["STEP 11: Operating Modes<br/>/snc diagnose|test|deploy|kpi"] --> S12
    S12["STEP 12: History & Timeline<br/>When things happened"] --> S13
    S13["STEP 13: Safety Rules<br/>Never break these"] --> S14
    S14["STEP 14: Collaboration Map<br/>Who does what"]

    style START fill:#4CAF50,color:#fff
    style S1 fill:#2196F3,color:#fff
    style S2 fill:#2196F3,color:#fff
    style S3 fill:#FF9800,color:#fff
    style S4 fill:#FF9800,color:#fff
    style S5 fill:#f44336,color:#fff
    style S6 fill:#9C27B0,color:#fff
    style S7 fill:#4CAF50,color:#fff
    style S8 fill:#f44336,color:#fff
    style S9 fill:#FF9800,color:#fff
    style S10 fill:#2196F3,color:#fff
    style S11 fill:#4CAF50,color:#fff
    style S12 fill:#607D8B,color:#fff
    style S13 fill:#f44336,color:#fff
    style S14 fill:#607D8B,color:#fff
```

---

## 🏗️ System Architecture Graph (3-Tier Topology — ADR 0008)

```mermaid
flowchart TB
    subgraph DEV["💻 Dev Layer"]
        MB["MateBook D:\\snc"]
    end

    subgraph GIT["🔀 Version Control"]
        GH["GitHub nithep/snc"]
    end

    subgraph EDGE["🏥 Edge Layer (Hospital)"]
        PBX["Phonik PBX<br/>192.168.1.91:23"]
        PI["Pi4 192.168.1.94<br/>snc_pbx_listener<br/>snc-backend:8000<br/>SQLite WAL"]
        CF["cloudflared<br/>(outbound tunnel)"]
        PROXY["TCP Proxy :2323<br/>(Room Manager mirror)"]
    end

    subgraph CLOUD["☁️ Cloud Layer"]
        CFE["Cloudflare Edge<br/>HTTPS TLS 1.3"]
        RUN["Cloud Run<br/>snc-cloud-backend<br/>(Firestore)"]
        BRIDGE["Cloud Run<br/>snc-alert-bridge"]
        MON["Cloud Monitoring<br/>uptime check"]
        SM["Secret Manager"]
        FS["Firestore"]
    end

    subgraph USER["👥 Users"]
        DASH["Nurse Dashboard<br/>snc.nithep.com"]
        TG["Telegram<br/>@snc2569_bot"]
        OCODE["OpenCode Agent<br/>snc-opencode.nithep.com"]
    end

    MB -->|git push| GH
    GH -->|git pull + rsync| PI
    PBX -->|SMDR Telnet| PI
    PI -->|HTTP POST| RUN
    PI -->|WebSocket| CF
    CF -->|outbound| CFE
    CFE -->|https| DASH
    PI -->|mirror| PROXY
    PROXY -.->|emulated handshake| PBX
    MON -->|fail 120s| BRIDGE
    BRIDGE -->|webhook| TG
    RUN --> FS
    RUN --> SM
    CFE --> OCODE
    OCODE -.->|localhost:4096| CF

    style PBX fill:#FF5722,color:#fff
    style PI fill:#4CAF50,color:#fff
    style RUN fill:#2196F3,color:#fff
    style BRIDGE fill:#FF9800,color:#fff
    style DASH fill:#E91E63,color:#fff
```

---

## 📊 Document Dependency Graph (Wiki ↔ ADR ↔ Core)

```mermaid
flowchart LR
    subgraph CORE["📘 Core Docs"]
        AG["AGENTS.md<br/>(repo rules)"]
        BP["BLUEPRINT_5CORE.md"]
        AF["ARCHITECTURE_FLOW.md"]
        NM["NOMENCLATURE.md"]
        QR["QUICK_REFERENCE.md"]
    end

    subgraph ADR["🏛️ ADR Chain"]
        A1["0001: ADR Pattern"]
        A2["0002: Alert Bridge"]
        A3["0003: Firestore"]
        A4["0004: Outbox"]
        A5["0005: Terraform"]
        A6["0006: Broker (future)"]
        A7["0007: Nomenclature"]
        A8["0008: Topology"]
        A9["0009: OpenCode"]
    end

    subgraph WIKI_DEPLOY["🔧 Deployment Wiki"]
        W1["SYSTEMD_SERVICES_SUMMARY"]
        W2["CLOUDFLARE_TUNNEL_SUMMARY"]
        W3["CLOUDFLARE_SETUP_SUMMARY"]
        W4["DOMAIN_MIGRATION_NOTE"]
    end

    subgraph WIKI_SEC["🔐 Security Wiki"]
        W5["API_KEY_SETUP_GUIDE"]
        W6["API_KEY_ROTATION_GUIDE"]
        W7["TELEGRAM_ROTATION_GUIDE"]
        W8["CLOUDFLARE_ROTATION_GUIDE"]
        W9["GEMINI_API_KEY_ROTATION_GUIDE"]
    end

    subgraph WIKI_HW["📡 PBX/Hardware Wiki"]
        W10["phonik_nurse_call_knowledge"]
        W11["PBX_CONNECTIVITY_TROUBLESHOOTING"]
        W12["PBX_RDSS_REALTIME_CHANNEL"]
    end

    subgraph WIKI_OPS["🔔 Operations Wiki"]
        W13["TELEGRAM_ALERTS"]
        W14["NOMENCLATURE_CLEANUP"]
        W15["OPENCODE_SETUP_GUIDE"]
    end

    subgraph WIKI_TEST["🧪 Testing Wiki"]
        W16["TEST_EXTENSION_INVENTORY"]
        W17["POST_BURNIN_FIELD_TEST_PLAN"]
        W18["GO_LIVE_MANUAL"]
    end

    subgraph WIKI_HIST["📅 History"]
        W19["project_timeline"]
        W20["INDEX_TIMELINE"]
        W21["SESSION_HANDOVER_2026-08-19"]
    end

    %% Core connections
    AG --> BP
    AG --> NM
    BP --> AF
    AF --> QR

    %% ADR chain
    A1 --> A2
    A1 --> A3
    A1 --> A4
    A1 --> A5
    A2 --> A3
    A3 --> W3
    A4 -.-> W11
    A7 --> NM
    A7 --> W14
    A8 --> AF
    A8 --> W1
    A8 --> W2
    A9 --> W15

    %% Wiki to Core
    W1 --> BP
    W1 --> AF
    W2 --> BP
    W4 --> W2
    W5 --> W6
    W6 --> AG
    W7 --> W13
    W8 --> W2
    W10 --> QR
    W11 --> W12
    W12 --> W11
    W13 --> W7
    W16 --> QR
    W17 --> W16
    W18 --> QR
    W19 --> W20
    W20 --> W21

    style AG fill:#f44336,color:#fff
    style BP fill:#4CAF50,color:#fff
    style AF fill:#2196F3,color:#fff
    style NM fill:#FF9800,color:#fff
    style QR fill:#607D8B,color:#fff
```

---

## 🔗 Secret Rotation Dependency Graph

```mermaid
flowchart TD
    subgraph PI_SECRETS["Pi4 Secrets (.env)"]
        AK["SNC_API_KEY<br/>api/.env"]
        PBXK["PBX_PASS<br/>pbx/.env"]
        TGK["TELEGRAM_BOT_TOKEN<br/>api/.env"]
        TGID["TELEGRAM_CHAT_ID<br/>api/.env"]
    end

    subgraph CLOUD_SECRETS["Cloud Secrets (Secret Manager)"]
        CAK["snc-api-key"]
        CTG["snc-telegram-bot-token"]
        CMW["snc-monitor-webhook-token"]
    end

    subgraph TUNNEL["Tunnel Secrets"]
        CRED["credentials.json<br/>(cloudflared)"]
        CENV["cloudflared.env"]
    end

    subgraph OPCODE["OpenCode Secrets"]
        OENV["opencode.env<br/>OPENCODE_SERVER_PASSWORD"]
        OKEY["OPENROUTER_API_KEY"]
    end

    %% Sync relationships
    AK -.->|"must match"| CAK
    TGK -.->|"must match"| CTG
    CMW -.->|"webhook auth"| MON

    subgraph MONITORING["Monitoring"]
        MON["Cloud Monitoring<br/>uptime check"]
    end

    MON -->|fail| BRIDGE["snc-alert-bridge"]
    BRIDGE -->|token auth| CMW
    BRIDGE -->|sendMessage| TGK

    CRED --> CENV
    CENV -->|"mounted by"| SVC["snc-cloudflared.service"]

    style AK fill:#f44336,color:#fff
    style CAK fill:#f44336,color:#fff
    style TGK fill:#FF9800,color:#fff
    style CTG fill:#FF9800,color:#fff
```

---

## ⚡ Event Lifecycle Graph (Signal → DB → Dashboard)

```mermaid
stateDiagram-v2
    [*] --> IDLE: System Online

    IDLE --> CALLING: Patient presses NCX-CORD<br/>(PBX emits e.{room})

    CALLING --> ACKNOWLEDGED: Nurse Ack<br/>(onM/onto signal)

    CALLING --> EMERGENCY: Repeat call within 90s<br/>(Temporal Escalation)

    ACKNOWLEDGED --> RESOLVED: Nurse clears<br/>(offM/offx signal)

    EMERGENCY --> ACKNOWLEDGED: Nurse Ack

    RESOLDED --> IDLE: Dashboard resets

    state CALLING {
        [*] --> RedFlash
        RedFlash: 🔴 Red Flash + Siren<br/>Ack timer starts (≤30s)
        RedFlash --> YellowAck: Nurse presses Ack
        RedFlash --> Breach: >30s no ack
    }

    state EMERGENCY {
        [*] --> FasterAlert
        FasterAlert: 🔴🔴 Faster Alert<br/>Bathroom Emergency
        FasterAlert --> YellowAck: Nurse presses Ack
    }

    state ACKNOWLEDGED {
        [*] --> YellowCard
        YellowCard: 🟡 Yellow Card<br/>Resolution timer (≤180s)
        YellowCard --> Green: Nurse clears
    }
```

---

## 📁 5-Core File Tree with Knowledge Links

```
snc/
├── api/
│   ├── server.py ─────────────────── ADR 0003 (Firestore), ADR 0004 (idempotency)
│   ├── storage.py ────────────────── ADR 0003 (factory: sqlite|firestore)
│   ├── bridge_server.py ──────────── ADR 0002 (alert bridge, แยก service)
│   ├── nurse_call_events.db ──────── SQLite WAL (Edge DB)
│   ├── services/
│   │   └── gemini_direct_service.py  AI report generation
│   └── .env ──────────────────────── 🔐 STEP 5 (SNC_API_KEY, TELEGRAM_*)
│
├── app/
│   ├── index.html ────────────────── Nurse Dashboard v2.0
│   ├── landing.html ──────────────── Landing page (SEO)
│   ├── roi.html ──────────────────── Content article
│   ├── snc-vs-imported.html ──────── Content article
│   └── how-to-phonik.html ────────── Content article + SOS CALL
│
├── pbx/
│   ├── snc_pbx_listener.py ──────── STEP 3 (SMDR/RDSS), STEP 4 (proxy 2323)
│   ├── event_outbox.py ───────────── ADR 0004 (durable delivery)
│   ├── test_smdr_parser.py ──────── STEP 11 (test mode)
│   └── .env ──────────────────────── 🔐 STEP 5 (PBX_PASS, SNC_API_KEY)
│
├── ops/
│   ├── notify-telegram.sh ────────── STEP 9 (Telegram alert)
│   ├── snc_telegram_agent.py ─────── STEP 9 (Q&A agent)
│   ├── tunnel-self-heal.sh ──────── STEP 9 (auto-recover tunnel)
│   ├── snc-evening-digest.sh ─────── STEP 9 (daily digest)
│   ├── deploy-snc-one-shot.sh ────── STEP 7 (deploy)
│   ├── backup-snc-db.sh ──────────── STEP 7 (backup cron)
│   ├── verify-daily.sh ──────────── STEP 9 (daily verify)
│   └── terraform/ ────────────────── ADR 0005 (IaC)
│
└── doc/
    ├── BLUEPRINT_5CORE.md ────────── STEP 2 (project structure)
    ├── ARCHITECTURE_FLOW.md ──────── STEP 7 (full topology)
    ├── NOMENCLATURE.md ───────────── STEP 2 (glossary)
    ├── QUICK_REFERENCE.md ────────── STEP 8 (cheat card)
    ├── adr/ ──────────────────────── STEP 6 (0001-0009)
    └── wiki/
        ├── phonik_nurse_call_knowledge.md ── STEP 1 (HW catalog)
        ├── SNC_PBX_RDSS_REALTIME_CHANNEL.md ── STEP 3 (RDSS)
        ├── SNC_PBX_CONNECTIVITY_TROUBLESHOOTING.md ── STEP 8
        ├── SNC_SYSTEMD_SERVICES_SUMMARY.md ── STEP 7
        ├── SNC_CLOUDFLARE_TUNNEL_SUMMARY.md ── STEP 7
        ├── SNC_TELEGRAM_ALERTS.md ── STEP 9
        ├── SNC_API_KEY_ROTATION_GUIDE.md ── STEP 5
        ├── SNC_TELEGRAM_ROTATION_GUIDE.md ── STEP 5
        ├── SNC_CLOUDFLARE_ROTATION_GUIDE.md ── STEP 5
        ├── SNC_GO_LIVE_MANUAL.md ── STEP 11
        ├── SNC_POST_BURNIN_FIELD_TEST_PLAN.md ── STEP 11
        ├── SNC_TEST_EXTENSION_INVENTORY.md ── STEP 3
        ├── SNC_NOMENCLATURE_CLEANUP.md ── STEP 2
        ├── SNC_DOMAIN_MIGRATION_NOTE.md ── STEP 7
        ├── SNC_OPENCODE_SETUP_GUIDE.md ── STEP 6 (ADR 0009)
        ├── SNC_SOVEREIGN_AI_BLUEPRINT.md ── Architecture
        ├── project_timeline.md ── STEP 12
        ├── INDEX_TIMELINE.md ── STEP 12
        ├── SESSION_HANDOVER_2026-08-19.md ── STEP 12
        └── WINDOWS_SCHEDULED_TASK_HYGIENE.md ── Ops
```

---

## 🔍 Lookup by Concern (Find the Right Doc Fast)

| ต้องการรู้... | อ่าน... |
|--------------|---------|
| ฮาร์ดแวร์ Phonik คืออะไร | `wiki/phonik_nurse_call_knowledge.md` |
| ตู้ต่อสายยังไง | `wiki/phonik_nurse_call_knowledge.md` §4 |
| ระบบ SOS CALL ทำงานยังไง | `wiki/phonik_nurse_call_knowledge.md` §7.1 |
| Listener แปลงสัญญาณยังไง | STEP 3 (SKILL.md) + `pbx/snc_pbx_listener.py` |
| RDSS poll คืออะไร | `wiki/SNC_PBX_RDSS_REALTIME_CHANNEL.md` |
| ตู้ไม่ยอมต่อ (Errno 111) | `wiki/SNC_PBX_CONNECTIVITY_TROUBLESHOOTING.md` |
| Session lock แก้ยังไง | `wiki/SNC_PBX_CONNECTIVITY_TROUBLESHOOTING.md` + power cycle |
| Systemd ตั้งค่ายังไง | `wiki/SNC_SYSTEMD_SERVICES_SUMMARY.md` |
| Cloudflare tunnel ตั้งค่ายังไง | `wiki/SNC_CLOUDFLARE_TUNNEL_SUMMARY.md` |
| Tunnel 502 แก้ยังไง | `wiki/SNC_CLOUDFLARE_TUNNEL_SUMMARY.md` §กฎเหล็ก |
| Tunnel self-heal ทำงานยังไง | ADR 0009 + `ops/tunnel-self-heal.sh` |
| หมุน API key ยังไง | `wiki/SNC_API_KEY_ROTATION_GUIDE.md` |
| หมุน Telegram token ยังไง | `wiki/SNC_TELEGRAM_ROTATION_GUIDE.md` |
| หมุน Cloudflare credentials ยังไง | `wiki/SNC_CLOUDFLARE_ROTATION_GUIDE.md` |
| Outbox ทำงานยังไง | ADR 0004 + `pbx/event_outbox.py` |
| Firestore vs SQLite ต่างกันยังไง | ADR 0003 + `api/storage.py` |
| Bridge คืออะไร ทำไมแยก | ADR 0002 |
| ทำไมต้อง Terraform | ADR 0005 |
| ทำไมยังไม่ใช้ Broker | ADR 0006 |
| ชื่อ legacy แก้ยังไง | ADR 0007 + `wiki/SNC_NOMENCLATURE_CLEANUP.md` |
| Domain ย้ายจาก nursecall → snc ยังไง | `wiki/SNC_DOMAIN_MIGRATION_NOTE.md` |
| OpenCode ติดตั้งยังไง | ADR 0009 + `wiki/SNC_OPENCODE_SETUP_GUIDE.md` |
| Telegram bot ตั้งค่ายังไง | `wiki/SNC_TELEGRAM_ALERTS.md` |
| Q&A agent ถามอะไรได้บ้าง | `wiki/SNC_TELEGRAM_ALERTS.md` §Q&A |
| สาธิตผู้บริหารยังไง | `wiki/SNC_GO_LIVE_MANUAL.md` |
| Field test ทดสอบอะไรบ้าง | `wiki/SNC_POST_BURNIN_FIELD_TEST_PLAN.md` |
| Timeline โครงการ | `wiki/project_timeline.md` |
| Handover ล่าสุด | `wiki/SESSION_HANDOVER_2026-08-19.md` |
| Topology ทั้งระบบ | ADR 0008 + `doc/ARCHITECTURE_FLOW.md` |
| KPI targets | STEP 10 (SKILL.md) |
| กฎ agent อะไรบ้าง | `AGENTS.md` + STEP 13 (SKILL.md) |

---

## 📐 Architecture Evolution Timeline

```mermaid
timeline
    title SNC Architecture Evolution
    section Aug 1-2
        Edge Serial/TCP Listener : Pi Zero 2W : Vertex AI Payload
        Pi Zero 2W Deploy : 192.168.1.20
    section Aug 3-5
        SNC PoC Strategy : Separate workspace
        MVP Validation : Zero-Hardware SLA
        Field Go-Live : Executive Approved
    section Aug 8-9
        SQLite WAL + Hotfix : Pi Zero 2W RAM issue
        Live E2E on Pi 4 : First production run
    section Aug 10-12
        Auth Hardening : X-API-Key
        Systemd Services : Self-healing
        Cloudflare Tunnel : Zero open ports
        TCP Proxy 2323 : Room Manager mirror
        RDSS Polling + Watchdog
    section Aug 13-15
        Dashboard v2.0 : Premium Dark Mode
        5-Core Split : api/app/pbx/ops/doc
        Burn-in 48h : 0 FAIL
    section Aug 16-17
        Cloud Run + Firestore : ADR 0002-0006
        Outbox + Idempotency
    section Aug 18-19
        Nomenclature Cleanup : ADR 0007
        Domain nursecall → snc
        Rotation Guides x3
        Tunnel Self-Heal Script
    section Aug 20
        ADR 0008-0009 : OpenCode Agent
        Power Outage Recovery
```

---

*Graphview v1.0 — สร้างจาก wiki 28 ไฟล์ + ADR 9 ฉบับ + raw 9 ไฟล์ + core docs 6 ไฟล์*
*อัปเดตครั้งถัดไปเมื่อมี ADR หรือ wiki doc ใหม่*
