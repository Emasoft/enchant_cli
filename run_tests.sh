#!/usr/bin/env bash
# run_tests.sh - Run tests locally using pytest
# Assumes dependencies are already installed in the active virtual environment.

set -eo pipefail # Exit on error, treat unset variables as error, propagate pipe failures

# Find the virtual environment relative to the script location
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
VENV_DIR="$SCRIPT_DIR/.venv"
PYTHON_CMD="$VENV_DIR/bin/python" # Path to python inside .venv

if [ ! -f "$PYTHON_CMD" ]; then
    echo "❌ Error: Virtual environment Python not found at '$PYTHON_CMD'."
    echo "   Please ensure the virtual environment exists in '.venv' and dependencies are installed (e.g., using 'uv pip sync')."
    exit 1
fi
echo "🐍 Using Python command: $PYTHON_CMD"

echo "🧪 Running tests with pytest..."
# Run pytest using the virtual environment's Python.
# Assumes pytest.ini handles PYTHONPATH=src or using editable install.
# Pass environment variables needed for tests.
TEST_ENV="true" \
PYTHONUTF8=1 \
"$PYTHON_CMD" -m pytest tests/ -v \
    --cov=enchant_cli \
    --cov-report=term-missing:skip-covered \
    --cov-report=html:coverage_report \
    --cov-fail-under=80 \
    --strict-markers \
    --html=report.html \
    --self-contained-html \
    --durations=10 # Show 10 slowest tests

EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo "✅ Tests completed successfully!"
    echo "📊 HTML Test report: open report.html"
    echo "📊 HTML Coverage report: open coverage_report/index.html"
else
    echo "❌ Tests failed with exit code $EXIT_CODE."
fi

exit $EXIT_CODE
