#!/usr/bin/env bash
# ============================================================================
# setup-cloudflared.sh — Install & configure Cloudflare Tunnel on Raspberry Pi 4
# ============================================================================
# ติดตั้ง cloudflared binary + ตั้ง systemd service + inject tunnel token
#
# วิธีใช้:
#   sudo ./ops/setup-cloudflared.sh                    # ติดตั้ง cloudflared + systemd
#   sudo ./ops/setup-cloudflared.sh --token <TOKEN>    # ตั้ง token ด้วย
#   sudo ./ops/setup-cloudflared.sh --status           # ตรวจสอบสถานะ
#   sudo ./ops/setup-cloudflared.sh --uninstall        # ลบ cloudflared ออก
#
# ข้อกำหนด:
#   - รันบน Raspberry Pi OS Bookworm (Debian 12) ARM64
#   - ต้องมีสิทธิ์ root (sudo)
#   - Tunnel ต้องสร้างไว้แล้วบน Cloudflare Zero Trust Dashboard
# ============================================================================
set -euo pipefail

# --- Config ---
ARCH=$(uname -m)
SNC_ROOT="/home/ecs-agent/snc"
CLOUDFLARED_BIN="/usr/local/bin/cloudflared"
ENV_FILE="/etc/snc/cloudflared.env"
SERVICE_NAME="snc-cloudflared"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

ok()   { echo -e "${GREEN}  [OK]${NC} $*"; }
warn() { echo -e "${YELLOW}  [!]${NC} $*"; }
err()  { echo -e "${RED}  [ERR]${NC} $*"; }
die()  { err "$*"; exit 1; }

# --- Parse args ---
ACTION="install"
TUNNEL_TOKEN=""
for arg in "$@"; do
  case "$arg" in
    --token=*)   TUNNEL_TOKEN="${arg#--token=}" ;;
    --token)     shift; TUNNEL_TOKEN="${1:-}" ;;
    --status)    ACTION="status" ;;
    --uninstall) ACTION="uninstall" ;;
    -h|--help)
      head -20 "$0" | grep '^#' | sed 's/^# \{0,1\}//'
      exit 0 ;;
    *) die "Unknown option: $arg" ;;
  esac
done

# --- Banner ---
echo -e "${CYAN}============================================${NC}"
echo -e "${CYAN}🌐 SNC — Cloudflare Tunnel Setup${NC}"
echo -e "${CYAN}   (Pi 4 / Bookworm / ARM64)${NC}"
echo -e "${CYAN}============================================${NC}"
echo ""

# ============================================================================
# UNINSTALL
# ============================================================================
if [ "$ACTION" = "uninstall" ]; then
  echo -e "${YELLOW}Uninstalling cloudflared...${NC}"
  systemctl stop "$SERVICE_NAME" 2>/dev/null || true
  systemctl disable "$SERVICE_NAME" 2>/dev/null || true
  rm -f "$SERVICE_FILE"
  systemctl daemon-reload
  rm -f "$CLOUDFLARED_BIN"
  rm -f "$ENV_FILE"
  ok "cloudflared removed"
  exit 0
fi

# ============================================================================
# STATUS
# ============================================================================
if [ "$ACTION" = "status" ]; then
  echo "=== cloudflared status ==="
  if [ -f "$CLOUDFLARED_BIN" ]; then
    ok "Binary: $CLOUDFLARED_BIN ($($CLOUDFLARED_BIN --version 2>/dev/null | head -1))"
  else
    err "Binary not found: $CLOUDFLARED_BIN"
  fi

  if systemctl is-active --quiet "$SERVICE_NAME" 2>/dev/null; then
    ok "Service: $SERVICE_NAME (active)"
  else
    err "Service: $SERVICE_NAME (inactive)"
  fi

  if [ -f "$ENV_FILE" ]; then
    ok "Env file: $ENV_FILE"
    # Show token presence (not the value)
    if grep -q "CLOUDFLARE_TUNNEL_TOKEN=" "$ENV_FILE"; then
      TOKEN_LEN=$(grep "CLOUDFLARE_TUNNEL_TOKEN=" "$ENV_FILE" | cut -d= -f2 | wc -c)
      ok "Tunnel token: configured (${TOKEN_LEN} chars)"
    else
      warn "Tunnel token: NOT configured in $ENV_FILE"
    fi
  else
    warn "Env file not found: $ENV_FILE"
  fi

  # Check tunnel connectivity
  echo ""
  echo "=== Tunnel connectivity ==="
  if systemctl is-active --quiet "$SERVICE_NAME" 2>/dev/null; then
    HEALTH=$(curl -s --max-time 10 https://snc.nithep.com/health 2>/dev/null || echo "UNREACHABLE")
    echo "$HEALTH" | grep -qE '"status"' && ok "Public health: $HEALTH" || warn "Public health: $HEALTH"
  else
    warn "Cannot check — service not running"
  fi
  exit 0
fi

# ============================================================================
# INSTALL
# ============================================================================

# --- Check root ---
if [ "$EUID" -ne 0 ]; then
  die "ต้องรันด้วย root: sudo ./ops/setup-cloudflared.sh"
fi

# --- Check architecture ---
echo "[1/5] ตรวจสอบสถาปัตยกรรม..."
case "$ARCH" in
  aarch64|arm64)  DL_ARCH="arm64" ;;
  armv7l|armhf)   DL_ARCH="arm" ;;
  x86_64)         DL_ARCH="amd64" ;;
  *)              die "สถาปัตยกรรมไม่รองรับ: $ARCH" ;;
esac
ok "Arch: $ARCH → cloudflared $DL_ARCH"

# --- Download cloudflared ---
echo ""
echo "[2/5] ดาวน์โหลด cloudflared..."
CF_URL="https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-${DL_ARCH}"
curl -fsSL "$CF_URL" -o "$CLOUDFLARED_BIN"
chmod +x "$CLOUDFLARED_BIN"
ok "Installed: $CLOUDFLARED_BIN ($($CLOUDFLARED_BIN --version 2>/dev/null | head -1))"

# --- Create env dir + write token ---
echo ""
echo "[3/5] ตั้งค่า tunnel token..."
mkdir -p /etc/snc
chmod 700 /etc/snc

if [ -n "$TUNNEL_TOKEN" ]; then
  echo "CLOUDFLARE_TUNNEL_TOKEN=$TUNNEL_TOKEN" > "$ENV_FILE"
  chmod 600 "$ENV_FILE"
  ok "Token written to $ENV_FILE (${#TUNNEL_TOKEN} chars)"
else
  if [ -f "$ENV_FILE" ] && grep -q "CLOUDFLARE_TUNNEL_TOKEN=" "$ENV_FILE"; then
    ok "Existing token preserved in $ENV_FILE"
  else
    warn "No token provided — run: sudo ./ops/setup-cloudflared.sh --token <YOUR_TOKEN>"
    warn "Or manually edit: $ENV_FILE"
    # Create placeholder
    echo "# CLOUDFLARE_TUNNEL_TOKEN=" > "$ENV_FILE"
    chmod 600 "$ENV_FILE"
  fi
fi

# --- Install systemd service ---
echo ""
echo "[4/5] ติดตั้ง systemd service..."
REPO_SERVICE="${SNC_ROOT}/ops/snc-cloudflared.service"
if [ -f "$REPO_SERVICE" ]; then
  cp "$REPO_SERVICE" "$SERVICE_FILE"
else
  # Write inline if repo not present yet
  cat > "$SERVICE_FILE" <<'SVCEOF'
[Unit]
Description=Cloudflare Tunnel for SNC (snc.nithep.com)
After=network-online.target snc-backend.service
Wants=network-online.target snc-backend.service

[Service]
Type=simple
User=root
ExecStart=/usr/local/bin/cloudflared tunnel --no-autoupdate run --token ${CLOUDFLARE_TUNNEL_TOKEN}
Restart=always
RestartSec=10
EnvironmentFile=-/etc/snc/cloudflared.env
SyslogIdentifier=snc-cloudflared
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
SVCEOF
fi

systemctl daemon-reload
systemctl enable "$SERVICE_NAME"
ok "Service installed and enabled: $SERVICE_NAME"

# --- Start tunnel ---
echo ""
echo "[5/5] เริ่ม tunnel..."
systemctl restart "$SERVICE_NAME"
sleep 3

if systemctl is-active --quiet "$SERVICE_NAME"; then
  ok "Tunnel started successfully!"
else
  err "Tunnel failed to start — check: journalctl -u $SERVICE_NAME -n 30"
  exit 1
fi

# --- Summary ---
echo ""
echo -e "${CYAN}============================================${NC}"
echo -e "${GREEN}✅ Cloudflare Tunnel Setup Complete!${NC}"
echo -e "${CYAN}============================================${NC}"
echo ""
echo "📋 สถานะ:"
echo "  • Binary:     $CLOUDFLARED_BIN"
echo "  • Service:    systemctl status $SERVICE_NAME"
echo "  • Token file: $ENV_FILE (perms 600)"
echo "  • Logs:       journalctl -u $SERVICE_NAME -f"
echo ""
echo "🔗 Public URL: https://snc.nithep.com"
echo ""
echo "📝 คำสั่งที่มีประโยชน์:"
echo "  sudo systemctl status $SERVICE_NAME"
echo "  sudo journalctl -u $SERVICE_NAME -f"
echo "  sudo $0 --status"
echo "  sudo $0 --uninstall"
echo ""
echo "⚠️  ตรวจสอบว่า Cloudflare Dashboard Ingress Rule ชี้ไป:"
echo "  Service URL: http://localhost:8000"
echo "  (ห้ามใช้ LAN IP เช่น 192.168.1.x — ดู doc/wiki/SNC_CLOUDFLARE_TUNNEL_SUMMARY.md)"
