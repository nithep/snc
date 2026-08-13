#!/bin/bash
# Interactive Log Viewer for SNC System
# Provides easy access to backend and PBX listener logs

LOG_DIR="/home/ecs-agent/nithep/snc/logs"

echo "=========================================="
echo "SNC System Log Viewer"
echo "=========================================="
echo ""

# Check if logs exist
if [ ! -d "$LOG_DIR" ]; then
    echo "❌ Log directory not found: $LOG_DIR"
    echo "   Has the system been started yet?"
    exit 1
fi

BACKEND_LOG="$LOG_DIR/backend.log"
PBX_LOG="$LOG_DIR/pbx_listener.log"

echo "Select log view mode:"
echo "  1) Backend log only"
echo "  2) PBX Listener log only"
echo "  3) Both logs (merged, real-time)"
echo "  4) Last 50 lines of both logs"
echo "  5) Search for errors in both logs"
echo "  6) Show recent events from backend"
echo ""
echo -n "Enter choice (1-6): "
read choice

case $choice in
    1)
        if [ -f "$BACKEND_LOG" ]; then
            echo "Viewing Backend Log (Ctrl+C to exit)..."
            echo "=========================================="
            tail -f "$BACKEND_LOG"
        else
            echo "❌ Backend log not found: $BACKEND_LOG"
        fi
        ;;
    2)
        if [ -f "$PBX_LOG" ]; then
            echo "Viewing PBX Listener Log (Ctrl+C to exit)..."
            echo "=========================================="
            tail -f "$PBX_LOG"
        else
            echo "❌ PBX log not found: $PBX_LOG"
        fi
        ;;
    3)
        echo "Viewing merged logs (Ctrl+C to exit)..."
        echo "=========================================="
        if [ -f "$BACKEND_LOG" ] && [ -f "$PBX_LOG" ]; then
            tail -f "$BACKEND_LOG" "$PBX_LOG"
        elif [ -f "$BACKEND_LOG" ]; then
            tail -f "$BACKEND_LOG"
        elif [ -f "$PBX_LOG" ]; then
            tail -f "$PBX_LOG"
        else
            echo "❌ No logs found"
        fi
        ;;
    4)
        echo "=== Last 50 lines of Backend Log ==="
        if [ -f "$BACKEND_LOG" ]; then
            tail -50 "$BACKEND_LOG"
        else
            echo "(No backend log)"
        fi
        echo ""
        echo "=== Last 50 lines of PBX Listener Log ==="
        if [ -f "$PBX_LOG" ]; then
            tail -50 "$PBX_LOG"
        else
            echo "(No PBX log)"
        fi
        ;;
    5)
        echo "=== Searching for Errors ==="
        echo ""
        echo "Backend Errors:"
        if [ -f "$BACKEND_LOG" ]; then
            grep -i "error\|exception\|fail" "$BACKEND_LOG" | tail -20 || echo "  No errors found"
        else
            echo "  (No backend log)"
        fi
        echo ""
        echo "PBX Listener Errors:"
        if [ -f "$PBX_LOG" ]; then
            grep -i "error\|exception\|fail" "$PBX_LOG" | tail -20 || echo "  No errors found"
        else
            echo "  (No PBX log)"
        fi
        ;;
    6)
        echo "=== Recent Events from Backend API ==="
        curl -s http://localhost:8000/api/events 2>/dev/null | python3 -m json.tool || echo "Failed to fetch events. Is backend running?"
        ;;
    *)
        echo "Invalid choice"
        exit 1
        ;;
esac
