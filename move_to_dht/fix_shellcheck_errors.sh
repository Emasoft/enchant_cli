#!/bin/bash
# Script to fix common shellcheck errors in all shell scripts in DHT folder

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

# Process each shell script in the DHT folder
echo "Fixing common shellcheck errors in all shell scripts in DHT folder..."
for script in "$DHT_DIR"/*.sh; do
    # Skip if not a file
    if [ ! -f "$script" ]; then
        continue
    fi
    
    # Get the script name
    script_name=$(basename "$script")
    echo "📄 Processing $script_name..."
    
    # Create a backup first
    cp "$script" "${script}.bak"
    
    # Fix 1: Remove trailing "exit 1" and "fi" that don't match any if statement
    # This is a common error that occurs with the safety checks
    
    # Check if the last line is 'fi' with nothing after it
    if grep -q 'fi *$' "$script" | tail -n 2; then
        # Create a temporary file
        tmp_file=$(mktemp)
        
        # Find the last occurrence of 'fi' and remove everything after it
        # This gets the line number of the last 'fi' in the file
        last_fi_line=$(grep -n '^fi *$' "$script" | tail -n 1 | cut -d: -f1)
        
        if [ -n "$last_fi_line" ]; then
            # Check if there's code before the last 'fi'
            # This makes sure we're not deleting the entire file content
            if [ "$last_fi_line" -gt 10 ]; then
                # Get all lines up to the last 'fi'
                head -n "$last_fi_line" "$script" > "$tmp_file"
                
                # Replace the original script with the fixed version
                mv "$tmp_file" "$script"
                chmod +x "$script"
                
                echo "✅ Fixed trailing 'fi' in $script_name"
            fi
        fi
    fi
    
    # Fix 2: Fix empty 'then' clauses by adding 'true' command
    # Create a temporary file
    tmp_file=$(mktemp)
    
    # Find and replace empty 'then' clauses
    awk '{
        if ($0 ~ /^if.*then$/ || $0 ~ /^if.*then *#/ || ($0 ~ /^if/ && $0 !~ /then/ && getline && $0 ~ /^then$/)) {
            print $0
            line = getline
            if (line == 0 || $0 ~ /^fi$/) {
                print "    true  # Added by fix_shellcheck_errors.sh"
            }
            print $0
        } else {
            print $0
        }
    }' "$script" > "$tmp_file"
    
    # Replace the original script with the fixed version
    mv "$tmp_file" "$script"
    chmod +x "$script"
    
    # Check if shellcheck still reports errors
    if shellcheck --severity=error "$script" 2>&1 | grep -v "Loading .zprofile" | grep -q "SC1089\|SC1056\|SC1048"; then
        echo "⚠️ Script $script_name still has shellcheck errors"
    else
        echo "✅ Script $script_name passes shellcheck"
    fi
done

echo "Completed fixing common shellcheck errors in all shell scripts in DHT folder"