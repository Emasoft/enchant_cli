#!/usr/bin/env bash
# first_push.sh - Initializes git, commits, and force pushes to GitHub for the first time.
# WARNING: This script assumes you want to overwrite any existing history on the remote 'main' branch.

set -eo pipefail

# --- Configuration ---
GITHUB_USER="Emasoft"
REPO_NAME="enchant_cli"
GIT_EMAIL="713559+Emasoft@users.noreply.github.com" # Use the email associated with your GitHub account
GIT_USERNAME="Emasoft" # Your GitHub username or preferred name
REPO_URL="https://github.com/${GITHUB_USER}/${REPO_NAME}.git"
DEFAULT_BRANCH="main"

# --- Safety Check ---
# Check if .git directory exists to prevent accidental re-init if not intended
if [ -d ".git" ]; then
  read -p "⚠️ A .git directory already exists. This script will re-initialize it. Continue? (y/N) " -n 1 -r
  echo
  if [[ ! $REPLY =~ ^[Yy]$ ]]; then
      echo "Aborted."
      exit 1
  fi
  echo "Removing existing .git directory..."
  rm -rf .git
  # Add a check to ensure the directory was actually removed
  if [ -d ".git" ]; then
      echo "❌ Error: Failed to remove the existing .git directory. Please remove it manually ('rm -rf .git') and re-run the script."
      exit 1
  fi
fi

# --- Validation ---
echo "🔍 Validating critical files..."
[ -f "src/enchant_cli/__init__.py" ] || { echo "❌ Missing package init: src/enchant_cli/__init__.py"; exit 1; }
[ -f "src/enchant_cli/enchant_cli.py" ] || { echo "❌ Missing CLI module: src/enchant_cli/enchant_cli.py"; exit 1; }
[ -f "pyproject.toml" ] || { echo "❌ Missing pyproject.toml"; exit 1; }
echo "✅ Critical files found."

# --- Git Initialization ---
echo "✨ Initializing new git repository..."
git init -b "$DEFAULT_BRANCH"
echo "👤 Configuring local git user..."
git config user.name "$GIT_USERNAME"
git config user.email "$GIT_EMAIL"

# --- Get Version ---
# Determine Python command
PYTHON_CMD=python
if command -v python3 &> /dev/null; then
    PYTHON_CMD=python3
fi
VERSION=$($PYTHON_CMD -c 'from src.enchant_cli import __version__; print(__version__)' 2>/dev/null || echo "0.0.0-error")
if [[ "$VERSION" == "0.0.0-error" ]]; then
    echo "❌ Error: Could not determine version from src/enchant_cli/__init__.py"
    exit 1
fi
echo "ℹ️ Current version detected: $VERSION"

# --- First Commit ---
echo "➕ Adding all files..."
git add -A
echo "📝 Creating initial commit (version $VERSION)..."
git commit -m "Initial commit: v$VERSION"

# --- Remote Setup and Push ---
echo "🔗 Setting remote origin to $REPO_URL..."
# Check if remote 'origin' already exists and remove it if it does
if git remote | grep -q '^origin$'; then
    echo "   Remote 'origin' already exists. Removing it first."
    git remote remove origin
fi
git remote add origin "$REPO_URL"

echo "🚀 Force pushing to GitHub ($DEFAULT_BRANCH branch)..."
git push -uf origin "$DEFAULT_BRANCH" # Force push for the very first time

# --- Secret Setup Instructions ---
echo ""
echo "✅✅✅ Initial push complete! ✅✅✅"
echo ""
echo "🔒 IMPORTANT: Set up GitHub secrets using the 'gh' CLI:"
echo "   (Ensure you have the necessary environment variables exported locally: PYPI_API_TOKEN, OPENROUTER_API_KEY, CODECOV_API_TOKEN)"
echo ""
echo "gh secret set PYPI_API_TOKEN -b\"\$PYPI_API_TOKEN\" -r\"${GITHUB_USER}/${REPO_NAME}\""
echo "gh secret set OPENROUTER_API_KEY -b\"\$OPENROUTER_API_KEY\" -r\"${GITHUB_USER}/${REPO_NAME}\""
echo "gh secret set CODECOV_API_TOKEN -b\"\$CODECOV_API_TOKEN\" -r\"${GITHUB_USER}/${REPO_NAME}\""
echo ""
echo "➡️ Also, manually update the Codecov badge token in README.md!"
