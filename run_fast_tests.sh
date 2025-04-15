#!/bin/bash
set -eo pipefail

# run_fast_tests.sh - Fast test script for quick validation
# Only runs a subset of tests for quick verification

# Find script directory for relative paths
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
VENV_DIR="$SCRIPT_DIR/.venv"
PYTHON_CMD="$VENV_DIR/bin/python"

if [ ! -f "$PYTHON_CMD" ]; then
    echo "⚠️ Python not found in virtual environment. Creating with uv..."
    if ! command -v uv &> /dev/null; then
        echo "❌ uv not found. Please install with: pip install uv"
        exit 1
    fi
    uv venv "$VENV_DIR"
    if [ ! -f "$PYTHON_CMD" ]; then
        echo "❌ Failed to create virtual environment."
        exit 1
    fi
fi

echo "⚡ Running fast tests for quick validation..."

# Verify test sample exists
if [ ! -f tests/samples/test_sample.txt ]; then
    echo "❌ Test sample file missing!"
    exit 1
fi

# Run a subset of fast tests with a strict timeout
"$PYTHON_CMD" -m pytest tests/test_cli.py::test_cli_version tests/test_cli.py::test_cli_help -v \
    --cov=enchant_cli \
    --cov-report=term-missing:skip-covered \
    --timeout=30 \
    --no-header

echo "✅ Fast tests completed successfully!"