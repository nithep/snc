# -*- coding: utf-8 -*-
"""Test script to debug SMDR parsing issues with actual PBX records."""
import sys
sys.path.insert(0, '.')

from snc_pbx_listener import PhonikSNCListener

# Create listener instance
listener = PhonikSNCListener()

# Test records from user (without ==SMDX prefix)
test_records = [
    "10/08/26 14:54 401 e.400 EC 0:00'05 0 #1",
    "10/08/26 17:21 401 e.400 EC 0:00'10 0 #1",
    "10/08/26 21:04 401 e.400 EC 0:00'08 0 #1",
    "10/08/26 22:15 401 e.400 EC 0:00'04 0 #1",
]

print("=" * 80)
print("Testing SMDR Parsing for Records WITHOUT ==SMDX Prefix")
print("=" * 80)

for i, record in enumerate(test_records, 1):
    print(f"\nTest {i}: {record}")
    event = listener.parse_smdr_line(record)
    
    if event:
        print(f"  ✅ PARSED SUCCESSFULLY")
        print(f"     Room ID: {event['extension']['roomId']}")
        print(f"     Event Type: {event['payload'][0]['contentString']}")
        print(f"     Status: {event['status']}")
    else:
        print(f"  ❌ FAILED TO PARSE - Returns None")
        print(f"     This record will NOT be sent to backend!")

print("\n" + "=" * 80)
print("Testing with ==SMDX prefix (for comparison)")
print("=" * 80)

test_with_prefix = [
    "==SMDX2005=10/08/26 14:54 401 e.400 EC 0:00'05 0 #1",
]

for record in test_with_prefix:
    print(f"\nTest: {record}")
    event = listener.parse_smdr_line(record)
    
    if event:
        print(f"  ✅ PARSED SUCCESSFULLY")
        print(f"     Room ID: {event['extension']['roomId']}")
        print(f"     Event Type: {event['payload'][0]['contentString']}")
    else:
        print(f"  ❌ FAILED TO PARSE")
