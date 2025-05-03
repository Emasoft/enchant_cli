#!/bin/bash
# DHT Launcher (DHTL) - Main entry point for all Development Helper Toolkit operations
# Provides centralized access to backup, git safeguards, and other utility scripts

set -e

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

# Modules directory
MODULES_DIR="$SCRIPT_DIR/DHT/modules"
REFACTORED_DIR="$SCRIPT_DIR/DHT/dhtl_refactored"

# Set up environment for modules
export DHTL_SESSION_ID="${DHTL_SESSION_ID:-$(date +%s)_$$}"
export DHTL_SKIP_ENV_SETUP=1
export SKIP_ENV_CHECK=1
export IN_DHTL=1

# Display banner
display_banner() {
    echo "╔════════════════════════════════════════════════════════════════════════════╗"
    echo "║           Development Helper Toolkit Launcher (DHTL)                      ║"
    echo "╚════════════════════════════════════════════════════════════════════════════╝"
    echo ""
    echo "This launcher provides access to all DHT modules and utilities:"
    echo "- Git safety protocols with automatic backup/restore of untracked files"
    echo "- Backup and restore functions for project files"
    echo "- Process guardian for resource management"
    echo "- GitHub workflow integration"
    echo "- Development utilities and tools"
    echo ""
    
    # Count modules
    MODULES_COUNT=$(find "$MODULES_DIR" -name "*.sh" 2>/dev/null | wc -l | tr -d ' ')
    REFACTORED_COUNT=$(find "$REFACTORED_DIR" -name "*.sh" 2>/dev/null | wc -l | tr -d ' ')
    
    echo "✅ Available modules: $(($MODULES_COUNT + $REFACTORED_COUNT))"
    echo ""
    
    # Show key modules
    echo "Key Modules:"
    echo "  - backup_utils.sh    - Backup/restore system with git safety"
    echo "  - process_guardian.py - Resource and process management"
    echo "  - bash_parser.py      - Bash script analysis and refactoring"
    echo ""
    
    echo "For help and usage information, run: ./dhtl.sh help"
    echo ""
}

# Check if a function exists
function_exists() {
    declare -f -F "$1" > /dev/null
    return $?
}

# Process command line arguments
process_args() {
    # Default options
    USE_GUARDIAN=true
    QUIET_MODE=false
    DEBUG_MODE=false
    COMMAND=""
    COMMAND_ARGS=()
    
    # Process arguments
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --help|-h)
                COMMAND="help"
                break
                ;;
            --version|-v)
                COMMAND="version"
                break
                ;;
            --no-guardian)
                USE_GUARDIAN=false
                shift
                ;;
            --quiet)
                QUIET_MODE=true
                shift
                ;;
            --debug)
                DEBUG_MODE=true
                shift
                ;;
            *)
                if [[ -z "$COMMAND" ]]; then
                    COMMAND="$1"
                    shift
                else
                    COMMAND_ARGS+=("$1")
                    shift
                fi
                ;;
        esac
    done
    
    # Export these values for modules to use
    export USE_GUARDIAN
    export QUIET_MODE
    export DEBUG_MODE
    export COMMAND
    export COMMAND_ARGS
}

# Main function
main() {
    # Display banner
    display_banner
    
    # Process command line arguments
    process_args "$@"
    
    # Handle special commands directly or forward to backup script
    if [[ $# -gt 0 ]]; then
        # Handle direct commands for DHT scripts
        if [[ "$COMMAND" == "backup" ]]; then
            echo "▶️ Running backup utilities"
            echo ""
            
            if [[ -f "$SCRIPT_DIR/DHT/backup_utils.sh" ]]; then
                # Make script executable if it's not
                if [[ ! -x "$SCRIPT_DIR/DHT/backup_utils.sh" ]]; then
                    chmod +x "$SCRIPT_DIR/DHT/backup_utils.sh"
                fi
                
                # Source the backup utilities script
                source "$SCRIPT_DIR/DHT/backup_utils.sh"
                
                # Call the backup main function with args
                backup_main "${COMMAND_ARGS[@]}"
                exit $?
            else
                echo "❌ Error: Backup utilities script not found"
                echo "Expected at: $SCRIPT_DIR/DHT/backup_utils.sh"
                exit 1
            fi
        elif [[ "$COMMAND" == "restore" ]]; then
            echo "▶️ Running restore utilities"
            echo ""
            
            if [[ -f "$SCRIPT_DIR/DHT/backup_utils.sh" ]]; then
                # Make script executable if it's not
                if [[ ! -x "$SCRIPT_DIR/DHT/backup_utils.sh" ]]; then
                    chmod +x "$SCRIPT_DIR/DHT/backup_utils.sh"
                fi
                
                # Source the backup utilities script
                source "$SCRIPT_DIR/DHT/backup_utils.sh"
                
                # Call the restore main function with args
                restore_main "${COMMAND_ARGS[@]}"
                exit $?
            else
                echo "❌ Error: Backup utilities script not found"
                echo "Expected at: $SCRIPT_DIR/DHT/backup_utils.sh"
                exit 1
            fi
        elif [[ "$COMMAND" == "git" ]]; then
            echo "▶️ Running git with automatic backup safeguards"
            echo ""
            
            if [[ -f "$SCRIPT_DIR/DHT/backup_utils.sh" ]]; then
                # Make script executable if it's not
                if [[ ! -x "$SCRIPT_DIR/DHT/backup_utils.sh" ]]; then
                    chmod +x "$SCRIPT_DIR/DHT/backup_utils.sh"
                fi
                
                # Source the backup utilities script
                source "$SCRIPT_DIR/DHT/backup_utils.sh"
                
                # Call the git main function with args
                git_main "${COMMAND_ARGS[@]}"
                exit $?
            else
                echo "❌ Error: Backup utilities script not found"
                echo "Expected at: $SCRIPT_DIR/DHT/backup_utils.sh"
                exit 1
            fi
        elif [[ "$COMMAND" == "cleanup" ]]; then
            echo "▶️ Running cleanup of temporary directories"
            echo ""
            
            if [[ -f "$SCRIPT_DIR/DHT/cleanup_temp_folders.sh" ]]; then
                # Make script executable if it's not
                if [[ ! -x "$SCRIPT_DIR/DHT/cleanup_temp_folders.sh" ]]; then
                    chmod +x "$SCRIPT_DIR/DHT/cleanup_temp_folders.sh"
                fi
                
                "$SCRIPT_DIR/DHT/cleanup_temp_folders.sh" "${COMMAND_ARGS[@]}"
                CLEANUP_STATUS=$?
                
                if [[ "$CLEANUP_STATUS" -eq 0 ]]; then
                    echo ""
                    echo "✅ Temporary directories cleaned successfully"
                fi
                
                exit $CLEANUP_STATUS
            else
                echo "❌ Error: Cleanup script not found"
                echo "Expected at: $SCRIPT_DIR/DHT/cleanup_temp_folders.sh"
                exit 1
            fi
        elif [[ "$COMMAND" == "move_tree_sitter" ]]; then
            echo "▶️ Moving tree-sitter-bash to DHT directory"
            echo ""
            
            if [[ -f "$SCRIPT_DIR/DHT/move_tree_sitter.sh" ]]; then
                # Make script executable if it's not
                if [[ ! -x "$SCRIPT_DIR/DHT/move_tree_sitter.sh" ]]; then
                    chmod +x "$SCRIPT_DIR/DHT/move_tree_sitter.sh"
                fi
                
                "$SCRIPT_DIR/DHT/move_tree_sitter.sh" "${COMMAND_ARGS[@]}"
                MOVE_STATUS=$?
                
                if [[ "$MOVE_STATUS" -eq 0 ]]; then
                    echo ""
                    echo "✅ tree-sitter-bash successfully moved to DHT directory"
                fi
                
                exit $MOVE_STATUS
            else
                echo "❌ Error: Move script not found"
                echo "Expected at: $SCRIPT_DIR/DHT/move_tree_sitter.sh"
                exit 1
            fi
        elif [[ "$COMMAND" == "test_dht" ]]; then
            echo "▶️ Running DHT test suite"
            
            # Display usage if --help flag is provided
            if [[ "${COMMAND_ARGS[0]}" == "--help" || "${COMMAND_ARGS[0]}" == "-h" ]]; then
                echo ""
                echo "Usage: ./dhtl.sh test_dht [subcommand] [options]"
                echo ""
                echo "Subcommands:"
                echo "  (none)       Run syntax tests on all DHT scripts"
                echo "  sizes        Check if all modules are under the 10KB size limit"
                echo "  check_sizes  Same as 'sizes'"
                echo "  prepare      Prepare directories for splitting large modules"
                echo "  help         Show this help message"
                echo ""
                echo "Examples:"
                echo "  ./dhtl.sh test_dht            # Run syntax tests on all scripts"
                echo "  ./dhtl.sh test_dht sizes      # Check if all modules are under 10KB"
                echo "  ./dhtl.sh test_dht prepare    # Prepare directories for splitting modules"
                exit 0
            fi
            
            echo ""
            if [[ -x "$SCRIPT_DIR/DHT/scripts/test_dht.sh" ]]; then
                "$SCRIPT_DIR/DHT/scripts/test_dht.sh" "${COMMAND_ARGS[@]}"
                exit $?
            else
                echo "❌ Error: DHT test script not found or not executable"
                echo "Expected at: $SCRIPT_DIR/DHT/scripts/test_dht.sh"
                exit 1
            fi
        # Handle publish_to_github command
        elif [[ "$COMMAND" == "publish_to_github" ]]; then
            echo "▶️ Running GitHub publishing workflow"
            echo ""
            
            if [[ -x "$SCRIPT_DIR/DHT/publish_to_github.sh" ]]; then
                "$SCRIPT_DIR/DHT/publish_to_github.sh" "${COMMAND_ARGS[@]}"
                exit $?
            else
                echo "❌ Error: GitHub publishing script not found or not executable"
                echo "Expected at: $SCRIPT_DIR/DHT/publish_to_github.sh"
                exit 1
            fi
        # Handle generic script running through the run command
        elif [[ "$COMMAND" == "run" ]]; then
            # Check if script provided
            if [[ ${#COMMAND_ARGS[@]} -lt 1 ]]; then
                echo "❌ Error: No script specified for 'run' command"
                echo "Usage: ./dhtl.sh run <script_path> [args...]"
                echo "Example: ./dhtl.sh run DHT/scripts/check_module_sizes.sh"
                exit 1
            fi
            
            # Get the script path and remaining args
            SCRIPT_PATH="${COMMAND_ARGS[0]}"
            SCRIPT_ARGS=("${COMMAND_ARGS[@]:1}")
            
            # Check if script exists
            if [[ -f "$SCRIPT_DIR/$SCRIPT_PATH" ]]; then
                # Make script executable if it's not
                if [[ ! -x "$SCRIPT_DIR/$SCRIPT_PATH" ]]; then
                    chmod +x "$SCRIPT_DIR/$SCRIPT_PATH"
                fi
                
                echo "▶️ Running script: $SCRIPT_PATH"
                echo ""
                
                # Run the script with any remaining arguments
                "$SCRIPT_DIR/$SCRIPT_PATH" "${SCRIPT_ARGS[@]}"
                exit $?
            else
                echo "❌ Error: Script not found: $SCRIPT_PATH"
                echo "Please provide a valid script path relative to the project root."
                exit 1
            fi
        else
            # Handle help command
            if [[ "$COMMAND" == "help" ]]; then
                echo -e "${BLUE}Development Helper Toolkit Launcher (DHTL) - Help${NC}"
                echo ""
                echo "Usage: ./dhtl.sh [command] [options]"
                echo ""
                echo "╔═══════════════════════╦════════════════════════════════════════════════════╗"
                echo "║ COMMAND CATEGORY      ║ COMMAND [OPTIONS]            DESCRIPTION           ║"
                echo "╠═══════════════════════╬════════════════════════════════════════════════════╣"
                echo "║                       ║ lint                       Run code linters        ║"
                echo "║                       ║ format                     Format source code      ║"
                echo "║                       ║ test [--fast]              Run tests               ║"
                echo "║ PROJECT MANAGEMENT    ║ coverage                   Generate coverage report║"
                echo "║                       ║ build [--no-checks]        Build Python package    ║"
                echo "║                       ║ commit [msg] [--no-checks] Commit changes to git   ║"
                echo "║                       ║ publish_to_github          Publish to GitHub       ║"
                echo "║                       ║ cleanup                    Clean temp directories  ║"
                echo "║                       ║ backup [all|paths|list]    Backup project files    ║"
                echo "║                       ║ restore [backup-file]      Restore from backup     ║"
                echo "║                       ║ git [git-command]          Git with auto-backup    ║"
                echo "╠═══════════════════════╬════════════════════════════════════════════════════╣"
                echo "║                       ║ venv                       Manage virtual env      ║"
                echo "║ ENVIRONMENT           ║ install_tools              Install dev tools       ║"
                echo "║ MANAGEMENT            ║ setup_project              Create config files     ║"
                echo "║                       ║ restore                    Restore dependencies    ║"
                echo "║                       ║ env                        Show env info           ║"
                echo "╠═══════════════════════╬════════════════════════════════════════════════════╣"
                echo "║                       ║ workflows [run|list|status] GitHub workflow mgmt   ║"
                echo "║ REPOSITORY            ║ rebase                      Reset to remote head   ║"
                echo "║ MANAGEMENT            ║ setup                       Set up project repo    ║"
                echo "║                       ║ clean                       Clean caches/temp files║"
                echo "╠═══════════════════════╬════════════════════════════════════════════════════╣"
                echo "║                       ║ test_dht [sizes|prepare]    Test DHT scripts       ║"
                echo "║ SCRIPT EXECUTION      ║ run <script_path>           Run DHT script         ║"
                echo "║                       ║ script [name] [args]        Run helper script      ║"
                echo "║                       ║ node [args]                 Run Node.js script     ║"
                echo "║                       ║ guardian [status|stop]      Process guardian mgmt  ║"
                echo "║                       ║ selfcheck                   Validate DHT scripts   ║"
                echo "╚═══════════════════════╩════════════════════════════════════════════════════╝"
                echo ""
                echo "Global Options:"
                echo "  --no-guardian  - Disable process guardian for this command"
                echo "  --quiet        - Reduce output verbosity"
                echo ""
                echo "Special Commands:"
                echo "  publish_to_github    Directly calls the publish_to_github.sh script"
                echo "    - --skip-tests     Skip running tests locally"
                echo "    - --skip-linters   Skip running linters locally"
                echo "    - --dry-run        Execute all steps except final GitHub push"
                echo ""
                echo "  backup               Backup project files"
                echo "    - all              Create a full project backup (everything)"
                echo "    - untracked        Create a backup of only untracked files (filtered by .gitignore)"
                echo "    - <path1> <path2>  Create a backup of specific paths"
                echo "    - list             List all available backups"
                echo "    - help             Show backup help"
                echo ""
                echo "  restore              Restore from backup"
                echo "    - untracked        Restore from most recent untracked files backup"
                echo "    - <backup-file>    Restore from a specific backup file"
                echo "    - (no arguments)   Restore from the most recent backup"
                echo ""
                echo "  git <git-command>    Run git with automatic backup and restore of untracked files"
                echo "                       --ignore-untracked   Skip automatic restoration"
                echo "                       CRITICAL: This is the ONLY safe way to use git"
                echo ""
                echo "  cleanup              Clean temporary directories (backups, build, coverage_report)"
                echo ""
                echo "  move_tree_sitter     Move tree-sitter-bash to the DHT directory"
                echo ""
                echo "  test_dht             Run syntax tests on all DHT scripts"
                echo "    - sizes            Check if all modules are under 10KB size limit"
                echo "    - prepare          Prepare directories for splitting large modules"
                echo "    - help             Show test_dht specific help"
                echo ""
                echo "  run <script_path>    Run any script in the DHT directory"
                echo "    Example: ./dhtl.sh run DHT/scripts/check_module_sizes.sh"
                echo ""
                echo "Run './dhtl.sh [command] --help' for more information about a specific command."
                exit 0
            else
                # Display helpful error message for unknown commands
                echo "❌ Unknown command: $1"
                echo "Run './dhtl.sh help' for a list of available commands."
                exit 1
            fi
        fi
    fi
}

# Run main function with all arguments
main "$@"