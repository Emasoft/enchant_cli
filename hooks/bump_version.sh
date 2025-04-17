#!/bin/bash
# This script bumps the version in __init__.py
# Always uses uv tool run for bump-my-version (required method)

set -eo pipefail

# Get script directory
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
PROJECT_ROOT=$(dirname "$SCRIPT_DIR")
UV_CMD="$PROJECT_ROOT/.venv/bin/uv"
INIT_PY="$PROJECT_ROOT/src/enchant_cli/__init__.py"

# Function to check if the version file exists
check_version_file() {
    if [ ! -f "$INIT_PY" ]; then
        echo "❌ Error: Version file not found at $INIT_PY"
        exit 1
    fi
}

# Check version file exists
check_version_file

# Multi-tier approach to bump version
echo "🔄 Bumping version..."

# Recommended approach: Always use uv tool run (never use direct binary calls)
if [ -f "$UV_CMD" ]; then
    # Preferred method: Using uv tool run with proper arguments
    echo "✅ Using uv tool run for bump-my-version (recommended method)"
    "$UV_CMD" tool run bump-my-version bump minor --commit --tag --allow-dirty || {
        echo "⚠️ WARNING: Version bump with uv tool failed, trying alternatives..."
    }
else
    # Fallback approaches (less preferred, only for extreme edge cases)
    if command -v uv >/dev/null 2>&1; then
        # Try global uv installation as fallback
        echo "⚠️ WARNING: Using global uv installation (non-isolated environment)"
        uv tool run bump-my-version bump minor --commit --tag --allow-dirty || {
            echo "⚠️ WARNING: Version bump failed with global uv - ensure uv is properly installed"
        }
    elif [ -f "$PROJECT_ROOT/.venv/bin/bump-my-version" ]; then
        # Direct virtualenv access (not recommended - may cause sync issues with uv)
        echo "⚠️ WARNING: Using direct virtualenv binary (not recommended)"
        "$PROJECT_ROOT/.venv/bin/bump-my-version" bump minor --commit --tag --allow-dirty || {
            echo "⚠️ WARNING: Version bump with direct binary failed"
        }
    else
        # Fallback to Python script approach
        echo "⚠️ WARNING: Using manual version bump (emergency fallback)"
        
        # Extract current version using grep and sed
        CURRENT_VERSION=$(grep -o '__version__[[:space:]]*=[[:space:]]*"[0-9]\+\.[0-9]\+\.[0-9]\+"' "$INIT_PY" | sed -E 's/__version__[[:space:]]*=[[:space:]]*"([0-9]+\.[0-9]+\.[0-9]+)"/\1/')
        
        if [ -z "$CURRENT_VERSION" ]; then
            echo "ERROR: Could not extract version from $INIT_PY"
            exit 1
        fi
        
        # Parse version components
        MAJOR=$(echo "$CURRENT_VERSION" | cut -d. -f1)
        MINOR=$(echo "$CURRENT_VERSION" | cut -d. -f2)
        PATCH=$(echo "$CURRENT_VERSION" | cut -d. -f3)
        
        # Increment minor version
        NEW_MINOR=$((MINOR + 1))
        NEW_VERSION="${MAJOR}.${NEW_MINOR}.0"
        
        # Update version in __init__.py
        sed -i.bak "s/__version__ = \"[0-9]\+\.[0-9]\+\.[0-9]\+\"/__version__ = \"$NEW_VERSION\"/" "$INIT_PY"
        rm -f "${INIT_PY}.bak"
        
        echo "Bumped version from $CURRENT_VERSION to $NEW_VERSION"
        
        # Create git commit and tag
        git add "$INIT_PY"
        git commit -m "chore: Bump version to $NEW_VERSION" --no-verify
        git tag -a "v$NEW_VERSION" -m "Version $NEW_VERSION"
    fi
fi

# Sync dependencies after version bump (important for uv workflow)
if [ -f "$UV_CMD" ]; then
    "$UV_CMD" sync || echo "⚠️ WARNING: uv sync failed after version bump"
fi