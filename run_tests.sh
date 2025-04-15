#!/bin/bash
# run_tests.sh - Run tests using project-isolated environment
# Uses only relative paths and ensures no external environment dependencies

set -eo pipefail # Exit on error, propagate pipe failures

# Find script directory for relative paths
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
VENV_DIR="$SCRIPT_DIR/.venv"
PYTHON_CMD="$VENV_DIR/bin/python"

# Check for clean environment
if [ -f "$VENV_DIR/pyvenv.cfg" ]; then
    if grep -q "ComfyUI\|comfyui" "$VENV_DIR/pyvenv.cfg"; then
        echo "⚠️ Warning: Environment contains external references"
        echo "Run ./reinitialize_env.sh to create a clean environment"
        exit 1
    fi
fi

# Check for project-isolated Python environment
if [ ! -f "$PYTHON_CMD" ]; then
    echo "⚠️ Project virtual environment not found at $VENV_DIR"
    echo "Run ./reinitialize_env.sh to create a clean environment"
    exit 1
fi

# Activate virtual environment for script execution
export VIRTUAL_ENV="$VENV_DIR"
export PATH="$VENV_DIR/bin:$PATH"

echo "🐍 Using Python from isolated environment: $PYTHON_CMD"

echo "🧪 Running tests with pytest..."

# Verify test sample exists
if [ ! -f "$SCRIPT_DIR/tests/samples/test_sample.txt" ]; then
    echo "❌ Test sample file missing!"
    exit 1
fi

# Set a fixed timeout value (10 minutes = 600 seconds)
# This matches the GitHub workflow timeout setting
PYTEST_TIMEOUT=600
echo "⏱️ Test timeout set to $PYTEST_TIMEOUT seconds (10 minutes)"

# Run pytest using the virtual environment's Python.
# Pass environment variables needed for tests.
TEST_ENV="true" \
PYTHONUTF8=1 \
timeout $PYTEST_TIMEOUT $PYTHON_CMD -m pytest "$SCRIPT_DIR/tests/" -v \
    --cov=enchant_cli \
    --cov-report=term-missing:skip-covered \
    --cov-report=html:"$SCRIPT_DIR/coverage_report" \
    --cov-fail-under=80 \
    --strict-markers \
    --html="$SCRIPT_DIR/report.html" \
    --self-contained-html \
    --durations=10 # Show 10 slowest tests

EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo "✅ Tests completed successfully!"
    echo "📊 HTML Test report: open $SCRIPT_DIR/report.html"
    echo "📊 HTML Coverage report: open $SCRIPT_DIR/coverage_report/index.html"
else
    echo "❌ Tests failed with exit code $EXIT_CODE."
fi

exit $EXIT_CODE