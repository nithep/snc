#!/bin/bash
# =============================================================================
# setup_pi.sh — Pi First-Run Setup for Smart Nurse Call (SNC)
# รองรับ: Raspberry Pi OS Bookworm (Debian 12), Python 3.11+
# รันครั้งเดียวก่อน quick_start.sh
# =============================================================================
set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}============================================${NC}"
echo -e "${CYAN}🏥 SNC — Raspberry Pi Setup Script${NC}"
echo -e "${CYAN}   (Bookworm / Python 3.11+ Compatible)${NC}"
echo -e "${CYAN}============================================${NC}"
echo ""

# ── 1. ตรวจสอบ Python 3 ──────────────────────────────────────────────────────
echo -e "${YELLOW}[1/4] ตรวจสอบ Python 3...${NC}"
if ! command -v python3 &>/dev/null; then
    echo -e "${RED}❌ Python 3 ไม่พบ — รัน: sudo apt install python3 python3-pip${NC}"
    exit 1
fi
PY_VER=$(python3 --version)
ARCH=$(uname -m)
echo -e "${GREEN}   ✅ $PY_VER | Arch: $ARCH${NC}"

# ── 2. ตรวจสอบ pip และ flag ที่ต้องใช้ ────────────────────────────────────────
echo ""
echo -e "${YELLOW}[2/4] ตรวจสอบ pip environment...${NC}"

# Detect Debian 12 / Raspberry Pi OS Bookworm (PEP 668 — externally managed)
PIP_FLAGS=""
if pip3 install --dry-run pip 2>&1 | grep -q "externally-managed"; then
    echo -e "${YELLOW}   ⚠️  Detected externally-managed environment (Bookworm/Debian 12)${NC}"
    echo -e "${YELLOW}   ℹ️  Using --break-system-packages flag${NC}"
    PIP_FLAGS="--break-system-packages"
fi

pip3 install --upgrade pip $PIP_FLAGS 2>/dev/null || true
echo -e "${GREEN}   ✅ pip พร้อมใช้งาน${NC}"

# ── 3. ติดตั้ง Backend Dependencies ──────────────────────────────────────────
echo ""
echo -e "${YELLOW}[3/4] ติดตั้ง Backend dependencies (pydantic v1 — no Rust required)...${NC}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

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

# ── 4. ติดตั้ง PBX Connector Dependencies ────────────────────────────────────
echo ""
echo -e "${YELLOW}[4/4] ติดตั้ง PBX Connector dependencies...${NC}"
pip3 install $PIP_FLAGS "aiohttp>=3.9.0"
echo -e "${GREEN}   ✅ PBX Connector dependencies ติดตั้งครบ${NC}"

# ── ยืนยันผล ──────────────────────────────────────────────────────────────────
echo ""
echo -e "${YELLOW}🔍 ยืนยัน packages ที่ติดตั้ง:${NC}"
python3 -c "
import fastapi, pydantic, uvicorn, aiohttp, websockets
print(f'   ✅ fastapi     = {fastapi.__version__}')
print(f'   ✅ pydantic    = {pydantic.VERSION}')
print(f'   ✅ uvicorn     = {uvicorn.__version__}')
print(f'   ✅ aiohttp     = {aiohttp.__version__}')
print(f'   ✅ websockets  = {websockets.__version__}')
"

# ── สรุปผล ────────────────────────────────────────────────────────────────────
echo ""
echo -e "${CYAN}============================================${NC}"
echo -e "${GREEN}🎉 Setup เสร็จสมบูรณ์!${NC}"
echo -e "${CYAN}============================================${NC}"
echo ""
echo "📋 ขั้นตอนถัดไป:"
echo "   cd ~/snc-poc && ./quick_start.sh"
echo ""
echo "🔗 Health Check (หลังรัน quick_start.sh):"
echo "   curl http://localhost:8000/health"
