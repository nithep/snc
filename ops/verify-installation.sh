#!/bin/bash
# Quick verification script for SNC system on Pi 4

set -e

BACKEND_PORT=8000
PBX_IP="192.168.1.91"
PBX_PORT=23

echo "=========================================="
echo "SNC System Quick Verification"
echo "=========================================="
echo ""

PASS=0
FAIL=0

# Test function
test_check() {
    local test_name=$1
    local command=$2
    
    echo -n "Testing: $test_name ... "
    if eval "$command" > /dev/null 2>&1; then
        echo "✅ PASS"
        PASS=$((PASS + 1))
        return 0
    else
        echo "❌ FAIL"
        FAIL=$((FAIL + 1))
        return 1
    fi
}

# Run tests
echo "[Backend Tests]"
test_check "Backend process running" "pgrep -f 'uvicorn.*server:app'"
test_check "Backend health endpoint" "curl -s -f http://localhost:$BACKEND_PORT/health"
test_check "Events API accessible" "curl -s -f http://localhost:$BACKEND_PORT/api/events"
test_check "Dashboard HTML served" "curl -s -f http://localhost:$BACKEND_PORT/dashboard-status.html"
echo ""

echo "[PBX Listener Tests]"
test_check "PBX listener process" "pgrep -f 'snc_pbx_listener.py'"
test_check "Listener log exists" "test -f /home/ecs-agent/nithep/snc/logs/pbx_listener.log"
test_check "Listener connected to PBX" "grep -q 'Connected successfully' /home/ecs-agent/nithep/snc/logs/pbx_listener.log"
echo ""

echo "[Network Tests]"
test_check "PBX port accessible" "timeout 2 bash -c 'cat < /dev/null > /dev/tcp/$PBX_IP/$PBX_PORT'"
test_check "Backend port listening" "ss -tlnp | grep :$BACKEND_PORT"
echo ""

echo "[Data Flow Tests]"
test_check "Test event trigger" "curl -s -X POST http://localhost:$BACKEND_PORT/api/events/trigger -H 'Content-Type: application/json' -d '{\"room_id\":\"400\",\"event_type\":\"CALL_BEDSIDE\"}' | grep -q success"
test_check "Event stored in DB" "curl -s http://localhost:$BACKEND_PORT/api/events | grep -q 'room_id'"
echo ""

# Summary
echo "=========================================="
echo "Test Results Summary"
echo "=========================================="
echo "Passed: $PASS"
echo "Failed: $FAIL"
echo ""

if [ $FAIL -eq 0 ]; then
    echo "✅ All tests passed! System is operational."
    echo ""
    echo "Access dashboard at:"
    echo "  http://$(hostname -I | awk '{print $1}'):$BACKEND_PORT/dashboard-status.html"
    exit 0
else
    echo "❌ Some tests failed. Check the output above."
    echo ""
    echo "Troubleshooting:"
    echo "  - If backend tests fail: ./start-snc-system.sh"
    echo "  - If PBX tests fail: ./test-pbx-connectivity.sh"
    echo "  - View logs: tail -f /home/ecs-agent/nithep/snc/logs/*.log"
    exit 1
fi
