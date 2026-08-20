#!/bin/bash
# SNC OpenCode Tunnel — Self-Heal Script
# ตรวจสอบว่า Cloudflare Tunnel "snc-opencode" มี connections อยู่หรือไม่
# ถ้า 0 connections (ตาย / Invalid tunnel secret หลังไฟดับ) จะต่ออายุ secret ใหม่และ restart service
# ติดตั้งผ่าน cron ของ user ecs-agent (ดูท้ายสคริปต์)

set -u

TUNNEL_NAME="snc-opencode"
TUNNEL_ID="72cb8359-9a5e-437a-b88d-abfac71ae292"
CRED="/home/ecs-agent/.cloudflared/${TUNNEL_ID}.json"
LOG_DIR="/home/ecs-agent/snc/logs"
LOG="${LOG_DIR}/tunnel-self-heal.log"

mkdir -p "$LOG_DIR"

ts() { date '+%Y-%m-%d %H:%M:%S'; }
log() { echo "$(ts) [self-heal] $*" >> "$LOG"; }

log "เช็ค tunnel $TUNNEL_NAME"

LINE=$(cloudflared tunnel list 2>/dev/null | awk -v t="$TUNNEL_NAME" '$2==t')

if echo "$LINE" | grep -qE '[1-9][0-9]*x'; then
  log "ปกติ (มี connections อยู่แล้ว) -> จบ"
  exit 0
fi

log "พบ 0 connections -> ต่ออายุ secret ใหม่"

TOK=$(cloudflared tunnel token "$TUNNEL_NAME" 2>/dev/null)
if [ -z "$TOK" ]; then
  log "ไม่สามารถออก token ได้ (เช็ค cert.pem / สิทธิ์) -> ออก"
  exit 1
fi

python3 - "$TOK" "$CRED" <<'PY'
import json, base64, sys, os
tok, cred = sys.argv[1], sys.argv[2]
pad = tok + '=' * (-len(tok) % 4)
d = json.loads(base64.urlsafe_b64decode(pad))
creds = {'AccountTag': d.get('a'), 'TunnelID': d.get('t'), 'TunnelSecret': d.get('s')}
with open(cred, 'w') as f:
    json.dump(creds, f)
os.chmod(cred, 0o600)
PY

log "เขียน credentials ใหม่แล้ว -> restart snc-cloudflared"

sudo systemctl restart snc-cloudflared.service
sleep 10

LINE2=$(cloudflared tunnel list 2>/dev/null | awk -v t="$TUNNEL_NAME" '$2==t')
if echo "$LINE2" | grep -qE '[1-9][0-9]*x'; then
  log "ฟื้นสำเร็จ (มี connections แล้ว)"
else
  log "ฟื้นไม่สำเร็จ (ยัง 0 connections) -> ต้องตรวจสอบเพิ่ม"
fi

# --- วิธีติดตั้ง (รันครั้งเดียวบน Pi4) ---
# 1) วางไฟล์นี้ที่ /home/ecs-agent/snc/ops/tunnel-self-heal.sh แล้ว chmod +x
# 2) ให้ ecs-agent restart tunnel ได้โดยไม่ต้องใส่รหัส:
#    echo 'ecs-agent ALL=(root) NOPASSWD: /bin/systemctl restart snc-cloudflared.service' | sudo tee /etc/sudoers.d/snc-tunnel
# 3) ตั้ง cron (crontab -e ของ ecs-agent) ตรวจทุก 15 นาที:
#    */15 * * * * /home/ecs-agent/snc/ops/tunnel-self-heal.sh
