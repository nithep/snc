#!/usr/bin/env bash
# ============================================================================
# rotate_phase_a.sh — Phase A (Pi4) ของ Telegram token rotation
# ----------------------------------------------------------------------------
# ใช้บนเครื่อง dev ที่มี ssh ถึง Pi4 ได้ (บน LAN เดียวกัน) โดยไม่ต้องตั้ง env
#
# วิธีใช้ (PowerShell/WSL bash):
#   bash ops/rotate_phase_a.sh "<TOKEN จาก @BotFather>"
#
# ทำอะไร:
#   [1/4] ตรวจ/สร้าง ssh key (~/.ssh/id_ed25519)
#   [2/4] ตั้ง alias pi4 ใน ~/.ssh/config + โยน public key ไป Pi4 (ถามรหัส Pi 1 ครั้ง)
#   [3/4] ตรวจ ssh pi4 (key-only, no password)
#   [4/4] รัน ops/rotate_telegram_token.sh --skip-cloud (หมุน token บน Pi4)
#
# อ้างอิง: doc/wiki/SNC_TELEGRAM_ROTATION_GUIDE.md
# ============================================================================
set -euo pipefail

NEW_TOKEN="${1:-${NEW_TELEGRAM_BOT_TOKEN:-}}"
if [ -z "$NEW_TOKEN" ]; then
  echo "[rotate_phase_a] ERROR: missing token (arg1 or NEW_TELEGRAM_BOT_TOKEN)" >&2
  exit 1
fi
if ! printf '%s' "$NEW_TOKEN" | grep -Eq '^[0-9]{8,10}:[A-Za-z0-9_-]{30,}$'; then
  echo "[rotate_phase_a] ERROR: token format invalid" >&2
  exit 1
fi

# หมายเหตุ: รันจาก repo root (D:\snc) เสมอ — script นี้กับ ops/rotate_telegram_token.sh
# อยู่ใต้โฟลเดอร์เดียวกัน (ใช้ relative path ตรง ๆ ไม่ต้อง cd หา root)

echo "[1/4] ensure ssh key"
mkdir -p ~/.ssh
[ -f ~/.ssh/id_ed25519 ] || ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519 -N "" -q

echo "[2/4] verify ssh pi4 (config+key ตั้งไว้โดย ops/pi_key_sync.sh)"
# Pi4 ปิด password auth → ไม่ใช้ ssh-copy-id; ใช้ key ที่ pi_key_sync.sh ตั้งไว้ให้

echo "[3/4] verify ssh pi4"
ssh -o ConnectTimeout=8 pi4 true && echo "pi4 OK"

echo "[4/4] run rotate_telegram_token.sh --skip-cloud"
export NEW_TELEGRAM_BOT_TOKEN="$NEW_TOKEN"
bash ops/rotate_telegram_token.sh --skip-cloud