#!/bin/bash
set -eo pipefail

# run_fast_tests.sh - Fast test script for quick validation
# Only runs a subset of tests for quick verification

# First, ensure we have a clean environment
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
source "$SCRIPT_DIR/ensure_env.sh"

# Utility functions for better output
print_header() {
    echo ""
    echo "🔶🔶🔶 $1 🔶🔶🔶"
    echo ""
}

print_step() {
    echo "📋 $1"
}

print_success() {
    echo "✅ $1"
}

print_warning() {
    echo "⚠️ $1"
}

print_error() {
    echo "❌ $1" >&2
}

print_info() {
    echo "ℹ️ $1"
}

print_header "Fast Test Runner"
echo "Running critical tests for quick validation."

# Set a reasonable timeout (120 seconds)
TIMEOUT=120
print_info "Test timeout set to $TIMEOUT seconds"

# Verify test sample exists
if [ ! -f tests/samples/test_sample.txt ]; then
    print_warning "Test sample file missing! Attempting to create sample directory..."
    mkdir -p tests/samples
    echo "This is a test sample file." > tests/samples/test_sample.txt
    print_success "Created sample test file."
fi

# Define critical tests to run
CRITICAL_TESTS=(
    "tests/test_cli.py::test_cli_version"
    "tests/test_cli.py::test_cli_help"
    # Add more critical tests here if needed
)

print_step "Running critical tests..."

# Export test environment variables
export TEST_ENV="true"
export PYTHONUTF8=1

# Run critical tests
TESTS_FAILED=0
timeout $TIMEOUT "$PYTHON_CMD" -m pytest "${CRITICAL_TESTS[@]}" -v \
    --cov=enchant_cli \
    --cov-report=term-missing:skip-covered \
    --timeout=120 \
    --no-header || TESTS_FAILED=$?

if [ $TESTS_FAILED -ne 0 ]; then
    if [ $TESTS_FAILED -eq 124 ]; then
        print_error "Tests timed out after $TIMEOUT seconds."
        print_warning "This may indicate slow tests or environment issues."
        exit 124
    else
        print_error "Tests failed with exit code $TESTS_FAILED."
        exit $TESTS_FAILED
    fi
fi

print_header "Fast Tests Completed Successfully"
print_info "For full test suite, run: ./run_tests.sh"

exit 0