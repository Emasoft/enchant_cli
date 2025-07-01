#!/bin/bash
# install-safe-git-hooks-v2.sh - Enhanced installer with multi-instance support
#
# This script installs git hooks that use the enhanced gitleaks-safe wrapper
# which supports multiple concurrent instances across different projects.

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Default: install pre-push only (recommended)
INSTALL_PRE_COMMIT=false
INSTALL_PRE_PUSH=true
NON_INTERACTIVE=false
USE_V2=true  # Use v2 by default

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
        install_gitleaks_docker
        return
    fi

    case $os in
        macos)
            install_gitleaks_macos
            ;;
        ubuntu|debian)
            install_gitleaks_debian
            ;;
        fedora|centos|rhel)
            install_gitleaks_redhat
            ;;
        arch)
            install_gitleaks_arch
            ;;
        alpine)
            install_gitleaks_alpine
            ;;
        windows)
            install_gitleaks_windows
            ;;
        *)
            install_gitleaks_generic
            ;;
    esac
}

# Platform-specific installation functions
install_gitleaks_macos() {
    if command -v brew &> /dev/null; then
        echo "Installing with Homebrew..."
        brew install gitleaks
    else
        echo -e "${RED}❌ Homebrew not found${NC}"
        echo "Install Homebrew from https://brew.sh or use binary installation"
        install_gitleaks_binary "darwin" "x64"
    fi
}

install_gitleaks_debian() {
    echo "Installing for Debian/Ubuntu..."
    if command -v snap &> /dev/null; then
        sudo snap install gitleaks
    else
        echo "Snap not available, using binary installation..."
        local arch=$(dpkg --print-architecture)
        case $arch in
            amd64) install_gitleaks_binary "linux" "x64" ;;
            arm64) install_gitleaks_binary "linux" "arm64" ;;
            *) echo -e "${RED}Unsupported architecture: $arch${NC}"; return 1 ;;
        esac
    fi
}

install_gitleaks_redhat() {
    echo "Installing for RedHat/Fedora/CentOS..."
    if command -v dnf &> /dev/null; then
        sudo dnf install -y gitleaks
    elif command -v yum &> /dev/null; then
        sudo yum install -y gitleaks
    else
        echo "Package manager not found, using binary installation..."
        install_gitleaks_binary "linux" "x64"
    fi
}

install_gitleaks_arch() {
    echo "Installing for Arch Linux..."
    if command -v yay &> /dev/null; then
        yay -S gitleaks
    elif command -v paru &> /dev/null; then
        paru -S gitleaks
    else
        echo -e "${YELLOW}AUR helper not found, using binary installation...${NC}"
        install_gitleaks_binary "linux" "x64"
    fi
}

install_gitleaks_alpine() {
    echo "Installing for Alpine Linux..."
    apk add --no-cache gitleaks
}

install_gitleaks_windows() {
    echo "Installing for Windows..."
    if command -v scoop &> /dev/null; then
        scoop install gitleaks
    elif command -v choco &> /dev/null; then
        choco install gitleaks
    else
        echo -e "${RED}Package manager not found${NC}"
        echo "Install scoop from https://scoop.sh or chocolatey from https://chocolatey.org"
        return 1
    fi
}

install_gitleaks_docker() {
    echo "Installing in Docker container..."
    local arch=$(uname -m)
    case $arch in
        x86_64) install_gitleaks_binary "linux" "x64" ;;
        aarch64|arm64) install_gitleaks_binary "linux" "arm64" ;;
        *) echo -e "${RED}Unsupported architecture: $arch${NC}"; return 1 ;;
    esac
}

install_gitleaks_generic() {
    echo "Attempting generic installation..."
    local os_type=$(uname -s | tr '[:upper:]' '[:lower:]')
    local arch=$(uname -m)

    case $arch in
        x86_64|amd64) arch="x64" ;;
        aarch64|arm64) arch="arm64" ;;
        *) echo -e "${RED}Unsupported architecture: $arch${NC}"; return 1 ;;
    esac

    install_gitleaks_binary "$os_type" "$arch"
}

# Function to install gitleaks from binary
install_gitleaks_binary() {
    local os=$1
    local arch=$2

    echo "Downloading gitleaks binary for $os/$arch..."

    # Get latest version
    local version=$(curl -s https://api.github.com/repos/gitleaks/gitleaks/releases/latest | grep '"tag_name":' | sed -E 's/.*"v([^"]+)".*/\1/')
    if [ -z "$version" ]; then
        echo -e "${RED}Failed to get latest version${NC}"
        return 1
    fi

    local url="https://github.com/gitleaks/gitleaks/releases/download/v${version}/gitleaks_${version}_${os}_${arch}.tar.gz"
    local install_dir="/usr/local/bin"

    # Check if we need sudo
    local sudo_cmd=""
    if [ ! -w "$install_dir" ]; then
        sudo_cmd="sudo"
    fi

    echo "Downloading from: $url"

    # Download and install
    if command -v curl &> /dev/null; then
        curl -sSfL "$url" | $sudo_cmd tar -xz -C "$install_dir" gitleaks
    elif command -v wget &> /dev/null; then
        wget -qO- "$url" | $sudo_cmd tar -xz -C "$install_dir" gitleaks
    else
        echo -e "${RED}Neither curl nor wget found${NC}"
        return 1
    fi

    $sudo_cmd chmod +x "$install_dir/gitleaks"
    echo -e "${GREEN}✅ Installed gitleaks to $install_dir/gitleaks${NC}"
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
        --v1)
            USE_V2=false
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [options]"
            echo ""
            echo "Options:"
            echo "  --pre-commit       Install pre-commit hook only"
            echo "  --pre-push         Install pre-push hook only (default)"
            echo "  --both             Install both hooks"
            echo "  --non-interactive  Don't prompt for input"
            echo "  --v1               Use v1 wrapper (single instance)"
            echo ""
            echo "Environment variables:"
            echo "  GITLEAKS_TIMEOUT   Timeout in seconds (default: 120)"
            echo "  GITLEAKS_VERBOSE   Enable verbose mode (default: false)"
            echo ""
            echo "Features of v2 (default):"
            echo "  - Supports multiple concurrent instances"
            echo "  - Only kills unsafe gitleaks processes"
            echo "  - Detects Docker container processes"
            echo "  - Shows all gitleaks installations"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            exit 1
            ;;
    esac
done

# Determine which wrapper to use
WRAPPER_SCRIPT="gitleaks-safe-v2.sh"
if [ "$USE_V2" = false ]; then
    WRAPPER_SCRIPT="gitleaks-safe.sh"
fi

echo -e "${BLUE}🚀 Installing Git Hooks with Gitleaks Safe Wrapper${NC}"
echo -e "${CYAN}Using: $WRAPPER_SCRIPT${NC}\n"

# Check if we're in a git repository
if ! git rev-parse --git-dir > /dev/null 2>&1; then
    echo -e "${RED}❌ Not in a git repository${NC}"
    exit 1
fi

# Check if gitleaks is installed
if ! command -v gitleaks &> /dev/null; then
    echo -e "${YELLOW}⚠️  Gitleaks is not installed${NC}"

    if [ "$NON_INTERACTIVE" = true ]; then
        echo -e "${BLUE}Installing gitleaks automatically...${NC}"
        if install_gitleaks; then
            echo -e "${GREEN}✅ Gitleaks installation successful${NC}"
        else
            echo -e "${RED}❌ Failed to install gitleaks${NC}"
            exit 1
        fi
    else
        read -p "Would you like to install gitleaks now? (y/N) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            if install_gitleaks; then
                echo -e "${GREEN}✅ Gitleaks installation successful${NC}"
            else
                echo -e "${RED}❌ Failed to install gitleaks${NC}"
                exit 1
            fi
        else
            echo -e "${RED}❌ Gitleaks is required${NC}"
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

# Check if wrapper script exists
WRAPPER_PATH="$SCRIPTS_DIR/$WRAPPER_SCRIPT"
if [ ! -f "$WRAPPER_PATH" ]; then
    echo -e "${YELLOW}⚠️  $WRAPPER_SCRIPT not found${NC}"

    # Try to find it in the same directory as this installer
    INSTALLER_DIR=$(dirname "$0")
    if [ -f "$INSTALLER_DIR/$WRAPPER_SCRIPT" ]; then
        echo -e "${BLUE}Copying $WRAPPER_SCRIPT from installer directory...${NC}"
        cp "$INSTALLER_DIR/$WRAPPER_SCRIPT" "$WRAPPER_PATH"
        chmod +x "$WRAPPER_PATH"
    else
        echo -e "${RED}❌ Cannot find $WRAPPER_SCRIPT${NC}"
        echo "Please ensure $WRAPPER_SCRIPT is in the scripts directory"
        exit 1
    fi
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
        echo -e "${YELLOW}⚠️  Backing up existing $hook_name hook${NC}"
        cp "$hook_path" "$hook_path.backup-$(date +%Y%m%d-%H%M%S)"
    fi

    # Create the hook
    cat > "$hook_path" << EOF
#!/bin/bash
# Git $hook_name hook with memory-safe gitleaks integration
# Generated by install-safe-git-hooks-v2.sh
# Using wrapper: $WRAPPER_SCRIPT

# Find the repository root and scripts directory
GIT_ROOT=\$(git rev-parse --show-toplevel)
SCRIPTS_DIR="\$GIT_ROOT/scripts"
GITLEAKS_SAFE="\$SCRIPTS_DIR/$WRAPPER_SCRIPT"

# Check if wrapper exists
if [ ! -f "\$GITLEAKS_SAFE" ]; then
    echo "❌ $WRAPPER_SCRIPT not found in \$SCRIPTS_DIR"
    echo "Please run: ./scripts/install-safe-git-hooks-v2.sh"
    exit 1
fi

# Run gitleaks with safety wrapper
echo "🔍 Running gitleaks $hook_name check (safe mode)..."

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
echo -e "${BLUE}Installing memory-safe git hooks...${NC}\n"

# Show current gitleaks processes
echo -e "${CYAN}Current gitleaks processes:${NC}"
pgrep -f "gitleaks" >/dev/null 2>&1 && ps aux | grep -E "gitleaks" | grep -v grep || echo "  None running"
echo ""

# Install selected hooks
if [ "$INSTALL_PRE_COMMIT" = true ]; then
    create_hook "pre-commit"
fi

if [ "$INSTALL_PRE_PUSH" = true ]; then
    create_hook "pre-push"
fi

# Make all scripts executable
chmod +x "$SCRIPTS_DIR"/*.sh 2>/dev/null || true

echo ""
echo -e "${GREEN}✅ Installation complete!${NC}"
echo ""
echo -e "${CYAN}Features:${NC}"
if [ "$USE_V2" = true ]; then
    echo "  ✅ Multi-instance support - run in multiple projects simultaneously"
    echo "  ✅ Smart process management - only kills unsafe processes"
    echo "  ✅ Docker awareness - checks containers for gitleaks"
    echo "  ✅ Installation detection - finds all gitleaks on system"
else
    echo "  ✅ Single instance mode - one scan at a time"
    echo "  ✅ Simple process management"
fi
echo ""
echo -e "${CYAN}Configuration:${NC}"
echo "  GITLEAKS_TIMEOUT=300     # Increase timeout to 5 minutes"
echo "  GITLEAKS_VERBOSE=true    # Enable verbose output"
echo ""
echo -e "${CYAN}Usage:${NC}"
echo "  Normal git operations will now use safe gitleaks checks"
echo "  Manual scan: ./scripts/$WRAPPER_SCRIPT detect --source ."
echo "  Cleanup: ./scripts/cleanup-gitleaks-v2.sh"
echo ""
echo -e "${YELLOW}⚠️  Note:${NC} Pre-push hooks are recommended over pre-commit"
echo "   to avoid running gitleaks too frequently during development."
