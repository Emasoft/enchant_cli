#!/bin/bash
# Script to add "no direct execution" safety check to all shell scripts in DHT folder

set -eo pipefail

# Get script directory
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
PROJECT_ROOT=$(dirname "$SCRIPT_DIR")
DHT_DIR="$PROJECT_ROOT/DHT"

# Safety check - ensure the DHT directory exists
if [ ! -d "$DHT_DIR" ]; then
    echo "Error: DHT directory not found at $DHT_DIR"
    exit 1
fi

# The standard error message to add to scripts - placed after the shebang
SAFETY_CHECK="
# Return error if executed directly - MUST BE PLACED AT THE BEGINNING
if [[ \"\${BASH_SOURCE[0]}\" == \"\${0}\" ]]; then
    echo \"Error: This script cannot be executed directly. All DHT scripts can only be called by the DHT Launcher in the project root. Please run dhtl.sh (or dhtl.bat) followed by the action you want to execute. For more informations use dhtl.sh --help\"
    exit 1
fi
"

# Process each shell script in the DHT folder
echo "Adding direct execution safety check to all shell scripts in DHT folder..."
for script in "$DHT_DIR"/*.sh; do
    # Skip if not a file
    if [ ! -f "$script" ]; then
        continue
    fi
    
    # Get the script name
    script_name=$(basename "$script")
    
    # Check if the script already has the safety check
    if grep -q "This script cannot be executed directly" "$script"; then
        # If it has the safety check at the end, remove it and place it at the beginning
        if ! head -n 10 "$script" | grep -q "This script cannot be executed directly"; then
            echo "🔄 Relocating safety check in $script_name to the beginning..."
            
            # Create a temporary file
            tmp_file=$(mktemp)
            
            # Create a backup
            cp "$script" "${script}.bak"
            
            # Remove existing safety check
            grep -v "This script cannot be executed directly" "$script" | grep -v "Return error if executed directly" | grep -v "BASH_SOURCE\[0\]" > "$tmp_file"
            
            # Check if the first line is the shebang
            if head -n 1 "$tmp_file" | grep -q "^#!"; then
                # Extract the shebang line
                shebang=$(head -n 1 "$tmp_file")
                # Remove the first line
                tail -n +2 "$tmp_file" > "${tmp_file}.tmp"
                # Create a new file with shebang, safety check, and then the rest of the file
                echo "$shebang" > "$script"
                echo "$SAFETY_CHECK" >> "$script"
                cat "${tmp_file}.tmp" >> "$script"
                # Clean up
                rm "${tmp_file}.tmp"
            else
                # For files without a shebang (unlikely), put the safety check at the top
                echo "#!/usr/bin/env bash" > "$script"
                echo "$SAFETY_CHECK" >> "$script"
                cat "$tmp_file" >> "$script"
            fi
            
            # Clean up
            rm "$tmp_file"
            chmod +x "$script"
            
            echo "✅ Relocated safety check to the beginning of $script_name"
        else
            echo "✅ $script_name already has the safety check at the beginning"
        fi
        continue
    fi
    
    echo "📄 Processing $script_name..."
    
    # Create a temporary file
    tmp_file=$(mktemp)
    
    # Create a backup
    cp "$script" "${script}.bak"
    
    # Check if the first line is the shebang
    if head -n 1 "$script" | grep -q "^#!"; then
        # Extract the shebang line
        shebang=$(head -n 1 "$script")
        # Remove the first line
        tail -n +2 "$script" > "$tmp_file"
        # Create a new file with shebang, safety check, and then the rest of the file
        echo "$shebang" > "$script"
        echo "$SAFETY_CHECK" >> "$script"
        cat "$tmp_file" >> "$script"
    else
        # For files without a shebang (unlikely), put the safety check at the top
        echo "#!/usr/bin/env bash" > "$script"
        echo "$SAFETY_CHECK" >> "$script"
        cat "$script" > "$tmp_file"
        cat "$tmp_file" >> "$script"
    fi
    
    # Clean up
    rm "$tmp_file"
    chmod +x "$script"
    
    echo "✅ Added safety check to the beginning of $script_name"
done

echo "Completed adding safety checks to all shell scripts in DHT folder"