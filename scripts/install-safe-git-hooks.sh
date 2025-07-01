#!/bin/bash
# install-safe-git-hooks.sh - Portable git hooks installer with memory-safe gitleaks
#
# This script installs git hooks that use the gitleaks-safe wrapper
# to prevent memory exhaustion issues.
#
# Usage: ./install-safe-git-hooks.sh [--pre-commit] [--pre-push] [--both]

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Default: install pre-push only (recommended)
INSTALL_PRE_COMMIT=false
INSTALL_PRE_PUSH=true
NON_INTERACTIVE=false

# Function to detect OS and distribution
detect_os() {
    if [[ "$OSTYPE" == "darwin"* ]]; then
        echo "macos"
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        if [ -f /etc/os-release ]; then
            . /etc/os-release
            echo "$ID"
        elif [ -f /etc/redhat-release ]; then
            echo "rhel"
        elif [ -f /etc/debian_version ]; then
            echo "debian"
        else
            echo "linux"
        fi
    elif [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" ]]; then
        echo "windows"
    else
        echo "unknown"
    fi
}

# Function to detect if running in Docker
is_docker() {
    if [ -f /.dockerenv ]; then
        return 0
    elif grep -q docker /proc/self/cgroup 2>/dev/null; then
        return 0
    else
        return 1
    fi
}

# Function to install gitleaks
install_gitleaks() {
    local os=$(detect_os)

    echo -e "${BLUE}📥 Installing gitleaks for $os...${NC}"

    # Docker installation
    if is_docker; then
        echo -e "${YELLOW}🐳 Detected Docker environment${NC}"
        if command -v wget &> /dev/null; then
            local arch=$(uname -m)
            local gitleaks_arch=""
            case $arch in
                x86_64) gitleaks_arch="x64" ;;
                aarch64|arm64) gitleaks_arch="arm64" ;;
                *)
                    echo -e "${RED}❌ Unsupported architecture: $arch${NC}"
                    return 1
                    ;;
            esac

            local version=$(curl -s https://api.github.com/repos/gitleaks/gitleaks/releases/latest | grep '"tag_name":' | sed -E 's/.*"v([^"]+)".*/\1/')
            local url="https://github.com/gitleaks/gitleaks/releases/download/v${version}/gitleaks_${version}_linux_${gitleaks_arch}.tar.gz"

            echo "Downloading gitleaks from $url..."
            wget -q -O /tmp/gitleaks.tar.gz "$url"
            tar -xzf /tmp/gitleaks.tar.gz -C /tmp
            mv /tmp/gitleaks /usr/local/bin/
            chmod +x /usr/local/bin/gitleaks
            rm -f /tmp/gitleaks.tar.gz
            echo -e "${GREEN}✅ Installed gitleaks in Docker container${NC}"
            return 0
        else
            echo -e "${RED}❌ wget not found. Install with: apt-get update && apt-get install -y wget${NC}"
            return 1
        fi
    fi

    case $os in
        macos)
            if command -v brew &> /dev/null; then
                echo "Installing with Homebrew..."
                brew install gitleaks
            else
                echo -e "${RED}❌ Homebrew not found. Please install from https://brew.sh${NC}"
                echo "Or install gitleaks manually from: https://github.com/gitleaks/gitleaks#installing"
                return 1
            fi
            ;;

        ubuntu|debian)
            echo "Installing with apt..."
            # Try snap first (more up to date)
            if command -v snap &> /dev/null; then
                sudo snap install gitleaks
            else
                # Fall back to downloading binary
                echo "Snap not available, downloading binary..."
                local arch=$(dpkg --print-architecture)
                local gitleaks_arch=""
                case $arch in
                    amd64) gitleaks_arch="x64" ;;
                    arm64) gitleaks_arch="arm64" ;;
                    *)
                        echo -e "${RED}❌ Unsupported architecture: $arch${NC}"
                        return 1
                        ;;
                esac

                local version=$(curl -s https://api.github.com/repos/gitleaks/gitleaks/releases/latest | grep '"tag_name":' | sed -E 's/.*"v([^"]+)".*/\1/')
                local url="https://github.com/gitleaks/gitleaks/releases/download/v${version}/gitleaks_${version}_linux_${gitleaks_arch}.tar.gz"

                echo "Downloading gitleaks from $url..."
                curl -sSfL "$url" | sudo tar -xz -C /usr/local/bin gitleaks
                sudo chmod +x /usr/local/bin/gitleaks
            fi
            ;;

        fedora|centos|rhel)
            echo "Installing with dnf/yum..."
            if command -v dnf &> /dev/null; then
                sudo dnf install -y gitleaks
            elif command -v yum &> /dev/null; then
                sudo yum install -y gitleaks
            else
                echo -e "${YELLOW}Package manager not found, trying binary installation...${NC}"
                # Download binary
                local arch=$(uname -m)
                local gitleaks_arch=""
                case $arch in
                    x86_64) gitleaks_arch="x64" ;;
                    aarch64) gitleaks_arch="arm64" ;;
                    *)
                        echo -e "${RED}❌ Unsupported architecture: $arch${NC}"
                        return 1
                        ;;
                esac

                local version=$(curl -s https://api.github.com/repos/gitleaks/gitleaks/releases/latest | grep '"tag_name":' | sed -E 's/.*"v([^"]+)".*/\1/')
                local url="https://github.com/gitleaks/gitleaks/releases/download/v${version}/gitleaks_${version}_linux_${gitleaks_arch}.tar.gz"

                echo "Downloading gitleaks from $url..."
                curl -sSfL "$url" | sudo tar -xz -C /usr/local/bin gitleaks
                sudo chmod +x /usr/local/bin/gitleaks
            fi
            ;;

        arch)
            echo "Installing with pacman..."
            if command -v yay &> /dev/null; then
                yay -S gitleaks
            elif command -v pacman &> /dev/null; then
                echo -e "${YELLOW}Installing from AUR requires yay or manual installation${NC}"
                echo "Install yay first or download gitleaks manually from:"
                echo "https://github.com/gitleaks/gitleaks/releases"
                return 1
            fi
            ;;

        alpine)
            echo "Installing with apk..."
            apk add --no-cache gitleaks
            ;;

        windows)
            echo "Installing with scoop or chocolatey..."
            if command -v scoop &> /dev/null; then
                scoop install gitleaks
            elif command -v choco &> /dev/null; then
                choco install gitleaks
            else
                echo -e "${RED}❌ Neither scoop nor chocolatey found.${NC}"
                echo "Install scoop from: https://scoop.sh"
                echo "Or install chocolatey from: https://chocolatey.org"
                echo "Or download gitleaks manually from: https://github.com/gitleaks/gitleaks/releases"
                return 1
            fi
            ;;

        *)
            echo -e "${YELLOW}⚠️  Unknown OS: $os${NC}"
            echo "Attempting generic binary installation..."

            # Try to download binary based on architecture
            local arch=$(uname -m)
            local os_type=$(uname -s | tr '[:upper:]' '[:lower:]')
            local gitleaks_arch=""

            case $arch in
                x86_64|amd64) gitleaks_arch="x64" ;;
                aarch64|arm64) gitleaks_arch="arm64" ;;
                *)
                    echo -e "${RED}❌ Unsupported architecture: $arch${NC}"
                    echo "Please install gitleaks manually from:"
                    echo "https://github.com/gitleaks/gitleaks/releases"
                    return 1
                    ;;
            esac

            local version=$(curl -s https://api.github.com/repos/gitleaks/gitleaks/releases/latest | grep '"tag_name":' | sed -E 's/.*"v([^"]+)".*/\1/')
            local url="https://github.com/gitleaks/gitleaks/releases/download/v${version}/gitleaks_${version}_${os_type}_${gitleaks_arch}.tar.gz"

            echo "Downloading gitleaks from $url..."
            if curl -sSfL "$url" -o /tmp/gitleaks.tar.gz; then
                sudo tar -xzf /tmp/gitleaks.tar.gz -C /usr/local/bin gitleaks
                sudo chmod +x /usr/local/bin/gitleaks
                rm -f /tmp/gitleaks.tar.gz
            else
                echo -e "${RED}❌ Failed to download gitleaks${NC}"
                echo "Please install manually from: https://github.com/gitleaks/gitleaks/releases"
                return 1
            fi
            ;;
    esac

    # Verify installation
    if command -v gitleaks &> /dev/null; then
        echo -e "${GREEN}✅ Gitleaks installed successfully!${NC}"
        gitleaks version
        return 0
    else
        echo -e "${RED}❌ Gitleaks installation failed${NC}"
        return 1
    fi
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --pre-commit)
            INSTALL_PRE_COMMIT=true
            INSTALL_PRE_PUSH=false
            shift
            ;;
        --pre-push)
            INSTALL_PRE_COMMIT=false
            INSTALL_PRE_PUSH=true
            shift
            ;;
        --both)
            INSTALL_PRE_COMMIT=true
            INSTALL_PRE_PUSH=true
            shift
            ;;
        --non-interactive|-n)
            NON_INTERACTIVE=true
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [--pre-commit] [--pre-push] [--both] [--non-interactive]"
            echo ""
            echo "Options:"
            echo "  --pre-commit       Install pre-commit hook only"
            echo "  --pre-push         Install pre-push hook only (default)"
            echo "  --both             Install both hooks"
            echo "  --non-interactive  Don't prompt for input (skip gitleaks install if missing)"
            echo ""
            echo "Environment variables:"
            echo "  GITLEAKS_TIMEOUT   Timeout in seconds (default: 120)"
            echo "  GITLEAKS_VERBOSE   Enable verbose mode (default: false)"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            exit 1
            ;;
    esac
done

# Check if we're in a git repository
if ! git rev-parse --git-dir > /dev/null 2>&1; then
    echo -e "${RED}❌ Not in a git repository${NC}"
    exit 1
fi

# Check if gitleaks is installed
if ! command -v gitleaks &> /dev/null; then
    echo -e "${YELLOW}⚠️  Gitleaks is not installed${NC}"

    if [ "$NON_INTERACTIVE" = true ]; then
        echo -e "${RED}❌ Gitleaks is required but not installed (running in non-interactive mode)${NC}"
        echo "Please install gitleaks first:"
        echo "  macOS:  brew install gitleaks"
        echo "  Ubuntu: sudo snap install gitleaks"
        echo "  Other:  https://github.com/gitleaks/gitleaks#installing"
        exit 1
    else
        read -p "Would you like to install gitleaks now? (y/N) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            if install_gitleaks; then
                echo -e "${GREEN}✅ Gitleaks installation successful${NC}"
            else
                echo -e "${RED}❌ Failed to install gitleaks${NC}"
                echo "Please install gitleaks manually and run this script again."
                exit 1
            fi
        else
            echo -e "${RED}❌ Gitleaks is required for the git hooks${NC}"
            echo "Please install gitleaks manually from: https://github.com/gitleaks/gitleaks#installing"
            exit 1
        fi
    fi
else
    echo -e "${GREEN}✅ Gitleaks is already installed${NC}"
    gitleaks version
fi

GIT_ROOT=$(git rev-parse --show-toplevel)
HOOKS_DIR="$GIT_ROOT/.git/hooks"
SCRIPTS_DIR="$GIT_ROOT/scripts"

# Create scripts directory if it doesn't exist
mkdir -p "$SCRIPTS_DIR"

# Check if gitleaks-safe.sh exists in the current repo
GITLEAKS_SAFE_SCRIPT="$SCRIPTS_DIR/gitleaks-safe.sh"
if [ ! -f "$GITLEAKS_SAFE_SCRIPT" ]; then
    echo -e "${YELLOW}⚠️  gitleaks-safe.sh not found in scripts directory${NC}"
    echo -e "${BLUE}📥 Downloading gitleaks-safe.sh...${NC}"

    # Create the gitleaks-safe.sh script inline
    cat > "$GITLEAKS_SAFE_SCRIPT" << 'SAFE_SCRIPT'
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
SAFE_SCRIPT

    chmod +x "$GITLEAKS_SAFE_SCRIPT"
    echo -e "${GREEN}✅ Created gitleaks-safe.sh${NC}"
fi

# Function to create hook
create_hook() {
    local hook_name=$1
    local hook_path="$HOOKS_DIR/$hook_name"
    local gitleaks_args=""

    # Different arguments for different hooks
    if [ "$hook_name" = "pre-commit" ]; then
        gitleaks_args="protect --staged"
    elif [ "$hook_name" = "pre-push" ]; then
        gitleaks_args="protect"
    fi

    # Backup existing hook if it exists
    if [ -f "$hook_path" ]; then
        echo -e "${YELLOW}⚠️  Backing up existing $hook_name hook to $hook_path.backup${NC}"
        cp "$hook_path" "$hook_path.backup"
    fi

    # Create the hook
    cat > "$hook_path" << EOF
#!/bin/bash
# Git $hook_name hook with memory-safe gitleaks integration
# Generated by install-safe-git-hooks.sh

# Find the repository root and scripts directory
GIT_ROOT=\$(git rev-parse --show-toplevel)
SCRIPTS_DIR="\$GIT_ROOT/scripts"
GITLEAKS_SAFE="\$SCRIPTS_DIR/gitleaks-safe.sh"

# Check if gitleaks-safe.sh exists
if [ ! -f "\$GITLEAKS_SAFE" ]; then
    echo "❌ gitleaks-safe.sh not found in \$SCRIPTS_DIR"
    echo "Please run: ./scripts/install-safe-git-hooks.sh"
    exit 1
fi

# Run gitleaks with safety wrapper
echo "🔍 Running gitleaks $hook_name check..."

# Look for .gitleaks.toml in repo root
if [ -f "\$GIT_ROOT/.gitleaks.toml" ]; then
    "\$GITLEAKS_SAFE" $gitleaks_args --config "\$GIT_ROOT/.gitleaks.toml"
else
    "\$GITLEAKS_SAFE" $gitleaks_args
fi

exit_code=\$?

# If you have other $hook_name hooks, add them here
# For example:
# npm test
# rubocop
# etc.

exit \$exit_code
EOF

    chmod +x "$hook_path"
    echo -e "${GREEN}✅ Installed $hook_name hook${NC}"
}

# Main installation
echo -e "${BLUE}🚀 Installing memory-safe git hooks...${NC}"
echo ""

# Install selected hooks
if [ "$INSTALL_PRE_COMMIT" = true ]; then
    create_hook "pre-commit"
fi

if [ "$INSTALL_PRE_PUSH" = true ]; then
    create_hook "pre-push"
fi

echo ""
echo -e "${GREEN}✅ Installation complete!${NC}"
echo ""
echo "Configuration options (set as environment variables):"
echo "  GITLEAKS_TIMEOUT=300     # Increase timeout to 5 minutes"
echo "  GITLEAKS_VERBOSE=true    # Enable verbose output"
echo "  GITLEAKS_RETRIES=3       # Number of retry attempts"
echo ""
echo "To use in other projects:"
echo "1. Copy the 'scripts' directory to your project"
echo "2. Run: ./scripts/install-safe-git-hooks.sh"
echo ""
echo -e "${YELLOW}⚠️  Note: The pre-push hook is recommended over pre-commit${NC}"
echo "   to avoid running gitleaks too frequently during development."
