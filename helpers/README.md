# CLAUDE HELPER SCRIPTS

A collection of portable Python utilities for enhancing shell scripts with advanced capabilities.

## Overview

These helper scripts provide functionality to improve GitHub workflow management, error analysis, and shell script compatibility. They're designed to be completely portable and work across different projects without modification.

## Features

### GitHub Workflow Management

- Detect and fix issues in workflow files
- Add missing workflow_dispatch events
- Fix shell script issues related to GitHub integration
- Validate and improve script functionality

### Log Analysis & Error Classification

- Analyze GitHub Actions workflow logs
- Classify errors by severity (critical, severe, warning)
- Identify common root causes of failures
- Generate detailed error reports

### Cross-Platform Shell Script Fixes

- Improve compatibility across different platforms
- Fix macOS-specific shell issues
- Replace non-portable commands with portable alternatives
- Ensure consistent behavior across environments

## Usage

```bash
# Fix all issues in shell scripts
python -m helpers.cli fix --all

# Analyze a specific log file
python -m helpers.cli logs --analyze logs/workflow_123456.log

# Check workflow files for workflow_dispatch events
python -m helpers.cli workflow --check

# Fix workflow files to add workflow_dispatch events
python -m helpers.cli workflow --fix
```

## Individual Tools

### Log Analyzer

```bash
# Run directly
python -m helpers.errors.log_analyzer logs/workflow_123456.log

# Output in JSON format
python -m helpers.errors.log_analyzer logs/workflow_123456.log --json

# Output in TSV format (for shell scripts)
python -m helpers.errors.log_analyzer logs/workflow_123456.log --tsv
```

### Workflow Helper

```bash
# Fix publish_to_github.sh
python -m helpers.github.workflow_helper --fix-workflow-script

# Fix shell compatibility issues in get_errorlogs.sh
python -m helpers.github.workflow_helper --fix-shell-compat

# Check and fix workflow_dispatch events
python -m helpers.github.workflow_helper --check-workflow-dispatch
python -m helpers.github.workflow_helper --fix-workflow-dispatch
```

## Installation

These scripts are designed to be included directly in your project without external dependencies. Simply copy the `helpers` directory to your project root.

## Portability

The helper scripts are designed to work without modification in any Python project. They:

1. Use standard library modules only
2. Auto-detect repository and workflow information
3. Work with different project structures
4. Adapt to different environments
5. Include graceful fallbacks for all operations

## License

Same as the containing project.