#!/bin/bash
# Script to move all scripts to DHT folder and delete helpers directory

# Get script directory
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
PROJECT_ROOT=$(dirname "$SCRIPT_DIR")
DHT_DIR="$PROJECT_ROOT/DHT"

# Ensure DHT directory exists
mkdir -p "$DHT_DIR"

# Step 1: Move all shell scripts except dhtl.sh to DHT
echo "Moving shell scripts from project root to DHT..."
for script in "$PROJECT_ROOT"/*.sh; do
    # Skip dhtl.sh and this script
    if [[ "$script" != *"dhtl.sh"* && "$script" != *"move_scripts.sh"* ]]; then
        # Get the base name
        base_name=$(basename "$script")
        
        # Check if destination already exists
        if [ -f "$DHT_DIR/$base_name" ]; then
            echo "File $base_name already exists in DHT folder, replacing..."
            mv -f "$script" "$DHT_DIR/" && echo "Replaced $base_name in DHT folder"
        else
            echo "Moving $base_name to DHT folder..."
            mv "$script" "$DHT_DIR/" && echo "Moved $base_name to DHT folder"
        fi
    fi
done

# Step 2: Move all Windows batch files except dhtl.bat to DHT
echo "Moving batch files from project root to DHT..."
for batch in "$PROJECT_ROOT"/*.bat; do
    # Skip if it doesn't exist and dhtl.bat
    if [ -f "$batch" ] && [[ "$batch" != *"dhtl.bat"* ]]; then
        # Get the base name
        base_name=$(basename "$batch")
        
        # Check if destination already exists
        if [ -f "$DHT_DIR/$base_name" ]; then
            echo "File $base_name already exists in DHT folder, replacing..."
            mv -f "$batch" "$DHT_DIR/" && echo "Replaced $base_name in DHT folder"
        else
            echo "Moving $base_name to DHT folder..."
            mv "$batch" "$DHT_DIR/" && echo "Moved $base_name to DHT folder"
        fi
    fi
done

# Step 3: Move all scripts from helpers folder to DHT (recursively)
echo "Moving all files from helpers/ to DHT..."
find "$PROJECT_ROOT/helpers" -type f -not -path "*/\.*" | while read -r file; do
    # Get the base name
    base_name=$(basename "$file")
    
    # Check if destination already exists
    if [ -f "$DHT_DIR/$base_name" ]; then
        echo "File $base_name already exists in DHT folder, replacing..."
        mv -f "$file" "$DHT_DIR/" && echo "Replaced $base_name in DHT folder"
    else
        echo "Moving $base_name to DHT folder..."
        mv "$file" "$DHT_DIR/" && echo "Moved $base_name to DHT folder"
    fi
done

# Step 4: Delete the helpers directory after moving everything
echo "Removing helpers directory..."
rm -rf "$PROJECT_ROOT/helpers"

# Step 5: Verify no scripts left in project root (except dhtl.sh/bat)
echo "Verifying all scripts have been moved..."
root_scripts=$(find "$PROJECT_ROOT" -maxdepth 1 -type f \( -name "*.sh" -o -name "*.bat" \) | grep -v "dhtl" | wc -l)
if [ "$root_scripts" -gt 0 ]; then
    echo "⚠️ Warning: Found $root_scripts scripts still in project root!"
    find "$PROJECT_ROOT" -maxdepth 1 -type f \( -name "*.sh" -o -name "*.bat" \) | grep -v "dhtl"
else
    echo "✅ Success: No scripts left in project root except dhtl.sh/bat"
fi

echo "Files moved to DHT folder and helpers directory removed."
echo "To run ruff on the Python files in DHT:"
echo "cd $PROJECT_ROOT && ruff check --ignore E203,E402,E501,E266,W505,F841,F842,F401,W293,I001,F811,UP015,C901,W291 --isolated --fix --output-format full ./DHT/*.py"