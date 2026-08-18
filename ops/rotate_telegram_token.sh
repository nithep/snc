#!/usr/bin/env bash
# ============================================================================
# rotate_telegram_token.sh — Rotate TELEGRAM_BOT_TOKEN แบบกึ่งอัตโนมัติ
# ----------------------------------------------------------------------------
# วิธีใช้:
#
#   export NEW_TELEGRAM_BOT_TOKEN="<token ใหม่จาก @BotFather>"
#   bash ops/rotate_telegram_token.sh
#
#   # หรือส่ง token เป็น argument แรก:
#   bash ops/rotate_telegram_token.sh "<token ใหม่>"
#
# ทำอะไร (ทั้งหมดที่ทำได้ในเครื่องที่รัน — auto-detect):
#   [Pi4]   backup + อัปเดต TELEGRAM_BOT_TOKEN ใน api/.env → chmod 600
#           → restart snc-tg-agent → ทดสอบส่งจริงผ่าน notify-telegram.sh
#   [Cloud] เพิ่ม secret version ใหม่ snc-telegram-bot-token → redeploy bridge
#           (re-resolve secret :latest — จำเป็น เพราะ revision เดิม pin version เก่า)
#           → ทดสอบ webhook → Telegram (ต้องได้ {"status":"sent"})
#
# ⚠️ ความจริง 2 สภาพแวดล้อม (สำคัญ):
#   - `ssh pi4` ใช้ได้จากเครื่องบน LAN (เครื่อง dev) เท่านั้น — Cloud Shell เข้าถึง Pi ไม่ได้
#   - `gcloud` ใช้ได้จาก Cloud Shell เท่านั้น — เครื่อง dev ไม่มี gcloud auth
#   → รันสคริปต์นี้ 2 ครั้งใน 2 ที่:
#       1) บนเครื่อง dev: อัปเดต Pi4 (ข้าม Cloud อัตโนมัติ เพราะไม่มี gcloud)
#       2) ใน Cloud Shell: อัปเดต Secret Manager + redeploy bridge (ข้าม Pi)
#   ถ้าเครื่องใดมีทั้ง ssh + gcloud → ทำครบในคำสั่งเดียว
#
# Options:
#   --skip-pi     ข้ามขั้นตอน Pi4
#   --skip-cloud  ข้ามขั้นตอน Cloud (Secret Manager + bridge)
#
# อ้างอิง: doc/wiki/SNC_TELEGRAM_ROTATION_GUIDE.md, doc/wiki/SNC_TELEGRAM_ALERTS.md
# ============================================================================
set -euo pipefail

# hotel-ecs-nithep = GCP Project ID จริง (คงไว้เป็น legacy id ตาม ADR 0007 / NOMENCLATURE)
PROJECT_ID="${GCP_PROJECT_ID:-hotel-ecs-nithep}"
# live path บน Pi4 (MIGRATION_RUNBOOK: ย้ายไป nithep/snc ไม่เคยเกิดขึ้นจริง — production คือ snc-poc)
SNC_ROOT="${SNC_ROOT:-/home/ecs-agent/snc-poc}"
CHAT_ID="${TELEGRAM_CHAT_ID:-7346817215}"

BRIDGE="snc-alert-bridge"
REGION="asia-southeast1"
BRIDGE_URL="https://snc-alert-bridge-59781590359.asia-southeast1.run.app"
SECRET_BOT="snc-telegram-bot-token"
SECRET_MONITOR="snc-monitor-webhook-token"

NEW_TOKEN="${NEW_TELEGRAM_BOT_TOKEN:-}"
if [ -z "$NEW_TOKEN" ] && [ "$#" -gt 0 ] && [[ "${1}" != --* ]]; then
  NEW_TOKEN="$1"
fi

SKIP_PI=0
SKIP_CLOUD=0
for a in "$@"; do
  case "$a" in
    --skip-pi) SKIP_PI=1 ;;
    --skip-cloud) SKIP_CLOUD=1 ;;
  esac
done

echo "═══════════ SNC Telegram Token Rotation ═══════════"

# ── validate token (กัน placeholder/base64/ของสั้น ตาม bug ที่เคยเจอ len 7) ──
if [ -z "$NEW_TOKEN" ]; then
  echo "❌ ยังไม่ได้ระบุ token ใหม่ — ใช้ NEW_TELEGRAM_BOT_TOKEN env หรือ argument แรก" >&2
  echo "   (revoke + สร้างใหม่ที่ @BotFather → /mybots → @snc2569_bot → API Token)" >&2
  exit 1
fi
if ! printf '%s' "$NEW_TOKEN" | grep -Eq '^[0-9]{8,10}:[A-Za-z0-9_-]{30,}$'; then
  echo "❌ token ใหม่มีรูปแบบไม่ถูกต้อง (ควรเป็น 1234567890:AAH... len ~46) — ตรวจใหม่" >&2
  exit 1
fi
echo "✅ token ใหม่: ${NEW_TOKEN:0:10}... (len ${#NEW_TOKEN}) — ไม่ log เต็ม"

# ── ตรวจความสามารถของเครื่องนี้ (auto-detect) ────────────────────────────────
HAS_SSH=0
if ssh -o ConnectTimeout=8 -o BatchMode=yes pi4 true >/dev/null 2>&1; then HAS_SSH=1; fi
HAS_GCLOUD=0
if command -v gcloud >/dev/null 2>&1; then HAS_GCLOUD=1; fi
echo "   capability: ssh_pi4=$HAS_SSH gcloud=$HAS_GCLOUD"
echo ""

# ════════════════════════════════════════════════════════════════════════════
# Phase A — Pi4: อัปเดต api/.env + restart tg-agent + ทดสอบ
# ════════════════════════════════════════════════════════════════════════════
if [ "$SKIP_PI" = "1" ] || [ "$HAS_SSH" != "1" ]; then
  echo "[Pi4] SKIP — $( [ "$SKIP_PI" = "1" ] && echo '--skip-pi' || echo 'ssh pi4 เข้าไม่ถึง (เครื่องนี้ไม่ได้อยู่บน LAN?)' )"
else
  echo "[Pi4] อัปเดต TELEGRAM_BOT_TOKEN ใน $SNC_ROOT/api/.env..."
  ssh -o ConnectTimeout=8 pi4 "SNC_ROOT='$SNC_ROOT' NEW_TOKEN='$NEW_TOKEN' bash -s" <<'REMOTE'
set -euo pipefail
ENV="${SNC_ROOT}/api/.env"
mkdir -p "${SNC_ROOT}/backups"
if [ -f "$ENV" ]; then
  TS="$(date +%Y%m%d%H%M%S)"
  cp "$ENV" "${SNC_ROOT}/backups/api.env.${TS}"
  echo "  💾 backup: ${SNC_ROOT}/backups/api.env.${TS}"
fi
if grep -q '^TELEGRAM_BOT_TOKEN=' "$ENV"; then
  sed -i "s|^TELEGRAM_BOT_TOKEN=.*|TELEGRAM_BOT_TOKEN=${NEW_TOKEN}|" "$ENV"
else
  echo "TELEGRAM_BOT_TOKEN=${NEW_TOKEN}" >> "$ENV"
fi
chmod 600 "$ENV"
printf '  ✅ api/.env: '
grep '^TELEGRAM_BOT_TOKEN' "$ENV" | sed 's/=\(.\{10\}\).*/=\1.../'
REMOTE

  echo "[Pi4] restart snc-tg-agent (อ่าน token จาก api/.env)..."
  ssh -o ConnectTimeout=8 pi4 "sudo systemctl restart snc-tg-agent && sleep 2 && systemctl is-active snc-tg-agent" \
    || echo "  ⚠️ restart snc-tg-agent ล้มเหลว/ไม่ active — ตรวจ sudo systemctl status snc-tg-agent"

  echo "[Pi4] ทดสอบส่งจริง (notify-telegram.sh)..."
  ssh -o ConnectTimeout=8 pi4 "\"${SNC_ROOT}/ops/notify-telegram.sh\" '🔔 หมุน Telegram token เสร็จ (Pi4) — ระบบ SNC'" || true
fi
echo ""

# ════════════════════════════════════════════════════════════════════════════
# Phase B — Cloud: Secret Manager + redeploy bridge (re-resolve :latest)
# ════════════════════════════════════════════════════════════════════════════
if [ "$SKIP_CLOUD" = "1" ] || [ "$HAS_GCLOUD" != "1" ]; then
  echo "[Cloud] SKIP — $( [ "$SKIP_CLOUD" = "1" ] && echo '--skip-cloud' || echo 'ไม่พบ gcloud (รันใน Cloud Shell)' )"
else
  gcloud config set project "$PROJECT_ID" >/dev/null

  echo "[Cloud] เพิ่ม secret version ใหม่: $SECRET_BOT ..."
  TMP_TOKEN="$(mktemp)"
  printf '%s' "$NEW_TOKEN" > "$TMP_TOKEN"
  if gcloud secrets describe "$SECRET_BOT" --project "$PROJECT_ID" >/dev/null 2>&1; then
    gcloud secrets versions add "$SECRET_BOT" --data-file="$TMP_TOKEN" --project "$PROJECT_ID" >/dev/null
  else
    gcloud secrets create "$SECRET_BOT" --data-file="$TMP_TOKEN" --project "$PROJECT_ID" >/dev/null
  fi
  rm -f "$TMP_TOKEN"
  echo "  ✅ secret อัปเดต (version ใหม่พร้อมใช้)"

  echo "[Cloud] redeploy bridge เพื่อ re-resolve secret :latest..."
  IMAGE="$(gcloud run services describe "$BRIDGE" --region "$REGION" --project "$PROJECT_ID" \
    --format='value(spec.template.spec.containers[0].image)')"
  if [ -z "$IMAGE" ]; then
    echo "  ❌ ไม่พบ image ปัจจุบันของ $BRIDGE — bridge อาจยังไม่เคย deploy" >&2
    echo "     ใช้: NEW_TELEGRAM_BOT_TOKEN=\"$NEW_TOKEN\" bash ops/deploy_bridge_cloudshell.sh" >&2
    exit 1
  fi
  echo "  image: $IMAGE"
  gcloud run deploy "$BRIDGE" \
    --image "$IMAGE" \
    --region "$REGION" \
    --project "$PROJECT_ID" \
    --allow-unauthenticated \
    --set-secrets "TELEGRAM_BOT_TOKEN=$SECRET_BOT:latest,MONITOR_WEBHOOK_TOKEN=$SECRET_MONITOR:latest" \
    --set-env-vars "TELEGRAM_CHAT_ID=$CHAT_ID"

  echo "[Cloud] ทดสอบ webhook bridge → Telegram..."
  sleep 10
  MONITOR_WEBHOOK_TOKEN="$(gcloud secrets versions access latest \
    --secret="$SECRET_MONITOR" --project "$PROJECT_ID" 2>/dev/null || true)"
  T=$(curl -s --max-time 20 -X POST "$BRIDGE_URL/webhook?token=$MONITOR_WEBHOOK_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"incident":{"state":"OPEN","summary":"หมุน Telegram token เสร็จ (bridge) — จาก rotate_telegram_token.sh","condition_name":"test"}}')
  echo "  webhook → $T"
  echo "$T" | grep -q '"sent"' && echo "  ✅ bridge → Telegram ส่งสำเร็จ" \
    || echo "  ⚠️ bridge รับได้แต่ส่งไม่ได้ — ตรวจ secret + log: gcloud logging read"
fi
echo ""

# ── สรุป checklist ──────────────────────────────────────────────────────────
echo "═══════════ สรุป rotation ═══════════"
[ "$SKIP_PI" = "0" ] && [ "$HAS_SSH" = "1" ] \
  && echo "  ✅ Pi4: api/.env + snc-tg-agent + notify ทดสอบแล้ว" \
  || echo "  ⏳ Pi4: ยังไม่ได้ทำ — รันบนเครื่องที่ ssh pi4 ได้"
[ "$SKIP_CLOUD" = "0" ] && [ "$HAS_GCLOUD" = "1" ] \
  && echo "  ✅ Cloud: secret + bridge redeploy + webhook sent" \
  || echo "  ⏳ Cloud: ยังไม่ได้ทำ — รันใน Cloud Shell (NEW_TELEGRAM_BOT_TOKEN เดิม)"
echo ""
echo "⚠️ เตือน: อย่าลืม Revoke token เก่าที่ @BotFather แล้ว (ถ้ายังไม่ทำ) — token เก่าจะไร้ค่าทันที"
