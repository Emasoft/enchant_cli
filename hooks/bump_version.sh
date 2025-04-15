#!/bin/bash
# This script bumps the version in __init__.py
# It first tries to use bump-my-version, then falls back to a Python script if necessary

set -e

if command -v uv >/dev/null 2>&1; then
    # Try uv tool run approach
    uv tool run bump-my-version bump minor --commit --tag --allow-dirty || echo "WARNING: Version bump with uv failed, trying alternatives..."
elif [ -f ".venv/bin/bump-my-version" ]; then
    # Try direct from virtualenv
    .venv/bin/bump-my-version bump minor --commit --tag --allow-dirty || echo "WARNING: Version bump with .venv binary failed, trying alternatives..."
elif command -v bump-my-version &>/dev/null; then
    # Try system-installed version
    bump-my-version bump minor --commit --tag --allow-dirty || echo "WARNING: Version bump with global binary failed, trying alternatives..."
else
    # Fallback to Python script approach
    # Get a clean version string without single or double quotes
    INIT_PY="src/enchant_cli/__init__.py"
    if [ ! -f "$INIT_PY" ]; then
        echo "ERROR: $INIT_PY not found"
        exit 1
    fi
    
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