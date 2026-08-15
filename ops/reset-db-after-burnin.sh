#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# SNC Database Reset Script (Post Burn-in)
# Usage: bash ops/reset-db-after-burnin.sh
# ═══════════════════════════════════════════════════════════════

set -e

DB_PATH="api/nurse_call_events.db"
BACKUP_PATH="api/nurse_call_events_backup_burnin.db"

echo "🛡️  Smart Nurse Call (SNC) - Post Burn-in Database Reset"
echo "---------------------------------------------------------"

if [ ! -f "$DB_PATH" ]; then
    echo "⚠️  Database file not found at $DB_PATH. Nothing to reset."
    exit 0
fi

echo "1️⃣  Creating backup of current database..."
cp "$DB_PATH" "$BACKUP_PATH"
echo "✅  Backup saved to: $BACKUP_PATH"

echo "2️⃣  Clearing event history from 'nurse_call_events' table..."
sqlite3 "$DB_PATH" "DELETE FROM nurse_call_events;"
echo "✅  Event history cleared successfully."

echo "3️⃣  Verifying clean state..."
COUNT=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM nurse_call_events;")
if [ "$COUNT" -eq 0 ]; then
    echo "✅  Database is now clean and ready for production use."
else
    echo "❌  Error: Database still contains $COUNT records."
    exit 1
fi

echo "---------------------------------------------------------"
echo "🚀  Reset complete. The SLA metrics will now start fresh."
