#!/usr/bin/env bash
# run_commands.sh - Executes a sequence of shell commands provided by the assistant.

set -eo pipefail # Exit immediately if a command exits with a non-zero status.

echo "🚀 Executing commands..."
echo "------------------------------------"

# --- Add commands below this line ---

echo "🔄 Synchronizing environment with uv..."
uv sync

echo "🧹 Clearing pre-commit cache..."
rm -rf ~/.cache/pre-commit
echo "   Pre-commit cache cleared."

echo "🔧 Reinstalling pre-commit hooks..."
pre-commit install --install-hooks

echo "🧪 Running tests..."
./run_tests.sh
TEST_EXIT_CODE=$? # Capture exit code from tests

# --- Add commands above this line ---

echo "------------------------------------"
# --- Final Status ---
if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo "✅ All commands executed successfully, tests passed!"
    echo "ℹ️  Remember to commit updated files if any changes were made."
    echo "   ⚠️ AND manually insert your Codecov badge token into README.md!"
else
    echo "❌ Tests failed with exit code $TEST_EXIT_CODE."
fi

exit $TEST_EXIT_CODE
