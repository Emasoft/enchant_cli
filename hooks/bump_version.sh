#!/bin/bash
# This script bumps the version in __init__.py
# It first tries to use bump-my-version, then falls back to a Python script if necessary

set -e

if command -v uv >/dev/null 2>&1; then
    # Try uv tool run approach
    uv tool run bump-my-version minor --commit --tag --allow-dirty || echo "WARNING: Version bump with uv failed, trying alternatives..."
elif [ -f ".venv/bin/bump-my-version" ]; then
    # Try direct from virtualenv
    .venv/bin/bump-my-version minor --commit --tag --allow-dirty || echo "WARNING: Version bump with .venv binary failed, trying alternatives..."
elif command -v bump-my-version &>/dev/null; then
    # Try system-installed version
    bump-my-version minor --commit --tag --allow-dirty || echo "WARNING: Version bump with global binary failed, trying alternatives..."
else
    # Fallback to Python script approach
    python -c '
import re, sys
init_file = "src/enchant_cli/__init__.py"
try:
    with open(init_file, "r") as f:
        content = f.read()
    version_match = re.search(r"__version__\s*=\s*\"([0-9]+)\.([0-9]+)\.([0-9]+)\"", content)
    if not version_match:
        print("WARNING: Version pattern not found in __init__.py")
        sys.exit(0)
    major, minor, patch = map(int, version_match.groups())
    new_minor = minor + 1
    new_version = f"{major}.{new_minor}.0"
    with open(init_file, "w") as f:
        f.write(re.sub(r"__version__\s*=\s*\"[0-9]+\.[0-9]+\.[0-9]+\"", f"__version__ = \"{new_version}\"", content))
    print(f"Bumped version to {new_version}")
except Exception as e:
    print(f"ERROR: {str(e)}")
    sys.exit(1)
'
fi