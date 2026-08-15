#!/usr/bin/env bash
# post-burnin-finalize.sh — one-shot post-burn-in finalize (SAFE, non-destructive)
# Runs via cron at burn-in completion (15 Aug 03:05). Generates burn-in report,
# DB backup, KPI snapshot and stale-open-event report, then removes its own cron entry.
set -uo pipefail

SNC_ROOT="$(cd "$(dirname "$0")" && pwd)"
STAMP="$(date +%Y%m%d_%H%M%S)"
OUT="${SNC_ROOT}/post_burnin_report_${STAMP}.txt"
exec > "${OUT}" 2>&1

echo "=== SNC Post-Burn-in Finalize @ $(date) ==="

echo
echo "### 1) Burn-in summary (burnin-monitor.sh --report)"
if [ -x "${SNC_ROOT}/burnin-monitor.sh" ]; then
  "${SNC_ROOT}/burnin-monitor.sh" --report || echo "(report command returned non-zero)"
else
  echo "burnin-monitor.sh not found"
fi

echo
echo "### 2) DB backup (safe, WAL-aware)"
if [ -x "${SNC_ROOT}/backup-snc-db.sh" ]; then
  "${SNC_ROOT}/backup-snc-db.sh" --pi || echo "(backup returned non-zero)"
else
  echo "backup-snc-db.sh not found"
fi

echo
echo "### 3) KPI snapshot"
curl -s -m 10 http://localhost:8000/api/analytics/kpi || echo "KPI endpoint unreachable"

echo
echo "### 4) Stale open events (active/acknowledged — need review/cleanup)"
curl -s -m 10 http://localhost:8000/api/events | python3 -c '
import sys, json
try:
    d = json.load(sys.stdin)
except Exception as e:
    print("parse error:", e); sys.exit(0)
evs = [e for e in d.get("events", []) if e.get("status") in ("active", "acknowledged")]
print(f"open events: {len(evs)}")
for e in evs:
    print(f"  {e[\"room_id\"]}  {e[\"event_type\"]:24} {e[\"status\"]:12} {e[\"timestamp\"][:16]}")
'

echo
echo "### 5) Remove this one-shot cron entry"
crontab -l 2>/dev/null | grep -v 'post-burnin-finalize' | crontab - || true
echo "cron self-removed"

echo
echo "### 6) Telegram alert (burn-in complete)"
TG_MSG="🎉 SNC Burn-in ครบ 48 ชม. ✅ (15 ส.ค. 03:03)"$'\n'"📄 รายงาน: ${OUT}"$'\n'"🔍 ตรวจผล: ssh pi4 'cat ${OUT}'"
"${SNC_ROOT}/notify-telegram.sh" "${TG_MSG}" || true

echo
echo "=== Finalize complete. Report saved: ${OUT} ==="
