#!/bin/bash
# PBX Connectivity Diagnostic Script
# Tests network connectivity, firewall rules, and PBX configuration

set -e

PBX_IP="192.168.1.91"
PBX_PORT=23
TIMEOUT=3

echo "=========================================="
echo "PBX Connectivity Diagnostic Tool"
echo "Target: $PBX_IP:$PBX_PORT (Telnet)"
echo "=========================================="
echo ""

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test 1: Network Reachability
echo "[Test 1/6] Network Reachability"
echo "------------------------------------------"
if ping -c 2 -W $TIMEOUT $PBX_IP > /dev/null 2>&1; then
    echo -e "${GREEN}✓ PASS${NC}: PBX is reachable via ICMP"
else
    echo -e "${RED}✗ FAIL${NC}: Cannot ping PBX at $PBX_IP"
    echo "   Possible causes:"
    echo "   - Network cable disconnected"
    echo "   - Wrong IP address"
    echo "   - PBX powered off"
fi
echo ""

# Test 2: DNS Resolution (if using hostname)
echo "[Test 2/6] IP Configuration"
echo "------------------------------------------"
echo "Target IP: $PBX_IP"
echo "Local IP: $(hostname -I | awk '{print $1}')"
echo "Subnet: $(hostname -I | awk '{print $1}' | cut -d. -f1-3).0/24"

# Check if PBX is on same subnet
LOCAL_SUBNET=$(hostname -I | awk '{print $1}' | cut -d. -f1-3)
PBX_SUBNET=$(echo $PBX_IP | cut -d. -f1-3)

if [ "$LOCAL_SUBNET" = "$PBX_SUBNET" ]; then
    echo -e "${GREEN}✓ PASS${NC}: PBX is on same subnet ($LOCAL_SUBNET.x)"
else
    echo -e "${YELLOW}⚠ WARN${NC}: PBX is on different subnet ($PBX_SUBNET.x vs $LOCAL_SUBNET.x)"
    echo "   Routing may be required"
fi
echo ""

# Test 3: Port Connectivity
echo "[Test 3/6] TCP Port Connectivity"
echo "------------------------------------------"
if timeout $TIMEOUT bash -c "cat < /dev/null > /dev/tcp/$PBX_IP/$PBX_PORT" 2>/dev/null; then
    echo -e "${GREEN}✓ PASS${NC}: Port $PBX_PORT is open and accepting connections"
else
    echo -e "${RED}✗ FAIL${NC}: Port $PBX_PORT is blocked or closed"
    echo "   Possible causes:"
    echo "   - Firewall blocking port 23"
    echo "   - Telnet service not enabled on PBX"
    echo "   - SMDR output not configured"
    echo ""
    echo "   Troubleshooting steps:"
    echo "   1. Check Pi firewall: sudo iptables -L"
    echo "   2. Check PBX telnet settings"
    echo "   3. Verify SMDR is enabled on PBX"
fi
echo ""

# Test 4: Firewall Rules
echo "[Test 4/6] Local Firewall Status"
echo "------------------------------------------"
if command -v ufw &> /dev/null; then
    UFW_STATUS=$(ufw status 2>/dev/null | head -1)
    echo "UFW Status: $UFW_STATUS"
    
    if echo "$UFW_STATUS" | grep -q "active"; then
        echo "Checking rules for port 23..."
        if ufw status | grep -q "23.*ALLOW"; then
            echo -e "${GREEN}✓ PASS${NC}: Firewall allows port 23"
        else
            echo -e "${YELLOW}⚠ WARN${NC}: No explicit rule for port 23"
            echo "   Add rule: sudo ufw allow out 23/tcp"
        fi
    fi
elif command -v iptables &> /dev/null; then
    echo "iptables rules (outbound to port 23):"
    iptables -L OUTPUT -n -v | grep "dpt:23" || echo "   No specific rules found"
else
    echo "   No firewall management tool detected"
fi
echo ""

# Test 5: Telnet Client Availability
echo "[Test 5/6] Telnet Client"
echo "------------------------------------------"
if command -v telnet &> /dev/null; then
    echo -e "${GREEN}✓ PASS${NC}: Telnet client is installed"
else
    echo -e "${RED}✗ FAIL${NC}: Telnet client not found"
    echo "   Install: sudo apt-get install telnet"
fi
echo ""

# Test 6: Manual Connection Test
echo "[Test 6/6] Manual Connection Test"
echo "------------------------------------------"
echo "Attempting 5-second connection test..."
if command -v telnet &> /dev/null; then
    timeout 5 telnet $PBX_IP $PBX_PORT <<EOF
quit
EOF
    EXIT_CODE=$?
    if [ $EXIT_CODE -eq 0 ] || [ $EXIT_CODE -eq 124 ]; then
        echo -e "${GREEN}✓ PASS${NC}: Successfully connected to PBX"
        echo "   You should see SMDR data streaming"
    else
        echo -e "${RED}✗ FAIL${NC}: Connection failed (exit code: $EXIT_CODE)"
    fi
else
    echo "   Skipping: Telnet not available"
fi
echo ""

# Summary and Recommendations
echo "=========================================="
echo "Diagnostic Summary"
echo "=========================================="
echo ""
echo "If tests are failing, check PBX configuration:"
echo ""
echo "1. Enable Telnet Server on Phonik PBX:"
echo "   - Access PBX web interface"
echo "   - Navigate to System > Network > Services"
echo "   - Enable Telnet server"
echo ""
echo "2. Enable SMDR Output:"
echo "   - Go to SMDR/Call Accounting settings"
echo "   - Enable SMDR output"
echo "   - Configure output to Telnet/streaming"
echo "   - Set format to match pattern: ==SMDX..."
echo ""
echo "3. Check Firewall on Pi:"
echo "   sudo ufw allow out 23/tcp"
echo "   sudo ufw status"
echo ""
echo "4. Verify network path:"
echo "   traceroute $PBX_IP"
echo "   nmap -p 23 $PBX_IP"
echo ""
echo "5. Test from another device:"
echo "   Try connecting from laptop/phone to isolate issue"
echo ""
echo "6. SMDR Stream Conflict Check (PC Operator)"
echo "------------------------------------------"
echo "⚠ IMPORTANT: Phonik PBX มักส่ง SMDR ไปยัง client ที่ authenticated แล้วเพียง 1 ตัว"
echo "   หาก Phonik PC Operator ยัง Online อยู่ Pi จะได้รับแค่ welcome banner"
echo "   วิธีแก้: Disconnect PC Operator จาก 192.168.1.91 ก่อนทดสอบ"
echo ""
