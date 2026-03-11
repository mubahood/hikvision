#!/bin/bash
# HikVision Bulletproof - Start Script
# Starts both the bridge and dashboard

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🛡️  HikVision Bulletproof${NC}"
echo "================================"

# Check if .env exists
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}⚠️  .env file not found. Creating from template...${NC}"
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo -e "${YELLOW}   Please edit .env with your settings${NC}"
    else
        echo -e "${RED}❌ .env.example not found. Please create .env manually.${NC}"
        exit 1
    fi
fi

# Check for virtual environment
if [ ! -d ".venv" ]; then
    echo -e "${YELLOW}📦 Creating virtual environment...${NC}"
    python3 -m venv .venv
fi

# Activate virtual environment
echo -e "${GREEN}🔧 Activating virtual environment...${NC}"
source .venv/bin/activate

# Check dependencies
if ! python -c "import streamlit" 2>/dev/null; then
    echo -e "${YELLOW}📥 Installing dependencies...${NC}"
    pip install -r requirements.txt
fi

# Kill any existing processes
echo -e "${YELLOW}🔄 Stopping any existing processes...${NC}"
pkill -f "hikvision_bridge.py" 2>/dev/null || true
pkill -f "streamlit run dashboard" 2>/dev/null || true
sleep 1

# Start bridge in background with auto-restart watchdog
echo -e "${GREEN}🚀 Starting bridge (with auto-restart watchdog)...${NC}"
nohup bash -c '
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "'"$SCRIPT_DIR"'"
source .venv/bin/activate
while true; do
    echo "[$(date)] Bridge starting..." >> bridge_watchdog.log
    python hikvision_bridge.py >> bridge_output.log 2>&1
    EXIT_CODE=$?
    echo "[$(date)] Bridge exited with code $EXIT_CODE — restarting in 5s..." >> bridge_watchdog.log
    sleep 5
done
' > /dev/null 2>&1 &
BRIDGE_PID=$!
echo $BRIDGE_PID > bridge.pid
echo -e "   Bridge watchdog PID: ${BRIDGE_PID}"

# Wait for bridge to start
sleep 2

# Check if bridge is running
if ps -p $BRIDGE_PID > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Bridge started successfully${NC}"
else
    echo -e "${RED}❌ Bridge failed to start. Check bridge_output.log${NC}"
    exit 1
fi

# Start dashboard
echo -e "${GREEN}🖥️  Starting dashboard...${NC}"
nohup streamlit run dashboard.py --server.port 8502 --server.headless true > dashboard.log 2>&1 &
DASHBOARD_PID=$!
echo $DASHBOARD_PID > dashboard.pid
echo -e "   Dashboard PID: ${DASHBOARD_PID}"

# Wait for dashboard
sleep 3

# Check if dashboard is running
if ps -p $DASHBOARD_PID > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Dashboard started successfully${NC}"
else
    echo -e "${RED}❌ Dashboard failed to start. Check dashboard.log${NC}"
fi

echo ""
echo "================================"
echo -e "${GREEN}🎉 HikVision Bulletproof is running!${NC}"
echo ""
echo -e "   Dashboard: ${GREEN}http://localhost:8502${NC}"
echo -e "   Bridge:    ${GREEN}Running (PID: $BRIDGE_PID)${NC}"
echo ""
echo -e "   To stop: ${YELLOW}./stop.sh${NC}"
echo "================================"
