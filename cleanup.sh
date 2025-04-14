#!/usr/bin/env bash
# cleanup.sh - Removes clutter and build artifacts from the project directory.

set -eo pipefail # Exit on error

echo "🧹 Starting project cleanup..."

# 1. Remove Redundant Scripts and Empty/Typo Files
echo "🗑️ Removing redundant scripts and empty/typo files..."
rm -f final_release.sh verify_release.sh LICENCE MANIFEST
echo "   Removed final_release.sh, verify_release.sh, LICENCE, MANIFEST."

# 2. Remove Build Artifacts and Caches
echo "🗑️ Removing build artifacts and caches..."
rm -rf dist/
rm -rf src/*.egg-info/
rm -rf coverage_report/
rm -rf .pytest_cache/
rm -rf .ruff_cache/
rm -f report.html # Remove HTML test report
echo "   Removed dist/, src/*.egg-info/, coverage_report/, .pytest_cache/, .ruff_cache/, report.html."

# 3. Remove macOS .DS_Store Files
echo "🗑️ Removing macOS .DS_Store files..."
find . -name '.DS_Store' -delete -print || echo "   No .DS_Store files found or error during deletion."

# 4. Remove Python __pycache__ Directories
echo "🗑️ Removing Python __pycache__ directories..."
find . -type d -name '__pycache__' -exec rm -rf {} + -print || echo "   No __pycache__ directories found or error during deletion."

# 5. Remove Aider Files (Optional - Uncomment if sure)
# echo "🗑️ Removing Aider files (optional)..."
# rm -f .aider.chat.history.md .aider.input.history
# rm -rf .aider.tags.cache.v4/
# echo "   Removed Aider files."

# 6. Remove Potential Output/Test Files (Optional - VERIFY FIRST!)
# echo "🗑️ Removing potential old output/test files (optional - VERIFY FIRST!)..."
# rm -f "Unknown Author by Unknown Author - Chapter 1.txt"
# rm -f "Unknown Author by Unknown Author - Chapter 2.txt"
# rm -f translated_empty.txt
# rm -f translated_test.txt
# echo "   Removed potential old output/test files."

echo "✅ Cleanup script finished."
echo "➡️ Next steps:"
echo "   1. Activate your virtual environment:"
echo "      source .venv/bin/activate"
echo "   2. Regenerate requirements and uv.lock:"
echo "      uv pip compile pyproject.toml -o requirements.txt"
echo "      uv pip compile pyproject.toml --extra dev -o requirements-dev.txt"
echo "      uv pip sync requirements.txt requirements-dev.txt"
echo "   3. Commit the changes (including updated requirements*.txt and uv.lock):"
echo "      git add requirements.txt requirements-dev.txt uv.lock ."
echo "      git commit -m \"Clean up project files and update dependencies\""
