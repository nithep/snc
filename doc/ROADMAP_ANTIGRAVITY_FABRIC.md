---
title: "Roadmap — SNC + Antigravity + Fabric + WikiSkill"
type: roadmap
tags: [roadmap, fabric, wiki, playbooks, knowledge-loop, nightly]
---

# 🗺️ Roadmap — SNC + Antigravity + Fabric + WikiSkill

> สถาปัตยกรรม Knowledge Loop (บันทึกการตัดสินใจ: [[0013-antigravity-fabric-wikiskill-loop|ADR 0013]])
> Critical Path (ความปลอดภัยชีวิต) ทำงาน deterministic & sub-second — ส่วนนี้คือ
> Enriched Intelligence Layer ที่ไม่รบกวน Critical Path

```mermaid
flowchart TD
    subgraph CP ["CRITICAL PATH (Life-Safety: Deterministic & Sub-second)"]
        PBX["Phonik PBX (DX-Series)<br/>Telnet :23"] -->|Raw SMDR| LIS["snc_pbx_listener.py<br/>(Edge Node Pi 4)"]
        LIS -->|Durable Delivery| OUT["event_outbox.py<br/>+ SQLite WAL"]
        OUT -->|FastAPI Trigger| API["SNC Backend API<br/>(:8000)"]
        API -->|WebSocket Push| DASH["Nurse Dashboard<br/>(app/index.html)"]
    end

    subgraph ENR ["ENRICHED INTELLIGENCE & BACKGROUND LEARNING"]
        OUT -.->|Non-PHI Trace Dump| RAW["ops/raw/<br/>(Event & Telemetry Traces)"]

        SCHED["Antigravity Orchestrator<br/>(/schedule & Sub-agents)"] -->|Nightly Maintenance| FAB["Fabric Patterns<br/>(ops/fabric/patterns/)"]
        RAW --> FAB
        FAB -->|Distill & Synthesize| WIKI["Wiki Layer (doc/wiki/)<br/>- Ward/Bed Context<br/>- SLA Bottlenecks"]
        FAB -->|Draft PR/Artifact| PB["Skills Layer (doc/playbooks/)<br/>- SOPs & Action Guides"]

        HUMAN["Head Nurse / System Operator"] -->|Review & Approve PR| MERGE["Git Commit / Merge"]
        MERGE --> PB
    end

    style CP fill:#1e293b,stroke:#ef4444,stroke-width:2px,color:#fff
    style ENR fill:#0f172a,stroke:#3b82f6,stroke-width:2px,color:#fff
    style PBX fill:#334155,stroke:#64748b,color:#fff
    style DASH fill:#064e3b,stroke:#10b981,color:#fff
    style HUMAN fill:#78350f,stroke:#f59e0b,color:#fff
```

## 📅 Gantt — 5 เฟส

```mermaid
gantt
    title SNC + Antigravity + Fabric + WikiSkill Roadmap
    dateFormat  YYYY-MM-DD
    section Phase 1: Scaffolding
    สร้างไดเรกทอรี & .gitignore & ADR 0013       :done, p1, 2026-09-04, 1d
    section Phase 2: Fabric Tools
    ติดตั้ง Fabric CLI & ออกแบบ 3 Patterns      :done, p2, after p1, 2d
    section Phase 3: Raw Traces
    เขียนสคริปต์ Export Traces (Non-PHI)        :done, p3, after p2, 2d
    section Phase 4: WikiSkill Loop
    ทำ Nightly Batch & Human Review Flow        :done, p4, after p3, 2d
    section Phase 5: Verification
    ทดสอบด้วย Browser Subagent & Pi Load Test    :done, p5, after p4, 2d
```

## ✅ สถานะเฟส

| เฟส | งาน | สถานะ |
|---|---|---|
| **1. Scaffolding** | สร้างไดเรกทอรี (`ops/raw/`, `ops/fabric/patterns/`, `doc/playbooks/`) · `.gitignore` · ADR 0013 | ✅ Done (2026-09-04) |
| **2. Fabric Tools** | ติดตั้ง Fabric CLI (winget 1.4.470) & ออกแบบ 3 Patterns (`snc-trace-summary` / `snc-wiki-distill` / `snc-playbook-draft`) | ✅ Done (2026-09-04) |
| **3. Raw Traces** | เขียนสคริปต์ Export Traces (`ops/export_traces.py`, Non-PHI whitelist) → `ops/raw/` | ✅ Done (2026-09-04) |
| **4. WikiSkill Loop** | Nightly Batch (`ops/nightly-kb-loop.sh` + Fabric 3 patterns) + Human Review Flow (drafts → PR → approve → merge) | ✅ Done (2026-09-04) |
| **5. Verification** | ✅ Done (2026-09-04) — Live E2E บน Pi: loop จริง (111 events/51 breach) · backend `/health` healthy · dashboard 200 · services active · cron 02:30 · พบ/แก้ bug: LLM นับ traces ผิด → เพิ่ม `--stats` deterministic เป็นตัวเลขหลัก |

## 📌 ข้อค้นพบจาก Phase 5 (สำคัญ)

1. **LLM นับสถิติจาก traces ดิบผิดพลาด** (รายงาน 24–34 breach จากจริง 51) → แก้โดยให้
   `ops/export_traces.py --stats` คำนวณสถิติ **deterministic ด้วยเครื่อง** แล้วป้อนเป็น
   ส่วนนำของ input — pattern ถูกสั่งให้ใช้ตัวเลขนั้นเป็นหลัก (ผลลัพธ์หลังแก้: ตรงกับจริง 100%)
2. **Fabric + key แบบ `sk-or-` (OpenRouter)**: ต้องใช้ vendor `OpenRouter` (env
   `OPENROUTER_API_KEY`) และ **unset `GEMINI_API_KEY`** ไม่งั้น fabric จะลองเรียก
   Gemini vendor ก่อนแล้ว error 400 หลุดมาปน stdout
3. Timing: export 111 records < 1s · fabric ~12s/call · loop เต็ม ~38s — เหมาะกับ nightly

## 🔗 เอกสารอ้างอิง

- [[0013-antigravity-fabric-wikiskill-loop|ADR 0013]] — การตัดสินใจเชิงสถาปัตยกรรม
- `ops/raw/README.md` — กฎ Non-PHI / นโยบาย gitignore ของ trace dump
- `ops/fabric/patterns/README.md` — การติดตั้ง Fabric CLI + มาตรฐาน/การใช้งาน Patterns (Phase 2)
- `doc/playbooks/README.md` — กระบวนการ Human Approval ก่อนเข้า playbooks