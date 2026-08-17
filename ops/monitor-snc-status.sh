#!/bin/bash
# SNC System Status Monitor with Timeout/ACK Logic
# Displays real-time status of Backend, PBX Listener, and PBX Stream

set -e

# Configuration
BACKEND_PORT=8000
PBX_IP="192.168.1.91"
PBX_PORT=23
LOG_DIR="/home/ecs-agent/snc/logs"
TIMEOUT_BACKEND=5    # seconds
TIMEOUT_PBX=3        # seconds
ACK_INTERVAL=10      # seconds between status checks

# Colors for terminal output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo "=========================================="
echo "SNC System Status Monitor"
echo "Press Ctrl+C to exit"
echo "=========================================="
echo ""

# Function to check if a process is running
check_process() {
    local pattern=$1
    if pgrep -f "$pattern" > /dev/null; then
        return 0
    else
        return 1
    fi
}

# Function to check backend health with timeout
check_backend_status() {
    local response
    local http_code
    
    # Try to get health endpoint with timeout
    http_code=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout $TIMEOUT_BACKEND http://localhost:$BACKEND_PORT/health 2>/dev/null) || true
    
    if [ "$http_code" = "200" ]; then
        # Get detailed health info
        response=$(curl -s --connect-timeout $TIMEOUT_BACKEND http://localhost:$BACKEND_PORT/health 2>/dev/null) || true
        echo -e "${GREEN}● RUNNING${NC}"
        echo "   Health: OK"
        if [ ! -z "$response" ]; then
            echo "   Details: $response" | python3 -c 'import sys, json; data=json.load(sys.stdin); print("   Service: " + str(data.get("service", "N/A"))); print("   Timestamp: " + str(data.get("timestamp", "N/A")))' 2>/dev/null || echo "   Response: OK"
        fi
        return 0
    else
        echo -e "${RED}● DOWN${NC}"
        echo "   Port: $BACKEND_PORT not responding"
        echo "   Timeout: ${TIMEOUT_BACKEND}s"
        return 1
    fi
}

# Function to check PBX listener status
check_pbx_listener_status() {
    if check_process "snc_pbx_listener.py"; then
        echo -e "${GREEN}● RUNNING${NC}"
        
        # Check recent logs for connection status (last 20 lines)
        local log_file="$LOG_DIR/pbx_listener.log"
        if [ -f "$log_file" ]; then
            local last_lines=$(tail -20 "$log_file")
            
            if echo "$last_lines" | grep -q "Connected successfully"; then
                echo "   Connection: Connected to PBX"
                echo -e "   Status: ${GREEN}Active${NC}"
            elif echo "$last_lines" | grep -q "Retrying"; then
                echo "   Connection: Attempting reconnect"
                echo -e "   Status: ${YELLOW}Reconnecting${NC}"
            elif echo "$last_lines" | grep -q "Error"; then
                echo "   Connection: Error detected"
                echo -e "   Status: ${RED}Error${NC}"
                echo "   Last error:" $(echo "$last_lines" | grep "Error" | tail -1 | sed 's/.*ERROR\] //')
            else
                echo "   Connection: Unknown"
                echo -e "   Status: ${YELLOW}Checking${NC}"
            fi
        else
            echo "   Logs: Not found at $log_file"
        fi
        return 0
    else
        echo -e "${RED}● STOPPED${NC}"
        echo "   Process: Not running"
        return 1
    fi
}

# Function to check PBX stream connectivity
check_pbx_stream_status() {
    # Test TCP connection to PBX
    if timeout $TIMEOUT_PBX bash -c "cat < /dev/null > /dev/tcp/$PBX_IP/$PBX_PORT" 2>/dev/null; then
        echo -e "${GREEN}● ACCESSIBLE${NC}"
        echo "   Target: $PBX_IP:$PBX_PORT"
        echo "   Protocol: Telnet (TCP)"
        
        # Check if SMDR data is flowing (from logs)
        local log_file="$LOG_DIR/pbx_listener.log"
        if [ -f "$log_file" ]; then
            # Check for recent SMDR events (last 5 minutes)
            if tail -100 "$log_file" | grep -q "SNC Event Detected"; then
                echo -e "   Data Flow: ${GREEN}Active${NC} (events detected)"
            else
                echo -e "   Data Flow: ${YELLOW}Idle${NC} (no recent events)"
            fi
        fi
        return 0
    else
        echo -e "${RED}● BLOCKED${NC}"
        echo "   Target: $PBX_IP:$PBX_PORT"
        echo "   Issue: Connection timed out (${TIMEOUT_PBX}s)"
        echo "   Actions needed:"
        echo "     - Check firewall rules (allow TCP port 23)"
        echo "     - Verify PBX SMDR/Telnet is enabled"
        echo "     - Check network routing"
        return 1
    fi
}

# Main monitoring loop
while true; do
    clear
    echo "=========================================="
    echo "SNC System Status - $(date '+%Y-%m-%d %H:%M:%S')"
    echo "=========================================="
    echo ""
    
    # Component 1: Backend Server
    echo -e "${BLUE}[1] Backend Server (FastAPI)${NC}"
    echo "------------------------------------------"
    check_backend_status
    BACKEND_STATUS=$?
    echo ""
    
    # Component 2: PBX Listener
    echo -e "${BLUE}[2] PBX Listener (Python)${NC}"
    echo "------------------------------------------"
    check_pbx_listener_status
    LISTENER_STATUS=$?
    echo ""
    
    # Component 3: PBX Stream
    echo -e "${BLUE}[3] PBX Stream (Telnet)${NC}"
    echo "------------------------------------------"
    check_pbx_stream_status
    STREAM_STATUS=$?
    echo ""
    
    # Overall Status Summary
    echo "=========================================="
    echo "Overall System Status"
    echo "=========================================="
    
    if [ $BACKEND_STATUS -eq 0 ] && [ $LISTENER_STATUS -eq 0 ] && [ $STREAM_STATUS -eq 0 ]; then
        echo -e "${GREEN}✓ ALL SYSTEMS OPERATIONAL${NC}"
    elif [ $BACKEND_STATUS -eq 0 ] && [ $LISTENER_STATUS -eq 0 ]; then
        echo -e "${YELLOW}⚠ PARTIAL: Backend & Listener OK, PBX Stream blocked${NC}"
    elif [ $BACKEND_STATUS -eq 0 ]; then
        echo -e "${YELLOW}⚠ PARTIAL: Backend only, services degraded${NC}"
    else
        echo -e "${RED}✗ SYSTEM DOWN: Critical failures detected${NC}"
    fi
    
    echo ""
    echo "Quick Commands:"
    echo "  View Backend Logs:  tail -f $LOG_DIR/backend.log"
    echo "  View PBX Logs:      tail -f $LOG_DIR/pbx_listener.log"
    echo "  Restart Services:   ./start-snc-system.sh"
    echo "  Stop Services:      pkill -f 'uvicorn|snc_pbx'"
    echo ""
    echo "Next update in ${ACK_INTERVAL}s... (Ctrl+C to exit)"
    
    sleep $ACK_INTERVAL
done
