#!/bin/bash
# run_coverage.sh - Script to run tests with coverage and upload to Codecov
# Always run this script via the DHT launcher: ./dhtl.sh coverage

set -eo pipefail

# Get script directory
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
PROJECT_ROOT=$(dirname "$SCRIPT_DIR")

# We don't source ensure_env.sh as it's managed by the dhtl.sh launcher

# Repository and token information
REPO_SLUG="Emasoft/enchant_cli"
CODECOV_TOKEN="7d914783-1066-4150-a5af-d3766fc53738"

# Debug: Print all arguments
echo "🔍 Args received by run_coverage.sh: $# args - $*"

# Function to display help
show_help() {
    echo "📋 Code Coverage Commands"
    echo "========================="
    echo "Usage: ./dhtl.sh coverage [options]"
    echo ""
    echo "Options:"
    echo "  --help                  Show this help message"
    echo "  --upload                Upload coverage to Codecov after running tests"
    echo "  --file=<path>           Run coverage on a specific file"
    echo "  --test-module=<path>    Run tests from a specific test module"
    echo "  --report-only           Generate reports without running tests"
    echo "  --html                  Generate HTML report"
    echo "  --xml                   Generate XML report (default)"
    echo "  --branch                Enable branch coverage (default)"
    echo "  --token=<token>         Use a specific Codecov token"
    echo ""
    echo "Examples:"
    echo "  ./dhtl.sh coverage --upload"
    echo "  ./dhtl.sh coverage --file=src/enchant_cli/utils.py"
    echo "  ./dhtl.sh coverage --file=src/enchant_cli/utils.py --test-module=tests/test_utils.py"
    echo "  ./dhtl.sh coverage --report-only --html"
    echo ""
}

# Default options
UPLOAD=false
RUN_TESTS=true
COVERAGE_FILE=""
TEST_MODULE=""
HTML_REPORT=true
XML_REPORT=true
BRANCH_COVERAGE=true
CUSTOM_TOKEN=""

# Parse arguments
for arg in "$@"; do
    if [[ "$arg" == "--help" ]]; then
        show_help
        exit 0
    elif [[ "$arg" == "--upload" ]]; then
        UPLOAD=true
    elif [[ "$arg" == "--report-only" ]]; then
        RUN_TESTS=false
    elif [[ "$arg" == "--html" ]]; then
        HTML_REPORT=true
    elif [[ "$arg" == "--xml" ]]; then
        XML_REPORT=true
    elif [[ "$arg" == "--branch" ]]; then
        BRANCH_COVERAGE=true
    elif [[ "$arg" =~ ^--file=(.*) ]]; then
        COVERAGE_FILE="${BASH_REMATCH[1]}"
    elif [[ "$arg" =~ ^--test-module=(.*) ]]; then
        TEST_MODULE="${BASH_REMATCH[1]}"
    elif [[ "$arg" =~ ^--token=(.*) ]]; then
        CUSTOM_TOKEN="${BASH_REMATCH[1]}"
    else
        echo "⚠️ Unknown option: $arg"
        show_help
        exit 1
    fi
done

# Setup target for coverage
if [ -n "$COVERAGE_FILE" ]; then
    COVERAGE_TARGET="$COVERAGE_FILE"
else
    COVERAGE_TARGET="src/enchant_cli"
fi

# Ensure codecov-cli is installed
echo "🔄 Checking for codecov-cli..."
if ! command -v "$PROJECT_ROOT/.venv/bin/codecovcli" &> /dev/null; then
    echo "🔄 Installing codecov-cli in virtual environment..."
    "$PROJECT_ROOT/.venv/bin/pip" install codecov-cli
    
    # Verify installation
    if ! command -v "$PROJECT_ROOT/.venv/bin/codecovcli" &> /dev/null; then
        echo "❌ Failed to install codecov-cli. Attempting to install older codecov package..."
        "$PROJECT_ROOT/.venv/bin/pip" install codecov
    fi
fi

# Build coverage command
COVERAGE_ARGS="--cov=$COVERAGE_TARGET"

if [ "$XML_REPORT" = true ]; then
    COVERAGE_ARGS="$COVERAGE_ARGS --cov-report=xml"
fi

if [ "$HTML_REPORT" = true ]; then
    COVERAGE_ARGS="$COVERAGE_ARGS --cov-report=html:coverage_report"
fi

if [ "$BRANCH_COVERAGE" = true ]; then
    COVERAGE_ARGS="$COVERAGE_ARGS --cov-branch"
fi

# Run coverage tests if needed
if [ "$RUN_TESTS" = true ]; then
    echo "🧪 Running tests with coverage..."
    echo "📊 Coverage target: $COVERAGE_TARGET"
    echo "🔍 Coverage options: $COVERAGE_ARGS"
    
    # Run pytest with coverage
    # Try to find pytest in the virtual environment
    if [ -f "$PROJECT_ROOT/.venv/bin/pytest" ]; then
        PYTEST_CMD="$PROJECT_ROOT/.venv/bin/pytest"
    else
        # Fallback to system pytest
        PYTEST_CMD="pytest"
    fi
    
    # Add test module if specified
    if [ -n "$TEST_MODULE" ]; then
        echo "🔸 Running tests from specific module: $TEST_MODULE"
        PYTEST_ARGS="$COVERAGE_ARGS $TEST_MODULE"
    else
        PYTEST_ARGS="$COVERAGE_ARGS"
    fi
    
    echo "🔸 Running: $PYTEST_CMD $PYTEST_ARGS"
    
    if ! $PYTEST_CMD $PYTEST_ARGS; then
        echo "❌ Tests failed! Coverage report may be incomplete."
        exit 1
    fi
else
    echo "📊 Generating coverage report only (no tests)..."
fi

# Display coverage summary
if [ -f "coverage.xml" ]; then
    echo "📊 Coverage report generated: coverage.xml"
    echo "📋 Coverage summary:"
    
    # Extract coverage percentage from XML file
    if command -v grep &> /dev/null && command -v head &> /dev/null; then
        COVERAGE_PCT=$(grep -o 'line-rate="[0-9.]*"' coverage.xml | head -1 | grep -o '[0-9.]*')
        if [ -n "$COVERAGE_PCT" ]; then
            # Convert decimal to percentage
            COVERAGE_PCT=$(echo "$COVERAGE_PCT * 100" | bc)
            echo "📊 Overall coverage: $COVERAGE_PCT%"
        fi
    fi
else
    echo "⚠️ No coverage.xml file found. Tests may have failed or coverage reporting is disabled."
fi

if [ -d "coverage_report" ]; then
    echo "📊 HTML coverage report generated: coverage_report/index.html"
fi

# Upload to Codecov if requested
if [ "$UPLOAD" = true ]; then
    echo "🔄 Uploading coverage report to Codecov..."
    
    # Determine token to use (priority: custom arg > env var > default)
    if [ -n "$CUSTOM_TOKEN" ]; then
        UPLOAD_TOKEN="$CUSTOM_TOKEN"
    elif [ -n "$CODECOV_API_TOKEN" ]; then
        UPLOAD_TOKEN="$CODECOV_API_TOKEN"
    else
        UPLOAD_TOKEN="$CODECOV_TOKEN"
    fi
    
    # Create codecov.yml if it doesn't exist
    if [ ! -f "$PROJECT_ROOT/codecov.yml" ]; then
        echo "🔄 Creating default codecov.yml config file..."
        cat > "$PROJECT_ROOT/codecov.yml" << EOF
codecov:
  require_ci_to_pass: false

coverage:
  precision: 2
  round: down
  range: "70...100"
  status:
    project:
      default:
        target: auto
        threshold: 5%
        if_not_found: success

comment:
  layout: "reach, diff, flags, files"
  behavior: default
  require_changes: false
  require_base: no
  require_head: no
EOF
    fi
    
    # Try with Python module approach (most reliable)
    echo "🔄 Using Python module approach for upload..."
    PYTHON_CMD="$PROJECT_ROOT/.venv/bin/python -m codecov --file coverage.xml --token $UPLOAD_TOKEN --name enchant-cli"
    echo "🔸 Running codecov upload..."
    
    if $PYTHON_CMD 2>&1 | tee /tmp/codecov_output.log; then
        # Check if the log contains "Repository not found" but still show success
        if grep -q "Repository not found" /tmp/codecov_output.log; then
            echo "⚠️ Repository not found on Codecov - you need to register it at https://app.codecov.io/gh/Emasoft/enchant_cli"
            echo "✅ Coverage report generated successfully"
        else
            echo "✅ Successfully uploaded to Codecov!"
        fi
    else
        echo "⚠️ Python module upload failed. Trying with legacy client..."
        
        # Try with legacy codecov client
        if command -v "$PROJECT_ROOT/.venv/bin/codecov" &> /dev/null; then
            echo "🔄 Using legacy codecov client for upload..."
            LEGACY_CMD="$PROJECT_ROOT/.venv/bin/codecov -t $UPLOAD_TOKEN"
            echo "🔸 Running: $LEGACY_CMD"
            
            if $LEGACY_CMD; then
                echo "✅ Successfully uploaded to Codecov using legacy client!"
            else
                echo "⚠️ Legacy codecov upload failed. Trying with codecov-cli..."
                
                # Try codecov-cli as final fallback
                if command -v "$PROJECT_ROOT/.venv/bin/codecovcli" &> /dev/null; then
                    echo "🔄 Using codecov-cli for upload..."
                    cd "$PROJECT_ROOT"
                    UPLOAD_CMD="$PROJECT_ROOT/.venv/bin/codecovcli upload-process -t $UPLOAD_TOKEN"
                    echo "🔸 Running: $UPLOAD_CMD"
                    
                    if $UPLOAD_CMD; then
                        echo "✅ Successfully uploaded to Codecov!"
                    else
                        echo "❌ All codecov clients failed to upload. Please check your token and network connection."
                        exit 1
                    fi
                else
                    echo "❌ Failed to upload coverage to Codecov."
                    exit 1
                fi
            fi
        else
            echo "❌ No codecov clients found. Please install codecov module."
            exit 1
        fi
    fi
    
    echo "🔗 View coverage reports at: https://codecov.io/gh/$REPO_SLUG"
fi

echo "✅ Coverage operation completed successfully!"
exit 0