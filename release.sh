#!/bin/bash
set -eo pipefail

# release.sh - Local validation script before pushing a release tag.
# This script DOES NOT commit, tag, push, or set secrets.

echo "🚀 Starting pre-release validation..."

# 0. Check required commands
check_command() {
    if ! command -v "$1" >/dev/null 2>&1; then
        echo >&2 "❌ Error: Command '$1' is required but not installed or not in PATH."
        exit 1
    fi
}
check_command git
check_command python
check_command uv
check_command twine
check_command bump-my-version # Needed to get current version

# 1. Ensure clean working directory
if ! git diff --quiet HEAD; then
    echo >&2 "❌ Error: Working directory is not clean. Please commit or stash changes."
    git status --short
    exit 1
fi

# 2. Get current version
CURRENT_VERSION=$(bump-my-version show current_version)
if [ -z "$CURRENT_VERSION" ]; then
    echo >&2 "❌ Error: Could not determine current version using bump-my-version."
    exit 1
fi
echo "ℹ️  Validating version: $CURRENT_VERSION"

# 3. Clean previous builds
echo "🧹 Cleaning previous builds..."
rm -rf dist/ build/ *.egg-info/ .coverage* coverage_report/ report.html

# 4. Install dependencies (using locked versions)
echo "📦 Installing dependencies..."
uv pip install --system -r requirements.txt --locked
uv pip install --system -r requirements-dev.txt --locked
uv pip install --system -e . # Install current package

# 5. Run linters/formatters (via pre-commit if configured)
echo "🎨 Checking code formatting and quality..."
if [ -f .pre-commit-config.yaml ]; then
    pre-commit run --all-files || exit 1
else
    echo "⚠️  Skipping pre-commit hooks (no .pre-commit-config.yaml found)."
    # Optionally run linters manually here if pre-commit isn't used
    # ruff check .
    # black --check .
fi

# 6. Run tests and check coverage
echo "🧪 Running tests and checking coverage..."
# Use pytest directly, assuming pytest.ini configures pythonpath etc.
pytest tests/ -v \
    --cov=enchant_cli \
    --cov-report=term-missing:skip-covered \
    --cov-fail-under=80 \
    --strict-markers \
    --html=report.html \
    --self-contained-html || exit 1
echo "📊 Test report generated: report.html"

# 7. Build package (sdist and wheel)
echo "🏗️ Building package..."
python -m build || exit 1

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
echo "   2. If not already done, run: bump-my-version [major|minor|patch] (this should create the commit and tag)"
echo "   3. Push changes and the tag: git push origin main --tags"
echo "   4. Create a GitHub Release from the tag 'v$CURRENT_VERSION'."

