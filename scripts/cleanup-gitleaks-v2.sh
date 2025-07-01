#!/bin/bash
# cleanup-gitleaks-v2.sh - Enhanced cleanup utility for unsafe gitleaks processes
#
# This script identifies and kills only unsafe gitleaks processes,
# preserving those managed by gitleaks-safe wrapper.

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

SAFE_MARKER="GITLEAKS_SAFE_INSTANCE"

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
    echo -e "${BLUE}📍 Gitleaks Installations Found:${NC}"

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
        "$HOME/.cargo/bin/gitleaks"
        "/opt/gitleaks/bin/gitleaks"
    )

    # Also check node_modules in current and parent directories
    local node_paths=(
        "./node_modules/.bin/gitleaks"
        "../node_modules/.bin/gitleaks"
        "../../node_modules/.bin/gitleaks"
    )

    for path in "${common_paths[@]}" "${node_paths[@]}"; do
        if [ -f "$path" ] && [ -x "$path" ]; then
            installations+=("$path")
        fi
    done

    # Remove duplicates
    local unique_installations=($(printf "%s\n" "${installations[@]}" | sort -u))

    if [ ${#unique_installations[@]} -gt 0 ]; then
        for inst in "${unique_installations[@]}"; do
            local version=$("$inst" version 2>/dev/null || echo "unknown")
            local size=$(ls -lh "$inst" 2>/dev/null | awk '{print $5}' || echo "unknown")
            echo -e "  ${CYAN}$inst${NC}"
            echo "    Version: $version | Size: $size"
        done
    else
        echo "  No gitleaks installations found"
    fi
    echo ""
}

# Function to check Docker containers
check_docker_containers() {
    if ! command -v docker &> /dev/null; then
        return
    fi

    echo -e "${BLUE}🐳 Checking Docker Containers:${NC}"

    local containers=$(docker ps -q 2>/dev/null || true)
    if [ -z "$containers" ]; then
        echo "  No running containers"
        return
    fi

    local total_found=0
    for container in $containers; do
        local container_name=$(docker inspect -f '{{.Name}}' "$container" | sed 's/^\/*//')
        local gitleaks_pids=$(docker exec "$container" pgrep -f "gitleaks" 2>/dev/null || true)

        if [ -n "$gitleaks_pids" ]; then
            local count=$(echo "$gitleaks_pids" | wc -l | tr -d ' ')
            total_found=$((total_found + count))
            echo -e "  ${YELLOW}Container: $container_name - $count process(es)${NC}"
        fi
    done

    if [ $total_found -eq 0 ]; then
        echo -e "  ${GREEN}No gitleaks processes in containers${NC}"
    fi
    echo ""
}

# Main function
main() {
    echo -e "${BLUE}🧹 Gitleaks Process Cleanup Utility v2.0${NC}"
    echo -e "${CYAN}Smart cleanup that preserves safe instances${NC}\n"

    # Find installations
    find_gitleaks_installations

    # Check Docker
    check_docker_containers

    # Check for existing gitleaks processes
    echo -e "${BLUE}📊 Process Analysis:${NC}"

    local all_pids=$(pgrep -f "gitleaks" 2>/dev/null || true)

    if [ -z "$all_pids" ]; then
        echo -e "${GREEN}✅ No gitleaks processes found running${NC}"
        exit 0
    fi

    # Analyze processes
    local safe_pids=()
    local unsafe_pids=()
    local safe_details=""
    local unsafe_details=""

    for pid in $all_pids; do
        # Skip our own process
        if [ "$pid" -eq "$$" ]; then
            continue
        fi

        # Get process details
        local cmd=$(ps -p "$pid" -o command= 2>/dev/null || echo "unknown")
        local stats=$(ps -p "$pid" -o pid,pcpu,pmem,etime 2>/dev/null | tail -n 1)

        if is_safe_process "$pid"; then
            safe_pids+=("$pid")
            safe_details+="  ${GREEN}✅ SAFE: $stats${NC}\n"
            safe_details+="     Command: $cmd\n"
        else
            unsafe_pids+=("$pid")
            unsafe_details+="  ${YELLOW}⚠️  UNSAFE: $stats${NC}\n"
            unsafe_details+="     Command: $cmd\n"
        fi
    done

    # Display results
    echo -e "\n${CYAN}Safe Processes (${#safe_pids[@]}):${NC}"
    if [ ${#safe_pids[@]} -gt 0 ]; then
        echo -e "$safe_details"
    else
        echo "  None"
    fi

    echo -e "\n${YELLOW}Unsafe Processes (${#unsafe_pids[@]}):${NC}"
    if [ ${#unsafe_pids[@]} -gt 0 ]; then
        echo -e "$unsafe_details"

        # Calculate total memory for unsafe processes
        local total_mem=0
        for pid in "${unsafe_pids[@]}"; do
            local mem=$(ps -p "$pid" -o pmem= 2>/dev/null || echo "0")
            total_mem=$(echo "$total_mem + $mem" | bc)
        done
        echo -e "\n${YELLOW}Total memory usage by unsafe processes: ${total_mem}%${NC}"
    else
        echo "  None"
    fi

    # Ask for confirmation only if there are unsafe processes
    if [ ${#unsafe_pids[@]} -gt 0 ]; then
        echo ""
        read -p "Do you want to terminate ${#unsafe_pids[@]} UNSAFE gitleaks process(es)? (y/N) " -n 1 -r
        echo

        if [[ $REPLY =~ ^[Yy]$ ]]; then
            echo -e "\n${YELLOW}Terminating unsafe processes...${NC}"

            # Kill unsafe processes
            for pid in "${unsafe_pids[@]}"; do
                echo -e "  Killing PID $pid..."
                kill -TERM "$pid" 2>/dev/null || true
            done

            sleep 2

            # Force kill if needed
            for pid in "${unsafe_pids[@]}"; do
                if kill -0 "$pid" 2>/dev/null; then
                    echo -e "  ${YELLOW}Force killing PID $pid...${NC}"
                    kill -KILL "$pid" 2>/dev/null || true
                fi
            done

            echo -e "${GREEN}✅ Successfully terminated unsafe processes${NC}"

            # Clean up lock files
            echo -e "\n${BLUE}Cleaning up orphaned lock files...${NC}"
            local lock_files=$(find /tmp -name "gitleaks-safe-*.lock" 2>/dev/null || true)
            if [ -n "$lock_files" ]; then
                local orphaned=0
                while IFS= read -r lockfile; do
                    if [ -f "$lockfile" ]; then
                        local lock_pid=$(cat "$lockfile" 2>/dev/null || echo "")
                        if [ -n "$lock_pid" ] && ! kill -0 "$lock_pid" 2>/dev/null; then
                            rm -f "$lockfile"
                            orphaned=$((orphaned + 1))
                        fi
                    fi
                done <<< "$lock_files"
                echo -e "${GREEN}✅ Cleaned up $orphaned orphaned lock file(s)${NC}"
            fi
        else
            echo -e "${BLUE}Cancelled. No processes were terminated.${NC}"
        fi
    else
        echo -e "\n${GREEN}✅ All running gitleaks processes are safe instances${NC}"
        echo "No cleanup needed."
    fi

    # Docker cleanup offer
    if command -v docker &> /dev/null; then
        local docker_pids=$(docker ps -q | xargs -I {} docker exec {} pgrep -f "gitleaks" 2>/dev/null | wc -l | tr -d ' ')
        if [ "$docker_pids" -gt 0 ]; then
            echo ""
            read -p "Also clean up gitleaks in Docker containers? (y/N) " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                for container in $(docker ps -q); do
                    local container_name=$(docker inspect -f '{{.Name}}' "$container" | sed 's/^\/*//')
                    local pids=$(docker exec "$container" pgrep -f "gitleaks" 2>/dev/null || true)
                    if [ -n "$pids" ]; then
                        echo -e "  Cleaning container: $container_name"
                        echo "$pids" | xargs -I {} docker exec "$container" kill -TERM {} 2>/dev/null || true
                    fi
                done
                echo -e "${GREEN}✅ Docker containers cleaned${NC}"
            fi
        fi
    fi

    echo -e "\n${BLUE}💡 Tips:${NC}"
    echo "- Use gitleaks-safe-v2.sh to run gitleaks safely"
    echo "- Safe instances can run concurrently across multiple projects"
    echo "- Set GITLEAKS_TIMEOUT to increase scan timeout"
}

# Run main
main
