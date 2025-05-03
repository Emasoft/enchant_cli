# CLAUDE HELPER SCRIPTS

A collection of Python utilities to enhance GitHub workflow management, log analysis, shell script compatibility, and uv package management.

## Overview

These helper scripts are designed to be modular, portable, and adaptable to different project environments. They provide a unified command-line interface for common development tasks related to GitHub Actions workflows, Python package management with uv, and shell script improvements.

## Quick Start

Run the helper scripts using the wrapper scripts:

```bash
# On Unix/macOS
./helpers-cli.sh [command] [options]

# On Windows
helpers-cli.bat [command] [options]
```

Or directly with Python:

```bash
python -m helpers.cli [command] [options]
```

## Commands

The following commands are available:

### General Commands

```bash
# Show help and available commands
./helpers-cli.sh --help

# Show version information
./helpers-cli.sh version
```

### Log Analysis

```bash
# Analyze the most recent log files
./helpers-cli.sh logs --latest

# Analyze a specific log file
./helpers-cli.sh logs --analyze logs/workflow_123456789.log

# Search logs for a specific pattern
./helpers-cli.sh logs --search "error message"

# Show log statistics
./helpers-cli.sh logs --stats

# Clean up old log files
./helpers-cli.sh logs --cleanup --age 15 --dry-run
```

### GitHub Repository Management

```bash
# Show repository information
./helpers-cli.sh repo --info

# Create a new repository
./helpers-cli.sh repo --create --name my-repo --description "My project"

# Set up repository secrets
./helpers-cli.sh repo --secrets

# Check branch setup
./helpers-cli.sh repo --check-branch

# Create a new branch
./helpers-cli.sh repo --create-branch --branch feature-branch

# Push to remote
./helpers-cli.sh repo --push --branch feature-branch

# Bump version (with uv integration)
./helpers-cli.sh repo --bump-version minor

# Install bump-my-version
./helpers-cli.sh repo --install-bumpversion
```

### GitHub Workflow Management

```bash
# Check workflow dispatch triggers
./helpers-cli.sh workflow --check

# Fix workflow dispatch triggers
./helpers-cli.sh workflow --fix --commit

# Trigger a workflow
./helpers-cli.sh workflow --trigger --workflow tests.yml --wait-logs --analyze-logs
```

### Shell Script Fixing

```bash
# Fix workflow script issues
./helpers-cli.sh fix --workflow-script

# Fix shell compatibility issues
./helpers-cli.sh fix --shell-compat

# Set up bump-my-version with proper uv integration
./helpers-cli.sh fix --setup-bumpversion

# Create a Windows .bat wrapper for a shell script
./helpers-cli.sh fix --create-bat-wrapper bump_version

# Fix all detected issues
./helpers-cli.sh fix --all
```

## Module Organization

```
helpers/
├── __init__.py         # Version and package initialization
├── cli.py              # Unified command-line interface
├── errors/             # Error handling and log analysis modules
│   ├── __init__.py
│   └── log_analyzer.py # Advanced log analysis utilities
├── github/             # GitHub integration modules
│   ├── __init__.py
│   ├── repo_helper.py  # Repository management utilities
│   └── workflow_helper.py # Workflow management utilities
└── shell/              # Shell script enhancement utilities
    ├── __init__.py
    └── script_fixer.py # Shell script fixing utilities
```

## Features

- **Zero-Configuration Operation**: Auto-detects repository information from multiple sources
- **Advanced Error Analysis**: Sophisticated error classification and root cause detection
- **GitHub Integration**: Comprehensive repository and workflow management tools
- **Shell Script Enhancement**: Automatic fixing of common shell script issues
- **UV Integration**: Proper setup and usage of uv for package management
- **Cross-Platform Compatibility**: Works consistently on macOS, Linux, and Windows

## Specialized Functions

### Bump Version Management with UV

The helper scripts provide comprehensive bump-my-version setup and management:

```bash
# Set up bump-my-version with proper uv integration
./helpers-cli.sh fix --setup-bumpversion

# Bump version using uv tool run
./helpers-cli.sh repo --bump-version minor

# Create Windows .bat wrapper for a version bump script
./helpers-cli.sh fix --create-bat-wrapper bump_version
```

### Shell Script Functions

The script_fixer module provides functions to:

- Check shell script quality and find common issues
- Add proper error handling (set -e, print_error function)
- Improve cross-platform compatibility
- Find duplicated functions across scripts
- Create Windows batch wrappers for shell scripts

### Error Log Analysis

The log_analyzer module provides:

- Advanced error classification (critical, severe, warning)
- Root cause detection for common failures
- Statistical analysis of workflow logs
- Log cleanup and management
- Detailed error reports with context

### GitHub Workflow Management

The workflow_helper and repo_helper modules provide:

- Fix workflow_dispatch triggers for manual workflow runs
- Trigger workflows and collect logs
- Set up repository secrets
- Verify repository and branch setup
- Create and manage branches
- Push changes safely

## Using in Other Projects

To use these helper scripts in another project:

1. Copy the `helpers/` directory to the target project
2. Copy the wrapper scripts (`helpers-cli.sh` and `helpers-cli.bat`) to the project root
3. Ensure Python 3.9+ is available
4. Run `./helpers-cli.sh version` to verify installation

## Requirements

- Python 3.9+
- GitHub CLI (recommended but not required for most functions)
- uv (recommended for version management, but not required)

## License

Same license as the parent project.