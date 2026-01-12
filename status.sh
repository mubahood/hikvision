#!/bin/bash
# HikVision Bulletproof - Status Script
# Shows status of bridge and dashboard

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🛡️  HikVision Bulletproof - Status${NC}"
echo "================================"

# Check bridge
BRIDGE_RUNNING=false
if [ -f "bridge.pid" ]; then
    BRIDGE_PID=$(cat bridge.pid)
    if ps -p $BRIDGE_PID > /dev/null 2>&1; then
        BRIDGE_RUNNING=true
        echo -e "Bridge:    ${GREEN}● Running${NC} (PID: $BRIDGE_PID)"
    fi
fi
if [ "$BRIDGE_RUNNING" = false ]; then
    echo -e "Bridge:    ${RED}○ Stopped${NC}"
fi

# Check dashboard
DASHBOARD_RUNNING=false
if [ -f "dashboard.pid" ]; then
    DASHBOARD_PID=$(cat dashboard.pid)
    if ps -p $DASHBOARD_PID > /dev/null 2>&1; then
        DASHBOARD_RUNNING=true
        echo -e "Dashboard: ${GREEN}● Running${NC} (PID: $DASHBOARD_PID)"
    fi
fi
if [ "$DASHBOARD_RUNNING" = false ]; then
    echo -e "Dashboard: ${RED}○ Stopped${NC}"
fi

# Check .env
if [ -f ".env" ]; then
    echo -e "Config:    ${GREEN}● .env exists${NC}"
else
    echo -e "Config:    ${RED}○ .env missing${NC}"
fi

# Check database connection
source .venv/bin/activate 2>/dev/null
if python -c "from database import get_db; db=get_db(); db.get_connection().close()" 2>/dev/null; then
    echo -e "Database:  ${GREEN}● Connected${NC}"
else
    echo -e "Database:  ${RED}○ Not connected${NC}"
fi

echo ""
echo "================================"
if [ "$BRIDGE_RUNNING" = true ] && [ "$DASHBOARD_RUNNING" = true ]; then
    echo -e "Dashboard URL: ${GREEN}http://localhost:8502${NC}"
else
    echo -e "To start: ${YELLOW}./start.sh${NC}"
fi
echo "================================"
