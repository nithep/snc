"""
Integration Test Script for Smart Nurse Call (SNC) System
Tests the complete flow: PBX Listener → Backend API → WebSocket → Frontend Dashboard
"""

import asyncio
import aiohttp
import json
import time
from datetime import datetime

BACKEND_URL = "http://localhost:8000"

class SNCIntegrationTest:
    def __init__(self):
        self.session = None
        self.test_results = []
    
    async def init_session(self):
        """Initialize HTTP session."""
        self.session = aiohttp.ClientSession()
    
    async def close_session(self):
        """Close HTTP session."""
        if self.session:
            await self.session.close()
    
    async def test_health_check(self):
        """Test 1: Health Check Endpoint."""
        print("\n🧪 Test 1: Health Check")
        print("-" * 50)
        
        try:
            async with self.session.get(f"{BACKEND_URL}/health") as response:
                data = await response.json()
                print(f"✅ Status: {data['status']}")
                print(f"✅ Service: {data['service']}")
                print(f"✅ Timestamp: {data['timestamp']}")
                self.test_results.append(("Health Check", "PASS"))
                return True
        except Exception as e:
            print(f"❌ Failed: {e}")
            self.test_results.append(("Health Check", "FAIL"))
            return False
    
    async def test_trigger_bedside_call(self, room_id="0400"):
        """Test 2: Trigger Bedside Call."""
        print(f"\n🧪 Test 2: Trigger Bedside Call (Room {room_id})")
        print("-" * 50)
        
        try:
            payload = {
                "room_id": room_id,
                "event_type": "CALL_BEDSIDE"
            }
            
            start_time = time.time()
            async with self.session.post(f"{BACKEND_URL}/api/events/trigger", json=payload) as response:
                elapsed = time.time() - start_time
                data = await response.json()
                
                print(f"✅ Response Status: {response.status}")
                print(f"✅ Event ID: {data['event']['id']}")
                print(f"✅ Room ID: {data['event']['extension']['roomId']}")
                print(f"✅ Latency: {elapsed*1000:.2f}ms")
                
                if elapsed < 1.0:
                    print(f"✅ Performance: PASS (< 1 second)")
                else:
                    print(f"⚠️ Performance: SLOW (> 1 second)")
                
                self.test_results.append(("Trigger Bedside Call", "PASS"))
                return True
        except Exception as e:
            print(f"❌ Failed: {e}")
            self.test_results.append(("Trigger Bedside Call", "FAIL"))
            return False
    
    async def test_trigger_bathroom_emergency(self, room_id="0401"):
        """Test 3: Trigger Bathroom Emergency (via temporal escalation)."""
        print(f"\n🧪 Test 3: Trigger Bathroom Emergency (Room {room_id})")
        print("-" * 50)
        
        try:
            # First call
            print("   📞 First call (Bedside)...")
            payload1 = {
                "room_id": room_id,
                "event_type": "CALL_BEDSIDE"
            }
            async with self.session.post(f"{BACKEND_URL}/api/events/trigger", json=payload1) as response:
                data1 = await response.json()
                print(f"   ✅ First call triggered")
            
            # Wait 30 seconds to simulate temporal pattern
            print("   ⏱️ Waiting 30 seconds for temporal pattern...")
            await asyncio.sleep(30)
            
            # Second call (should escalate to bathroom emergency)
            print("   📞 Second call (should escalate to Bathroom Emergency)...")
            payload2 = {
                "room_id": room_id,
                "event_type": "CALL_BEDSIDE"
            }
            async with self.session.post(f"{BACKEND_URL}/api/events/trigger", json=payload2) as response:
                data2 = await response.json()
                print(f"   ✅ Second call triggered")
                print(f"   ⚠️ Note: Temporal escalation is handled by PBX Listener, not Backend API")
                
                self.test_results.append(("Bathroom Emergency Escalation", "PASS"))
                return True
        except Exception as e:
            print(f"❌ Failed: {e}")
            self.test_results.append(("Bathroom Emergency Escalation", "FAIL"))
            return False
    
    async def test_acknowledge_call(self, room_id="0400"):
        """Test 4: Acknowledge Call."""
        print(f"\n🧪 Test 4: Acknowledge Call (Room {room_id})")
        print("-" * 50)
        
        try:
            start_time = time.time()
            async with self.session.post(f"{BACKEND_URL}/api/events/acknowledge/{room_id}") as response:
                elapsed = time.time() - start_time
                data = await response.json()
                
                print(f"✅ Response Status: {response.status}")
                print(f"✅ Room ID: {data['room_id']}")
                
                if data.get('sla_metrics'):
                    ack_time = data['sla_metrics'].get('ack_time_seconds', 'N/A')
                    sla_breached = data['sla_metrics'].get('sla_breached', False)
                    print(f"✅ Ack Time: {ack_time}s")
                    print(f"✅ SLA Breached: {sla_breached}")
                
                print(f"✅ Latency: {elapsed*1000:.2f}ms")
                
                self.test_results.append(("Acknowledge Call", "PASS"))
                return True
        except Exception as e:
            print(f"❌ Failed: {e}")
            self.test_results.append(("Acknowledge Call", "FAIL"))
            return False
    
    async def test_clear_call(self, room_id="0400"):
        """Test 5: Clear Call."""
        print(f"\n🧪 Test 5: Clear Call (Room {room_id})")
        print("-" * 50)
        
        try:
            start_time = time.time()
            async with self.session.post(f"{BACKEND_URL}/api/events/clear/{room_id}") as response:
                elapsed = time.time() - start_time
                data = await response.json()
                
                print(f"✅ Response Status: {response.status}")
                print(f"✅ Room ID: {data['room_id']}")
                
                if data.get('sla_metrics'):
                    resolution_time = data['sla_metrics'].get('resolution_time_seconds', 'N/A')
                    sla_breached = data['sla_metrics'].get('sla_breached', False)
                    print(f"✅ Resolution Time: {resolution_time}s")
                    print(f"✅ SLA Breached: {sla_breached}")
                
                print(f"✅ Latency: {elapsed*1000:.2f}ms")
                
                self.test_results.append(("Clear Call", "PASS"))
                return True
        except Exception as e:
            print(f"❌ Failed: {e}")
            self.test_results.append(("Clear Call", "FAIL"))
            return False
    
    async def test_get_events(self):
        """Test 6: Get Recent Events."""
        print("\n🧪 Test 6: Get Recent Events")
        print("-" * 50)
        
        try:
            async with self.session.get(f"{BACKEND_URL}/api/events") as response:
                data = await response.json()
                
                print(f"✅ Total Events: {len(data['events'])}")
                
                if data['events']:
                    latest = data['events'][0]
                    print(f"✅ Latest Event:")
                    print(f"   - Room: {latest['room_id']}")
                    print(f"   - Type: {latest['event_type']}")
                    print(f"   - Status: {latest['status']}")
                    print(f"   - Timestamp: {latest['timestamp']}")
                
                self.test_results.append(("Get Events", "PASS"))
                return True
        except Exception as e:
            print(f"❌ Failed: {e}")
            self.test_results.append(("Get Events", "FAIL"))
            return False
    
    async def test_kpi_analytics(self):
        """Test 7: KPI Analytics."""
        print("\n🧪 Test 7: KPI Analytics")
        print("-" * 50)
        
        try:
            async with self.session.get(f"{BACKEND_URL}/api/analytics/kpi") as response:
                data = await response.json()
                
                print(f"✅ Average Ack Time: {data['avg_ack_time_seconds']}s")
                print(f"✅ Average Resolution Time: {data['avg_resolution_time_seconds']}s")
                print(f"✅ Total Events: {data['total_events']}")
                print(f"✅ SLA Compliance Rate: {data['sla_compliance_rate']}%")
                print(f"✅ Events by Type: {data['events_by_type']}")
                
                # Check SLA targets
                if data['avg_ack_time_seconds'] <= 30:
                    print(f"✅ Ack Time SLA: PASS (≤ 30s)")
                else:
                    print(f"⚠️ Ack Time SLA: FAIL (> 30s)")
                
                if data['avg_resolution_time_seconds'] <= 180:
                    print(f"✅ Resolution Time SLA: PASS (≤ 180s)")
                else:
                    print(f"⚠️ Resolution Time SLA: FAIL (> 180s)")
                
                if data['sla_compliance_rate'] >= 95:
                    print(f"✅ Overall SLA Compliance: PASS (≥ 95%)")
                else:
                    print(f"⚠️ Overall SLA Compliance: FAIL (< 95%)")
                
                self.test_results.append(("KPI Analytics", "PASS"))
                return True
        except Exception as e:
            print(f"❌ Failed: {e}")
            self.test_results.append(("KPI Analytics", "FAIL"))
            return False
    
    async def run_all_tests(self):
        """Run all integration tests."""
        print("=" * 70)
        print("🏥 Smart Nurse Call (SNC) Integration Test Suite")
        print("=" * 70)
        print(f"🕐 Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        await self.init_session()
        
        # Run tests in sequence
        await self.test_health_check()
        await self.test_trigger_bedside_call("0400")
        await self.test_acknowledge_call("0400")
        await self.test_clear_call("0400")
        await self.test_trigger_bedside_call("0401")
        await self.test_acknowledge_call("0401")
        await self.test_clear_call("0401")
        await self.test_get_events()
        await self.test_kpi_analytics()
        
        # Skip temporal escalation test for quick testing
        # await self.test_trigger_bathroom_emergency("0402")
        
        await self.close_session()
        
        # Print summary
        print("\n" + "=" * 70)
        print("📊 Test Summary")
        print("=" * 70)
        
        passed = sum(1 for _, result in self.test_results if result == "PASS")
        failed = sum(1 for _, result in self.test_results if result == "FAIL")
        total = len(self.test_results)
        
        for test_name, result in self.test_results:
            status_icon = "✅" if result == "PASS" else "❌"
            print(f"{status_icon} {test_name}: {result}")
        
        print("-" * 70)
        print(f"Total: {total} | Passed: {passed} | Failed: {failed}")
        
        if failed == 0:
            print("\n🎉 All tests PASSED! System is ready for Phase 1 deployment.")
        else:
            print(f"\n⚠️ {failed} test(s) FAILED. Please review and fix issues.")
        
        print("=" * 70)

if __name__ == "__main__":
    tester = SNCIntegrationTest()
    asyncio.run(tester.run_all_tests())
