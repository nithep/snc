# ops/fabric/patterns/ — Fabric Patterns (SNC Knowledge Loop)

> ตามสถาปัตยกรรม ADR 0013 — จุดเก็บ **Fabric Patterns** ใช้กลั่นความรู้จาก Trace Dump
> (Non-PHI) เป็น Wiki / Playbooks โดย **Antigravity Orchestrator** ใน Nightly Batch

## สถานะ

✅ **Phase 2 เสร็จสิ้น (2026-09-04)** — ติดตั้ง Fabric CLI + ออกแบบ 3 Patterns แล้ว
ดู roadmap: `doc/ROADMAP_ANTIGRAVITY_FABRIC.md`

## 📦 การติดตั้ง Fabric CLI (Windows — ผ่าน Winget)

```powershell
winget install danielmiessler.Fabric
```

- เวอร์ชันที่ใช้: **1.4.470** (Go-based CLI — `fabric --version`)
- ทางเลือกอื่น: PowerShell one-liner installer, Scoop (`scoop install fabric-ai`), หรือ `go install` — ดู README ของ danielmiessler/fabric
- บน **Raspberry Pi (Linux ARM)**: ใช้ binary release `linux_arm64` จาก GitHub Releases (fabric v1.4.303+ รองรับ ARM)

## 🔌 การชี้ Fabric ไปยัง patterns ของโปรเจกต์

Fabric อ่าน custom patterns จาก env `CUSTOM_PATTERNS_DIRECTORY` ซึ่งตั้งค่าได้ใน
`~/.config/fabric/.env` (ไฟล์ env ของ fabric เอง):

```
CUSTOM_PATTERNS_DIRECTORY=D:/snc/ops/fabric/patterns
```

- รองรับ `~/...` expansion
- Pattern แต่ละตัว = **โฟลเดอร์ + `system.md`** (ไม่มี YAML ใน Go version นี้):

```
ops/fabric/patterns/
├── README.md
├── snc-trace-summary/system.md      # RAW → รายงานสรุป (สถิติ SLA, จุดคอขวด)
├── snc-wiki-distill/system.md       # สรุป → บทความ Wiki (OKF: กระชับ + wikilink)
└── snc-playbook-draft/system.md     # ข้อค้นพบ → ร่าง SOP/Action Guide (DRAFT)
```

## 🚀 การใช้งาน

```bash
# 1) รายงานสรุปจาก traces (non-PHI)
cat ops/raw/traces-20260903.jsonl | fabric -V Gemini -m gemini-2.0-flash -p snc-trace-summary

# 2) กลั่นเป็น Wiki note (ขั้นที่ 2 — ผลลัพธ์ DRAFT รอ human review)
fabric -V Gemini -m gemini-2.0-flash -p snc-wiki-distill < summary.md

# 3) ร่าง Playbook (ขั้นสุดท้าย — DRAFT รอ PR approval ตาม ADR 0013)
fabric -V Gemini -m gemini-2.0-flash -p snc-playbook-draft < findings.md

# ตรวจ prompt ที่จะส่ง (ไม่ต้องใช้ API key)
cat sample.jsonl | fabric --dry-run -p snc-trace-summary
```

### ข้อกำหนดรันจริง (live run)

- ต้องมี `GEMINI_API_KEY` (fabric ใช้ env นี้สำหรับ vendor `Gemini` — ตรงกับโปรเจกต์)
- ตัวอย่าง: `set -a; . api/.env; set +a` (หรือตั้งใน `~/.config/fabric/.env`)
- ตรวจ vendor/model: `fabric --listvendors` / `fabric --listmodels`
- กำหนด model ต่อ pattern ได้ด้วย `FABRIC_MODEL_<PATTERN_NAME>=vendor|model`
- ⚠️ เครื่อง dev นี้มี key placeholder ใน `api/.env` — live run ทำบน Pi (key จริง) หรือใส่ key จริง

## 📄 ไฟล์ตัวอย่าง

- `../samples/sample-traces-20260903.jsonl` — traces สังเคราะห์ Non-PHI สำหรับทดสอบ pattern (dry-run / smoke test)
- `../samples/sample-traces-live-20260904.jsonl` — ตัวอย่าง traces จริง (Non-PHI whitelist) จาก DB บน Pi 2026-08-24 → 08-30 (8 rows: breach + non-breach, CALL_BEDSIDE + CALL_BATHROOM_EMERGENCY, source real/demo) — อ้างอิงการทำงานจริง ใช้แทน synthetic ได้

## Conventions

- ตั้งชื่อโฟลเดอร์ pattern: `kebab-case` (เช่น `snc-trace-summary`)
- ภาษา: คำสั่งใน pattern ภาษาไทยทางการ (ตาม AGENTS.md) — output เป็นภาษาไทย
- ทุก pattern ระบุ: purpose / input format / output sections / กฎ (ห้าม fabricate, Non-PHI, DRAFT note)
- ห้าม commit traces จริงลง repo — เก็บเฉพาะใน `ops/raw/` (gitignored) และตัวอย่างสังเคราะห์