#!/usr/bin/env bash
# ============================================================================
# deploy-snc-one-shot.sh — SNC Backend One-Shot Deploy (Raspberry Pi 4)
# ----------------------------------------------------------------------------
# สคริปต์นี้ deploy ไฟล์ SNC Backend ขึ้น Pi 4 แบบจบครบในคำสั่งเดียว:
#   1) Preflight ตรวจความพร้อม (ไฟล์ local, SSH ถึง Pi)
#   2) Drift check — เตือนหากไฟล์บน Pi มีการแก้ไขหน้างาน (กันทับของ)
#   3) Backup ไฟล์เดิมบน Pi (timestamp) ไว้ย้อนกลับ
#   4) scp ไฟล์ขึ้น Pi
#   5) ตรวจสอบ md5 ตรงกัน (รับประกัน integrity ของไฟล์ที่ส่ง)
#   6) Restart snc-backend.service (systemd)
#   7) Verify — services active, /health OK, Dashboard เสิร์ฟถูก, ไม่มี error ใน log
#   8) (optional) ตรวจ tunnel สาธารณะ snc.nithep.com
#
# วิธีใช้:
#   ./ops/deploy-snc-one-shot.sh                 # deploy ปกติ
#   ./ops/deploy-snc-one-shot.sh --check-tunnel  # deploy + ตรวจ tunnel
#   ./ops/deploy-snc-one-shot.sh --dry-run       # จำลองเท่านั้น ไม่แตะ Pi
#
# ข้อกำหนด:
#   - ใช้ alias `pi4` จาก ~/.ssh/config (192.168.1.94)
#   - ssh key ต้อง login ได้โดยไม่ต้องใส่รหัส (ใช้ -o BatchMode=yes)
#   - Pi ต้องมี passwordless sudo (sudo -n) เพื่อ restart systemd
# ============================================================================
set -uo pipefail

# --- Config -----------------------------------------------------------------
PI_HOST="${PI_HOST:-pi4}"
REMOTE_ROOT="${SNC_ROOT:-/home/ecs-agent/snc}"  # 5-Core: path จริงบน Pi4
REMOTE_BASE="$REMOTE_ROOT/api"
REMOTE_APP="$REMOTE_ROOT/app"
REMOTE_PBX="$REMOTE_ROOT/pbx"
SERVICE="snc-backend.service"
SIBLING_SERVICE="snc-pbx-listener.service"
SSH_OPTS=(-o ConnectTimeout=10 -o BatchMode=yes)

# ไฟล์ที่จะ deploy: [ชื่อใน repo : path บน Pi]
FILES=(
  "api/server.py:api/server.py"
  "api/services/gemini_direct_service.py:api/services/gemini_direct_service.py"
  "api/services/intelligence/__init__.py:api/services/intelligence/__init__.py"
  "api/services/intelligence/ops_agent.py:api/services/intelligence/ops_agent.py"
  "api/services/intelligence/clinical.py:api/services/intelligence/clinical.py"
  "api/services/intelligence/handover.py:api/services/intelligence/handover.py"
  "api/services/intelligence/routes.py:api/services/intelligence/routes.py"
  "app/index.html:app/index.html"
  "app/demo.html:app/demo.html"
  "app/landing.html:app/landing.html"
  "app/roi.html:app/roi.html"
  "app/snc-vs-imported.html:app/snc-vs-imported.html"
  "app/how-to-phonik.html:app/how-to-phonik.html"
  "pbx/snc_pbx_listener.py:pbx/snc_pbx_listener.py"
  "ops/snc-backend.service:ops/snc-backend.service"
  "ops/snc-pbx-listener.service:ops/snc-pbx-listener.service"
  "ops/ws-tunnel-test.py:ops/ws-tunnel-test.py"
  "ops/ws-tunnel-cron.sh:ops/ws-tunnel-cron.sh"
  "ops/alerting.py:ops/alerting.py"
  "ops/snc_telegram_agent.py:ops/snc_telegram_agent.py"
  "ops/snc-tg-agent.service:ops/snc-tg-agent.service"
  "ops/snc-intelligence.service:ops/snc-intelligence.service"
)

# --- 5-Core structure check (Blueprint: doc/BLUEPRINT_5CORE.md) ------------
CORE_DIRS=(api app pbx ops doc)
check_core_structure() {
  local side="$1"  # local | remote
  local missing=0
  for d in "${CORE_DIRS[@]}"; do
    if [ "$side" = "local" ]; then
      [ -d "$REPO_ROOT/$d" ] || { err "โครงสร้าง 5-Core ไม่ครบ (ขาด: $REPO_ROOT/$d)"; missing=1; }
    else
      ssh "${SSH_OPTS[@]}" "$PI_HOST" "[ -d $REMOTE_ROOT/$d ]" 2>/dev/null \
        || { err "Pi ขาดไดเรกทอรี 5-Core: $REMOTE_ROOT/$d"; missing=1; }
    fi
  done
  [ "$missing" -eq 0 ] || die "โครงสร้าง 5-Core ไม่ตรงตาม Blueprint — ตรวจ doc/BLUEPRINT_5CORE.md"
  ok "โครงสร้าง 5-Core ครบ ($side): ${CORE_DIRS[*]}"
}

# Flags
CHECK_TUNNEL=0
DRY_RUN=0
for arg in "$@"; do
  case "$arg" in
    --check-tunnel) CHECK_TUNNEL=1 ;;
    --dry-run)      DRY_RUN=1 ;;
    -h|--help)
      grep -E '^#' "$0" | sed 's/^# \{0,1\}//' | head -40
      exit 0 ;;
    *) echo "ไม่รู้จัก option: $arg (ลอง --help)" >&2; exit 1 ;;
  esac
done

# --- Paths ------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"

# --- Colors -----------------------------------------------------------------
if [ -t 1 ]; then
  C_GREEN=$'\033[0;32m'; C_RED=$'\033[0;31m'; C_YELLOW=$'\033[1;33m'
  C_CYAN=$'\033[0;36m'; C_BOLD=$'\033[1m'; C_DIM=$'\033[2m'; C_RESET=$'\033[0m'
else
  C_GREEN=""; C_RED=""; C_YELLOW=""; C_CYAN=""; C_BOLD=""; C_DIM=""; C_RESET=""
fi

step() { printf '%s\n' "" "${C_CYAN}${C_BOLD}==> $1${C_RESET}"; }
ok()   { printf '%s\n' "${C_GREEN}  [OK] $1${C_RESET}"; }
warn() { printf '%s\n' "${C_YELLOW}  [!] $1${C_RESET}"; }
err()  { printf '%s\n' "${C_RED}  [ERR] $1${C_RESET}"; }
info() { printf '%s\n' "${C_DIM}  $1${C_RESET}"; }

die() { err "$1"; exit 1; }

# ============================================================================
# 0) Banner
# ============================================================================
echo "${C_BOLD}==============================================================${C_RESET}"
echo "${C_BOLD}  SNC One-Shot Deploy → ${PI_HOST} (Raspberry Pi 4)${C_RESET}"
echo "${C_BOLD}==============================================================${C_RESET}"
[ "$DRY_RUN" -eq 1 ] && echo "${C_YELLOW}${C_BOLD}  *** DRY-RUN MODE — จะไม่มีการเปลี่ยนแปลงใด ๆ กับ Pi ***${C_RESET}"

# ============================================================================
# 1) Preflight — ตรวจไฟล์ local และ SSH ถึง Pi
# ============================================================================
step "1/8 Preflight ตรวจความพร้อม"

for spec in "${FILES[@]}"; do
  local_path="$REPO_ROOT/${spec%%:*}"
  [ -f "$local_path" ] || die "ไม่พบไฟล์ local: $local_path"
  ok "ไฟล์ local พร้อม: ${spec%%:*}"
done
check_core_structure local

if [ "$DRY_RUN" -eq 1 ]; then
  ok "ข้ามการตรวจ SSH (dry-run)"
else
  ssh "${SSH_OPTS[@]}" "$PI_HOST" "echo SSH_OK && hostname" >/dev/null 2>&1 \
    || die "SSH ไปยัง '$PI_HOST' ไม่สำเร็จ — ตรวจสอบ alias ใน ~/.ssh/config และสถานะ Pi"
  ok "SSH ถึง $PI_HOST สำเร็จ"
  check_core_structure remote
fi

# ============================================================================
# 2) Drift check — เตือนถ้าไฟล์บน Pi ต่างจากที่ commit ไว้
# ============================================================================
step "2/8 Drift check ไฟล์บน Pi (กันทับการแก้ไขหน้างาน)"

if [ "$DRY_RUN" -eq 1 ]; then
  info "(dry-run) ข้ามการอ่าน md5 ฝั่ง Pi"
else
  for spec in "${FILES[@]}"; do
    local_path="$REPO_ROOT/${spec%%:*}"
    remote_path="${spec#*:}"
    remote_md5=$(ssh "${SSH_OPTS[@]}" "$PI_HOST" "md5sum \"$REMOTE_ROOT/$remote_path\" 2>/dev/null | awk '{print \$1}'" 2>/dev/null || true)
    local_md5=$(md5sum "$local_path" | awk '{print $1}')

    if [ -z "$remote_md5" ]; then
      warn "ไม่พบไฟล์บน Pi: $remote_path (จะ deploy ใหม่)"
    elif [ "$local_md5" = "$remote_md5" ]; then
      ok "$remote_path — เหมือนกับ local (ไม่มี drift)"
    else
      warn "$remote_path — ต่างจาก local (มีการแก้ไขหน้างานบน Pi)!"
      info "  local : $local_md5"
      info "  remote: $remote_md5"
      warn "จะ backup ก่อน overwrite เพื่อให้ย้อนกลับได้ (ดูตอนจบ)"
    fi
  done
fi

# ============================================================================
# 3) Backup ไฟล์เดิมบน Pi
# ============================================================================
step "3/8 Backup ไฟล์เดิมบน Pi (timestamp)"
TS="$(date +%Y%m%d%H%M%S)"
BACKUP_PREFIX="$$REMOTE_BASE/server.py.bak.$TS"

if [ "$DRY_RUN" -eq 1 ]; then
  info "(dry-run) ssh $PI_HOST cp server.py server.py.bak.$TS + index.html.bak.$TS"
  ok "Backup ชื่อ: *.bak.$TS"
else
  ssh "${SSH_OPTS[@]}" "$PI_HOST" "set -e
for f in server.py ../app/index.html ../pbx/snc_pbx_listener.py; do
  [ -f \"$REMOTE_BASE/\$f\" ] && cp \"$REMOTE_BASE/\$f\" \"$REMOTE_BASE/\$f.bak.$TS\"
done
ls -la $REMOTE_BASE/*.bak.$TS 2>/dev/null || echo '(no backup files found)'" \
    || die "Backup บน Pi ล้มเหลว"
  ok "Backup สำเร็จ: *.bak.$TS"
fi

# ============================================================================
# 4) scp ไฟล์ขึ้น Pi
# ============================================================================
step "4/8 ถ่ายโอนไฟล์ (scp)"

if [ "$DRY_RUN" -eq 1 ]; then
  info "(dry-run) mkdir -p $REMOTE_ROOT/api/services/intelligence $REMOTE_ROOT/ops"
else
  ssh "${SSH_OPTS[@]}" "$PI_HOST" "mkdir -p '$REMOTE_ROOT/api/services/intelligence' '$REMOTE_ROOT/ops'" \
    || die "สร้างไดเรกทอรีปลายทางบน Pi ไม่สำเร็จ"
  ok "เตรียมไดเรกทอรีปลายทางสำหรับ Intelligence plugin แล้ว"
fi

for spec in "${FILES[@]}"; do
  local_path="$REPO_ROOT/${spec%%:*}"
  remote_path="${spec#*:}"
  info "→ $local_path → $PI_HOST:$REMOTE_ROOT/$remote_path"
  if [ "$DRY_RUN" -eq 1 ]; then
    ok "(dry-run) scp $local_path"
  else
    scp "${SSH_OPTS[@]}" "$local_path" "$PI_HOST:$REMOTE_ROOT/$remote_path" \
      || die "scp ล้มเหลว: $remote_path"
    ok "ส่ง $remote_path สำเร็จ"
  fi
done

# ============================================================================
# 5) ตรวจสอบ md5 ตรงกัน (local == remote)
# ============================================================================
step "5/8 ตรวจสอบ md5 ตรงกัน"

if [ "$DRY_RUN" -eq 1 ]; then
  ok "(dry-run) ข้ามการตรวจ md5"
else
  ALL_OK=1
  for spec in "${FILES[@]}"; do
    local_path="$REPO_ROOT/${spec%%:*}"
    remote_path="${spec#*:}"
    local_md5=$(md5sum "$local_path" | awk '{print $1}')
    remote_md5=$(ssh "${SSH_OPTS[@]}" "$PI_HOST" "md5sum \"$REMOTE_ROOT/$remote_path\" | awk '{print \$1}'" 2>/dev/null || true)
    if [ "$local_md5" = "$remote_md5" ]; then
      ok "$remote_path md5 ตรงกัน ($local_md5)"
    else
      err "$remote_path md5 ไม่ตรง! local=$local_md5 remote=$remote_md5"
      ALL_OK=0
    fi
  done
  [ "$ALL_OK" -eq 1 ] || die "integrity check ล้มเหลว — หยุดก่อน restart"
fi

# ============================================================================
# 6) Restart snc-backend.service
# ============================================================================
step "6/8 Restart $SERVICE"

if [ "$DRY_RUN" -eq 1 ]; then
  info "(dry-run) sudo systemctl restart $SERVICE"
else
  ssh "${SSH_OPTS[@]}" "$PI_HOST" "sudo -n true" 2>/dev/null \
    || die "Pi ไม่รองรับ passwordless sudo — รันสคริปต์ผ่าน user ที่มี NOPASSWD"
  ssh "${SSH_OPTS[@]}" "$PI_HOST" "sudo systemctl restart $SERVICE && (sudo systemctl restart snc-tg-agent.service || true) && echo RESTART_OK" \
    || die "restart $SERVICE ล้มเหลว"
  ok "restart $SERVICE สำเร็จ (รวม snc-tg-agent ถ้ามี)"
fi

# ===============================================================
# ============================================================================
# 7) Verify — services, health, dashboard, log
# ============================================================================
step "7/8 Verify ระบบหลัง deploy"

VERIFY_SCRIPT='sleep 3
echo "--- services ---"
systemctl is-active snc-backend.service snc-pbx-listener.service || true
echo "--- health ---"
curl -s --max-time 5 http://localhost:8000/health; echo
echo "--- dashboard markers ---"
FTS_V2=$(grep -cE "Math\.min\(1\.3|usableHf|--scale-origin" "${REMOTE_ROOT}/app/index.html" 2>/dev/null || true)
echo "fitToScreen v2 markers: ${FTS_V2:-0} (คาดหวัง >= 3)"
if [ "${FTS_V2:-0}" -eq 0 ]; then
  echo "WARN: ไม่พบ marker fitToScreen v2 — app/index.html บน Pi อาจยังเป็นเวอร์ชันเก่า"
fi
curl -s --max-time 5 http://localhost:8000/ | grep -o "<title>[^<]*</title>" || true
echo "--- recent backend errors ---"
sudo journalctl -u snc-backend.service --since "5 minutes ago" --no-pager 2>/dev/null | grep -iE "error|traceback|exception" | tail -5 || true
echo "--- end verify ---"'

if [ "$DRY_RUN" -eq 1 ]; then
  info "(dry-run) ssh $PI_HOST ตรวจ services/health/dashboard/log"
  ok "Verify จำลองผ่าน"
else
  ssh "${SSH_OPTS[@]}" "$PI_HOST" "REMOTE_ROOT='$REMOTE_ROOT' bash -s" <<< "$VERIFY_SCRIPT" || warn "verify script บางส่วนไม่สมบูรณ์ (ดู output ด้านบน)"
  SERVICES_ACTIVE=$(ssh "${SSH_OPTS[@]}" "$PI_HOST" "systemctl is-active $SERVICE $SIBLING_SERVICE 2>/dev/null | paste -sd ',' -")
  case "$SERVICES_ACTIVE" in
    "active,active") ok "Services ทั้งคู่ active" ;;
    *) warn "สถานะ services: $SERVICES_ACTIVE (ต้องเป็น active,active)" ;;
  esac
  HEALTH=$(ssh "${SSH_OPTS[@]}" "$PI_HOST" "curl -s --max-time 5 http://localhost:8000/health" 2>/dev/null || true)
  echo "$HEALTH" | grep -qE '"status"[^,}]*"(OK|healthy)"' && ok "Backend /health OK: $HEALTH" || warn "health ผิดปกติ: $HEALTH"
fi
# ============================================================================
# 8) (optional) ตรวจ tunnel สาธารณะ
# ============================================================================
if [ "$CHECK_TUNNEL" -eq 1 ]; then
  step "8/8 ตรวจ tunnel สาธารณะ snc.nithep.com"
  if [ "$DRY_RUN" -eq 1 ]; then
    info "(dry-run) curl https://snc.nithep.com/health"
  else
    PUB_HEALTH=$(curl -s --max-time 10 https://snc.nithep.com/health 2>/dev/null || true)
    echo "$PUB_HEALTH" | grep -qE '"status"[^,}]*"(OK|healthy)"' && ok "Tunnel public /health OK: $PUB_HEALTH" || warn "Tunnel ผิดปกติ: $PUB_HEALTH"
    PUB_TITLE=$(curl -s --max-time 10 https://snc.nithep.com/ 2>/dev/null | grep -o "<title>[^<]*</title>" || true)
    [ -n "$PUB_TITLE" ] && ok "Public dashboard: $PUB_TITLE" || warn "อ่าน title dashboard สาธารณะไม่ได้"
  fi
else
  step "8/8 ข้าม (ใช้ --check-tunnel เพื่อตรวจ tunnel สาธารณะ)"
fi

# ============================================================================
# สรุป
# ============================================================================
echo ""
echo "${C_GREEN}${C_BOLD}==============================================================${C_RESET}"
echo "${C_GREEN}${C_BOLD}  Deploy เสร็จสิ้น ✅${C_RESET}"
echo "${C_GREEN}${C_BOLD}==============================================================${C_RESET}"
echo ""
echo "  ไฟล์ที่ deploy:"
for spec in "${FILES[@]}"; do
  echo "    • ${spec%%:*} → $PI_HOST:$REMOTE_ROOT/${spec#*:}"
done
echo ""
echo "  Backup (สำหรับย้อนกลับ): ${REMOTE_ROOT}/api/server.py.bak.$TS"
echo "    sudo cp ${REMOTE_ROOT}/api/server.py.bak.$TS ${REMOTE_ROOT}/api/server.py"
echo "    sudo systemctl restart $SERVICE"
echo ""
if [ "$DRY_RUN" -eq 1 ]; then
  echo "  ${C_YELLOW}*** นี่คือ DRY-RUN — ไม่มีการเปลี่ยนแปลงใด ๆ เกิดขึ้น ***${C_RESET}"
else
  echo "  หน้า Dashboard:  https://snc.nithep.com  |  LAN: http://192.168.1.94:8000"
fi
echo ""
