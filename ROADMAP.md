# Development Roadmap

This roadmap outlines the tasks and goals for improving the ENCHANT_BOOK_MANAGER project. Each task has a status indicator:

- [❌] - Missing/Not Started
- [✅] - Completed
- [⛔] - Stopped (due to bugs or issues)
- [▶️] - In Progress/In Development
- [🧪] - Awaiting Tests/Tests Not Passed/Needs Revision

## [DHT Helpers]

### Categorization and Analysis

- [✅] Identify all commands currently implemented by the DHT toolbox scripts
- [✅] Divide scripts into LAUNCHER, COMMANDS SCRIPTS, and SECONDARY SCRIPTS (See DHT_SCRIPTS_CATEGORIZATION.md)

### Command Scripts Improvements

- [❌] CHECK FOR ERRORS AND FIX ALL ISSUES of the DHT command `help`. Ensure the dhtl launcher will do the preparatory steps before calling/sourcing the script, and monitor/cleanup during and at the end of the process execution.
- [❌] CHECK FOR ERRORS AND FIX ALL ISSUES of the DHT command `setup`. Ensure the dhtl launcher will do the preparatory steps before calling/sourcing the script, and monitor/cleanup during and at the end of the process execution.
- [❌] CHECK FOR ERRORS AND FIX ALL ISSUES of the DHT command `restore`. Ensure the dhtl launcher will do the preparatory steps before calling/sourcing the script, and monitor/cleanup during and at the end of the process execution.
- [❌] CHECK FOR ERRORS AND FIX ALL ISSUES of the DHT command `env`. Ensure the dhtl launcher will do the preparatory steps before calling/sourcing the script, and monitor/cleanup during and at the end of the process execution.
- [❌] CHECK FOR ERRORS AND FIX ALL ISSUES of the DHT command `clean`. Ensure the dhtl launcher will do the preparatory steps before calling/sourcing the script, and monitor/cleanup during and at the end of the process execution.
- [❌] CHECK FOR ERRORS AND FIX ALL ISSUES of the DHT command `lint`. Ensure the dhtl launcher will do the preparatory steps before calling/sourcing the script `run_platform.sh`, and monitor/cleanup during and at the end of the process execution.
- [❌] CHECK FOR ERRORS AND FIX ALL ISSUES of the DHT command `format`. Ensure the dhtl launcher will do the preparatory steps before calling/sourcing the script, and monitor/cleanup during and at the end of the process execution.
- [✅] CHECK FOR ERRORS AND FIX ALL ISSUES of the DHT command `test`. Ensure the dhtl launcher will do the preparatory steps before calling/sourcing the script `run_tests.sh`, and monitor/cleanup during and at the end of the process execution.
- [❌] CHECK FOR ERRORS AND FIX ALL ISSUES of the DHT command `coverage`. Ensure the dhtl launcher will do the preparatory steps before calling/sourcing the script, and monitor/cleanup during and at the end of the process execution.
- [❌] CHECK FOR ERRORS AND FIX ALL ISSUES of the DHT command `build`. Ensure the dhtl launcher will do the preparatory steps before calling/sourcing the script, and monitor/cleanup during and at the end of the process execution.
- [❌] CHECK FOR ERRORS AND FIX ALL ISSUES of the DHT command `commit`. Ensure the dhtl launcher will do the preparatory steps before calling/sourcing the script, and monitor/cleanup during and at the end of the process execution.
- [❌] CHECK FOR ERRORS AND FIX ALL ISSUES of the DHT command `publish`. Ensure the dhtl launcher will do the preparatory steps before calling/sourcing the script `publish_to_github.sh`, and monitor/cleanup during and at the end of the process execution.
- [❌] CHECK FOR ERRORS AND FIX ALL ISSUES of the DHT command `venv`. Ensure the dhtl launcher will do the preparatory steps before calling/sourcing the script, and monitor/cleanup during and at the end of the process execution.
- [❌] CHECK FOR ERRORS AND FIX ALL ISSUES of the DHT command `install_tools`. Ensure the dhtl launcher will do the preparatory steps before calling/sourcing the script `install_uv.sh`, and monitor/cleanup during and at the end of the process execution.
- [❌] CHECK FOR ERRORS AND FIX ALL ISSUES of the DHT command `setup_project`. Ensure the dhtl launcher will do the preparatory steps before calling/sourcing the script `setup_package.sh`, and monitor/cleanup during and at the end of the process execution.
- [❌] CHECK FOR ERRORS AND FIX ALL ISSUES of the DHT command `workflows`. Ensure the dhtl launcher will do the preparatory steps before calling/sourcing the script `publish_trigger_workflow.sh`, and monitor/cleanup during and at the end of the process execution.
- [❌] CHECK FOR ERRORS AND FIX ALL ISSUES of the DHT command `rebase`. Ensure the dhtl launcher will do the preparatory steps before calling/sourcing the script `resetgit.sh`, and monitor/cleanup during and at the end of the process execution.
- [❌] CHECK FOR ERRORS AND FIX ALL ISSUES of the DHT command `node`. Ensure the dhtl launcher will do the preparatory steps before calling/sourcing the script `node-wrapper.sh`, and monitor/cleanup during and at the end of the process execution.
- [❌] CHECK FOR ERRORS AND FIX ALL ISSUES of the DHT command `script`. Ensure the dhtl launcher will do the preparatory steps before calling/sourcing the appropriate script, and monitor/cleanup during and at the end of the process execution.
- [❌] CHECK FOR ERRORS AND FIX ALL ISSUES of the DHT command `guardian`. Ensure the dhtl launcher will do the preparatory steps before calling/sourcing the script `process-guardian-watchdog.py`, and monitor/cleanup during and at the end of the process execution.
- [❌] CHECK FOR ERRORS AND FIX ALL ISSUES of the DHT command `selfcheck`. Ensure the dhtl launcher will do the preparatory steps before calling/sourcing the script, and monitor/cleanup during and at the end of the process execution.

## [Process Guardian]

- [▶️] Improve process guardian integration with all commands
- [▶️] Fix resource monitoring and limits for all script types
- [▶️] Implement proper cleanup for guardian processes
- [❌] Add memory leak detection and prevention
- [✅] Add automatic psutil installation for process guardian
- [✅] Add verification of guardian startup
- [❌] Add process priority management for resource-intensive operations
- [❌] Implement process queuing for concurrent operations
- [❌] Create guardian dashboard for monitoring active processes

## [Documentation]

- [▶️] Update CLAUDE.md with DHT Launcher usage instructions
- [❌] Add detailed documentation for each command
- [❌] Create command-specific help documentation
- [❌] Update README with usage examples
- [✅] Create DHT_SCRIPTS_CATEGORIZATION.md with script organization
- [❌] Add error code documentation for troubleshooting
- [❌] Create flowcharts for command dependencies
- [❌] Document resource requirements for each command

## [Testing]

- [❌] Create test cases for each command
- [❌] Implement integration tests between commands
- [❌] Test resource usage under load
- [❌] Test error handling and recovery
- [❌] Implement automated test discovery
- [❌] Create standardized test data fixtures
- [❌] Set up test environment isolation
- [❌] Create stress tests for process guardian

## [Future Enhancements]

- [❌] Create configurable extension system for custom scripts
- [❌] Implement command dependencies (run X before Y)
- [❌] Add progress tracking for long-running commands
- [❌] Implement command queuing for resource-intensive operations
- [❌] Create interactive mode for commands
- [❌] Add support for remote execution
- [❌] Implement activity logging and analytics
- [❌] Create plugin architecture for third-party extensions
- [❌] Build web interface for command monitoring

## [Code Quality]

- [❌] Implement consistent error handling pattern
- [❌] Standardize log message format
- [❌] Reduce code duplication across commands
- [❌] Optimize resource usage for memory-intensive operations
- [❌] Create reusable utility functions for common tasks
- [❌] Implement proper signal handling
- [❌] Optimize startup time for commonly used commands

## [Installation & Distribution]

- [❌] Create easy installation script
- [❌] Package DHT for distribution
- [❌] Create auto-update mechanism
- [❌] Add cross-platform compatibility checks
- [❌] Create uninstallation script