#!/usr/bin/env bash
# ============================================================================
# pi_key_debug.sh — ตรวจว่า WSL root key กับ authorized_keys บน Pi ตรงกันไหม
# ============================================================================
set -uo pipefail
PI=ecs-agent@192.168.1.94
STAGING=/root/.ssh/pi_key_sync
WORKING="$STAGING/id_rsa"

echo "=== [1] WSL key file =="
ls -la /root/.ssh/id_ed25519.pub
echo "WSL_PUB = $(cat /root/.ssh/id_ed25519.pub)"

echo ""
echo "=== [2] ~/.ssh/config pi4 =="
grep -A3 "^Host pi4" /root/.ssh/config 2>/dev/null || echo "(no pi4 alias)"

echo ""
echo "=== [3] Pi authorized_keys (via id_rsa) =="
ssh -i "$WORKING" -o BatchMode=yes -o StrictHostKeyChecking=accept-new "$PI" \
  "ls -la ~/.ssh/ && echo '--- authorized_keys ---' && cat ~/.ssh/authorized_keys 2>/dev/null || echo '(empty/no file)'"

echo ""
echo "=== [4] debug ssh pi4 (show verbose auth methods) ==="
ssh -v -o BatchMode=yes -o ConnectTimeout=8 pi4 true 2>&1 | grep -Ei "Offering|Authentications|denied|Server accepts|key_load|Try private|identity" | head -30 || echo "(none)"