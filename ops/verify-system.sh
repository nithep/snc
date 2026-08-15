#!/usr/bin/env bash
# ============================================================================
# verify-system.sh — ตรวจสอบความพร้อมระบบ SNC (โครงสร้าง 5-Core) ฉบับมาตรฐาน
# ----------------------------------------------------------------------------
# วิธีใช้:
#   ./ops/verify-system.sh                    # รันบนเครื่อง Pi โดยตรง
#   ssh pi4 'bash -s' < ops/verify-system.sh  # รันจากเครื่อง dev ผ่าน ssh
#
# ตั้งค่า (ค่าเริ่มต้น = SNC บน Pi4):
#   SNC_ROOT=/path/to/root   ./ops/verify-system.sh   # root ของโปรเจกต์
#   CORE_DIRS="api app ..."  ./ops/verify-system.sh   # ปรับรายการ 5-Core
#   SERVICES="a.service b"   ./ops/verify-system.sh   # ปรับรายการ services
#
# อ้างอิง: doc/BLUEPRINT_5CORE.md — โครงสร้าง 5-Core + Vault 5-C
# ============================================================================
set -uo pipefail

ROOT="${SNC_ROOT:-/home/ecs-agent/snc-poc}"
read -r -a CORE_DIRS <<< "${CORE_DIRS:-api app pbx ops doc}"
read -r -a SERVICES <<< "${SERVICES:-snc-backend.service snc-pbx-listener.service}"
OLD_DIRS=(${OLD_DIRS:-backend pbx-connector})
PROXY_PORT="${PROXY_PORT:-2323}"
PBX_HOST="${PBX_HOST:-192.168.1.91}"
PBX_PORT="${PBX_PORT:-23}"
HEALTH_URL="${HEALTH_URL:-http://localhost:8000/health}"

PASS=0; FAIL=0; SKIP=0
ok()    { echo "  [PASS] $1"; PASS=$((PASS+1)); }
bad()   { echo "  [FAIL] $1"; FAIL=$((FAIL+1)); }
skip()  { echo "  [SKIP] $1"; SKIP=$((SKIP+1)); }
warn()  { echo "  [WARN] $1"; }

echo "═══════════ SNC System Verification ═══════════"
echo "Root : $ROOT"
echo "Date : $(date '+%Y-%m-%d %H:%M:%S')"
echo

# ── [1] 5-Core layout ─────────────────────────────────────────────────────
echo "[1] โครงสร้าง 5-Core"
for d in "${CORE_DIRS[@]}"; do
  [ -d "$ROOT/$d" ] && ok "dir: $d/" || bad "dir: $d/ ไม่มี!"
done

# ── [2] ไม่มี directory เก่า ───────────────────────────────────────────────
echo "[2] Directory เก่า (ควรไม่มี)"
found=0
for d in "${OLD_DIRS[@]}"; do
  [ -d "$ROOT/$d" ] && { bad "dir เก่ายังอยู่: $d/"; found=1; }
done
[ "$found" -eq 0 ] && ok "ไม่มี dir เก่า: ${OLD_DIRS[*]}"

# ── [3] cron → ops/ ────────────────────────────────────────────────────────
echo "[3] cron (ต้องชี้ไป \$ROOT/ops/)"
if command -v crontab >/dev/null 2>&1; then
  CRON_BAD=$(crontab -l 2>/dev/null | grep -F "$ROOT" | grep -vF "/ops/" | grep -vE '^\s*#')
  if [ -n "$CRON_BAD" ]; then
    bad "cron มี path ไม่อยู่ใน ops/:"
    echo "$CRON_BAD" | sed 's/^/      /'
  else
    ok "cron ทั้งหมดชี้ไปที่ \$ROOT/ops/"
  fi
else
  skip "ไม่มี crontab (ไม่ใช่ systemd host?)"
fi

# ── [4] Services ───────────────────────────────────────────────────────────
echo "[4] Services"
for s in "${SERVICES[@]}"; do
  if systemctl is-active --quiet "$s" 2>/dev/null; then
    ok "service: $s (active)"
  else
    bad "service: $s ไม่ active"
  fi
done

# ── [5] Health ─────────────────────────────────────────────────────────────
echo "[5] Health endpoint"
HEALTH=$(curl -s --max-time 5 "$HEALTH_URL" 2>/dev/null || true)
if echo "$HEALTH" | grep -qE '"status"[^,}]*"(OK|healthy)"'; then
  ok "/health OK"
else
  bad "/health ผิดปกติ: ${HEALTH:-ไม่มี response}"
fi

# ── [6] Secrets (.env) ─────────────────────────────────────────────────────
echo "[6] Secrets (.env — key ตรงกัน + perms 600)"
if [ -f "$ROOT/api/.env" ] && [ -f "$ROOT/pbx/.env" ]; then
  K1=$(grep '^SNC_API_KEY=' "$ROOT/api/.env" 2>/dev/null | cut -d= -f2)
  K2=$(grep '^SNC_API_KEY=' "$ROOT/pbx/.env" 2>/dev/null | cut -d= -f2)
  if [ -n "$K1" ] && [ "$K1" = "$K2" ]; then
    ok "SNC_API_KEY ตรงกัน (api/.env == pbx/.env, len ${#K1})"
  else
    bad "SNC_API_KEY ไม่ตรงกันหรือว่าง (api.len=${#K1} pbx.len=${#K2})"
  fi
  P1=$(stat -c '%a' "$ROOT/api/.env" 2>/dev/null || echo '?')
  P2=$(stat -c '%a' "$ROOT/pbx/.env" 2>/dev/null || echo '?')
  [ "$P1" = "600" ] && ok "api/.env perms 600" || bad "api/.env perms $P1 (ควร 600)"
  [ "$P2" = "600" ] && ok "pbx/.env perms 600" || bad "pbx/.env perms $P2 (ควร 600)"
else
  skip "ไม่มี api/.env หรือ pbx/.env (โปรเจกต์นี้อาจไม่ใช้ key)"
fi

# ── [7] TCP Proxy ──────────────────────────────────────────────────────────
echo "[7] TCP Proxy (:$PROXY_PORT)"
if ss -tln 2>/dev/null | grep -q ":$PROXY_PORT "; then
  ok "proxy :$PROXY_PORT ฟังอยู่"
else
  bad "proxy :$PROXY_PORT ไม่ทำงาน"
fi

# ── [8] PBX connection ─────────────────────────────────────────────────────
echo "[8] PBX connection ($PBX_HOST:$PBX_PORT)"
if ss -tn 2>/dev/null | grep -q "$PBX_HOST:$PBX_PORT"; then
  ok "เชื่อม PBX อยู่"
else
  warn "ยังไม่เห็น TCP $PBX_HOST:$PBX_PORT (ตู้อาจปิด/ไม่มีสายค้าง — ดูเพิ่มเติม)"
fi

# ── [9] Git sync ───────────────────────────────────────────────────────────
echo "[9] Git HEAD vs upstream"
if [ -d "$ROOT/.git" ]; then
  LOCAL=$(git -C "$ROOT" rev-parse HEAD 2>/dev/null)
  REMOTE=$(git -C "$ROOT" rev-parse origin/main 2>/dev/null || echo '')
  if [ -n "$REMOTE" ]; then
    if [ "$LOCAL" = "$REMOTE" ]; then
      ok "git HEAD == origin/main ($(git -C "$ROOT" log --oneline -1 | cut -c1-50))"
    else
      bad "git HEAD ต่างจาก origin/main (local: $(git -C "$ROOT" log --oneline -1 | cut -c1-40))"
    fi
  else
    skip "ไม่มี origin/main ref"
  fi
else
  skip "ไม่มี .git"
fi

# ── สรุป ───────────────────────────────────────────────────────────────────
echo
echo "═══════════ สรุป: PASS=$PASS FAIL=$FAIL SKIP=$SKIP ═══════════"
if [ "$FAIL" -eq 0 ]; then
  echo "✅ ระบบพร้อมใช้งาน"
  exit 0
else
  echo "❌ พบ $FAIL จุดที่ต้องแก้ไข"
  exit 1
fi
