#!/bin/bash
# gitleaks-safe-v2.sh - Enhanced memory-safe wrapper for gitleaks with multi-instance support
#
# Features:
# - Supports multiple concurrent safe instances across different projects
# - Only kills unsafe gitleaks processes (not spawned by this script)
# - Detects gitleaks running in Docker containers
# - Identifies multiple gitleaks installations
# - Uses unique process markers for identification
#
# Usage: ./gitleaks-safe-v2.sh [gitleaks arguments]

set -euo pipefail

# Configuration
SCRIPT_NAME="gitleaks-safe"
SAFE_MARKER="GITLEAKS_SAFE_INSTANCE"  # Environment variable to mark safe processes
SESSION_ID="$(date +%s)-$$-$(echo "$PWD" | md5sum | cut -c1-8)"  # Unique session ID
LOCKFILE="${TMPDIR:-/tmp}/${SCRIPT_NAME}-$(echo "$PWD" | md5sum | cut -c1-32).lock"
TIMEOUT_SECONDS=${GITLEAKS_TIMEOUT:-120}  # 2 minutes default
MAX_RETRIES=${GITLEAKS_RETRIES:-1}       # No retries by default
VERBOSE=${GITLEAKS_VERBOSE:-false}       # Verbose mode off by default

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Cleanup function
cleanup() {
    local exit_code=$?
    rm -f "$LOCKFILE"
    exit $exit_code
}

# Set up trap for cleanup
trap cleanup EXIT INT TERM

# Function to get MD5 hash (cross-platform)
get_md5() {
    if command -v md5sum &> /dev/null; then
        echo "$1" | md5sum | cut -c1-32
    elif command -v md5 &> /dev/null; then
        echo "$1" | md5 | cut -c1-32
    else
        # Fallback to simple hash
        echo "$1" | cksum | cut -c1-32
    fi
}

# Function to check if a process is a safe instance
is_safe_process() {
    local pid=$1
    # Check if process has our safe marker in environment
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS: Use ps with environment variables
        ps -p "$pid" -E 2>/dev/null | grep -q "$SAFE_MARKER" && return 0
    else
        # Linux: Check /proc/PID/environ
        if [ -f "/proc/$pid/environ" ]; then
            grep -q "$SAFE_MARKER" "/proc/$pid/environ" 2>/dev/null && return 0
        fi
    fi
    return 1
}

# Function to find all gitleaks installations
find_gitleaks_installations() {
    echo -e "${BLUE}🔍 Scanning for gitleaks installations...${NC}"

    local installations=()

    # Check PATH
    local path_gitleaks=$(which gitleaks 2>/dev/null || true)
    if [ -n "$path_gitleaks" ]; then
        installations+=("$path_gitleaks")
    fi

    # Common installation locations
    local common_paths=(
        "/usr/local/bin/gitleaks"
        "/usr/bin/gitleaks"
        "/opt/homebrew/bin/gitleaks"
        "/home/linuxbrew/.linuxbrew/bin/gitleaks"
        "$HOME/.local/bin/gitleaks"
        "$HOME/go/bin/gitleaks"
        "/snap/bin/gitleaks"
    )

    for path in "${common_paths[@]}"; do
        if [ -f "$path" ] && [ -x "$path" ]; then
            installations+=("$path")
        fi
    done

    # Remove duplicates
    local unique_installations=($(printf "%s\n" "${installations[@]}" | sort -u))

    if [ ${#unique_installations[@]} -gt 0 ]; then
        echo -e "${CYAN}Found ${#unique_installations[@]} gitleaks installation(s):${NC}"
        for inst in "${unique_installations[@]}"; do
            local version=$("$inst" version 2>/dev/null || echo "unknown")
            echo "  - $inst (version: $version)"
        done
    fi
}

# Function to check Docker containers for gitleaks
check_docker_containers() {
    if ! command -v docker &> /dev/null; then
        return
    fi

    echo -e "${BLUE}🐳 Checking Docker containers for gitleaks processes...${NC}"

    # Get list of running containers
    local containers=$(docker ps -q 2>/dev/null || true)
    if [ -z "$containers" ]; then
        echo "  No running containers found"
        return
    fi

    local found_in_containers=false
    for container in $containers; do
        local container_name=$(docker inspect -f '{{.Name}}' "$container" | sed 's/^\/*//')

        # Check for gitleaks processes in container
        local gitleaks_pids=$(docker exec "$container" pgrep -f "gitleaks" 2>/dev/null || true)

        if [ -n "$gitleaks_pids" ]; then
            found_in_containers=true
            echo -e "${YELLOW}  ⚠️  Found gitleaks in container: $container_name${NC}"

            # Show process details
            docker exec "$container" ps -p "$gitleaks_pids" -o pid,pcpu,pmem,etime,command 2>/dev/null || true

            # Kill processes in container
            echo -e "${YELLOW}  Killing gitleaks processes in container $container_name...${NC}"
            echo "$gitleaks_pids" | xargs -I {} docker exec "$container" kill -TERM {} 2>/dev/null || true
        fi
    done

    if [ "$found_in_containers" = false ]; then
        echo "  No gitleaks processes found in containers"
    fi
}

# Enhanced function to kill only unsafe gitleaks processes
kill_unsafe_processes() {
    echo -e "${BLUE}🔍 Scanning for unsafe gitleaks processes...${NC}"

    # Get all gitleaks processes with detailed info
    local all_pids=$(pgrep -f "gitleaks" 2>/dev/null || true)

    if [ -z "$all_pids" ]; then
        echo -e "${GREEN}✅ No gitleaks processes found${NC}"
        return
    fi

    local safe_count=0
    local unsafe_count=0
    local unsafe_pids=()

    echo -e "${CYAN}Found processes:${NC}"
    for pid in $all_pids; do
        # Skip our own process
        if [ "$pid" -eq "$$" ]; then
            continue
        fi

        # Get process command line
        local cmd=$(ps -p "$pid" -o command= 2>/dev/null || echo "unknown")

        # Check if it's a safe process
        if is_safe_process "$pid"; then
            safe_count=$((safe_count + 1))
            echo -e "${GREEN}  ✅ PID $pid: SAFE (managed by gitleaks-safe) - $cmd${NC}"
        else
            unsafe_count=$((unsafe_count + 1))
            unsafe_pids+=("$pid")
            echo -e "${YELLOW}  ⚠️  PID $pid: UNSAFE - $cmd${NC}"

            # Show resource usage
            ps -p "$pid" -o pid,pcpu,pmem,etime 2>/dev/null || true
        fi
    done

    echo -e "\n${CYAN}Summary: $safe_count safe, $unsafe_count unsafe processes${NC}"

    # Kill only unsafe processes
    if [ ${#unsafe_pids[@]} -gt 0 ]; then
        echo -e "${YELLOW}⚠️  Terminating ${#unsafe_pids[@]} unsafe gitleaks process(es)...${NC}"

        for pid in "${unsafe_pids[@]}"; do
            kill -TERM "$pid" 2>/dev/null || true
        done

        sleep 1

        # Force kill if still running
        for pid in "${unsafe_pids[@]}"; do
            if kill -0 "$pid" 2>/dev/null; then
                echo -e "${YELLOW}  Force killing PID $pid...${NC}"
                kill -KILL "$pid" 2>/dev/null || true
            fi
        done

        echo -e "${GREEN}✅ Cleaned up unsafe gitleaks processes${NC}"
    else
        echo -e "${GREEN}✅ No unsafe processes to clean up${NC}"
    fi
}

# Function to check if gitleaks is already running for this directory
check_running() {
    if [ -f "$LOCKFILE" ]; then
        local pid=$(cat "$LOCKFILE" 2>/dev/null || echo "")
        if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
            # Check if it's actually a gitleaks-safe process
            if is_safe_process "$pid"; then
                return 0  # Already running
            else
                # Not a safe process, remove stale lock
                rm -f "$LOCKFILE"
            fi
        else
            # Stale lock file, remove it
            rm -f "$LOCKFILE"
        fi
    fi
    return 1  # Not running
}

# Main execution
main() {
    echo -e "${BLUE}🛡️  Gitleaks Safe Wrapper v2.0${NC}"
    echo -e "${CYAN}Session ID: $SESSION_ID${NC}"
    echo -e "${CYAN}Project: $PWD${NC}\n"

    # Find all gitleaks installations
    find_gitleaks_installations
    echo ""

    # Check if gitleaks is installed
    if ! command -v gitleaks &> /dev/null; then
        echo -e "${RED}❌ gitleaks is not installed in PATH${NC}"
        echo "Please install it using one of these methods:"
        echo ""
        echo "macOS:        brew install gitleaks"
        echo "Ubuntu/Debian: sudo snap install gitleaks"
        echo "Fedora:       sudo dnf install gitleaks"
        echo "Arch:         yay -S gitleaks"
        echo "Windows:      scoop install gitleaks"
        echo ""
        exit 1
    fi

    # Check if already running for this directory
    if check_running; then
        echo -e "${YELLOW}⚠️  A safe gitleaks instance is already running for this repository${NC}"
        echo "Lock file: $LOCKFILE"
        echo "If this is an error, remove the lock file and try again"
        exit 1
    fi

    # Kill unsafe gitleaks processes
    kill_unsafe_processes
    echo ""

    # Check Docker containers
    check_docker_containers
    echo ""

    # Create lock file with current PID
    echo $$ > "$LOCKFILE"

    # Prepare gitleaks command with our safe marker
    local gitleaks_cmd="env $SAFE_MARKER=$SESSION_ID gitleaks"

    # Add verbose flag if enabled
    if [ "$VERBOSE" = "true" ]; then
        gitleaks_cmd="$gitleaks_cmd --verbose"
    fi

    # Add all passed arguments
    gitleaks_cmd="$gitleaks_cmd $*"

    echo -e "${GREEN}🔍 Running safe gitleaks scan...${NC}"
    echo "Timeout: ${TIMEOUT_SECONDS}s | Verbose: ${VERBOSE}"
    echo "Command: $gitleaks_cmd"
    echo ""

    # Run gitleaks with timeout and our safe marker
    local attempt=1
    while [ $attempt -le $MAX_RETRIES ]; do
        if [ $attempt -gt 1 ]; then
            echo -e "${YELLOW}⚠️  Retry attempt $attempt of $MAX_RETRIES${NC}"
        fi

        # Run with timeout and safe marker
        if timeout "${TIMEOUT_SECONDS}s" bash -c "$gitleaks_cmd"; then
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
                    echo "Exit code: $exit_code"
                    echo ""
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
