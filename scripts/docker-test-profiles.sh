#!/bin/bash
# Run Docker tests with different profiles

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo "🐳 EnChANT Book Manager - Docker Test Suite with Profiles"
echo "========================================================"
echo ""

# Function to run tests with a specific profile
run_profile() {
    local profile=$1
    local service=$2

    echo -e "${YELLOW}Running $profile profile tests...${NC}"
    echo "Profile: $profile"
    echo "Service: $service"
    echo ""

    # Build the image
    docker-compose -f docker-compose.test.yml build $service

    # Run the tests
    if docker-compose -f docker-compose.test.yml run --rm $service; then
        echo -e "${GREEN}✅ $profile tests passed!${NC}"
        return 0
    else
        echo -e "${RED}❌ $profile tests failed!${NC}"
        return 1
    fi
}

# Parse command line arguments
PROFILE=${1:-all}

case $PROFILE in
    local)
        run_profile "Local" "test-local"
        ;;
    remote)
        run_profile "Remote (CI)" "test-remote"
        ;;
    full)
        run_profile "Full" "test-full"
        ;;
    build)
        run_profile "Build" "test-project-build"
        ;;
    all)
        echo "Running all test profiles..."
        echo ""

        failed=0

        # Run each profile
        for profile in "local:test-local" "remote:test-remote" "full:test-full"; do
            IFS=':' read -r name service <<< "$profile"
            if ! run_profile "$name" "$service"; then
                failed=$((failed + 1))
            fi
            echo ""
        done

        # Summary
        echo "========================================"
        if [ $failed -eq 0 ]; then
            echo -e "${GREEN}✅ All profiles passed!${NC}"
        else
            echo -e "${RED}❌ $failed profile(s) failed!${NC}"
            exit 1
        fi
        ;;
    *)
        echo "Usage: $0 [local|remote|full|build|all]"
        echo ""
        echo "Profiles:"
        echo "  local  - Development environment tests"
        echo "  remote - CI/GitHub Actions environment tests"
        echo "  full   - All tests with full coverage"
        echo "  build  - Project build and setup tests"
        echo "  all    - Run all profiles (default)"
        exit 1
        ;;
esac
