#!/usr/bin/env bash
# ============================================================================
# alert-recovery-check.sh — cron helper: ส่ง RECOVERY อัตโนมัติเมื่อระบบกลับมาปกติ
# ----------------------------------------------------------------------------
# หน้าที่:
#   1) เรียก /health (default: http://localhost:8000/health — บน Pi)
#   2) ถ้า healthy และมี alert ใน ledger ที่ยังไม่มี RECOVERY ตามหลัง
#      → ส่งข้อความ 💚 RECOVERY อ้างรหัส alert เดิม + ระยะเวลาผิดปกติ
#   3) cron-safe: exit 0 เสมอ, ระบบยังล่ม → ไม่ทำอะไร
#
# ติดตั้ง cron (ตรวจทุก 10 นาที):
#   */10 * * * * /home/ecs-agent/snc/ops/alert-recovery-check.sh >> /home/ecs-agent/snc/logs/recovery-check.log 2>&1
#
# ตรวจนอก cron:
#   ops/alert-recovery-check.sh http://localhost:8000/health
#   ops/alert-recovery-check.sh https://snc.nithep.com/health   # ตรวจผ่าน tunnel
# ============================================================================
set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
HEALTH_URL="${1:-http://localhost:8000/health}"

exec python3 "$SCRIPT_DIR/alerting.py" --recovery-auto --health-url "$HEALTH_URL"
