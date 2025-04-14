#!/usr/bin/env bash
# install_apache_license.sh

# Check for required tools (curl or wget)
if ! command -v curl &> /dev/null && ! command -v wget &> /dev/null; then
    echo "Error: curl or wget is required to download the license file." >&2
    # Suggest installation based on common package managers
    if command -v apt-get &> /dev/null; then
        echo "Try: sudo apt-get update && sudo apt-get install curl wget" >&2
    elif command -v yum &> /dev/null; then
        echo "Try: sudo yum install curl wget" >&2
    elif command -v brew &> /dev/null; then
        echo "Try: brew install curl wget" >&2
    fi
    exit 1
fi

LICENSE_URL="https://www.apache.org/licenses/LICENSE-2.0.txt"
OUTPUT_FILE="LICENSE"

echo "⬇️  Downloading Apache 2.0 License from $LICENSE_URL..."

# Download official Apache 2.0 LICENSE file
if command -v curl &> /dev/null; then
    curl -fsSL "$LICENSE_URL" -o "$OUTPUT_FILE" # Use -f to fail silently on server errors, -s silent, -L follow redirects
elif command -v wget &> /dev/null; then
    wget -q "$LICENSE_URL" -O "$OUTPUT_FILE" # Use -q quiet
else
    # This check is redundant due to the initial check, but kept for safety
    echo "Error: Could not find curl or wget." >&2
    exit 1
fi

# Verify download was successful and contains expected text
if [ ! -s "$OUTPUT_FILE" ] || ! grep -q "Apache License" "$OUTPUT_FILE"; then
    echo "Error: Failed to download or verify the Apache LICENSE file from $LICENSE_URL." >&2
    rm -f "$OUTPUT_FILE" # Clean up failed download
    exit 1
fi

# No need to update setup.cfg as license is specified in pyproject.toml

echo "✅ Apache 2.0 LICENSE installed successfully as '$OUTPUT_FILE'."
echo "ℹ️  Ensure 'license = \"Apache-2.0\"' is set in your pyproject.toml [project] section."
echo "ℹ️  You may need to re-install the package if it was already installed:"
echo "   pip uninstall enchant-cli -y"
echo "   pip install -e ."

