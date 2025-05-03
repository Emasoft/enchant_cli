#!/bin/bash
# test.sh - Test runner for projects using the DHT framework
# This file can be called directly or sourced by other scripts

# Determine script directory for relative paths
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    # Script is being run directly, get its directory
    SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
    # Get parent directory (project root)
    PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
else
    # Script is being sourced, use the provided SCRIPT_DIR or try to determine
    if [ -z "$SCRIPT_DIR" ]; then
        SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
        PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
    fi
fi

# Set up environment variables
VENV_DIR="$PROJECT_ROOT/.venv"
PYTHON_CMD="$VENV_DIR/bin/python"

# Default timeout (15 minutes = 900 seconds)
TIMEOUT=900

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

# Parse arguments
FAST_MODE=0
for arg in "$@"; do
    if [[ "$arg" == "--fast" || "$arg" == "-f" ]]; then
        FAST_MODE=1
        print_info "Running in fast mode - only critical tests will be executed"
    fi
done

print_header "Starting Test Runner"

# Verify test sample exists
if [ ! -f "$PROJECT_ROOT/tests/samples/test_sample.txt" ]; then
    print_warning "Test sample file missing! Attempting to create sample directory..."
    mkdir -p "$PROJECT_ROOT/tests/samples"
    echo "This is a test sample file." > "$PROJECT_ROOT/tests/samples/test_sample.txt"
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
    --cov-report=html:"$PROJECT_ROOT/coverage_report"
    --cov-fail-under=80
    --strict-markers
    --html="$PROJECT_ROOT/report.html"
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
    )
    
    timeout $TIMEOUT $PYTHON_CMD -m pytest "${CRITICAL_TESTS[@]}" "${PYTEST_ARGS[@]}"
else
    print_step "Running full test suite..."
    
    # Run all tests
    timeout $TIMEOUT $PYTHON_CMD -m pytest "$PROJECT_ROOT/tests/" "${PYTEST_ARGS[@]}"
fi

EXIT_CODE=$?

# Handle exit code
if [ $EXIT_CODE -eq 0 ]; then
    print_success "Tests completed successfully!"
    print_info "HTML Test report: $PROJECT_ROOT/report.html"
    print_info "HTML Coverage report: $PROJECT_ROOT/coverage_report/index.html"
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