#!/bin/bash
set -eo pipefail


echo "🚀 Starting automated pre-release preparation..."
echo "   This script will sync, commit changes (if any), validate, and push."
echo "   Publishing to PyPI still requires manually creating a GitHub Release."
echo "   NOTE: Version bumping and tagging are handled automatically on commit by pre-commit hooks."

# Ensure environment is synchronized
echo "🔄 Synchronizing environment with uv..."
uv sync || { echo >&2 "❌ uv sync failed."; exit 1; }

# Check for uncommitted changes and commit them
echo "🔍 Checking for uncommitted changes..."
if ! git diff --quiet HEAD; then
    echo "⚠️ Uncommitted changes detected. Staging and committing automatically..."
    git add -A
    # Use a standard commit message. The pre-commit hook will trigger the version bump.
    git commit -m "chore: Prepare for release validation" || { echo >&2 "❌ git commit failed."; exit 1; }
    echo "✅ Changes committed. Pre-commit hooks (including version bump) should have run."
else
    echo "✅ Working directory is clean."
fi

RELEASE_SCRIPT="./release.sh"
if [ ! -f "$RELEASE_SCRIPT" ]; then
    echo >&2 "❌ Error: The validation script '$RELEASE_SCRIPT' was not found."
    exit 1
fi
if [ ! -x "$RELEASE_SCRIPT" ]; then
    echo >&2 "❌ Error: The validation script '$RELEASE_SCRIPT' is not executable. Run 'chmod +x $RELEASE_SCRIPT'."
    exit 1
fi

echo "🔍 Executing validation script $RELEASE_SCRIPT..."
"$RELEASE_SCRIPT"
VALIDATION_EXIT_CODE=$?

if [ $VALIDATION_EXIT_CODE -ne 0 ]; then
    echo >&2 "❌ Local pre-release validation failed. Please fix the issues reported by '$RELEASE_SCRIPT'."
    exit $VALIDATION_EXIT_CODE
else
    echo ""
    echo "✅✅✅ All local validations passed! ✅✅✅"
    echo ""
    echo "🚀 Pushing latest commit and tags to GitHub..."
    # Assuming 'main' is the default branch and 'origin' is the remote name
    git push origin main --tags || { echo >&2 "❌ git push failed."; exit 1; }
    echo "✅ Push successful."
    echo ""
    echo "➡️ Next Step to Publish:"
    echo "   1. Create a GitHub Release:"
    echo "      - Go to your repository's 'Releases' page on GitHub."
    echo "      - Click 'Draft a new release'."
    echo "      - Choose the latest tag that was just pushed (e.g., vX.Y.Z)."
    echo "      - Add release notes."
    echo "      - Click 'Publish release'."
    echo ""
    echo "   2. Monitor the GitHub Action:"
    echo "      - Publishing the GitHub Release will trigger the 'Publish Python Package' workflow."
    echo "      - Check the 'Actions' tab in your GitHub repository to monitor its progress."
    echo "      - This workflow will build the package again and publish it to PyPI."
    echo ""
    echo "📦 The package will be published to PyPI by the GitHub Action, not by this script."
    echo "🔒 Ensure GitHub secrets (PYPI_API_TOKEN, OPENROUTER_API_KEY, CODECOV_API_TOKEN) were set up during initial push (see first_push.sh or docs/environment.md)."
fi

exit $VALIDATION_EXIT_CODE
