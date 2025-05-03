#!/bin/bash

# Return error if executed directly - MUST BE PLACED AT THE BEGINNING
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    echo "Error: This script cannot be executed directly. All DHT scripts can only be called by the DHT Launcher in the project root. Please run dhtl.sh (or dhtl.bat) followed by the action you want to execute. For more informations use dhtl.sh --help"
    exit 1
fi

# bump_version.sh - Script for bumping project version with proper uv integration
set -eo pipefail

# Get script directory

# Default version part if not specified
VERSION_PART=${1:-minor}

# Validate version part
if [[ ! "$VERSION_PART" =~ ^(major|minor|patch)$ ]]; then
    echo "❌ Error: Invalid version part. Use one of: major, minor, patch"
    echo "Usage: ./bump_version.sh [major|minor|patch]"
    exit 1
fi

# Define file locations
INIT_PY="$SCRIPT_DIR/src/enchant_cli/__init__.py"
VENV_DIR="$SCRIPT_DIR/.venv"
UV_CMD="$VENV_DIR/bin/uv"

# Check if version file exists
if [[ ! -f "$INIT_PY" ]]; then
    echo "❌ Error: Version file not found at $INIT_PY"
    exit 1
fi

echo "🔄 Bumping $VERSION_PART version..."

# Try using helpers-cli.sh if available (recommended approach)
if [[ -f "$SCRIPT_DIR/helpers-cli.sh" ]]; then
    echo "Using helpers-cli.sh to run bump-my-version..."
    "$SCRIPT_DIR/helpers-cli.sh" repo --bump-version "$VERSION_PART" || {
        echo "⚠️ Warning: helpers-cli.sh approach failed, trying alternatives..."
    }
# Use uv if available (second best approach)
elif [[ -f "$UV_CMD" ]]; then
    echo "Using uv for bump-my-version..."
    "$UV_CMD" tool run bump-my-version bump "$VERSION_PART" --commit --tag --allow-dirty || {
        echo "⚠️ Warning: uv approach failed, trying global uv..."
        # Try global uv as fallback
        if command -v uv &>/dev/null; then
            uv tool run bump-my-version bump "$VERSION_PART" --commit --tag --allow-dirty || {
                echo "⚠️ Warning: Global uv approach failed."
            }
        fi
    }
# Try direct virtualenv binary (less preferred)
elif [[ -f "$VENV_DIR/bin/bump-my-version" ]]; then
    echo "⚠️ Using direct virtualenv binary (not recommended)"
    "$VENV_DIR/bin/bump-my-version" bump "$VERSION_PART" --commit --tag --allow-dirty || {
        echo "⚠️ Warning: Direct binary approach failed."
    }
# Final fallback: manual version bump
else
    echo "🔄 No bump-my-version found. Using pure shell version bump as fallback..."
    
    # Extract current version using grep and sed
    CURRENT_VERSION=$(grep -o '__version__[[:space:]]*=[[:space:]]*"[0-9]\+\.[0-9]\+\.[0-9]\+"' "$INIT_PY" | sed -E 's/__version__[[:space:]]*=[[:space:]]*"([0-9]+\.[0-9]+\.[0-9]+)"/\1/')
    
    if [[ -z "$CURRENT_VERSION" ]]; then
        echo "❌ Error: Could not extract current version from $INIT_PY"
        exit 1
    fi
    
    # Split version
    IFS='.' read -r MAJOR MINOR PATCH <<< "$CURRENT_VERSION"
    
    # Increment version based on part
    case "$VERSION_PART" in
        major)
            NEW_MAJOR=$((MAJOR + 1))
            NEW_VERSION="$NEW_MAJOR.0.0"
            ;;
        minor)
            NEW_MINOR=$((MINOR + 1))
            NEW_VERSION="$MAJOR.$NEW_MINOR.0"
            ;;
        patch)
            NEW_PATCH=$((PATCH + 1))
            NEW_VERSION="$MAJOR.$MINOR.$NEW_PATCH"
            ;;
    esac
    
    # Replace version in file
    sed -i.bak -E "s/__version__[[:space:]]*=[[:space:]]*\"[0-9]+\.[0-9]+\.[0-9]+\"/__version__ = \"$NEW_VERSION\"/" "$INIT_PY"
    rm -f "$INIT_PY.bak"
    
    # Commit changes
    git add "$INIT_PY"
    git commit -m "Bump version: $CURRENT_VERSION → $NEW_VERSION"
    
    # Create tag
    git tag -a "v$NEW_VERSION" -m "Bump version: $CURRENT_VERSION → $NEW_VERSION"
    
    echo "✅ Version bumped from $CURRENT_VERSION to $NEW_VERSION"
fi

# Sync dependencies after version bump (important for uv workflow)
if [[ -f "$UV_CMD" ]]; then
    "$UV_CMD" sync || echo "⚠️ Warning: uv sync failed after version bump"
fi

echo "✅ Version bump process completed."
exit 0
