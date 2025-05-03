# DHT Scripts Categorization

This document categorizes the scripts in the DHT directory by their usage in the dhtl.sh launcher.

## 1. LAUNCHER

The main launcher script that serves as the entry point for all operations:

- `dhtl.sh` - The main launcher script that manages commands and processes

## 2. COMMAND SCRIPTS

These scripts are directly called by dhtl.sh to implement specific commands:

### Project Management
- `run_tests.sh` - Implements the 'test' command
- `run_platform.sh` - Used for platform-specific operations (lint, format)
- `publish_to_github.sh` - Implements the 'publish' command
- `resetgit.sh` - Implements the 'rebase' command
- `setup_package.sh` - Implements the 'setup_project' command
- `bump_version.sh` - Handles version bumping
- `release.sh` - Prepares project for release
- `major_release.sh` - Handles major version releases

### Environment Management
- `ensure_env.sh` - Ensures consistent environment setup
- `reinitialize_env.sh` - Recreates the virtual environment
- `install_uv.sh` - Installs and configures uv
- `cleanup.sh` - Cleans up temporary files and caches

### Script Execution
- `node-wrapper.sh` - Wraps Node.js commands with resource limits
- `python-dev-wrapper.sh` - Wraps Python commands with resource limits
- `get_errorlogs.sh` - Main entry point for error log analysis

### Process Management
- `start-process-guardian.sh` - Starts the process guardian
- `stop-process-guardian.sh` - Stops the process guardian
- `guard-process.sh` - Manages resource limits for processes

### GitHub Workflows
- `publish_trigger_workflow.sh` - Implements the 'workflows' command
- `check_workflow_dispatch.sh` - Checks workflows for dispatch events

## 3. SECONDARY SCRIPTS

These scripts are not directly called by dhtl.sh but are used by COMMAND SCRIPTS:

### Publish Scripts
- `publish_common.sh` - Common functions for publishing
- `publish_env_prep.sh` - Prepares environment for publishing
- `publish_env_verify.sh` - Verifies environment for publishing
- `publish_final_notes.sh` - Displays final notes after publishing
- `publish_local_checks.sh` - Performs local checks before publishing
- `publish_push_part1.sh` - First part of the push process
- `publish_push_part2.sh` - Second part of the push process
- `publish_repo_status.sh` - Checks repository status
- `publish_trigger_detect.sh` - Detects available triggers
- `publish_trigger_manual.sh` - Manual trigger handling
- `publish_wf_detect_1.sh` - First workflow detection phase
- `publish_wf_detect_2.sh` - Second workflow detection phase
- `publish_wf_trigger_1.sh` - First workflow trigger phase
- `publish_wf_trigger_verify.sh` - Verifies workflow triggers
- `publish_yaml_validate.sh` - Validates YAML files

### Error Log Analysis
- `get_errorlogs_classify_errors.sh` - Classifies errors in logs
- `get_errorlogs_cleanup.sh` - Cleans up error logs
- `get_errorlogs_detect_workflows.sh` - Detects workflows in error logs
- `get_errorlogs_generate_stats.sh` - Generates statistics from error logs
- `get_errorlogs_list_saved_logs.sh` - Lists saved error logs
- `get_errorlogs_logs_processing.sh` - Processes error logs
- `get_errorlogs_repo_info.sh` - Gets repository information
- `get_errorlogs_search_logs.sh` - Searches error logs
- `get_errorlogs_show_help.sh` - Shows help for error log commands
- `get_errorlogs_utils.sh` - Utility functions for error log analysis
- `get_errorlogs_workflow_logs.sh` - Gets workflow logs
- `get_errorlogs_workflow_type.sh` - Determines workflow types

### UV Management
- `uv_commands.sh` - Commands for uv package manager
- `uv_core_functions.sh` - Core functions for uv

### Other Utilities
- `first_push.sh` - Sets up repository for first push
- `run_commands.sh` - Runs multiple commands in sequence
- `install_apache_license.sh` - Installs Apache license
- `test.sh` and `test2.sh` - Test scripts

## 4. PYTHON SCRIPTS

These Python scripts are part of the DHT system:

### Process Management
- `process-guardian-watchdog.py` - Main process guardian implementation
- `process_guardian.py` - Process guardian functionality
- `integrate_process_guardian.py` - Integrates process guardian

### GitHub Helpers
- `repo_helper.py` - Repository helper functions
- `workflow_helper.py` - Workflow helper functions

### Error Analysis
- `log_analyzer.py` - Analyzes error logs

### Script Fixing
- `script_fixer.py` - Fixes script issues
- `fix_workflow_script.py` - Fixes workflow script issues
- `fix_recent_failure.py` - Fixes recent failures
- `fix_final.py` - Final fixes for scripts

### Other
- `cli.py` - CLI functionality
- `check_summary_output.py` - Checks summary output
- `test_script.py` - Test script