#!/usr/bin/env bash
# lean-snc-data.sh — clean up stale synthetic events so KPI reflects real calls.
# DESTRUCTIVE on the event DB — always backs up first and requires --confirm.
#
# Usage:
#   ./lean-snc-data.sh                          # dry-run: report only, change nothing
#   ./lean-snc-data.sh --confirm                # delete stale OPEN events (older than 24h, never resolved)
#   ./lean-snc-data.sh --confirm --purge-legacy # also delete ALL legacy CALL_TRIGGERED rows (pre-sourceEventType-fix)
set -uo pipefail

SNC_ROOT="$(cd "$(dirname "$0")" && pwd)"
DB=""
for candidate in "${SNC_ROOT}/backend/nurse_call_events.db" "${SNC_ROOT}/api/nurse_call_events.db"; do
  [ -f "$candidate" ] && DB="$candidate" && break
done
[ -z "$DB" ] && { echo "event DB not found"; exit 1; }

CONFIRM=0
PURGE_LEGACY=0
for arg in "$@"; do
  [ "$arg" = "--confirm" ] && CONFIRM=1
  [ "$arg" = "--purge-legacy" ] && PURGE_LEGACY=1
done

echo "DB: $DB"

python3 - "$DB" "$CONFIRM" "$PURGE_LEGACY" <<'PY'
import sys, sqlite3
db, confirm, purge_legacy = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
conn = sqlite3.connect(db)
conn.row_factory = sqlite3.Row
c = conn.cursor()

c.execute("""SELECT room_id, event_type, status, substr(timestamp,1,16) AS ts
             FROM nurse_call_events WHERE status IN ('active','acknowledged')
             ORDER BY timestamp""")
print("=== open (active/acknowledged) events ===")
for r in c.fetchall():
    print(f"  {r['room_id']}  {r['event_type']:24} {r['status']:12} {r['ts']}")

c.execute("""SELECT event_type, status, COUNT(*) AS n FROM nurse_call_events
             GROUP BY event_type, status ORDER BY event_type, status""")
print("\n=== events by type/status ===")
for r in c.fetchall():
    print(f"  {r['event_type']:24} {r['status']:12} {r['n']}")

c.execute("""SELECT room_id, event_type, status, substr(timestamp,1,16) AS ts
             FROM nurse_call_events
             WHERE status IN ('active','acknowledged') AND timestamp < datetime('now','-1 day')
             ORDER BY timestamp""")
del_open = c.fetchall()
print(f"\n=== open rows that would be deleted (older than 24h): {len(del_open)} ===")
for r in del_open:
    print(f"  {r['room_id']}  {r['event_type']:24} {r['status']:12} {r['ts']}")

c.execute("""SELECT room_id, event_type, status, substr(timestamp,1,16) AS ts
             FROM nurse_call_events WHERE event_type = 'CALL_TRIGGERED'
             ORDER BY timestamp""")
legacy = c.fetchall()
print(f"\n=== legacy CALL_TRIGGERED rows (--purge-legacy would delete): {len(legacy)} ===")
for r in legacy:
    print(f"  {r['room_id']}  {r['status']:12} {r['ts']}")

conn.close()
if not confirm:
    print("\nDRY-RUN — nothing changed. Re-run with --confirm to apply.")
PY

# กัน dry-run หลุดไปลบข้อมูล: python ข้างบนอ่านอย่างเดียวเสมอ ต้อง --confirm ถึงจะไปต่อ
if [ "$CONFIRM" = "0" ]; then
  exit 0
fi

echo
echo "--- backing up DB first ---"
if [ -x "${SNC_ROOT}/backup-snc-db.sh" ]; then
  "${SNC_ROOT}/backup-snc-db.sh" --pi || echo "(backup returned non-zero)"
else
  cp "$DB" "${DB}.lean-backup.$(date +%Y%m%d%H%M%S)"
  echo "copied ${DB} to a timestamped backup"
fi

echo
echo "--- deleting stale open events (older than 24h) ---"
python3 - "$DB" <<'PY'
import sys, sqlite3
conn = sqlite3.connect(sys.argv[1])
c = conn.cursor()
c.execute("""DELETE FROM nurse_call_events
             WHERE status IN ('active','acknowledged') AND timestamp < datetime('now','-1 day')""")
print(f"deleted {c.rowcount} open row(s)")
conn.commit()
conn.close()
PY

if [ "$PURGE_LEGACY" = "1" ]; then
  echo
  echo "--- deleting legacy CALL_TRIGGERED rows ---"
  python3 - "$DB" <<'PY'
import sys, sqlite3
conn = sqlite3.connect(sys.argv[1])
c = conn.cursor()
c.execute("DELETE FROM nurse_call_events WHERE event_type = 'CALL_TRIGGERED'")
print(f"deleted {c.rowcount} legacy row(s)")
conn.commit()
conn.close()
PY
fi

echo
echo "=== KPI after cleanup ==="
curl -s -m 10 http://localhost:8000/api/analytics/kpi || echo "KPI endpoint unreachable"
echo
echo "=== done ==="
