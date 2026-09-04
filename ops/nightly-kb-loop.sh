#!/usr/bin/env bash
# nightly-kb-loop.sh — Nightly Knowledge Loop (ADR 0013 · Phase 4)
#
# ลำดับการทำงาน (ตาม flowchart ใน doc/ROADMAP_ANTIGRAVITY_FABRIC.md):
#
#   ops/raw/ (traces non-PHI) ─► fabric snc-trace-summary ─► รายงานสรุป
#        ─► fabric snc-wiki-distill ─►  draft wiki (DRAFT)
#        ─► fabric snc-playbook-draft ─► draft playbook (DRAFT)
#        ─► ops/fabric/drafts/ + REVIEW.md  (รอ Human Review → PR → merge)
#
# หลักการ (ADR 0013):
#   - ข้อมูลที่ส่งเข้า Fabric = Non-PHI เท่านั้น (export_traces.py ตัด whitelist field)
#   - Draft ถูกเขียนลง ops/fabric/drafts/ (gitignored) — ห้าม commit อัตโนมัติ
#   - มนุษย์ (Head Nurse / System Operator) review + approve ผ่าน PR เท่านั้น
#
# วิธีใช้:
#   ./nightly-kb-loop.sh                  # ข้อมูล 1 วันที่ผ่านมา (ค่าเริ่มต้น)
#   ./nightly-kb-loop.sh --days 2         # ข้อมูล 2 วันที่ผ่านมา
#   ./nightly-kb-loop.sh --dry-run        # ทดสอบเฉพาะขั้น export (ไม่เรียก Fabric)
#
# Env ที่ปรับได้: PYTHON_BIN, FABRIC_VENDOR, FABRIC_MODEL, EXPORT_DAYS, TRACES_RETENTION_DAYS, SNC_ROOT
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SNC_ROOT="${SNC_ROOT:-$(cd "$SCRIPT_DIR/.." && pwd)}"

EXPORT_DAYS="${EXPORT_DAYS:-1}"
# เก็บ trace ไว้กี่วันก่อนลบ (ตามนโยบาย Non-PHI ของ ops/raw/ — ADR 0013)
TRACES_RETENTION_DAYS="${TRACES_RETENTION_DAYS:-14}"
# FABRIC_VENDOR/FABRIC_MODEL default ตั้งใน block เลือก vendor (หลัง load_env)
# — กันการ override ด้วยค่าเริ่มต้นก่อนตรวจจับชนิด key
DRAFTS_DIR="$SNC_ROOT/ops/fabric/drafts"
RAW_DIR="$SNC_ROOT/ops/raw"
LOG_DIR="$SNC_ROOT/logs"
DRY_RUN=0

# ── parse args ────────────────────────────────────────────────────────────────
while [ "$#" -gt 0 ]; do
  case "$1" in
    --days) EXPORT_DAYS="$2"; shift 2 ;;
    --dry-run) DRY_RUN=1; shift ;;
    *) echo "[nightly-kb-loop] ไม่รู้จัก option: $1" >&2; exit 1 ;;
  esac
done

log() { echo "[nightly-kb-loop] $*"; }

# ── เลือก Python อัตโนมัติ (ถ้าไม่ตั้ง PYTHON_BIN) ──────────────────────────────────
# Windows/Git Bash: alias python3 มักเป็น Windows Store stub (rc≠0 เมื่อรันจริง)
# — ทดสอบด้วยการรันจริง ไม่ใช่แค่ command -v กันชน stub
PYTHON_BIN="${PYTHON_BIN:-}"
if [ -z "$PYTHON_BIN" ]; then
  for _cand in python3 python /usr/bin/python3; do
    if command -v "$_cand" >/dev/null 2>&1 && "$_cand" -c 'import sys' >/dev/null 2>&1; then
      PYTHON_BIN="$_cand"
      break
    fi
  done
fi
if [ -z "$PYTHON_BIN" ]; then
  log "ERROR: ไม่พบ Python ที่ใช้งานได้ — ตั้ง PYTHON_BIN เช่น: PYTHON_BIN=python3 $0" >&2
  exit 1
fi

# ── load env (GEMINI_API_KEY จาก api/.env — ไม่ print ค่า key) ───────────────
load_env() {
  local f="$1" k v
  [ -f "$f" ] || return 0
  while IFS='=' read -r k v; do
    [ -z "$k" ] && continue
    case "$k" in \#*) continue ;; esac
    k="${k//[$'\r']/}"; v="${v//[$'\r']/}"
    if [ "$k" = "GEMINI_API_KEY" ] && [ -z "${GEMINI_API_KEY:-}" ]; then
      export GEMINI_API_KEY="$v"
    fi
  done < "$f"
}
load_env "$SNC_ROOT/api/.env"
load_env "$SNC_ROOT/.env"

# ── เลือก vendor/model อัตโนมัติตามชนิด key ──────────────────────────────────
# key แบบ sk-or-* = OpenRouter (backend ใช้ meta-llama/llama-3.3-70b-instruct)
# key แบบอื่น = Google Gemini โดยตรง
if [[ "${GEMINI_API_KEY:-}" == sk-or-* ]]; then
  export OPENROUTER_API_KEY="${OPENROUTER_API_KEY:-$GEMINI_API_KEY}"
  # unset GEMINI_API_KEY — กัน fabric เห็น key แล้วลองเรียก Gemini vendor ก่อน
  # (จะ error 400 หลุดมาปน stdout — ดู bug ที่เจอระหว่าง Phase 5)
  unset GEMINI_API_KEY
  FABRIC_VENDOR="${FABRIC_VENDOR:-OpenRouter}"
  FABRIC_MODEL="${FABRIC_MODEL:-meta-llama/llama-3.3-70b-instruct}"
else
  FABRIC_VENDOR="${FABRIC_VENDOR:-Gemini}"
  FABRIC_MODEL="${FABRIC_MODEL:-gemini-2.0-flash}"
fi
log "AI vendor/model: $FABRIC_VENDOR / $FABRIC_MODEL"

mkdir -p "$DRAFTS_DIR" "$RAW_DIR" "$LOG_DIR"
STAMP="$(date +%Y%m%d-%H%M)"

# ── Step 0: ตรวจ prerequisites ────────────────────────────────────────────────
# cron มี PATH แบบ minimal — ใช้ FABRIC_BIN env หรือหาใน ~/.local/bin ก่อน
FABRIC_BIN="${FABRIC_BIN:-}"
if [ -z "$FABRIC_BIN" ]; then
  if command -v fabric >/dev/null 2>&1; then
    FABRIC_BIN="$(command -v fabric)"
  elif [ -x "$HOME/.local/bin/fabric" ]; then
    FABRIC_BIN="$HOME/.local/bin/fabric"
  fi
fi
if [ -z "$FABRIC_BIN" ]; then
  log "ERROR: ไม่พบคำสั่ง fabric — ติดตั้งก่อน (winget install danielmiessler.Fabric หรือ ARM binary สำหรับ Pi)" >&2
  exit 1
fi
log "fabric: $FABRIC_BIN ($($FABRIC_BIN --version 2>/dev/null | head -1))"
if [ "$DRY_RUN" -eq 0 ] && [ -z "${GEMINI_API_KEY:-}" ] && [ -z "${OPENROUTER_API_KEY:-}" ]; then
  log "ERROR: ไม่พบ GEMINI_API_KEY / OPENROUTER_API_KEY (ตั้งใน api/.env หรือ env)" >&2
  exit 1
fi

# ── Step 1: export traces (Non-PHI) ───────────────────────────────────────────
log "Step 1: export traces (${EXPORT_DAYS} วัน) → $RAW_DIR"
TRACES_FILE="$RAW_DIR/traces-$(date -u +%Y%m%d).jsonl"
EXPORT_OUT="$("$PYTHON_BIN" "$SCRIPT_DIR/export_traces.py" --days "$EXPORT_DAYS" --out-dir "$RAW_DIR" 2>&1)" || EXPORT_RC=$?
EXPORT_RC="${EXPORT_RC:-0}"
echo "$EXPORT_OUT" | tee -a "$LOG_DIR/nightly-kb-loop.log"
if [ "$EXPORT_RC" -eq 2 ]; then
  log "ไม่มี trace ในช่วง ${EXPORT_DAYS} วัน — จบงาน (ไม่เรียก Fabric)"
  exit 0
fi
if [ "$EXPORT_RC" -ne 0 ] || [ ! -s "$TRACES_FILE" ]; then
  log "ERROR: export traces ล้มเหลว (rc=$EXPORT_RC)" >&2
  exit 1
fi
log "traces: $TRACES_FILE"

# ── Step 1b: housekeeping — ลบ traces เก่าตาม retention (Non-PHI hygiene) ─────
# ops/raw/ เก็บ trace dump ชั่วคราว ไม่ใช่ archive — ค่าเริ่มต้นเก็บ 14 วัน
# ปิดได้ด้วย TRACES_RETENTION_DAYS=0 (ห้าม auto-delete)
if [ "$TRACES_RETENTION_DAYS" -gt 0 ] 2>/dev/null; then
  OLD_COUNT=$(find "$RAW_DIR" -name 'traces-*.jsonl' -mtime +"$TRACES_RETENTION_DAYS" 2>/dev/null | wc -l)
  if [ "$OLD_COUNT" -gt 0 ]; then
    find "$RAW_DIR" -name 'traces-*.jsonl' -mtime +"$TRACES_RETENTION_DAYS" -delete
    log "housekeeping: ลบ traces ผ่านการใช้งานเกิน $TRACES_RETENTION_DAYS วันแล้ว $OLD_COUNT ไฟล์"
  fi
fi

if [ "$DRY_RUN" -eq 1 ]; then
  log "DRY-RUN: ข้ามขั้น Fabric (จะรัน snc-trace-summary → snc-wiki-distill → snc-playbook-draft)"
  exit 0
fi

# ── Step 2: fabric snc-trace-summary ──────────────────────────────────────────
log "Step 2: fabric snc-trace-summary (model=$FABRIC_MODEL)"
SUMMARY_FILE="$DRAFTS_DIR/$STAMP-summary.md"
# สถิติ deterministic จากเครื่อง (Python) — Phase 5 พบว่า LLM นับ traces ดิบผิด
STATS_BLOCK="$("$PYTHON_BIN" "$SCRIPT_DIR/export_traces.py" --days "$EXPORT_DAYS" \
    --stats --out-dir "$RAW_DIR" 2>/dev/null)" || true
if ! { echo "# สถิติอ้างอิง (คำนวณโดยเครื่อง — ใช้เป็นหลัก ห้ามนับเอง):"; echo "$STATS_BLOCK"; \
       echo; echo "# traces ดิบ:"; cat "$TRACES_FILE"; } \
    | "$FABRIC_BIN" -V "$FABRIC_VENDOR" -m "$FABRIC_MODEL" \
    -p snc-trace-summary > "$SUMMARY_FILE" 2> "$DRAFTS_DIR/$STAMP-fabric.err"; then
  log "ERROR: fabric snc-trace-summary ล้มเหลว — ดู $DRAFTS_DIR/$STAMP-fabric.err" >&2
  exit 1
fi
[ -s "$SUMMARY_FILE" ] || { log "ERROR: สรุปว่างเปล่า"; exit 1; }
log "summary: $SUMMARY_FILE"

# ── Step 3: fabric snc-wiki-distill ───────────────────────────────────────────
log "Step 3: fabric snc-wiki-distill → draft wiki"
WIKI_FILE="$DRAFTS_DIR/$STAMP-wiki-draft.md"
# ป้อนสถิติอ้างอิง (period) + รายชื่อเอกสาร vault — กัน pattern เดาวันที่/สร้าง wikilink ตาย
# (บทเรียน live run 2026-09-05: wiki draft ใช้หัวข้อปี 2023 เอง + ลิงก์ [[สัญญา SLA]] ที่ไม่มีจริง)
VAULT_INVENTORY="$(ls "$SNC_ROOT/doc/wiki/" "$SNC_ROOT/doc/adr/" 2>/dev/null | grep '\.md$' | sort -u)"
if ! { echo "# สถิติอ้างอิง (คำนวณโดยเครื่อง — ใช้เป็นหลัก ห้ามนับเอง):"; echo "$STATS_BLOCK"; \
       echo; echo "# เอกสารที่มีอยู่จริงใน vault (wikilink ได้เฉพาะชื่อในรายการนี้):"; echo "$VAULT_INVENTORY"; \
       echo; echo "# รายงานสรุป (input หลัก):"; cat "$SUMMARY_FILE"; } \
    | "$FABRIC_BIN" -V "$FABRIC_VENDOR" -m "$FABRIC_MODEL" \
    -p snc-wiki-distill > "$WIKI_FILE" 2>> "$DRAFTS_DIR/$STAMP-fabric.err"; then
  log "WARN: fabric snc-wiki-distill ล้มเหลว — ข้าม (ดู $DRAFTS_DIR/$STAMP-fabric.err)" >&2
  WIKI_FILE=""
else
  [ -s "$WIKI_FILE" ] || WIKI_FILE=""
  [ -n "$WIKI_FILE" ] && log "wiki draft: $WIKI_FILE"
fi

# ── Step 4: fabric snc-playbook-draft ─────────────────────────────────────────
log "Step 4: fabric snc-playbook-draft → draft playbook"
PLAYBOOK_FILE="$DRAFTS_DIR/$STAMP-playbook-draft.md"
if ! cat "$SUMMARY_FILE" | "$FABRIC_BIN" -V "$FABRIC_VENDOR" -m "$FABRIC_MODEL" \
    -p snc-playbook-draft > "$PLAYBOOK_FILE" 2>> "$DRAFTS_DIR/$STAMP-fabric.err"; then
  log "WARN: fabric snc-playbook-draft ล้มเหลว — ข้าม (ดู $DRAFTS_DIR/$STAMP-fabric.err)" >&2
  PLAYBOOK_FILE=""
else
  [ -s "$PLAYBOOK_FILE" ] || PLAYBOOK_FILE=""
  [ -n "$PLAYBOOK_FILE" ] && log "playbook draft: $PLAYBOOK_FILE"
fi

# ── Step 5: Human Review checklist ────────────────────────────────────────────
REVIEW_FILE="$DRAFTS_DIR/$STAMP-REVIEW.md"
{
  echo "# 📋 Human Review — Knowledge Loop ${STAMP}"
  echo ""
  echo "> ตาม ADR 0013: artifact ทุกชิ้นต้องผ่าน Human Review & Approve (PR → merge)"
  echo "> ก่อนจะถือเป็นความรู้/playbook ทางการ ห้าม merge แบบอัตโนมัติ"
  echo ""
  echo "## ไฟล์ที่รอ review"
  echo ""
  echo "- **Summary:** \`${SUMMARY_FILE##*/}\` (ข้อมูลต้นทาง)"
  [ -n "$WIKI_FILE" ] && echo "- **Wiki draft:** \`${WIKI_FILE##*/}\` → review แล้ว copy ไป \`doc/wiki/\`"
  [ -n "$PLAYBOOK_FILE" ] && echo "- **Playbook draft:** \`${PLAYBOOK_FILE##*/}\` → review แล้ว copy ไป \`doc/playbooks/\`"
  echo ""
  echo "## วิธีอนุมัติ (Manual — ยังไม่ automation)"
  echo ""
  echo '1. อ่าน draft ใน `ops/fabric/drafts/` — ตรวจความถูกต้องกับข้อมูลจริง (ตัวเลข SLA ต้องตรง)'
  echo '2. ถ้าผ่าน: ย้ายไฟล์ไป `doc/wiki/` (หรือ `doc/playbooks/`) แล้วตั้งชื่อตาม convention'
  echo '3. commit + PR — ทีม review อีกครั้ง แล้ว merge (ไฟล์ใน doc/playbooks/ = ทางการหลัง merge เท่านั้น)'
  echo '4. ถ้าไม่ผ่าน: แก้ pattern ใน `ops/fabric/patterns/` หรือทิ้ง draft นี้ (drafts/ เป็น gitignored)'
  echo ""
  echo "*สร้างโดย nightly-kb-loop.sh — ${STAMP}*"
} > "$REVIEW_FILE"
log "review checklist: $REVIEW_FILE"

# ── Step 6: แจ้งเตือน (optional — ถ้าตั้ง TELEGRAM ไว้) ────────────────────────
if [ -x "$SCRIPT_DIR/notify-telegram.sh" ]; then
  "$SCRIPT_DIR/notify-telegram.sh" \
    "🔄 Nightly KB Loop ${STAMP}: summary + drafts พร้อม review แล้ว (ดู ops/fabric/drafts/)" \
    || true
fi

log "เสร็จสิ้น ✅ — ไฟล์ทั้งหมดใน $DRAFTS_DIR"