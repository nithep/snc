#!/bin/bash
# Quick Start Script for Smart Nurse Call (SNC) System
# Usage: ./quick_start.sh

echo "🏥 Smart Nurse Call (SNC) - Quick Start"
echo "========================================"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python 3 is not installed. Please install Python 3.10+${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Python 3 found: $(python3 --version)${NC}"

# Install Backend dependencies
echo ""
echo "📦 Installing Backend dependencies..."
cd backend
pip3 install --break-system-packages --upgrade -r requirements.txt
if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Failed to install Backend dependencies. Check network or pip logs above.${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Backend dependencies installed${NC}"

# Install PBX Connector dependencies
echo ""
echo "📦 Installing PBX Connector dependencies..."
cd ../pbx-connector
pip3 install --break-system-packages --upgrade -r requirements.txt
if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Failed to install PBX Connector dependencies.${NC}"
    exit 1
fi
echo -e "${GREEN}✅ PBX Connector dependencies installed${NC}"

cd ..

echo ""
echo "🚀 Starting Services..."
echo ""

# Start Backend Server in background
echo -e "${YELLOW}1️⃣  Starting Backend Server on port 8000...${NC}"
cd backend
python3 server.py > ../backend.log 2>&1 &
BACKEND_PID=$!
echo -e "${GREEN}   ✅ Backend started (PID: $BACKEND_PID)${NC}"
cd ..

# Wait for Backend to start
echo "   ⏱️  Waiting for Backend to initialize..."
sleep 3

# Check if Backend is running
if curl -s http://localhost:8000/health > /dev/null; then
    echo -e "${GREEN}   ✅ Backend is healthy${NC}"
else
    echo -e "${RED}   ❌ Backend failed to start. Check backend.log for details${NC}"
    kill $BACKEND_PID
    exit 1
fi

# Start PBX Listener in background (optional - only if PBX is available)
echo ""
echo -e "${YELLOW}2️⃣  Starting PBX Listener...${NC}"
echo "   ℹ️  Note: This will attempt to connect to PBX at 192.168.1.91:23"
echo "   ℹ️  If PBX is not available, the listener will retry every 5 seconds"
cd pbx-connector
python3 snc_pbx_listener.py > ../pbx_listener.log 2>&1 &
PBX_PID=$!
echo -e "${GREEN}   ✅ PBX Listener started (PID: $PBX_PID)${NC}"
cd ..

echo ""
echo "========================================"
echo -e "${GREEN}🎉 All services started successfully!${NC}"
echo "========================================"
echo ""
echo "📊 Service Status:"
echo "   • Backend API: http://localhost:8000"
echo "   • Health Check: http://localhost:8000/health"
echo "   • WebSocket: ws://localhost:8000/ws/nurse-station"
echo ""
echo "🌐 Frontend Dashboard:"
echo "   • Open: app/index.html in your browser"
echo "   • Or run: npx serve app"
echo ""
echo "🧪 Run Integration Tests:"
echo "   cd api && python3 integration_test.py"
echo ""
echo "📝 View Logs:"
echo "   • Backend: tail -f backend.log"
echo "   • PBX Listener: tail -f pbx_listener.log"
echo ""
echo "🛑 Stop Services:"
echo "   kill $BACKEND_PID $PBX_PID"
echo ""
echo "========================================"
echo ""

# Keep script running
echo -e "${YELLOW}Press Ctrl+C to stop all services...${NC}"
trap "kill $BACKEND_PID $PBX_PID 2>/dev/null; echo ''; echo 'Services stopped.'; exit" INT

# Monitor logs
tail -f backend.log pbx_listener.log
