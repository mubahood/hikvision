#!/bin/bash
# HikVision Bulletproof - Stop Script
# Stops both the bridge and dashboard

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${RED}🛑 Stopping HikVision Bulletproof${NC}"
echo "================================"

# Stop bridge
if [ -f "bridge.pid" ]; then
    BRIDGE_PID=$(cat bridge.pid)
    if ps -p $BRIDGE_PID > /dev/null 2>&1; then
        echo -e "${YELLOW}Stopping bridge (PID: $BRIDGE_PID)...${NC}"
        kill $BRIDGE_PID 2>/dev/null || true
        sleep 1
        kill -9 $BRIDGE_PID 2>/dev/null || true
    fi
    rm -f bridge.pid
fi

# Kill any remaining bridge processes
pkill -f "hikvision_bridge.py" 2>/dev/null || true

echo -e "${GREEN}✅ Bridge stopped${NC}"

# Stop dashboard
if [ -f "dashboard.pid" ]; then
    DASHBOARD_PID=$(cat dashboard.pid)
    if ps -p $DASHBOARD_PID > /dev/null 2>&1; then
        echo -e "${YELLOW}Stopping dashboard (PID: $DASHBOARD_PID)...${NC}"
        kill $DASHBOARD_PID 2>/dev/null || true
        sleep 1
        kill -9 $DASHBOARD_PID 2>/dev/null || true
    fi
    rm -f dashboard.pid
fi

# Kill any remaining streamlit processes for this project
pkill -f "streamlit run dashboard" 2>/dev/null || true

echo -e "${GREEN}✅ Dashboard stopped${NC}"

echo ""
echo "================================"
echo -e "${GREEN}All services stopped.${NC}"
echo -e "To start again: ${YELLOW}./start.sh${NC}"
echo "================================"
