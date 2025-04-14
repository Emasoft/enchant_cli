#!/bin/bash
set -eo pipefail


echo "🚀 Starting local pre-release validation using release.sh..."
echo "   This script prepares for a release but does NOT publish to PyPI."
echo "   Publishing is handled by the GitHub Action triggered by a GitHub Release."

RELEASE_SCRIPT="./release.sh"
if [ ! -f "$RELEASE_SCRIPT" ]; then
    echo >&2 "❌ Error: The validation script '$RELEASE_SCRIPT' was not found."
    exit 1
fi
if [ ! -x "$RELEASE_SCRIPT" ]; then
    echo >&2 "❌ Error: The validation script '$RELEASE_SCRIPT' is not executable. Attempting to fix..."
    chmod +x "$RELEASE_SCRIPT"
    if [ ! -x "$RELEASE_SCRIPT" ]; then
        echo >&2 "❌ Error: Failed to make '$RELEASE_SCRIPT' executable. Please fix permissions manually."
        exit 1
    fi
fi

echo "🔍 Executing $RELEASE_SCRIPT..."
"$RELEASE_SCRIPT"
VALIDATION_EXIT_CODE=$?

if [ $VALIDATION_EXIT_CODE -ne 0 ]; then
    echo >&2 "❌ Local pre-release validation failed. Please fix the issues reported by '$RELEASE_SCRIPT'."
    exit $VALIDATION_EXIT_CODE
else
    echo ""
    echo "✅✅✅ All local validations passed! ✅✅✅"
    echo ""
    echo "➡️ Next Steps to Publish (after initial push is done via first_push.sh):"
    echo "   1. Ensure the current version is correct. If needed, bump the version using:"
    echo "      ./bump_version.sh [major|minor|patch]"
    echo "      (This should create a new commit and tag automatically based on .bumpversion.toml)"
    echo ""
    echo "   2. Push the commit and the new tag to GitHub:"
    echo "      git push origin main --tags"
    echo "      (Replace 'main' if your default branch is different)"
    echo ""
    echo "   3. Create a GitHub Release:"
    echo "      - Go to your repository's 'Releases' page on GitHub."
    echo "      - Click 'Draft a new release'."
    echo "      - Choose the tag you just pushed (e.g., vX.Y.Z)."
    echo "      - Add release notes."
    echo "      - Click 'Publish release'."
    echo ""
    echo "   4. Monitor the GitHub Action:"
    echo "      - Publishing the GitHub Release will trigger the 'Publish Python Package' workflow."
    echo "      - Check the 'Actions' tab in your GitHub repository to monitor its progress."
    echo "      - This workflow will build the package again and publish it to PyPI."
    echo ""
    echo "📦 The package will be published to PyPI by the GitHub Action, not by this script."
fi

exit $VALIDATION_EXIT_CODE
