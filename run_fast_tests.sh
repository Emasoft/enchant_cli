#!/bin/bash
set -eo pipefail

# run_fast_tests.sh - Fast test script for quick validation
# Only runs a subset of tests for quick verification

# First, ensure we have a clean environment
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
source "$SCRIPT_DIR/ensure_env.sh"

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