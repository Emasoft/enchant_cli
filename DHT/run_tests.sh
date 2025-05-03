#!/bin/bash

# Direct execution check disabled for integration with guardian process

# run_tests.sh - Comprehensive test runner for all testing scenarios
# Uses only relative paths and ensures no external environment dependencies

set -eo pipefail # Exit on error, propagate pipe failures

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

# Find script directory for relative paths
if [ -z "$SCRIPT_DIR" ]; then
    SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
    # If called directly, SCRIPT_DIR will be the DHT directory, so get parent
    if [[ "$SCRIPT_DIR" == */DHT ]]; then
        SCRIPT_DIR="$(dirname "$SCRIPT_DIR")"
    fi
fi

VENV_DIR="$SCRIPT_DIR/.venv"
PYTHON_CMD="$VENV_DIR/bin/python"

# Set a consistent timeout for all operations (15 minutes = 900 seconds)
TIMEOUT=900

# Check if any argument was passed to run in fast mode
FAST_MODE=0
if [[ "$1" == "--fast" || "$1" == "-f" ]]; then
    FAST_MODE=1
    print_info "Running in fast mode - only critical tests will be executed"
fi

# Check for clean environment
if [ -f "$VENV_DIR/pyvenv.cfg" ]; then
    if grep -q "ComfyUI\|comfyui" "$VENV_DIR/pyvenv.cfg"; then
        print_warning "Environment contains external references"
        print_info "Run ./reinitialize_env.sh to create a clean environment"
        exit 1
    fi
fi

# Check for project-isolated Python environment
if [ ! -f "$PYTHON_CMD" ]; then
    print_warning "Project virtual environment not found at $VENV_DIR"
    print_info "Run ./reinitialize_env.sh to create a clean environment"
    exit 1
fi

# Try to activate the environment, but continue even if it fails (guardian might handle this)
if [ -f "$SCRIPT_DIR/ensure_env.sh" ]; then
    source "$SCRIPT_DIR/ensure_env.sh" || {
        print_warning "Could not source environment script. Using basic activation."
        export VIRTUAL_ENV="$VENV_DIR"
        export PATH="$VENV_DIR/bin:$PATH"
    }
fi

print_header "Starting Test Runner"

# Verify test sample exists
if [ ! -f "$SCRIPT_DIR/tests/samples/test_sample.txt" ]; then
    print_warning "Test sample file missing! Attempting to create sample directory..."
    mkdir -p "$SCRIPT_DIR/tests/samples"
    echo "This is a test sample file." > "$SCRIPT_DIR/tests/samples/test_sample.txt"
    print_success "Created sample test file."
fi

print_info "Test timeout set to $TIMEOUT seconds (15 minutes)"

# Set environment variables for testing
export TEST_ENV="true"
export PYTHONUTF8=1

# Set test arguments
PYTEST_ARGS=(
    -v
    --cov=enchant_cli
    --cov-report=term-missing:skip-covered
    --cov-report=html:"$SCRIPT_DIR/coverage_report"
    --cov-fail-under=80
    --strict-markers
    --html="$SCRIPT_DIR/report.html"
    --self-contained-html
    --durations=10  # Show 10 slowest tests
    --timeout=900   # Test timeout in seconds (15 minutes)
)

# Run either full test suite or critical tests based on mode
if [ $FAST_MODE -eq 1 ]; then
    print_step "Running critical tests only..."
    
    # Define critical tests to run (subset of full test suite)
    CRITICAL_TESTS=(
        "tests/test_cli.py::test_cli_version"
        "tests/test_cli.py::test_cli_help"
        "tests/test_cli.py::test_cli_missing_filepath"
        "tests/test_cli.py::test_cli_nonexistent_filepath"
        "tests/test_translation_service.py::test_translator_init_test_env"
        # Add more essential tests here if needed
    )
    
    timeout $TIMEOUT $PYTHON_CMD -m pytest "${CRITICAL_TESTS[@]}" "${PYTEST_ARGS[@]}"
else
    print_step "Running full test suite..."
    
    # Run all tests
    timeout $TIMEOUT $PYTHON_CMD -m pytest "$SCRIPT_DIR/tests/" "${PYTEST_ARGS[@]}"
fi

EXIT_CODE=$?

# Handle exit code
if [ $EXIT_CODE -eq 0 ]; then
    print_success "Tests completed successfully!"
    print_info "HTML Test report: $SCRIPT_DIR/report.html"
    print_info "HTML Coverage report: $SCRIPT_DIR/coverage_report/index.html"
elif [ $EXIT_CODE -eq 124 ]; then
    print_error "Tests timed out after $TIMEOUT seconds."
    print_warning "This may indicate slow tests or environment issues."
    exit 124
else
    print_error "Tests failed with exit code $EXIT_CODE."
    exit $EXIT_CODE
fi

print_header "Test Execution Complete"

exit 0