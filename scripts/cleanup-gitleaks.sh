#!/bin/bash
# cleanup-gitleaks.sh - Kill all gitleaks processes to prevent memory exhaustion
#
# This script can be run manually to clean up stuck gitleaks processes
# that might be consuming excessive memory.

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}🧹 Gitleaks Process Cleanup Utility${NC}"
echo ""

# Check for existing gitleaks processes
all_pids=$(pgrep -f "gitleaks" 2>/dev/null || true)

if [ -z "$all_pids" ]; then
    echo -e "${GREEN}✅ No gitleaks processes found running${NC}"
    exit 0
fi

# Count processes
process_count=$(echo "$all_pids" | wc -l | tr -d ' ')
echo -e "${YELLOW}⚠️  Found $process_count gitleaks process(es) running:${NC}"
echo ""

# Show detailed information about each process
echo "PID    %CPU  %MEM  ELAPSED  COMMAND"
echo "-----  ----  ----  -------  -------"
ps -p "$all_pids" -o pid,pcpu,pmem,etime,command | tail -n +2

# Calculate total memory usage
total_mem=$(ps -p "$all_pids" -o pmem | tail -n +2 | awk '{sum += $1} END {printf "%.1f", sum}')
echo ""
echo -e "${YELLOW}Total memory usage: ${total_mem}%${NC}"

# Ask for confirmation
echo ""
read -p "Do you want to terminate ALL these gitleaks processes? (y/N) " -n 1 -r
echo

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${BLUE}Cancelled. No processes were terminated.${NC}"
    exit 0
fi

# Terminate processes
echo ""
echo -e "${YELLOW}Terminating processes gracefully (SIGTERM)...${NC}"
echo "$all_pids" | xargs kill -TERM 2>/dev/null || true
sleep 2

# Check if any are still running
remaining=$(pgrep -f "gitleaks" 2>/dev/null || true)
if [ -n "$remaining" ]; then
    remaining_count=$(echo "$remaining" | wc -l | tr -d ' ')
    echo -e "${YELLOW}⚠️  $remaining_count process(es) still running, force killing (SIGKILL)...${NC}"
    echo "$remaining" | xargs kill -KILL 2>/dev/null || true
    sleep 1
fi

# Final check
final_check=$(pgrep -f "gitleaks" 2>/dev/null || true)
if [ -z "$final_check" ]; then
    echo -e "${GREEN}✅ Successfully terminated all gitleaks processes${NC}"

    # Clean up any lock files
    lock_files=$(find /tmp -name "gitleaks-safe-*.lock" 2>/dev/null || true)
    if [ -n "$lock_files" ]; then
        echo ""
        echo -e "${BLUE}Cleaning up lock files...${NC}"
        echo "$lock_files" | xargs rm -f
        echo -e "${GREEN}✅ Lock files cleaned up${NC}"
    fi
else
    echo -e "${RED}❌ Some processes could not be terminated:${NC}"
    ps -p "$final_check" -o pid,pcpu,pmem,etime,command
    echo ""
    echo "You may need to run this script with sudo or reboot the system."
fi

echo ""
echo -e "${BLUE}💡 Tip: Use the memory-safe git hooks to prevent this issue:${NC}"
echo "   ./scripts/install-safe-git-hooks.sh"
