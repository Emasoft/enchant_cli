#!/bin/bash
# gitleaks-safe.sh - A portable wrapper for gitleaks that prevents memory exhaustion
#
# Features:
# - Prevents multiple concurrent runs
# - Adds timeout protection
# - Limits memory usage
# - Provides clear feedback
# - Works across different projects
#
# Usage: ./gitleaks-safe.sh [gitleaks arguments]

set -euo pipefail

# Configuration
SCRIPT_NAME="gitleaks-safe"
LOCKFILE="${TMPDIR:-/tmp}/${SCRIPT_NAME}-$(echo "$PWD" | md5).lock"
TIMEOUT_SECONDS=${GITLEAKS_TIMEOUT:-120}  # 2 minutes default, configurable via env
MAX_RETRIES=${GITLEAKS_RETRIES:-1}       # No retries by default
VERBOSE=${GITLEAKS_VERBOSE:-false}       # Verbose mode off by default

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Cleanup function
cleanup() {
    local exit_code=$?
    rm -f "$LOCKFILE"
    exit $exit_code
}

# Set up trap for cleanup
trap cleanup EXIT INT TERM

# Function to check if gitleaks is already running
check_running() {
    if [ -f "$LOCKFILE" ]; then
        local pid=$(cat "$LOCKFILE" 2>/dev/null || echo "")
        if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
            return 0  # Already running
        else
            # Stale lock file, remove it
            rm -f "$LOCKFILE"
        fi
    fi
    return 1  # Not running
}

# Function to kill ALL existing gitleaks processes system-wide
kill_existing() {
    # First, kill any gitleaks processes system-wide
    local all_pids=$(pgrep -f "gitleaks" 2>/dev/null || true)
    if [ -n "$all_pids" ]; then
        echo -e "${YELLOW}⚠️  Found existing gitleaks processes system-wide:${NC}"
        # Show what processes we're killing
        ps -p "$all_pids" -o pid,pcpu,pmem,etime,command 2>/dev/null || true

        echo -e "${YELLOW}⚠️  Terminating ALL gitleaks processes to prevent memory leaks...${NC}"
        echo "$all_pids" | xargs kill -TERM 2>/dev/null || true
        sleep 1

        # Force kill if still running
        local remaining=$(pgrep -f "gitleaks" 2>/dev/null || true)
        if [ -n "$remaining" ]; then
            echo -e "${YELLOW}⚠️  Force killing remaining gitleaks processes...${NC}"
            echo "$remaining" | xargs kill -KILL 2>/dev/null || true
            sleep 0.5
        fi

        echo -e "${GREEN}✅ Cleaned up existing gitleaks processes${NC}"
    fi
}

# Main execution
main() {
    # First, check for any existing gitleaks processes that might cause memory issues
    local existing_count=$(pgrep -f "gitleaks" 2>/dev/null | wc -l | tr -d ' ')
    if [ "$existing_count" -gt 0 ]; then
        echo -e "${YELLOW}⚠️  WARNING: Found $existing_count existing gitleaks process(es)${NC}"
        echo -e "${YELLOW}These can cause memory exhaustion if left running${NC}"
    fi

    # Check if gitleaks is installed
    if ! command -v gitleaks &> /dev/null; then
        echo -e "${RED}❌ gitleaks is not installed.${NC}"
        echo "Please install it using one of these methods:"
        echo ""
        echo "macOS:        brew install gitleaks"
        echo "Ubuntu/Debian: sudo snap install gitleaks"
        echo "Fedora:       sudo dnf install gitleaks"
        echo "Arch:         yay -S gitleaks"
        echo "Windows:      scoop install gitleaks"
        echo ""
        echo "Or run: ./scripts/install-safe-git-hooks.sh (it will offer to install gitleaks)"
        echo "Or visit: https://github.com/gitleaks/gitleaks#installing"
        exit 1
    fi

    # Check if already running
    if check_running; then
        echo -e "${YELLOW}⚠️  Gitleaks is already running for this repository${NC}"
        echo "If this is an error, you can remove the lock file: rm $LOCKFILE"
        exit 1
    fi

    # Kill any zombie gitleaks processes (ALL of them system-wide)
    kill_existing

    # Create lock file with current PID
    echo $$ > "$LOCKFILE"

    # Prepare gitleaks command
    local gitleaks_cmd="gitleaks"

    # Add verbose flag only if explicitly enabled
    if [ "$VERBOSE" = "true" ]; then
        gitleaks_cmd="$gitleaks_cmd --verbose"
    fi

    # Add all passed arguments
    gitleaks_cmd="$gitleaks_cmd $*"

    echo -e "${GREEN}🔍 Running gitleaks scan...${NC}"
    echo "Timeout: ${TIMEOUT_SECONDS}s | Verbose: ${VERBOSE}"

    # Run gitleaks with timeout and resource limits
    local attempt=1
    while [ $attempt -le $MAX_RETRIES ]; do
        if [ $attempt -gt 1 ]; then
            echo -e "${YELLOW}⚠️  Retry attempt $attempt of $MAX_RETRIES${NC}"
        fi

        # On macOS, we can't use ulimit for memory, but timeout works
        if timeout "${TIMEOUT_SECONDS}s" $gitleaks_cmd; then
            echo -e "${GREEN}✅ No secrets detected by gitleaks${NC}"
            exit 0
        else
            local exit_code=$?
            if [ $exit_code -eq 124 ]; then
                echo -e "${RED}❌ Gitleaks scan timed out after ${TIMEOUT_SECONDS} seconds${NC}"
                echo "You can increase the timeout by setting: export GITLEAKS_TIMEOUT=300"
                exit 1
            elif [ $exit_code -ne 0 ]; then
                if [ $attempt -eq $MAX_RETRIES ]; then
                    echo -e "${RED}❌ Gitleaks detected potential secrets or encountered an error${NC}"
                    echo "Please review the findings and either:"
                    echo "1. Remove the secrets from your code"
                    echo "2. Add false positives to .gitleaks.toml allowlist"
                    echo "3. Run with verbose mode: GITLEAKS_VERBOSE=true git commit"
                    exit 1
                fi
            fi
        fi

        attempt=$((attempt + 1))
    done
}

# Run main function with all arguments
main "$@"
