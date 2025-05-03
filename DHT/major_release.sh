#!/bin/bash

# Return error if executed directly - MUST BE PLACED AT THE BEGINNING
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    echo "Error: This script cannot be executed directly. All DHT scripts can only be called by the DHT Launcher in the project root. Please run dhtl.sh (or dhtl.bat) followed by the action you want to execute. For more informations use dhtl.sh --help"
    exit 1
fi

# Script to create a major version release
# This indicates a breaking change with backward incompatible changes

set -euo pipefail

# Print header
echo "===== Creating Major Version Release ====="
echo "This will increment the MAJOR version number, indicating breaking changes"
echo "Only use this for backward-incompatible API changes"
echo ""

# Check if version tool is available
if ! command -v bump-my-version &> /dev/null; then
    echo "bump-my-version not found. Installing..."
    python -m pip install bump-my-version
fi

# Run the version bump (major)
bump-my-version major --allow-dirty

# Get the new version
NEW_VERSION=$(grep -o '[0-9]\+\.[0-9]\+\.[0-9]\+' src/enchant_cli/__init__.py)
echo "Bumped to version $NEW_VERSION"

# Run validation
echo "Running validation tests..."
./release.sh

echo ""
echo "Major version bump to $NEW_VERSION complete!"
echo ""
echo "Next steps:"
echo "1. Review changes: git log -p"
echo "2. Commit the changes: git commit -am \"BREAKING CHANGE: Major version bump to $NEW_VERSION\""
echo "3. Push to GitHub: git push origin main --tags"
echo "4. Create a release on GitHub"
echo ""
echo "IMPORTANT: Update CHANGELOG.md with all breaking changes!"
