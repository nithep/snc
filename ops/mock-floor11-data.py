#!/usr/bin/env python3
"""
Mock Data Generator for Floor 11 (Rajavithi Hospital)
Based on the wiring diagram: DX-ATI-1 to DX-ATI-4
"""
import requests
import random
import time

# Configuration
BASE_URL = "https://snc-cloud-backend-59781590359.asia-southeast1.run.app" # Point to Cloud Run
API_KEY = "" # Leave blank if no key is set on Cloud Run, or enter your key

HEADERS = {
    "Content-Type": "application/json",
    "X-API-Key": API_KEY
}

def trigger_event(room_id, event_type="CALL_BEDSIDE"):
    """Trigger an emergency event for a specific room."""
    url = f"{BASE_URL}/api/events/trigger"
    payload = {"room_id": str(room_id), "event_type": event_type}
    try:
        response = requests.post(url, json=payload, headers=HEADERS)
        if response.status_code == 200:
            print(f"✅ Triggered {event_type} for Room {room_id}")
        else:
            print(f"❌ Failed for Room {room_id}: {response.text}")
    except Exception as e:
        print(f"⚠️ Error connecting to {BASE_URL}: {e}")

def acknowledge_room(room_id):
    """Acknowledge an event for a specific room."""
    url = f"{BASE_URL}/api/events/acknowledge/{room_id}"
    try:
        response = requests.post(url, headers=HEADERS)
        if response.status_code == 200:
            print(f" Acknowledged Room {room_id}")
    except Exception as e:
        print(f"⚠️ Error acknowledging Room {room_id}: {e}")

def main():
    print("🏥 Starting Mock Data Generation for Floor 11...")
    
    # 1. Define Rooms based on Wiring Diagram
    patient_rooms = list(range(1101, 1128)) # 1101 to 1127
    nurse_station = "KEY-1100"
    display_console = "DISPLAY-1100"

    # 2. Clear existing data (Optional: Uncomment if you have a reset endpoint)
    # requests.post(f"{BASE_URL}/api/admin/reset-db", headers=HEADERS)

    # 3. Simulate Active Calls (Emergency)
    print("\n🚨 Simulating Emergency Calls...")
    active_rooms = random.sample(patient_rooms, 5) # Pick 5 random rooms for emergency
    for room in active_rooms:
        trigger_event(room, "CALL_BEDSIDE")
        time.sleep(0.5)

    # 4. Simulate Acknowledged Calls
    print("\n📞 Simulating Acknowledged Calls...")
    ack_rooms = random.sample([r for r in patient_rooms if r not in active_rooms], 3)
    for room in ack_rooms:
        trigger_event(room, "CALL_BEDSIDE")
        time.sleep(0.2)
        acknowledge_room(room)
        time.sleep(0.3)

    # 5. Simulate Bathroom Emergencies
    print("\n Simulating Bathroom Emergencies...")
    bathroom_rooms = random.sample([r for r in patient_rooms if r not in active_rooms and r not in ack_rooms], 2)
    for room in bathroom_rooms:
        trigger_event(room, "CALL_BATHROOM_EMERGENCY")
        time.sleep(0.5)

    # 6. Simulate Nurse Station & Display Status (Info/Normal)
    print("\n💻 Updating Nurse Station & Display...")
    trigger_event(nurse_station, "INFO_UPDATE")
    trigger_event(display_console, "INFO_UPDATE")

    print("\n✨ Mock Data Generation Complete! Check your Dashboard at https://snc.nithep.com")

if __name__ == "__main__":
    main()
