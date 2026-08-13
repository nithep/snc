# -*- coding: utf-8 -*-
"""Script to check if SMDR events are in the database."""
import sqlite3
import json
import sys
from datetime import datetime

# Windows console ใช้ cp874/cp1252 ลง emoji ไม่ได้ -> บังคับ UTF-8
if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

DB_PATH = "nurse_call_events.db"

def check_events():
    print("=" * 80)
    print("Checking Nurse Call Events Database")
    print("=" * 80)
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Get total count
        cursor.execute("SELECT COUNT(*) FROM nurse_call_events")
        total = cursor.fetchone()[0]
        print(f"\n📊 Total events in database: {total}\n")
        
        # Get recent events for room 400
        print("🔍 Recent events for Room 400:")
        print("-" * 80)
        cursor.execute("""
            SELECT id, room_id, event_type, status, timestamp, 
                   ack_time_seconds, resolution_time_seconds, sla_breached
            FROM nurse_call_events 
            WHERE room_id = '0400'
            ORDER BY timestamp DESC 
            LIMIT 10
        """)
        
        rows = cursor.fetchall()
        if not rows:
            print("❌ No events found for Room 400")
            print("\n💡 This means either:")
            print("   1. PBX listener is not sending events to backend")
            print("   2. Events are being sent but failing to save")
            print("   3. Backend is not receiving the events")
        else:
            for i, row in enumerate(rows, 1):
                print(f"\nEvent {i}:")
                print(f"  ID: {row[0]}")
                print(f"  Room: {row[1]}")
                print(f"  Type: {row[2]}")
                print(f"  Status: {row[3]}")
                print(f"  Timestamp: {row[4]}")
                if row[5]:
                    print(f"  Ack Time: {row[5]}s")
                if row[6]:
                    print(f"  Resolution Time: {row[6]}s")
                print(f"  SLA Breached: {'YES' if row[7] else 'NO'}")
        
        # Check for duplicate IDs
        print("\n" + "=" * 80)
        print("🔎 Checking for duplicate event IDs:")
        print("-" * 80)
        cursor.execute("""
            SELECT id, COUNT(*) as count
            FROM nurse_call_events
            GROUP BY id
            HAVING count > 1
        """)
        
        duplicates = cursor.fetchall()
        if duplicates:
            print(f"⚠️  Found {len(duplicates)} duplicate ID(s):")
            for dup in duplicates:
                print(f"  - {dup[0]} (appears {dup[1]} times)")
        else:
            print("✅ No duplicate IDs found")
        
        # Show all events by type
        print("\n" + "=" * 80)
        print("📈 Events by type:")
        print("-" * 80)
        cursor.execute("""
            SELECT event_type, COUNT(*) as count
            FROM nurse_call_events
            GROUP BY event_type
            ORDER BY count DESC
        """)
        
        for row in cursor.fetchall():
            print(f"  {row[0]}: {row[1]}")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_events()
