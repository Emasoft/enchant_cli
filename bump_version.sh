#!/bin/bash
set -eo pipefail

# This script is now just a wrapper around bump-my-version
# It assumes .bumpversion.toml is configured correctly to update necessary files.

if [ -z "$1" ]; then
  echo "Usage: ./bump_version.sh [major|minor|patch|build|alpha|beta|rc|final]"
  echo "       (Or any other part defined in .bumpversion.toml)"
  exit 1
fi

PART=$1

# Check if bump-my-version is installed
if ! command -v bump-my-version &> /dev/null; then
    echo "Error: bump-my-version command not found." >&2
    echo "Please install it: pip install bump-my-version" >&2
    exit 1
fi

echo "🚀 Bumping version part: $PART"

# Run bump-my-version with the specified part
# Assumes --commit and --tag are configured in .bumpversion.toml if desired
bump-my-version bump "$PART"

# Get the new version for confirmation message
NEW_VERSION=$(bump-my-version show current_version)

echo "✅ Version bumped to $NEW_VERSION"
echo "ℹ️  Remember to 'git push --follow-tags' to push the changes and the new tag."

