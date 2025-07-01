#!/bin/bash
# export-safe-hooks.sh - Export the memory-safe git hooks for use in other projects
#
# Usage: ./scripts/export-safe-hooks.sh [target-directory]

set -euo pipefail

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Default target is current directory
TARGET_DIR="${1:-$PWD}"

# Create a temporary directory for the export
EXPORT_DIR=$(mktemp -d)
EXPORT_NAME="memory-safe-git-hooks"

echo -e "${BLUE}📦 Exporting memory-safe git hooks...${NC}"

# Create the export structure
mkdir -p "$EXPORT_DIR/$EXPORT_NAME"

# Copy the necessary files
cp "$SCRIPT_DIR/gitleaks-safe.sh" "$EXPORT_DIR/$EXPORT_NAME/"
cp "$SCRIPT_DIR/install-safe-git-hooks.sh" "$EXPORT_DIR/$EXPORT_NAME/"
cp "$SCRIPT_DIR/README.md" "$EXPORT_DIR/$EXPORT_NAME/"

# Create a simple install script for the target project
cat > "$EXPORT_DIR/$EXPORT_NAME/install.sh" << 'EOF'
#!/bin/bash
# Quick installer for memory-safe git hooks

set -euo pipefail

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}Installing memory-safe git hooks...${NC}"

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Check if we're in a git repository
if ! git rev-parse --git-dir > /dev/null 2>&1; then
    echo -e "${RED}❌ Not in a git repository${NC}"
    echo "Please run this script from the root of your git project."
    exit 1
fi

# Create scripts directory in the target project
mkdir -p scripts

# Copy files
cp "$SCRIPT_DIR/gitleaks-safe.sh" scripts/
cp "$SCRIPT_DIR/install-safe-git-hooks.sh" scripts/
cp "$SCRIPT_DIR/README.md" scripts/

# Make scripts executable
chmod +x scripts/gitleaks-safe.sh
chmod +x scripts/install-safe-git-hooks.sh

# Check if gitleaks is installed
if ! command -v gitleaks &> /dev/null; then
    echo -e "${YELLOW}⚠️  Gitleaks is not installed${NC}"
    echo "The installer will prompt you to install it."
fi

# Run the installer
./scripts/install-safe-git-hooks.sh "$@"

echo -e "${GREEN}✅ Installation complete!${NC}"
echo ""
echo "The memory-safe git hooks are now installed in your project."
echo "See scripts/README.md for configuration options."
EOF

chmod +x "$EXPORT_DIR/$EXPORT_NAME/install.sh"

# Create a tarball
cd "$EXPORT_DIR"
tar -czf "$TARGET_DIR/$EXPORT_NAME.tar.gz" "$EXPORT_NAME"

# Clean up
rm -rf "$EXPORT_DIR"

echo -e "${GREEN}✅ Exported to: $TARGET_DIR/$EXPORT_NAME.tar.gz${NC}"
echo ""
echo "To use in another project:"
echo "1. Copy $EXPORT_NAME.tar.gz to the target project"
echo "2. Extract: tar -xzf $EXPORT_NAME.tar.gz"
echo "3. Run: ./$EXPORT_NAME/install.sh"
echo ""
echo "Or install directly:"
echo "  tar -xzf $EXPORT_NAME.tar.gz && ./$EXPORT_NAME/install.sh && rm -rf $EXPORT_NAME"
