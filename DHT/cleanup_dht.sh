#!/bin/bash
# Script to clean up the DHT directory structure and remove unnecessary files

set -eo pipefail

# Get script directory
SCRIPT_DIR="$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
PROJECT_ROOT=$(dirname "$SCRIPT_DIR")

# Force removal of backups directory flag
FORCE_REMOVE_BACKUPS=${FORCE_REMOVE_BACKUPS:-false}

# Function to display banner messages
print_banner() {
    echo "🧹 $1"
    echo "=================================================="
}

# Function to determine if file is referenced by any DHT script
is_file_referenced() {
    local file_pattern="$1"
    local referenced=false
    
    # Convert to regex-friendly pattern
    file_pattern=$(basename "$file_pattern" | sed 's/\./\\./g')
    
    # Search in all shell scripts
    if grep -r --include="*.sh" -E "$file_pattern" "$SCRIPT_DIR" | grep -v "cleanup_dht.sh" > /dev/null; then
        referenced=true
    fi
    
    # Search in Python scripts
    if grep -r --include="*.py" -E "$file_pattern" "$SCRIPT_DIR" > /dev/null; then
        referenced=true
    fi
    
    # Search in batch files
    if grep -r --include="*.bat" -E "$file_pattern" "$SCRIPT_DIR" > /dev/null; then
        referenced=true
    fi
    
    # Search in the main dhtl.sh
    if grep -E "$file_pattern" "$PROJECT_ROOT/dhtl.sh" > /dev/null; then
        referenced=true
    fi
    
    $referenced
}

# Main execution
print_banner "Cleaning DHT Directory Structure"

# 1. Remove backup files in DHT/backups
print_banner "Checking DHT/backups for references"
backup_dir="$SCRIPT_DIR/backups"

if [ -d "$backup_dir" ]; then
    echo "🔍 Checking for script references to backup files..."
    referenced_files=0
    
    for backup_file in "$backup_dir"/*; do
        if is_file_referenced "$backup_file"; then
            echo "⚠️ File still referenced: $(basename "$backup_file")"
            referenced_files=$((referenced_files+1))
        fi
    done
    
    if [ $referenced_files -eq 0 ] || [ "$FORCE_REMOVE_BACKUPS" = "true" ]; then
        if [ $referenced_files -gt 0 ] && [ "$FORCE_REMOVE_BACKUPS" = "true" ]; then
            echo "⚠️ $referenced_files backup files are still referenced"
            echo "⚠️ Forcing removal of backups directory as requested"
        else
            echo "✅ No backup files are referenced by DHT scripts"
        fi
        echo "🧹 Removing DHT/backups directory..."
        rm -rf "$backup_dir"
        echo "✅ Backup directory removed"
    else
        echo "❌ $referenced_files backup files are still referenced - cannot remove directory"
        echo "   Please fix the references first or use FORCE_REMOVE_BACKUPS=true"
    fi
else
    echo "✅ DHT/backups directory does not exist"
fi

# 2. Remove duplicate modules between modules/ and dhtl_refactored/
print_banner "Checking for duplicate modules"
modules_dir="$SCRIPT_DIR/modules"
refactored_dir="$SCRIPT_DIR/dhtl_refactored"

if [ -d "$modules_dir" ] && [ -d "$refactored_dir" ]; then
    echo "🔍 Checking for duplicated modules..."
    
    # Create a list of modules in both directories
    modules_list=$(find "$modules_dir" -name "*.sh" -type f -exec basename {} \; | sort)
    refactored_list=$(find "$refactored_dir" -name "*.sh" -type f -exec basename {} \; | sort)
    
    # Find duplicates
    duplicates=$(comm -12 <(echo "$modules_list") <(echo "$refactored_list"))
    
    if [ -n "$duplicates" ]; then
        echo "🔍 Found duplicated modules:"
        while read -r module; do
            echo "  - $module"
            
            # Check if the module in modules/ is referenced
            if is_file_referenced "$modules_dir/$module"; then
                echo "    ⚠️ Module in modules/ is referenced - keeping both versions"
            else
                echo "    🧹 Removing duplicate from modules/ directory..."
                rm -f "$modules_dir/$module"
                echo "    ✅ Removed: $modules_dir/$module"
            fi
        done <<< "$duplicates"
    else
        echo "✅ No duplicate modules found"
    fi
else
    echo "⚠️ One or both module directories do not exist"
fi

# 3. Remove temporary output directories
print_banner "Cleaning temporary output directories"

# Find and clean output directories
output_dirs=$(find "$SCRIPT_DIR" -type d -name "output" -o -name "temp_*" -o -name "output_*")

if [ -n "$output_dirs" ]; then
    echo "🧹 Removing temporary output directories..."
    
    while read -r output_dir; do
        echo "  - Removing: $output_dir"
        rm -rf "$output_dir"
    done <<< "$output_dirs"
    
    echo "✅ Temporary output directories removed"
else
    echo "✅ No temporary output directories found"
fi

# 4. Find and remove completely unused scripts
print_banner "Cleaning unused scripts"

# Array of essential scripts that should not be deleted even if not referenced
essential_scripts=(
    "backup_utils.sh"
    "process_guardian.py"
    "bash_parser.py"
    "cleanup_dht.sh" 
    "cleanup_temp_folders.sh"
    "move_tree_sitter.sh"
)

# Find all scripts
all_scripts=$(find "$SCRIPT_DIR" -name "*.sh" -o -name "*.py" -o -name "*.bat" | sort)

echo "🔍 Checking for unused scripts..."
removed_count=0

while read -r script_path; do
    script_name=$(basename "$script_path")
    
    # Skip essential scripts
    if [[ " ${essential_scripts[@]} " =~ " ${script_name} " ]]; then
        echo "  - Keeping essential script: $script_name"
        continue
    fi
    
    # Skip scripts in test directories
    if [[ "$script_path" == *"/tests/"* ]]; then
        continue
    fi
    
    # Check if this script is referenced by any other script
    if ! is_file_referenced "$script_path"; then
        # Additional check - attempt to grep inside the file for known DHT functions
        # This helps identify entry-point scripts that might not be referenced
        if grep -q "dhtl\|DHT\|backup_project\|git_safeguard" "$script_path"; then
            echo "  - Keeping script with DHT functions: $script_name"
        else
            echo "  - Removing unused script: $script_name"
            rm -f "$script_path"
            removed_count=$((removed_count+1))
        fi
    fi
done <<< "$all_scripts"

echo "✅ Cleanup complete - removed $removed_count unused scripts"

# 5. Delete any empty directories 
print_banner "Removing empty directories"

find "$SCRIPT_DIR" -type d -empty | while read -r empty_dir; do
    # Skip essential directories
    if [[ "$empty_dir" == *"__pycache__"* || "$empty_dir" == *".git"* ]]; then
        continue
    fi
    
    echo "  - Removing empty directory: $(basename "$empty_dir")"
    rmdir "$empty_dir"
done

echo "✅ Empty directories removed"

print_banner "DHT Cleanup Complete"
echo "The DHT directory has been cleaned of unnecessary files and directories."
echo "Remember to run appropriate tests to ensure functionality is preserved."