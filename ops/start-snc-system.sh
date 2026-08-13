#!/bin/bash
# SNC System Startup Script for Raspberry Pi 4
# This script starts the Backend and PBX Listener services

set -e

# Configuration
BACKEND_DIR="/home/ecs-agent/nithep/snc/backend"
PBX_DIR="/home/ecs-agent/nithep/snc/pbx-connector"
LOG_DIR="/home/ecs-agent/nithep/snc/logs"
BACKEND_PORT=8000
PBX_IP="192.168.1.91"
PBX_PORT=23

# Create log directory if it doesn't exist
mkdir -p "$LOG_DIR"

echo "=========================================="
echo "SNC System Starting on Pi 4"
echo "=========================================="
echo "Timestamp: $(date)"
echo ""

# Function to check if a port is open
check_port() {
    local host=$1
    local port=$2
    timeout 2 bash -c "cat < /dev/null > /dev/tcp/$host/$port" 2>/dev/null
    return $?
}

# Function to check if backend is healthy
check_backend_health() {
    local max_retries=10
    local retry_count=0
    
    while [ $retry_count -lt $max_retries ]; do
        if curl -s -f http://localhost:$BACKEND_PORT/health > /dev/null 2>&1; then
            return 0
        fi
        retry_count=$((retry_count + 1))
        echo "Waiting for backend to start... (attempt $retry_count/$max_retries)"
        sleep 2
    done
    return 1
}

# Step 1: Check PBX connectivity
echo "[1/5] Checking PBX connectivity..."
if check_port "$PBX_IP" "$PBX_PORT"; then
    echo "✅ PBX Port $PBX_IP:$PBX_PORT is accessible"
else
    echo "❌ WARNING: Cannot reach PBX at $PBX_IP:$PBX_PORT"
    echo "   Please check:"
    echo "   - Firewall rules allowing TCP port 23"
    echo "   - PBX SMDR/Telnet output is enabled"
    echo "   - Network route to $PBX_IP"
fi
echo ""

# Step 2: Start Backend Server
echo "[2/5] Starting SNC Backend Server on port $BACKEND_PORT..."
cd "$BACKEND_DIR"

# Kill any existing backend process
pkill -f "uvicorn.*server:app" 2>/dev/null || true
sleep 1

# Start backend in background
nohup python3 -m uvicorn server:app --host 0.0.0.0 --port $BACKEND_PORT > "$LOG_DIR/backend.log" 2>&1 &
BACKEND_PID=$!
echo "Backend started with PID: $BACKEND_PID"

# Wait for backend to be ready
if check_backend_health; then
    echo "✅ Backend is healthy and responding on http://localhost:$BACKEND_PORT/health"
    curl -s http://localhost:$BACKEND_PORT/health | python3 -m json.tool
else
    echo "❌ Backend failed to start. Check logs: $LOG_DIR/backend.log"
    exit 1
fi
echo ""

# Step 3: Start PBX Listener
echo "[3/5] Starting PBX Listener..."
cd "$PBX_DIR"

# Kill any existing listener process
pkill -f "python3.*snc_pbx_listener.py" 2>/dev/null || true
sleep 1

# Start PBX listener in background
nohup python3 snc_pbx_listener.py > "$LOG_DIR/pbx_listener.log" 2>&1 &
PBX_PID=$!
echo "PBX Listener started with PID: $PBX_PID"

# Wait a moment for connection attempt
sleep 3

# Check if listener is still running
if kill -0 $PBX_PID 2>/dev/null; then
    echo "✅ PBX Listener is running"
    # Check recent logs for connection status
    if grep -q "Connected successfully" "$LOG_DIR/pbx_listener.log"; then
        echo "✅ PBX Listener connected successfully"
    else
        echo "⚠️  PBX Listener may not have connected yet. Check logs: $LOG_DIR/pbx_listener.log"
    fi
else
    echo "❌ PBX Listener crashed. Check logs: $LOG_DIR/pbx_listener.log"
fi
echo ""

# Step 4: Display Status Summary
echo "[4/5] System Status Summary"
echo "=========================================="
echo "Backend Server:  http://localhost:$BACKEND_PORT"
echo "Health Endpoint: http://localhost:$BACKEND_PORT/health"
echo "Dashboard:       http://$(hostname -I | awk '{print $1}'):$BACKEND_PORT"
echo ""
echo "Process IDs:"
echo "  Backend PID:   $BACKEND_PID"
echo "  PBX PID:       $PBX_PID"
echo ""
echo "Log Files:"
echo "  Backend:       $LOG_DIR/backend.log"
echo "  PBX Listener:  $LOG_DIR/pbx_listener.log"
echo ""

# Step 5: Show how to monitor
echo "[5/5] Monitoring Commands"
echo "=========================================="
echo "# Check backend health:"
echo "curl http://localhost:$BACKEND_PORT/health"
echo ""
echo "# View backend logs:"
echo "tail -f $LOG_DIR/backend.log"
echo ""
echo "# View PBX listener logs:"
echo "tail -f $LOG_DIR/pbx_listener.log"
echo ""
echo "# Check processes:"
echo "ps aux | grep -E 'uvicorn|snc_pbx'"
echo ""
echo "# Stop services:"
echo "kill $BACKEND_PID $PBX_PID"
echo ""
echo "=========================================="
echo "SNC System Started Successfully!"
echo "=========================================="
