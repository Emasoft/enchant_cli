#!/bin/bash

# Return error if executed directly - MUST BE PLACED AT THE BEGINNING
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    echo "Error: This script cannot be executed directly. All DHT scripts can only be called by the DHT Launcher in the project root. Please run dhtl.sh (or dhtl.bat) followed by the action you want to execute. For more informations use dhtl.sh --help"
    exit 1
fi

# run_commands.sh - Executes the final sequence for validation and push preparation.
# Uses only relative paths and project-isolated environment

set -eo pipefail # Exit immediately if a command exits with a non-zero status.

# Find script directory for relative paths
VENV_DIR="$SCRIPT_DIR/.venv"
PYTHON_CMD="$VENV_DIR/bin/python"
UV_CMD="$VENV_DIR/bin/uv"

echo "🚀 Executing final preparation sequence..."
echo "------------------------------------"

# Check for project-isolated Python environment
if [ ! -f "$PYTHON_CMD" ]; then
    echo "⚠️ Project virtual environment not found at $VENV_DIR"
    echo "Run ./reinitialize_env.sh to create a clean environment"
    exit 1
fi

# Check for clean environment
if [ -f "$VENV_DIR/pyvenv.cfg" ]; then
    if grep -q "ComfyUI\|comfyui" "$VENV_DIR/pyvenv.cfg"; then
        echo "⚠️ Warning: Environment contains external references"
        echo "Run ./reinitialize_env.sh to create a clean environment"
        exit 1
    fi
fi

# --- Commands Sequence ---
# Activate virtual environment for script execution
export VIRTUAL_ENV="$VENV_DIR"
export PATH="$VENV_DIR/bin:$PATH"

# 1. Ensure environment is synchronized
echo "🔒 Ensuring lock file is up-to-date with all dependencies (including dev)..."
$UV_CMD lock || { echo >&2 "❌ uv lock failed."; exit 1; }
echo "✅ Lock file updated."

echo "🔄 Synchronizing environment with uv..."
$UV_CMD sync || { echo >&2 "❌ uv sync failed."; exit 1; }
echo "✅ Environment synchronized."

echo "🐍 Using Python from isolated environment: $PYTHON_CMD"

# 2. Proactively prepare pre-commit environment
echo "🔧 Preparing pre-commit environment..."
echo "   🧹 Forcefully cleaning pre-commit cache..."
rm -rf "$HOME/.cache/pre-commit" || echo "   ⚠️  Failed to remove pre-commit cache, continuing..."
echo "   🔧 Reinstalling pre-commit hooks..."
$PYTHON_CMD -m pre_commit install --install-hooks || { echo >&2 "❌ pre-commit install failed."; exit 1; }
echo "   ✅ Pre-commit environment ready."

# 3. Check for uncommitted changes and commit them
echo "🔍 Checking for uncommitted changes..."
if ! git diff --quiet HEAD; then
    echo "⚠️ Uncommitted changes detected. Staging and attempting to commit automatically..."
    git add -A # Stage all changes first

    echo "⚙️ Running pre-commit hooks manually on staged files before commit..."
    STAGED_FILES=$(git diff --name-only --cached)
    if [ -n "$STAGED_FILES" ]; then
        $PYTHON_CMD -m pre_commit run --files $STAGED_FILES || {
            echo >&2 "❌ Manual pre-commit run failed on staged files."
            echo >&2 "   Please check pre-commit logs and fix the hook issue manually."
            exit 1
        }
        echo "✅ Manual pre-commit run successful."
        echo "   Re-staging potentially modified files..."
        git add -A
    fi

    echo "📝 Committing staged changes..."
    # Use a generic message; the version bump hook will create its own commit
    git commit -m "chore: Apply pre-commit changes and prepare for validation" || { echo >&2 "❌ git commit failed."; exit 1; }
    echo "✅ Changes committed. Pre-commit hooks (including version bump) should have run."
else
    echo "✅ Working directory is clean."
fi

# 4. Execute the main validation and push script
echo "🚀 Running validation and push script (publish_to_github.sh)..."
"$SCRIPT_DIR/publish_to_github.sh"
SCRIPT_EXIT_CODE=$? # Capture exit code

# --- Final Status ---
echo "------------------------------------"
if [ $SCRIPT_EXIT_CODE -eq 0 ]; then
    echo "✅✅✅ All commands executed successfully! Validation passed and changes pushed. ✅✅✅"
    echo "➡️ Final Step: Manually create the GitHub Release using the latest tag."
else
    echo "❌ Script failed with exit code $SCRIPT_EXIT_CODE."
    echo "   Please review the logs above to diagnose the failure."
fi

exit $SCRIPT_EXIT_CODE
