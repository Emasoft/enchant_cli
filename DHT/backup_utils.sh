#!/bin/bash
# Utility script for DHT backup and restore operations

set -eo pipefail

# Get script directory
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
PROJECT_ROOT=$(dirname "$SCRIPT_DIR")

# Function to display banner messages
print_banner() {
    echo "📦 $1"
    echo "=================================================="
}

# Function to create a backup of the whole project or specific paths
backup_project() {
    local backup_name="enchant_cli_backup_$(date +"%Y%m%d_%H%M%S")"
    local backup_type="partial"
    local backup_paths=()
    local untracked_only=false
    
    # Process arguments
    if [[ "$1" == "all" ]]; then
        backup_type="full"
        backup_name="${backup_name}_full"
        backup_paths=("$PROJECT_ROOT")
    elif [[ "$1" == "untracked" ]]; then
        backup_type="untracked"
        backup_name="${backup_name}_untracked"
        untracked_only=true
        
        # Check if git command exists
        if ! command -v git &> /dev/null; then
            echo "❌ Error: git command not found, required for untracked files backup"
            return 1
        fi
        
        # Check if current directory is a git repository
        if ! git -C "$PROJECT_ROOT" rev-parse --is-inside-work-tree &> /dev/null; then
            echo "❌ Error: Not a git repository, required for untracked files backup"
            return 1
        fi
        
        # Get all untracked files and directories, including those ignored by gitignore
        echo "🔍 Identifying all untracked files (including those in .gitignore)..."
        local untracked_files=$(git -C "$PROJECT_ROOT" ls-files --others)
        
        if [[ -z "$untracked_files" ]]; then
            echo "⚠️ No untracked files found in the project"
            return 0
        fi
        
        # Convert to array of full paths
        while IFS= read -r file; do
            # Skip empty lines
            [[ -z "$file" ]] && continue
            
            # Skip common temporary and cache patterns, but keep other ignored files
            if [[ "$file" == *"__pycache__"* || 
                  "$file" == *".pytest_cache"* || 
                  "$file" == *"node_modules"* || 
                  "$file" == *".DS_Store" || 
                  "$file" == "*.zip" || 
                  "$file" == *.so || 
                  "$file" == *.pyc ||
                  "$file" == *.o ||
                  "$file" == *".git/"* ]]; then
                continue
            fi
            
            backup_paths+=("$PROJECT_ROOT/$file")
        done <<< "$untracked_files"
        
        # Check if we have any files to backup after filtering
        if [[ ${#backup_paths[@]} -eq 0 ]]; then
            echo "⚠️ No untracked files found after filtering temporary files"
            return 0
        fi
    else
        # Add each path to backup_paths
        for path in "$@"; do
            # Check if path is absolute or relative
            if [[ "$path" == /* ]]; then
                # Absolute path, check if it's within project
                if [[ "$path" == "$PROJECT_ROOT"* ]]; then
                    backup_paths+=("$path")
                else
                    echo "❌ Error: Path is outside project directory: $path"
                    echo "Paths must be within the project directory: $PROJECT_ROOT"
                    return 1
                fi
            else
                # Relative path, make it absolute
                backup_paths+=("$PROJECT_ROOT/$path")
            fi
        done
        backup_name="${backup_name}_partial"
    fi
    
    # Create backup directory if it doesn't exist
    mkdir -p "$PROJECT_ROOT/backups"
    
    # Check if zip is available
    if ! command -v zip &> /dev/null; then
        echo "❌ Error: zip command not found"
        echo "Please install zip to create backup files"
        return 1
    fi

    # Create backup
    if [[ "$backup_type" == "full" ]]; then
        print_banner "Creating full project backup"
        echo "🔍 Creating backup: backups/${backup_name}.zip"
        
        # Go to project root and create the backup
        (cd "$PROJECT_ROOT" && zip -q -r "backups/${backup_name}.zip" . \
            -x "*.git/*" \
            -x "*.venv/*" \
            -x "*.venv_windows/*" \
            -x "*__pycache__/*" \
            -x "*.pytest_cache/*" \
            -x "*node_modules/*" \
            -x "*.DS_Store" \
            -x "*.zip" \
            -x "backups/*.zip") || {
            echo "❌ Error: Failed to create backup"
            return 1
        }
        
        echo "✅ Full project backup created: backups/${backup_name}.zip"
    else
        print_banner "Creating partial backup of specified paths"
        echo "🔍 Creating backup: backups/${backup_name}.zip"
        
        # Check if any specified paths exist
        local paths_exist=false
        for path in "${backup_paths[@]}"; do
            if [ -e "$path" ]; then
                paths_exist=true
                break
            fi
        done
        
        if [ "$paths_exist" != true ]; then
            echo "❌ Error: None of the specified paths exist"
            return 1
        fi
        
        # Go to project root and create the backup of specified paths
        (cd "$PROJECT_ROOT" && zip -q -r "backups/${backup_name}.zip" "${backup_paths[@]}" \
            -x "*.git/*" \
            -x "*.venv/*" \
            -x "*.venv_windows/*" \
            -x "*__pycache__/*" \
            -x "*.pytest_cache/*" \
            -x "*node_modules/*" \
            -x "*.DS_Store" \
            -x "*.zip") || {
            echo "❌ Error: Failed to create backup"
            return 1
        }
        
        echo "✅ Partial backup created: backups/${backup_name}.zip"
        echo "📦 Included paths:"
        for path in "${backup_paths[@]}"; do
            if [ -e "$path" ]; then
                echo "  - ${path#$PROJECT_ROOT/}"
            fi
        done
    fi
    
    # Return success
    return 0
}

# Function to restore from a backup
restore_project() {
    print_banner "Restoring from backup"
    
    local backup_file=""
    
    # Check if backup file is specified
    if [[ -n "$1" ]]; then
        # Check if it's a full path or just a filename
        if [[ "$1" == /* ]]; then
            # It's a full path
            backup_file="$1"
        else
            # It's just a filename, prepend backups directory
            backup_file="$PROJECT_ROOT/backups/$1"
        fi
    else
        # No backup file specified, find most recent backup
        if [ -d "$PROJECT_ROOT/backups" ]; then
            backup_file=$(find "$PROJECT_ROOT/backups" -name "*.zip" -type f -print0 | xargs -0 ls -t | head -1)
            
            if [[ -z "$backup_file" ]]; then
                echo "❌ Error: No backup files found in backups directory"
                return 1
            fi
        else
            echo "❌ Error: Backups directory not found"
            return 1
        fi
    fi
    
    # Check if backup file exists
    if [[ ! -f "$backup_file" ]]; then
        echo "❌ Error: Backup file not found: $backup_file"
        return 1
    fi
    
    echo "🔍 Restoring from backup: $backup_file"
    
    # Check what type of backup it is
    local backup_type="unknown"
    if [[ "$(basename "$backup_file")" == *"_full.zip" ]]; then
        backup_type="full"
    elif [[ "$(basename "$backup_file")" == *"_untracked.zip" ]]; then
        backup_type="untracked"
    elif [[ "$(basename "$backup_file")" == *"_partial.zip" ]]; then
        backup_type="partial"
    fi
    
    # Create extraction directory
    local temp_dir=$(mktemp -d)
    echo "📦 Extracting backup to temporary directory..."
    
    # Check if unzip is available
    if ! command -v unzip &> /dev/null; then
        echo "❌ Error: unzip command not found"
        echo "Please install unzip to extract backup files"
        rm -rf "$temp_dir"
        return 1
    fi
    
    # Extract backup
    unzip -q "$backup_file" -d "$temp_dir" || {
        echo "❌ Error: Failed to extract backup file"
        rm -rf "$temp_dir"
        return 1
    }
    
    # Check if rsync is available 
    if command -v rsync &> /dev/null; then
        # Restore specific paths based on backup type
        if [[ "$backup_type" == "full" ]]; then
            echo "📦 Performing full restore (excluding configuration files)..."
            
            # For full restores, copy everything except configuration and version control files
            rsync -a "$temp_dir/" "$PROJECT_ROOT/" \
                --exclude=".git/" \
                --exclude=".gitignore" \
                --exclude=".github/" \
                --exclude="setup.py" \
                --exclude="setup.cfg" \
                --exclude="pyproject.toml" \
                --exclude="tox.ini" \
                --exclude="pytest.ini" \
                --exclude=".pre-commit-config.yaml" \
                --exclude="codecov.yml" \
                --exclude=".bumpversion.toml"
        elif [[ "$backup_type" == "untracked" ]]; then
            echo "📦 Performing restore of untracked files only..."
            
            # For untracked restores, copy everything from the temp directory
            # (untracked files backup already filtered out unnecessary files)
            rsync -a "$temp_dir/" "$PROJECT_ROOT/"
        else
            echo "📦 Performing selective restore of files in backup..."
            
            # For partial restores, copy everything from the temp directory
            rsync -a "$temp_dir/" "$PROJECT_ROOT/"
        fi
    else
        # Fallback to cp if rsync is not available
        echo "⚠️ rsync not found, using cp instead (less reliable)"
        if [[ "$backup_type" == "full" ]]; then
            echo "📦 Performing full restore (excluding configuration files)..."
            
            # Copy files, but need to be careful about excludes
            find "$temp_dir" -type f -not -path "*/\.*" | while read -r file; do
                # Skip configuration files
                if [[ "$file" != *"setup.py" && "$file" != *"setup.cfg" && 
                      "$file" != *"pyproject.toml" && "$file" != *"tox.ini" && 
                      "$file" != *"pytest.ini" && "$file" != *".pre-commit-config.yaml" && 
                      "$file" != *"codecov.yml" && "$file" != *".bumpversion.toml" ]]; then
                    
                    # Get relative path
                    rel_path="${file#$temp_dir/}"
                    target_path="$PROJECT_ROOT/$rel_path"
                    
                    # Create directory if needed
                    target_dir=$(dirname "$target_path")
                    mkdir -p "$target_dir"
                    
                    # Copy file
                    cp -f "$file" "$target_path"
                fi
            done
        elif [[ "$backup_type" == "untracked" ]]; then
            echo "📦 Performing restore of untracked files only..."
            
            # Copy all files from temp directory to project root since
            # untracked files backup already filtered unnecessary files
            cp -R "$temp_dir"/* "$PROJECT_ROOT/" 2>/dev/null || true
        else
            echo "📦 Performing selective restore of files in backup..."
            
            # Copy all files from temp directory to project root
            cp -R "$temp_dir"/* "$PROJECT_ROOT/" 2>/dev/null || true
        fi
    fi
    
    # Clean up temp directory
    rm -rf "$temp_dir"
    
    echo "✅ Restore completed successfully from: $(basename "$backup_file")"
    
    # Return success
    return 0
}

# Function to list available backups with details
list_backups() {
    print_banner "Available Backups"
    
    local backups_dir="$PROJECT_ROOT/backups"
    
    # Check if backups directory exists
    if [ ! -d "$backups_dir" ]; then
        mkdir -p "$backups_dir"
        echo "📦 Created backups directory at: $backups_dir"
        echo "📦 No backup files found yet"
        return 0
    fi
    
    # Find zip files in backups directory
    local backup_files=($(find "$backups_dir" -name "*.zip" -type f | sort -r))
    
    if [ ${#backup_files[@]} -eq 0 ]; then
        echo "📦 No backup files found"
        return 0
    fi
    
    echo "📦 Found ${#backup_files[@]} backup(s):"
    echo ""
    echo "| Backup File | Type | Size | Date |"
    echo "|-------------|------|------|------|"
    
    for backup in "${backup_files[@]}"; do
        local filename=$(basename "$backup")
        local filesize=$(du -h "$backup" | awk '{print $1}')
        local filedate=$(date -r "$backup" "+%Y-%m-%d %H:%M:%S")
        local type="Partial"
        
        if [[ "$filename" == *"_full.zip" ]]; then
            type="Full"
        fi
        
        echo "| $filename | $type | $filesize | $filedate |"
    done
    
    echo ""
    echo "Restore with: ./dhtl.sh restore <backup_filename> or ./dhtl.sh restore (for most recent)"
    echo ""
    
    # Return success
    return 0
}

# Function to automatically backup before git operations
git_safeguard() {
    local git_command="$1"
    shift
    local git_args=("$@")
    
    # Check if git command exists
    if ! command -v git &> /dev/null; then
        echo "❌ Error: git command not found"
        return 1
    fi
    
    # Check if current directory is a git repository
    if ! git rev-parse --is-inside-work-tree &> /dev/null; then
        echo "❌ Error: Not a git repository"
        return 1
    fi
    
    # STANDARDIZED ORDER OF OPERATIONS FOR ALL GIT COMMANDS
    
    # 1. ALWAYS create a backup of untracked files BEFORE any git operation
    echo "📦 Creating automatic backup of untracked files..."
    backup_project "untracked"
    local untracked_backup_status=$?
    
    # Check if untracked backup failed (critical error)
    if [ $untracked_backup_status -ne 0 ]; then
        echo "❌ Error: Untracked files backup failed with status: $untracked_backup_status"
        echo "⚠️ Aborting git operation for safety - crucial files could be lost"
        return $untracked_backup_status
    fi
    
    # Check for the --ignore-untracked flag
    local ignore_untracked=false
    local non_flag_args=()
    
    # Process command args to extract flags
    for arg in "${git_args[@]}"; do
        if [[ "$arg" == "--ignore-untracked" ]]; then
            ignore_untracked=true
        else
            non_flag_args+=("$arg")
        fi
    done
    
    # Reassign args without our custom flags
    git_args=("${non_flag_args[@]}")
    
    # Check if this is a potentially destructive operation
    case "$git_command" in
        # High-risk destructive operations that can remove or modify files
        checkout|switch|reset|clean|stash|pull|merge|rebase|restore)
            echo "⚠️ POTENTIALLY DESTRUCTIVE GIT OPERATION DETECTED: git $git_command ${git_args[*]}"
            
            # Remember the latest untracked backup file for restoration later
            local latest_untracked_backup=$(find "$PROJECT_ROOT/backups" -name "*_untracked.zip" -type f -print0 | xargs -0 ls -t 2>/dev/null | head -1)
            
            # 2. For destructive operations, also create a full backup
            echo "📦 Creating additional FULL backup before proceeding with destructive operation..."
            backup_project "all"
            local full_backup_status=$?
            
            # Check if full backup failed
            if [ $full_backup_status -ne 0 ]; then
                echo "❌ Error: Full backup failed with status: $full_backup_status"
                echo "⚠️ Aborting git operation for safety"
                return $full_backup_status
            fi
            
            # 3. Proceed with git command AFTER both backups are successful
            echo "🔄 Proceeding with git operation: git $git_command ${git_args[*]}"
            git "$git_command" "${git_args[@]}"
            
            # 4. Check operation status
            local git_status=$?
            
            # 5. AUTOMATICALLY RESTORE UNTRACKED FILES unless --ignore-untracked flag is set
            if [ $git_status -eq 0 ] && [ "$ignore_untracked" = false ]; then
                echo "🔄 Automatically restoring untracked files..."
                
                # Determine the backup file to restore from
                if [ -n "$latest_untracked_backup" ]; then
                    # Create temporary directory for extraction
                    local temp_dir=$(mktemp -d)
                    
                    # Extract backup to temporary directory
                    if command -v unzip &> /dev/null; then
                        unzip -q "$latest_untracked_backup" -d "$temp_dir" || {
                            echo "⚠️ Warning: Failed to extract untracked files backup"
                            rm -rf "$temp_dir"
                            echo "💡 You can manually restore with: ./dhtl.sh restore untracked"
                            return $git_status
                        }
                        
                        # Restore files using rsync or cp
                        if command -v rsync &> /dev/null; then
                            rsync -a "$temp_dir/" "$PROJECT_ROOT/"
                        else
                            cp -R "$temp_dir"/* "$PROJECT_ROOT/" 2>/dev/null || true
                        fi
                        
                        # Clean up
                        rm -rf "$temp_dir"
                        echo "✅ Untracked files automatically restored"
                    else
                        echo "⚠️ Warning: unzip command not found, skipping automatic restoration"
                        echo "💡 You can manually restore with: ./dhtl.sh restore untracked"
                    fi
                else
                    echo "⚠️ Warning: No untracked files backup found to restore from"
                fi
            fi
            
            # 6. Final status reporting
            if [ $git_status -eq 0 ]; then
                echo "✅ Git operation completed successfully"
                if [ "$ignore_untracked" = true ]; then
                    echo "💡 Untracked files were NOT automatically restored (--ignore-untracked flag set)"
                    echo "   To manually restore untracked files: ./dhtl.sh restore untracked"
                fi
            else
                echo "❌ Git operation failed with status: $git_status"
                echo "⚠️ Recovery options:"
                echo "   1. Restore untracked files: ./dhtl.sh restore untracked"
                echo "   2. Full restore: ./dhtl.sh restore"
            fi
            return $git_status
            ;;
            
        # Medium-risk operations that modify git metadata but not working files
        commit|branch|tag|config)
            # For these, we already have the untracked files backup from step 1
            echo "🔄 Proceeding with git operation: git $git_command ${git_args[*]}"
            git "$git_command" "${git_args[@]}"
            return $?
            ;;
            
        # Low-risk read-only operations
        *)
            # For standard non-destructive operations, proceed normally
            # We still have the untracked backup from step 1 as a precaution
            echo "🔄 Proceeding with git operation: git $git_command ${git_args[*]}"
            git "$git_command" "${git_args[@]}"
            return $?
            ;;
    esac
}

# Function to show usage information
show_backup_help() {
    echo "DHT Backup & Restore Utilities"
    echo ""
    echo "Usage: ./dhtl.sh backup [command] [options]"
    echo ""
    echo "Commands:"
    echo "  all                     Create a full project backup (everything)"
    echo "  untracked               Create a backup of only untracked files (filtered by .gitignore)"
    echo "  <path1> <path2> ...     Create a backup of specific paths"
    echo "  list                    List all available backups"
    echo "  help                    Show this help message"
    echo ""
    echo "Usage: ./dhtl.sh restore [command] [options]"
    echo ""
    echo "Commands:"
    echo "  untracked               Restore from most recent untracked files backup"
    echo "  <backup_filename>       Restore from a specific backup file"
    echo "  (no arguments)          Restore from the most recent backup"
    echo ""
    echo "Usage: ./dhtl.sh git [git-command] [options]"
    echo ""
    echo "  This is a safety wrapper around the git command that automatically:"
    echo "  1. Creates backups before ALL git operations"
    echo "  2. Provides extra protection for destructive operations (checkout, pull, stash, etc.)"
    echo "  3. AUTOMATICALLY RESTORES untracked files after destructive operations"
    echo ""
    echo "  Options:"
    echo "  --ignore-untracked    Skip automatic restoration of untracked files"
    echo ""
    echo "  CRITICAL: This is the ONLY safe way to use Git with this project."
    echo "  See ./DHT/docs/GIT_SAFETY_PROTOCOL.md for the full details."
    echo ""
    echo "Examples:"
    echo "  ./dhtl.sh backup all                # Backup entire project"
    echo "  ./dhtl.sh backup untracked          # Backup only untracked files"
    echo "  ./dhtl.sh backup src tests docs     # Backup specific directories"
    echo "  ./dhtl.sh backup list               # List all backups"
    echo "  ./dhtl.sh restore                   # Restore from most recent backup"
    echo "  ./dhtl.sh restore untracked         # Restore from most recent untracked files backup"
    echo "  ./dhtl.sh restore enchant_cli_backup_20250505_120030_full.zip  # Restore specific backup"
    echo "  ./dhtl.sh git checkout main         # Safely checkout the main branch with auto-backup"
    echo ""
    
    # Return success
    return 0
}

# Main function to dispatch subcommands
backup_main() {
    local subcommand="$1"
    shift
    
    # Check the subcommand
    case "$subcommand" in
        "all")
            backup_project "all"
            ;;
        "list")
            list_backups
            ;;
        "help")
            show_backup_help
            ;;
        "")
            echo "❌ Error: No backup command specified"
            echo "Run './dhtl.sh backup help' for usage information"
            return 1
            ;;
        *)
            # Any other argument is treated as a path to backup
            backup_project "$subcommand" "$@"
            ;;
    esac
    
    # Return the status of the last command
    return $?
}

# Main function for restore command
restore_main() {
    local backup_file="$1"
    local restore_type=""
    
    # Check if we're asked to restore untracked files specifically
    if [[ "$backup_file" == "untracked" ]]; then
        restore_type="untracked"
        backup_file=""
        
        # Find most recent untracked backup
        if [ -d "$PROJECT_ROOT/backups" ]; then
            backup_file=$(find "$PROJECT_ROOT/backups" -name "*_untracked.zip" -type f -print0 | xargs -0 ls -t 2>/dev/null | head -1)
            
            if [[ -z "$backup_file" ]]; then
                echo "❌ Error: No untracked files backup found in backups directory"
                return 1
            fi
        else
            echo "❌ Error: Backups directory not found"
            return 1
        fi
        
        echo "🔍 Found most recent untracked files backup: $(basename "$backup_file")"
    fi
    
    # Restore from specified backup or most recent
    restore_project "$backup_file"
    
    # Return the status of the restore command
    return $?
}

# Main function for git safeguard command
git_main() {
    local git_command="$1"
    shift
    
    # Show help if no command is provided
    if [[ -z "$git_command" ]]; then
        echo "❌ Error: No git command specified"
        echo "Usage: ./dhtl.sh git [git-command] [options]"
        echo "Run './dhtl.sh backup help' for more information"
        return 1
    fi
    
    # Execute git command with safeguarding
    git_safeguard "$git_command" "$@"
    
    # Return the status of the git command
    return $?
}