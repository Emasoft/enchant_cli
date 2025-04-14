#!/usr/bin/env bash
# resetgit.sh - WARNING: This will DESTROY all git history permanently!

set -e # Exit on error

read -p "⚠️ WARNING: This will permanently delete the .git directory and all history. Are you sure? (y/N) " -n 1 -r
echo # Move to a new line
if [[ ! $REPLY =~ ^[Yy]$ ]]
then
    echo "Aborted."
    exit 1
fi

# 1. Remove existing git configuration
echo "🔥 Removing existing .git directory..."
rm -rf .git

# 2. Create fresh repository
echo "✨ Initializing new git repository..."
git init -b main # Initialize and set default branch name to main

# 3. Add all current files
echo "➕ Adding all files..."
git add --all

# 4. Create initial commit
# Determine Python command
PYTHON_CMD=python
if command -v python3 &> /dev/null; then
    PYTHON_CMD=python3
fi

# Get version from __init__.py (assuming it exists and is correct)
VERSION=$($PYTHON_CMD -c 'from src.enchant_cli import __version__; print(__version__)' 2>/dev/null || echo "0.0.0-unknown")

echo "📝 Creating initial commit (version $VERSION)..."
git commit -m "Initial commit: v$VERSION"

echo "✅ Git history reset and initial commit created."
echo "ℹ️  Remember to set your remote origin: git remote add origin <your-repo-url>"
echo "ℹ️  And perform the first push: git push -u origin main"

