#!/bin/bash
set -eo pipefail

# release.sh - Local validation script before pushing a release tag.
# This script DOES NOT commit, tag, push, or set secrets.

echo "🚀 Starting pre-release validation..."

# Find script directory for relative paths
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
VENV_DIR="$SCRIPT_DIR/.venv"
PYTHON_CMD="$VENV_DIR/bin/python"

# 0. Check required commands and potentially install
ensure_command() {
    if ! command -v "$1" >/dev/null 2>&1; then
        echo "⚠️ Command '$1' not found globally. Checking in local environment..."
        if [ -f "$VENV_DIR/bin/$1" ]; then
            echo "✅ Found $1 in virtual environment."
            return 0
        fi
        echo "⚠️ Installing $1 in virtual environment..."
        "$PYTHON_CMD" -m pip install "$1"
        if [ ! -f "$VENV_DIR/bin/$1" ]; then
            echo >&2 "❌ Error: Failed to install $1."
            exit 1
        fi
    fi
}

ensure_command git
ensure_command uv
ensure_command twine

# Install bump-my-version using uv tool
if command -v uv &> /dev/null; then
    echo "🔧 Installing bump-my-version via uv tools..."
    uv tool install --quiet bump-my-version || echo "⚠️ Failed to install bump-my-version via uv, continuing anyway."
    BUMP_CMD="uv tool run bump-my-version"
elif [ -f "$VENV_DIR/bin/bump-my-version" ]; then
    BUMP_CMD="$VENV_DIR/bin/bump-my-version"
else
    echo "⚠️ Installing bump-my-version in virtual environment..."
    "$PYTHON_CMD" -m pip install bump-my-version || echo "⚠️ Failed to install bump-my-version, continuing anyway."
    BUMP_CMD="$VENV_DIR/bin/bump-my-version"
fi

# 2. Get current version directly from the Python file
INIT_PY="$SCRIPT_DIR/src/enchant_cli/__init__.py"
if [ -f "$INIT_PY" ]; then
    CURRENT_VERSION=$(grep -o '[0-9]\+\.[0-9]\+\.[0-9]\+' "$INIT_PY")
else
    echo >&2 "❌ Error: Could not find __init__.py at $INIT_PY"
    exit 1
fi

if [ -z "$CURRENT_VERSION" ]; then
    echo >&2 "❌ Error: Could not extract version from __init__.py."
    exit 1
fi
echo "ℹ️  Validating version: $CURRENT_VERSION"

# 3. Clean previous builds
echo "🧹 Cleaning previous builds..."
rm -rf dist/ build/ ./*.egg-info/ .coverage* coverage_report/ report.html

# 4. Install dependencies (using specified requirements files into the active venv)
echo "📦 Installing dependencies into active virtual environment..."
uv pip install -r requirements.txt
uv pip install -r requirements-dev.txt
uv pip install -e . # Install current package into the active venv

# 5. Run linters/formatters (via pre-commit if configured)
echo "🎨 Checking code formatting and quality..."
if [ -f .pre-commit-config.yaml ]; then
    # Run pre-commit hooks. Assumes environment was prepared by the calling script.
    # If this fails, it's likely a real lint/format error needing manual fix.
    $PYTHON_CMD -m pre_commit run --all-files || {
        echo >&2 "❌ Pre-commit checks failed. Please fix the reported issues."
        exit 1
    }
    echo "✅ Pre-commit checks passed."
else
    echo "⚠️  Skipping pre-commit hooks (no .pre-commit-config.yaml found)."
    # Optionally run linters manually here if pre-commit isn't used
    # ruff check .
    # black --check .
fi

# 6. Run tests and check coverage
echo "🧪 Running tests and checking coverage..."

# Verify test sample exists
if [ ! -f tests/samples/test_sample.txt ]; then
    echo "❌ Test sample file missing!"
    exit 1
fi

# Set a fixed timeout value (10 minutes = 600 seconds)
# This matches the GitHub workflow timeout setting
PYTEST_TIMEOUT=600
echo "⏱️ Test timeout set to $PYTEST_TIMEOUT seconds (10 minutes)"

# Use pytest directly, assuming pytest.ini configures pythonpath etc.
# Set environment variables needed for tests
TEST_ENV="true" \
PYTHONUTF8=1 \
timeout $PYTEST_TIMEOUT pytest tests/ -v \
    --cov=enchant_cli \
    --cov-report=term-missing:skip-covered \
    --cov-fail-under=80 \
    --strict-markers \
    --html=report.html \
    --self-contained-html || exit 1
echo "📊 Test report generated: report.html"

# 7. Build package (sdist and wheel)
echo "🏗️ Building package..."
uv build || exit 1 # Use uv build

# 8. Check package metadata and contents
echo "🔍 Validating built packages..."
twine check dist/* || exit 1

# Verify test sample inclusion in both wheel and sdist
echo "    Verifying test sample inclusion..."
if ! (unzip -l dist/*.whl | grep -q 'tests/samples/test_sample.txt') ; then
    echo "❌ Test sample file missing from wheel package!"
    exit 1
fi
if ! (tar -ztf dist/*.tar.gz | grep -q 'tests/samples/test_sample.txt') ; then
    echo "❌ Test sample file missing from sdist package!"
    exit 1
fi
echo "    ✅ Test sample file found in packages."


echo -e "\n✅✅✅ All local validations passed for version $CURRENT_VERSION! ✅✅✅"
echo "➡️ Next steps:"
echo "   1. Ensure the version $CURRENT_VERSION is correct."
echo "   2. To manually bump version, run: uv tool run bump-my-version [major|minor|patch]"
echo "   3. Push changes and tags with: git push origin main --tags"
echo "   4. Create a GitHub Release from the tag 'v$CURRENT_VERSION'."

