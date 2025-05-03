#!/bin/bash
# Enhanced bump_version.sh - Script for bumping project version using bump-my-version
set -eo pipefail

# Get script directory
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

# Default version part if not specified
VERSION_PART=${1:-minor}

# Validate version part
if [[ ! "$VERSION_PART" =~ ^(major|minor|patch)$ ]]; then
    echo "❌ Error: Invalid version part. Use one of: major, minor, patch"
    echo "Usage: ./bump_version.sh [major|minor|patch]"
    exit 1
fi

# First try using the helper script (recommended approach)
if [[ -f "$SCRIPT_DIR/helpers-cli.sh" ]]; then
    echo "🔄 Using helpers-cli.sh to run bump-my-version..."
    "$SCRIPT_DIR/helpers-cli.sh" repo --bump-version "$VERSION_PART"
    exit $?
fi

# Check if uv is available for running bump-my-version (preferred method)
if command -v uv >/dev/null 2>&1; then
    echo "🔄 Bumping $VERSION_PART version with uv..."
    uv tool run bump-my-version bump "$VERSION_PART" --commit --tag --allow-dirty
    
    # Get the new version for confirmation message
    NEW_VERSION=$(uv tool run bump-my-version show current_version)
    echo "✅ Version bumped to $NEW_VERSION"
    echo "ℹ️ Remember to 'git push --follow-tags' to push the changes and the new tag."
    exit 0
fi

# Fall back to directly using bump-my-version if available
if command -v bump-my-version >/dev/null 2>&1; then
    echo "🔄 Bumping $VERSION_PART version with bump-my-version..."
    bump-my-version bump "$VERSION_PART" --commit --tag --allow-dirty
    
    # Get the new version for confirmation message
    NEW_VERSION=$(bump-my-version show current_version)
    echo "✅ Version bumped to $NEW_VERSION"
    echo "ℹ️ Remember to 'git push --follow-tags' to push the changes and the new tag."
    exit 0
fi

# If we get here, we need to install bump-my-version
echo "🔄 bump-my-version not found, setting up with helpers-cli..."

# Install Python dependencies if needed
if [[ ! -f "$SCRIPT_DIR/.venv/bin/python" ]]; then
    echo "🔄 Setting up Python environment..."
    if [[ -f "$SCRIPT_DIR/ensure_env.sh" ]]; then
        source "$SCRIPT_DIR/ensure_env.sh"
    else
        # Check if uv is available
        if command -v uv >/dev/null 2>&1; then
            echo "🔄 Creating virtual environment with uv..."
            uv venv "$SCRIPT_DIR/.venv"
        else
            # Fall back to python -m venv
            echo "🔄 Creating virtual environment with python venv..."
            python3 -m venv "$SCRIPT_DIR/.venv"
        fi
        source "$SCRIPT_DIR/.venv/bin/activate"
        
        # Check if we need to install uv
        if ! command -v "$SCRIPT_DIR/.venv/bin/uv" >/dev/null 2>&1; then
            echo "🔄 Installing uv in virtual environment..."
            curl -LsSf https://astral.sh/uv/install.sh | sh
            "$SCRIPT_DIR/.venv/bin/pip" install uv
        fi
    fi
fi

# Ensure our helper scripts are available
if [[ -f "$SCRIPT_DIR/helpers/cli.py" ]]; then
    echo "🔄 Setting up bump-my-version using helper scripts..."
    python -m helpers.cli fix --setup-bumpversion
    
    # Now run the version bump
    echo "🔄 Bumping $VERSION_PART version..."
    python -m helpers.cli repo --bump-version "$VERSION_PART"
    exit $?
else
    echo "❌ Helper scripts not found. Cannot set up bump-my-version."
    echo "💡 Try installing bump-my-version manually: pip install bump-my-version"
    exit 1
fi

