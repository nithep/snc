#!/usr/bin/env bash
# ============================================================================
# verify-system.sh — ตรวจสอบความพร้อมระบบตาม Blueprint 5-Core (หลายโปรเจกต์)
# ----------------------------------------------------------------------------
# วิธีใช้:
#   ./ops/verify-system.sh                  # โปรเจกต์ default (SNC บน Pi4)
#   ./ops/verify-system.sh --all            # ทุกโปรเจกต์ใน ops/verify-projects.conf
#   ./ops/verify-system.sh <ชื่อโปรเจกต์>    # เฉพาะโปรเจกต์นั้น (จาก conf)
#   ssh pi4 'cd <root> && bash -s' < ops/verify-system.sh
#
# โปรเจกต์หลายตัว: แก้ไข ops/verify-projects.conf (หนึ่งบรรทัดต่อโปรเจกต์)
# ถ้าไม่มี conf → ใช้ค่า default (SNC) ซึ่ง override ได้ผ่าน env:
#   SNC_ROOT / CORE_DIRS / SERVICES / OLD_DIRS / PROXY_PORT / PBX_HOST ...
#
# อ้างอิง: doc/BLUEPRINT_5CORE.md — โครงสร้าง 5-Core + Vault 5-C
# ============================================================================
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CONF="${VERIFY_CONF:-$SCRIPT_DIR/verify-projects.conf}"

# ── ค่า default (SNC บน Pi4) ──────────────────────────────────────────────
D_NAME="snc"
D_ROOT="/home/ecs-agent/snc-poc"
D_CORE="api app pbx ops doc"
D_SERVICES="snc-backend.service snc-pbx-listener.service"
D_HEALTH="http://localhost:8000/health"
D_OLD="backend pbx-connector"
D_KEYFILES="api/.env pbx/.env"
D_KEYNAME="SNC_API_KEY"
D_PROXY="2323"
D_PBXHOST="192.168.1.91"
D_PBXPORT="23"
D_BRANCH="main"
D_CLOUD=""

# PASS/FAIL/SKIP = รวมทุกโปรเจกต์, P*/F*/S* = เฉพาะโปรเจกต์ปัจจุบัน
PASS=0; FAIL=0; SKIP=0
PP=0; PF=0; PS=0
ok()   { echo "  [PASS] $1"; PASS=$((PASS+1)); PP=$((PP+1)); }
bad()  { echo "  [FAIL] $1"; FAIL=$((FAIL+1)); PF=$((PF+1)); }
skip() { echo "  [SKIP] $1"; SKIP=$((SKIP+1)); PS=$((PS+1)); }
warn() { echo "  [WARN] $1"; }

# ── ตรวจ 1 โปรเจกต์ ───────────────────────────────────────────────────────
# args: name root core_dirs services health old_dirs key_files key_name
#       proxy_port pbx_host pbx_port git_branch
run_checks() {
  local name="$1" root="$2" core_s="$3" services_s="$4" health="$5" \
        old_s="$6" keyfiles_s="$7" keyname="${8:-SNC_API_KEY}" \
        proxy="${9:-}" pbxhost="${10:-}" pbxport="${11:-23}" branch="${12:-main}" \
        cloud_url="${13:-}"
  local -a CORE_DIRS SERVICES OLD_DIRS KEYFILES
  read -r -a CORE_DIRS <<< "$core_s"
  read -r -a SERVICES <<< "$services_s"
  read -r -a OLD_DIRS <<< "$old_s"
  read -r -a KEYFILES <<< "$keyfiles_s"

  echo "═══════════ [$name] System Verification ═══════════"
  echo "Root : $root"
  echo "Date : $(date '+%Y-%m-%d %H:%M:%S')"
  echo

  # ── [1] 5-Core layout ───────────────────────────────────────────────────
  echo "[1] โครงสร้าง 5-Core"
  if [ "${#CORE_DIRS[@]}" -gt 0 ]; then
    for d in "${CORE_DIRS[@]}"; do
      [ -d "$root/$d" ] && ok "dir: $d/" || bad "dir: $d/ ไม่มี!"
    done
  else
    skip "ไม่ได้ตั้ง CORE_DIRS — ข้ามตรวจ layout"
  fi

  # ── [2] ไม่มี directory เก่า ─────────────────────────────────────────────
  if [ "${#OLD_DIRS[@]}" -gt 0 ]; then
    echo "[2] Directory เก่า (ควรไม่มี)"
    found=0
    for d in "${OLD_DIRS[@]}"; do
      [ -d "$root/$d" ] && { bad "dir เก่ายังอยู่: $d/"; found=1; }
    done
    [ "$found" -eq 0 ] && ok "ไม่มี dir เก่า: ${OLD_DIRS[*]}"
  else
    skip "ไม่ได้ตั้ง OLD_DIRS — ข้ามตรวจ dir เก่า"
  fi

  # ── [3] cron → ops/ ──────────────────────────────────────────────────────
  echo "[3] cron (ต้องชี้ไป \$root/ops/)"
  if command -v crontab >/dev/null 2>&1; then
    CRON_BAD=$(crontab -l 2>/dev/null | grep -F "$root" | grep -vF "/ops/" | grep -vE '^\s*#')
    if [ -n "$CRON_BAD" ]; then
      bad "cron มี path ไม่อยู่ใน ops/:"
      echo "$CRON_BAD" | sed 's/^/      /'
    else
      ok "cron ทั้งหมดชี้ไปที่ \$root/ops/"
    fi
  else
    skip "ไม่มี crontab (ไม่ใช่ systemd host?)"
  fi

  # ── [4] Services ─────────────────────────────────────────────────────────
  echo "[4] Services"
  if [ "${#SERVICES[@]}" -gt 0 ]; then
    for s in "${SERVICES[@]}"; do
      if systemctl is-active --quiet "$s" 2>/dev/null; then
        ok "service: $s (active)"
      else
        bad "service: $s ไม่ active"
      fi
    done
  else
    skip "ไม่ได้ตั้ง SERVICES — ข้ามตรวจ services"
  fi

  # ── [5] Health ───────────────────────────────────────────────────────────
  if [ -n "$health" ]; then
    echo "[5] Health endpoint"
    HEALTH=$(curl -s --max-time 5 "$health" 2>/dev/null || true)
    if echo "$HEALTH" | grep -qE '"status"[^,}]*"(OK|healthy)"'; then
      ok "/health OK"
    else
      bad "/health ผิดปกติ: ${HEALTH:-ไม่มี response}"
    fi
  else
    skip "ไม่ได้ตั้ง HEALTH_URL — ข้ามตรวจ health"
  fi

  # ── [6] Secrets (.env) ───────────────────────────────────────────────────
  if [ "${#KEYFILES[@]}" -gt 0 ]; then
    echo "[6] Secrets (.env — $keyname ตรงกัน + perms 600)"
    VALS=(); PERMS=()
    for f in "${KEYFILES[@]}"; do
      FULL="$root/$f"
      if [ -f "$FULL" ]; then
        VALS+=("$(grep "^$keyname=" "$FULL" 2>/dev/null | cut -d= -f2)")
        PERMS+=("$(stat -c '%a' "$FULL" 2>/dev/null || echo '?')")
      else
        VALS+=(""); PERMS+=("MISSING")
      fi
    done
    ok_all=1
    for i in "${!KEYFILES[@]}"; do
      v="${VALS[$i]:-}"; p="${PERMS[$i]:-}"
      if [ -z "$v" ]; then
        bad "${KEYFILES[$i]}: ไม่มี $keyname หรือว่าง"; ok_all=0
      elif [ "$p" != "600" ]; then
        bad "${KEYFILES[$i]}: perms $p (ควร 600)"; ok_all=0
      fi
    done
    if [ "$ok_all" -eq 1 ]; then
      same=1
      for i in $(seq 1 $((${#VALS[@]}-1))); do
        [ "${VALS[$i]}" != "${VALS[0]}" ] && same=0
      done
      [ "$same" -eq 1 ] && ok "$keyname ตรงกันทุกไฟล์ (len ${#VALS[0]})" \
                        || bad "$keyname ไม่ตรงกันระหว่างไฟล์ .env"
    fi
  else
    skip "ไม่ได้ตั้ง KEY_FILES — ข้ามตรวจ secrets"
  fi

  # ── [7] TCP Proxy ────────────────────────────────────────────────────────
  if [ -n "$proxy" ]; then
    echo "[7] TCP Proxy (:$proxy)"
    if ss -tln 2>/dev/null | grep -q ":$proxy "; then
      ok "proxy :$proxy ฟังอยู่"
    else
      bad "proxy :$proxy ไม่ทำงาน"
    fi
  else
    skip "ไม่ได้ตั้ง PROXY_PORT — ข้ามตรวจ proxy"
  fi

  # ── [8] External connection (PBX ฯลฯ) ────────────────────────────────────
  if [ -n "$pbxhost" ]; then
    echo "[8] External connection ($pbxhost:$pbxport)"
    if ss -tn 2>/dev/null | grep -q "$pbxhost:$pbxport"; then
      ok "เชื่อม $pbxhost:$pbxport อยู่"
    else
      warn "ยังไม่เห็น TCP $pbxhost:$pbxport (อุปกรณ์อาจปิด — ดูเพิ่มเติม)"
    fi
  else
    skip "ไม่ได้ตั้ง PBX_HOST — ข้ามตรวจ external connection"
  fi

  # ── [9] Git sync ─────────────────────────────────────────────────────────
  echo "[9] Git HEAD vs origin/$branch"
  if [ -d "$root/.git" ]; then
    LOCAL=$(git -C "$root" rev-parse HEAD 2>/dev/null)
    REMOTE=$(git -C "$root" rev-parse "origin/$branch" 2>/dev/null || echo '')
    if [ -n "$REMOTE" ]; then
      if [ "$LOCAL" = "$REMOTE" ]; then
        ok "git HEAD == origin/$branch ($(git -C "$root" log --oneline -1 | cut -c1-50))"
      else
        bad "git HEAD ต่างจาก origin/$branch (local: $(git -C "$root" log --oneline -1 | cut -c1-40))"
      fi
    else
      skip "ไม่มี origin/$branch ref"
    fi
  else
    skip "ไม่มี .git"
  fi

  # ── [10] Cloud Run (optional — health + auth + dashboard) ──────────────
  if [ -n "$cloud_url" ]; then
    echo "[10] Cloud Run ($cloud_url)"
    CH=$(curl -s -o /dev/null -w '%{http_code}' --max-time 20 "$cloud_url/health" 2>/dev/null || true)
    HB=$(curl -s --max-time 20 "$cloud_url/health" 2>/dev/null || true)
    if [ "$CH" = "200" ] && echo "$HB" | grep -qE '"status"[^,}]*"healthy"'; then
      ok "health → 200 healthy"
    else
      bad "health ผิดปกติ (HTTP $CH)"
    fi
    CA=$(curl -s -o /dev/null -w '%{http_code}' --max-time 20 \
      -X POST "$cloud_url/api/events/acknowledge/9999" \
      -H 'Content-Type: application/json' -d '{}' 2>/dev/null || true)
    [ "$CA" = "401" ] && ok "auth: POST ไม่มี key → 401" \
                     || bad "auth: POST ไม่มี key → HTTP $CA (ควร 401)"
    CD=$(curl -s -o /dev/null -w '%{http_code}' --max-time 20 "$cloud_url/" 2>/dev/null || true)
    [ "$CD" = "200" ] && ok "dashboard / → 200" \
                     || bad "dashboard / → HTTP $CD (ควร 200)"
    # persistent DB (Firestore): อ่าน KPI ด้วย key จาก api/.env — พิสูจน์ว่าข้อมูลไม่หาย
    CLOUD_KEY=""
    [ -f "$root/api/.env" ] && CLOUD_KEY=$(grep "^SNC_API_KEY=" "$root/api/.env" 2>/dev/null | head -1 | cut -d= -f2)
    if [ -n "$CLOUD_KEY" ]; then
      CK=$(curl -s -o /dev/null -w '%{http_code}' --max-time 20 -H "X-API-Key: $CLOUD_KEY" "$cloud_url/api/analytics/kpi" 2>/dev/null || true)
      [ "$CK" = "200" ] && ok "persistent DB: KPI → 200" \
                       || bad "persistent DB: KPI → HTTP $CK (ควร 200)"
    else
      skip "ไม่มี SNC_API_KEY ใน api/.env — ข้ามตรวจ KPI"
    fi
  else
    skip "ไม่ได้ตั้ง CLOUD_RUN_URL — ข้ามตรวจ Cloud Run"
  fi

  # ── สรุปเฉพาะโปรเจกต์นี้ ─────────────────────────────────────────────────
  echo
  echo "═══════════ [$name] สรุป: PASS=$PP FAIL=$PF SKIP=$PS ═══════════"
  PP=0; PF=0; PS=0
}

# ═══════════════════════ main ═══════════════════════
MODE="${1:-default}"

# กรณีไม่มี conf → ใช้ default (env override ได้)
if [ ! -f "$CONF" ]; then
  echo "[verify-system] ไม่พบ $CONF — ใช้ค่า default (SNC)" >&2
  run_checks \
    "${SNC_NAME:-$D_NAME}" \
    "${SNC_ROOT:-$D_ROOT}" \
    "${CORE_DIRS:-$D_CORE}" \
    "${SERVICES:-$D_SERVICES}" \
    "${HEALTH_URL:-$D_HEALTH}" \
    "${OLD_DIRS:-$D_OLD}" \
    "${KEY_FILES:-$D_KEYFILES}" \
    "${KEY_NAME:-$D_KEYNAME}" \
    "${PROXY_PORT:-$D_PROXY}" \
    "${PBX_HOST:-$D_PBXHOST}" \
    "${PBX_PORT:-$D_PBXPORT}" \
    "${GIT_BRANCH:-$D_BRANCH}" \
    "${CLOUD_RUN_URL:-$D_CLOUD}"
  echo
  echo "═══════════ รวมทั้งหมด: PASS=$PASS FAIL=$FAIL SKIP=$SKIP ═══════════"
  [ "$FAIL" -eq 0 ] && { echo "✅ ระบบพร้อมใช้งาน"; exit 0; } \
                    || { echo "❌ พบ $FAIL จุดที่ต้องแก้ไข"; exit 1; }
fi

# มี conf → parse ทีละบรรทัด (name|root|core|services|health|old|keyfiles|keyname|proxy|pbxhost|pbxport|branch)
matched=0
while IFS='|' read -r name root core services health old keyfiles keyname proxy pbxhost pbxport branch cloud_url; do
  [ -z "${name:-}" ] && continue
  case "$name" in \#*) continue ;; esac
  core="${core:-$D_CORE}";        services="${services:-$D_SERVICES}"
  health="${health:-$D_HEALTH}";  old="${old:-$D_OLD}"
  keyfiles="${keyfiles:-$D_KEYFILES}"; keyname="${keyname:-$D_KEYNAME}"
  proxy="${proxy:-$D_PROXY}";     pbxhost="${pbxhost:-$D_PBXHOST}"
  pbxport="${pbxport:-$D_PBXPORT}"; branch="${branch:-$D_BRANCH}"
  cloud_url="${cloud_url:-$D_CLOUD}"
  if [ "$MODE" = "--all" ] || [ "$MODE" = "default" ] || [ "$MODE" = "$name" ]; then
    [ "$matched" -gt 0 ] && echo
    run_checks "$name" "$root" "$core" "$services" "$health" "$old" "$keyfiles" "$keyname" "$proxy" "$pbxhost" "$pbxport" "$branch" "$cloud_url"
    matched=$((matched+1))
  fi
done < "$CONF"

if [ "$matched" -eq 0 ]; then
  echo "❌ ไม่พบโปรเจกต์ '$MODE' ใน $CONF" >&2
  echo "   โปรเจกต์ที่มี: $(grep -vE '^\s*(#|$)' "$CONF" | cut -d'|' -f1 | tr '\n' ' ')" >&2
  exit 1
fi

echo
echo "═══════════ รวมทั้งหมด: PASS=$PASS FAIL=$FAIL SKIP=$SKIP ═══════════"
[ "$FAIL" -eq 0 ] && { echo "✅ ระบบพร้อมใช้งาน"; exit 0; } \
                  || { echo "❌ พบ $FAIL จุดที่ต้องแก้ไข"; exit 1; }
