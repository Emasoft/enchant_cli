#!/bin/bash
# Test GitHub Actions locally with act

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}Testing GitHub Actions locally with act...${NC}"

# Check if act is installed
if ! command -v act &> /dev/null; then
    echo -e "${RED}act is not installed. Please install it with: brew install act${NC}"
    exit 1
fi

# Test different workflows
echo -e "\n${YELLOW}1. Testing lint job...${NC}"
act -j lint -P ubuntu-latest=catthehacker/ubuntu:act-latest

echo -e "\n${YELLOW}2. Testing dependency-check workflow...${NC}"
act workflow_run -W .github/workflows/dependency-check.yml -P ubuntu-latest=catthehacker/ubuntu:act-latest

echo -e "\n${YELLOW}3. Testing pre-commit workflow...${NC}"
act workflow_run -W .github/workflows/pre-commit.yml -P ubuntu-latest=catthehacker/ubuntu:act-latest

echo -e "\n${GREEN}Done! Check the output above for any issues.${NC}"
