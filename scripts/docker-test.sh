#!/usr/bin/env bash
# -*- coding: utf-8 -*-

# Script to run tests in Docker container with uv

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Default values
SERVICE="test"
BUILD_FRESH=false
INTERACTIVE=false
CUSTOM_COMMAND=""

# Function to display usage
usage() {
    echo "Usage: $0 [OPTIONS] [pytest arguments]"
    echo ""
    echo "Options:"
    echo "  -b, --build         Force rebuild Docker image"
    echo "  -i, --interactive   Run interactive shell in container"
    echo "  -s, --service       Docker service to run (default: test)"
    echo "  -h, --help          Display this help message"
    echo ""
    echo "Examples:"
    echo "  $0                              # Run all tests"
    echo "  $0 -b                           # Rebuild image and run all tests"
    echo "  $0 tests/test_translation.py    # Run specific test file"
    echo "  $0 -i                           # Start interactive shell"
    echo "  $0 -s test-specific tests/test_translation.py::test_init_local -v"
    exit 1
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -b|--build)
            BUILD_FRESH=true
            shift
            ;;
        -i|--interactive)
            INTERACTIVE=true
            SERVICE="shell"
            shift
            ;;
        -s|--service)
            SERVICE="$2"
            shift 2
            ;;
        -h|--help)
            usage
            ;;
        *)
            # Collect remaining arguments as pytest args
            CUSTOM_COMMAND="${CUSTOM_COMMAND} $1"
            shift
            ;;
    esac
done

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}Error: Docker is not running${NC}"
    echo "Please start Docker and try again"
    exit 1
fi

# Check for required environment variables for remote tests
if [[ -z "${OPENROUTER_API_KEY:-}" ]]; then
    echo -e "${YELLOW}Warning: OPENROUTER_API_KEY not set${NC}"
    echo "Remote API tests will be skipped"
fi

# Build or rebuild if requested
if [[ "$BUILD_FRESH" == true ]]; then
    echo -e "${GREEN}Building Docker image...${NC}"
    docker-compose build --no-cache "$SERVICE"
else
    echo -e "${GREEN}Building Docker image (using cache)...${NC}"
    docker-compose build "$SERVICE"
fi

# Create test-results directory if it doesn't exist
mkdir -p test-results

# Run the appropriate service
if [[ "$INTERACTIVE" == true ]]; then
    echo -e "${GREEN}Starting interactive shell...${NC}"
    docker-compose run --rm "$SERVICE"
elif [[ -n "$CUSTOM_COMMAND" ]]; then
    echo -e "${GREEN}Running custom command: uv run pytest${CUSTOM_COMMAND}${NC}"
    docker-compose run --rm "$SERVICE" uv run pytest ${CUSTOM_COMMAND}
else
    echo -e "${GREEN}Running all tests...${NC}"
    docker-compose up --abort-on-container-exit "$SERVICE"
fi

# Check exit code
EXIT_CODE=$?

if [[ $EXIT_CODE -eq 0 ]]; then
    echo -e "${GREEN}Tests completed successfully!${NC}"

    # Show coverage report location if it exists
    if [[ -f "htmlcov/index.html" ]]; then
        echo -e "${GREEN}Coverage report available at: htmlcov/index.html${NC}"
    fi
    if [[ -f "test-results/junit.xml" ]]; then
        echo -e "${GREEN}JUnit report available at: test-results/junit.xml${NC}"
    fi
else
    echo -e "${RED}Tests failed with exit code: $EXIT_CODE${NC}"
fi

exit $EXIT_CODE
