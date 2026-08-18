#!/bin/bash
# =============================================================================
# setup_pi.sh — Pi First-Run Setup for Smart Nurse Call (SNC)
# รองรับ: Raspberry Pi OS Bookworm (Debian 12), Python 3.11+, ARM64
# รันครั้งเดียวก่อน quick_start.sh หรือ systemd enable
# =============================================================================
set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}============================================${NC}"
echo -e "${CYAN}🏥 SNC — Raspberry Pi 4 Setup Script${NC}"
echo -e "${CYAN}   (5-Core / Bookworm / Python 3.11+)${NC}"
echo -e "${CYAN}============================================${NC}"
echo ""

# --- Config ---
SNC_ROOT="/home/ecs-agent/snc"
SNC_USER="ecs-agent"

# ── 0. ตรวจสอบ root ───────────────────────────────────────────────────────
echo -e "${YELLOW}[0/6] ตรวจสอบสิทธิ์...${NC}"
if [ "$EUID" -ne 0 ]; then
  echo -e "${RED}❌ ต้องรันด้วย root: sudo ./ops/setup_pi.sh${NC}"
  exit 1
fi
echo -e "${GREEN}   ✅ root OK${NC}"

# ── 1. ตรวจสอบ Python 3 ──────────────────────────────────────────────────
echo ""
echo -e "${YELLOW}[1/6] ตรวจสอบ Python 3...${NC}"
if ! command -v python3 &>/dev/null; then
  echo -e "${RED}❌ Python 3 ไม่พบ — รัน: sudo apt install python3 python3-pip${NC}"
  exit 1
fi
PY_VER=$(python3 --version)
ARCH=$(uname -m)
echo -e "${GREEN}   ✅ $PY_VER | Arch: $ARCH${NC}"

# ── 2. ตรวจสอบ pip + ติดตั้ง dependencies ─────────────────────────────────
echo ""
echo -e "${YELLOW}[2/6] ติดตั้ง Python dependencies...${NC}"

# Detect PEP 668 (externally-managed)
PIP_FLAGS=""
if pip3 install --dry-run pip 2>&1 | grep -q "externally-managed"; then
  echo -e "${YELLOW}   ⚠️  Bookworm externally-managed → using --break-system-packages${NC}"
  PIP_FLAGS="--break-system-packages"
fi

pip3 install --upgrade pip $PIP_FLAGS 2>/dev/null || true

echo -e "${CYAN}   📦 Backend (FastAPI + uvicorn + SQLite)...${NC}"
pip3 install $PIP_FLAGS \
    "fastapi>=0.95.0,<0.100.0" \
    "uvicorn>=0.24.0" \
    "pydantic>=1.10.0,<2.0.0" \
    "httpx>=0.25.2" \
    "python-multipart>=0.0.6" \
    "aiohttp>=3.9.0" \
    "websockets>=12.0" \
    "requests>=2.31.0"

echo -e "${GREEN}   ✅ Backend dependencies ติดตั้งครบ${NC}"

# ── 3. ติดตั้ง cloudflared ────────────────────────────────────────────────
echo ""
echo -e "${YELLOW}[3/6] ตรวจสอบ cloudflared...${NC}"
CF_BIN="/usr/local/bin/cloudflared"
if [ -f "$CF_BIN" ]; then
  echo -e "${GREEN}   ✅ cloudflared ติดตั้งแล้ว ($($CF_BIN --version 2>/dev/null | head -1))${NC}"
else
  echo -e "${YELLOW}   ⚠️  cloudflared ไม่พบ — ติดตั้งด้วย: sudo ./ops/setup-cloudflared.sh${NC}"
  echo -e "${YELLOW}   (ข้ามขั้นตอนนี้ ติดตั้งภายหลังได้)${NC}"
fi

# ── 4. ตั้งค่า system user ─────────────────────────────────────────────────
echo ""
echo -e "${YELLOW}[4/6] ตรวจสอบ system user...${NC}"
if id "$SNC_USER" &>/dev/null; then
  echo -e "${GREEN}   ✅ User $SNC_USER มีอยู่แล้ว${NC}"
else
  echo -e "${YELLOW}   สร้าง user $SNC_USER...${NC}"
  useradd --create-home --shell /bin/bash "$SNC_USER"
  echo -e "${GREEN}   ✅ User $SNC_USER สร้างแล้ว${NC}"
fi

# ── 5. ตั้งค่าไดเรกทอรี + permissions ────────────────────────────────────
echo ""
echo -e "${YELLOW}[5/6] ตั้งค่าไดเรกทอรี SNC...${NC}"
mkdir -p "$SNC_ROOT"/{api,app,pbx,ops,doc,backups}
chown -R "$SNC_USER:$SNC_USER" "$SNC_ROOT"

# Backup dir perms
chmod 700 "$SNC_ROOT/backups"
echo -e "${GREEN}   ✅ 5-Core directories ready: $SNC_ROOT/{api,app,pbx,ops,doc,backups}${NC}"

# ── 6. ติดตั้ง systemd services ───────────────────────────────────────────
echo ""
echo -e "${YELLOW}[6/6] ติดตั้ง systemd services...${NC}"
REPO_OPS="${SNC_ROOT}/ops"

for SVC in snc-backend snc-pbx-listener snc-tg-agent; do
  SVC_FILE="${REPO_OPS}/${SVC}.service"
  TARGET="/etc/systemd/system/${SVC}.service"
  if [ -f "$SVC_FILE" ]; then
    cp "$SVC_FILE" "$TARGET"
    echo -e "${GREEN}   ✅ ${SVC}.service → $TARGET${NC}"
  else
    echo -e "${YELLOW}   ⚠️  ${SVC}.service ไม่พบใน repo — ข้าม${NC}"
  fi
done

# Cloudflared service
if [ -f "${REPO_OPS}/snc-cloudflared.service" ]; then
  cp "${REPO_OPS}/snc-cloudflared.service" /etc/systemd/system/
  echo -e "${GREEN}   ✅ snc-cloudflared.service → /etc/systemd/system/${NC}"
fi

# Reload + enable
systemctl daemon-reload
for SVC in snc-backend snc-pbx-listener snc-tg-agent; do
  systemctl enable "$SVC" 2>/dev/null && echo -e "${GREEN}   ✅ $SVC enabled${NC}" || true
done
echo -e "${GREEN}   ✅ systemd daemon-reload done${NC}"

# ── ยืนยันผล ──────────────────────────────────────────────────────────────
echo ""
echo -e "${YELLOW}🔍 ยืนยัน packages:${NC}"
python3 -c "
import fastapi, pydantic, uvicorn, aiohttp, websockets
print(f'   ✅ fastapi     = {fastapi.__version__}')
print(f'   ✅ pydantic    = {pydantic.VERSION}')
print(f'   ✅ uvicorn     = {uvicorn.__version__}')
print(f'   ✅ aiohttp     = {aiohttp.__version__}')
print(f'   ✅ websockets  = {websockets.__version__}')
"

# ── สรุปผล ────────────────────────────────────────────────────────────────
echo ""
echo -e "${CYAN}============================================${NC}"
echo -e "${GREEN}🎉 Setup เสร็จสมบูรณ์!${NC}"
echo -e "${CYAN}============================================${NC}"
echo ""
echo "📋 ขั้นตอนถัดไป:"
echo "   1. Copy .env:  cp ops/.env.example api/.env && cp ops/.env.example pbx/.env"
echo "   2. ตั้ง SNC_API_KEY ใน api/.env และ pb/.env ให้ตรงกัน"
echo "   3. ตั้ง Cloudflare Tunnel Token:"
echo "      sudo ./ops/setup-cloudflared.sh --token <YOUR_TOKEN>"
echo "   4. เริ่มระบบ:"
echo "      sudo systemctl start snc-backend snc-pbx-listener"
echo "      sudo systemctl start snc-tg-agent        # optional"
echo "      sudo systemctl start snc-cloudflared      # public tunnel"
echo ""
echo "🔗 Health Check:"
echo "   curl http://localhost:8000/health"
echo ""
echo "📊 Status:"
echo "   sudo systemctl status snc-backend snc-pbx-listener"
echo "   sudo journalctl -u snc-backend -f"
echo ""
echo "🌐 Public (after tunnel setup):"
echo "   https://snc.nithep.com"
