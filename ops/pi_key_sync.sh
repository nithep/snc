#!/usr/bin/env bash
# ============================================================================
# pi_key_sync.sh — ทำให้ WSL root ssh pi4 ทำงาน
# ----------------------------------------------------------------------------
# สรุป: Pi4 ปิด password auth → ssh-copy-id ใช้ไม่ได้. Windows key id_rsa
#       authenticate ได้จริง (พิสูจน์แล้ว). วิธีนี้จะ:
#       1) คัดลอก id_rsa (ตัวที่ใช้งานได้) เข้า /root/.ssh/id_rsa (chmod 600)
#       2) ตั้ง pi4 alias ให้ชี้ IdentityFile = ~/.ssh/id_rsa
#       3) ยังพยายาม push WSL ed25519.pub เข้า authorized_keys ด้วย (เผื่อใช้ได้)
#       4) verify ssh pi4
#
# วิธีใช้: bash ops/pi_key_sync.sh
# ============================================================================
set -uo pipefail

PI=ecs-agent@192.168.1.94
WINDOWS_SSH="/mnt/c/Users/Nithep/.ssh"
WSL_PUB_KEY="/root/.ssh/id_ed25519.pub"
STAGING=/root/.ssh/pi_key_sync
WORKING=""

# 1) เอา Windows private keys มา staging (chmod 600)
mkdir -p "$STAGING"
rm -f "$STAGING"/*
shopt -s nullglob
for f in "$WINDOWS_SSH"/*; do
  base="$(basename "$f")"
  case "$base" in
    *.pub|known_hosts*|config*|agent*) continue ;;
  esac
  [ -f "$f" ] || continue
  cp "$f" "$STAGING/$base" 2>/dev/null && chmod 600 "$STAGING/$base" 2>/dev/null
done

# 2) หา key ที่ login Pi ได้จริง
for K in "$STAGING"/*; do
  [ -f "$K" ] || continue
  if ssh -i "$K" -o BatchMode=yes -o StrictHostKeyChecking=accept-new -o ConnectTimeout=8 "$PI" true 2>/dev/null; then
    WORKING="$K"
    echo "[found] working key: $(basename "$K")"
    break
  fi
done

if [ -z "$WORKING" ]; then
  echo "[ERROR] ไม่พบ Windows key ที่ login Pi ได้" >&2
  exit 1
fi

# 3) copy key ที่ใช้ได้ไปเป็น ~/.ssh/id_rsa ตัวหลักของ WSL
#    (เพื่อให้ ssh ใช้เป็น default ได้) + push WSL pub key เข้า Pi (dedupe)
cp "$WORKING" /root/.ssh/id_rsa && chmod 600 /root/.ssh/id_rsa
cp "$WORKING.pub" /root/.ssh/id_rsa.pub 2>/dev/null || true

WSL_PUB="$(cat "$WSL_PUB_KEY")"
echo "[push] WSL ed25519.pub -> Pi authorized_keys"
ssh -i "$WORKING" -o BatchMode=yes -o StrictHostKeyChecking=accept-new "$PI" bash -s <<REMOTE
set -e
WSL_PUB='$WSL_PUB'
mkdir -p ~/.ssh && touch ~/.ssh/authorized_keys && chmod 700 ~/.ssh
if grep -qF "\$WSL_PUB" ~/.ssh/authorized_keys; then
  echo "[skip] ed25519 already present"
else
  echo "\$WSL_PUB" >> ~/.ssh/authorized_keys && echo "[added] ed25519 appended"
fi
chmod 600 ~/.ssh/authorized_keys
REMOTE

# 4) ตั้ง pi4 alias ให้ใช้ id_rsa ที่ใช้งานได้ (IdentityFile ชัดเจน)
mkdir -p /root/.ssh
if grep -qs "^Host pi4" /root/.ssh/config 2>/dev/null; then
  # แก้/เพิ่ม IdentityFile ใต้ Host pi4 (ลบบล็อกเดิมแล้วเขียนใหม่ให้ชัด)
  sed -i '/^Host pi4$/,/^[[:space:]]*$/d' /root/.ssh/config 2>/dev/null || true
fi
printf "\nHost pi4\n    HostName 192.168.1.94\n    User ecs-agent\n    IdentityFile /root/.ssh/id_rsa\n" >> /root/.ssh/config
chmod 600 /root/.ssh/config

# 5) verify
echo "[verify] ssh pi4..."
ssh -o BatchMode=yes -o ConnectTimeout=8 pi4 true && echo "[OK] pi4 works via /root/.ssh/id_rsa"