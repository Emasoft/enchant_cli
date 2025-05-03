# Process Guardian Enhancements

## Summary of Improvements

We've significantly enhanced the process guardian system to address memory management issues in both Node.js and Python development scripts, while keeping it strictly project-scoped.

## Key Enhancements

### 1. Project-Scoped Process Guardian

The process guardian is now:
- **Fully project-scoped**: Lives entirely within the project directory (`.process_guardian/`)
- **Self-contained**: No system-wide installation or configuration needed
- **Auto-lifecycle management**: Starts when needed, terminates when no monitored processes remain
- **Zero configuration**: Works out of the box with sensible defaults

### 2. Expanded Coverage to Python Development Scripts

- Added support for monitoring Python development scripts
- Created dedicated wrapper scripts for Python dev scripts
- Implemented different memory and concurrency limits for Python vs Node.js
- Prioritization system to manage resources between different process types
  
### 3. Enhanced Process Monitoring

- **Tiered monitoring**: Different memory limits based on process type
- **Process queuing**: Intelligent queuing of processes when resource limits are reached
- **Priority-based management**: Higher priority for critical processes
- **Memory sampling**: Performance-efficient memory sampling to reduce overhead

### 4. Process Type-Specific Configurations

- **Node.js Processes**:
  - 768MB per process limit
  - Maximum 2 concurrent processes
  - Lower priority (queued first when resources are limited)

- **Python Development Scripts**:
  - 512MB per process limit
  - Maximum 3 concurrent processes
  - Medium priority (higher than Node.js)

### 5. Improved State Management

- Separate tracking for Node.js and Python processes
- Enhanced status reporting with memory usage statistics
- Cross-process type resource management
- Automatic cleanup of stale process registrations

### 6. New Command-Line Utilities

- Added `python-dev-wrapper.sh` and `python-dev-wrapper.bat` for Python scripts
- Enhanced `process-guardian-watchdog.py` with support for process types
- Support for combined monitoring of different process types

## Implementation Details

### Major Components Updated

1. **`process-guardian-watchdog.py`**:
   - Added support for Python process type tracking
   - Enhanced configuration with separate limits for each process type
   - Improved status reporting with per-type statistics
   - Updated command-line interface with process type support

2. **Wrapper Scripts**:
   - Enhanced `node-wrapper.sh` and `node-wrapper.bat` for Node.js
   - Added new `python-dev-wrapper.sh` and `python-dev-wrapper.bat` for Python
   - Script-type detection and conditional guardian usage

3. **Documentation**:
   - Added comprehensive `.process_guardian/README.md`
   - Updated main README.md with process guardian information
   - Added detailed usage examples for both Node.js and Python

## Usage

### Node.js Commands

```bash
# Unix/Linux/macOS
./node-wrapper.sh node [args...]
./node-wrapper.sh npm [args...]
./node-wrapper.sh npx [args...]

# Windows
node-wrapper.bat node [args...]
node-wrapper.bat npm [args...]
node-wrapper.bat npx [args...]
```

### Python Development Scripts

```bash
# Unix/Linux/macOS
./python-dev-wrapper.sh helpers/errors/log_analyzer.py [args...]
./python-dev-wrapper.sh get_errorlogs.sh [args...]

# Windows
python-dev-wrapper.bat helpers\errors\log_analyzer.py [args...]
```

## Benefits

1. **Prevents memory-related crashes**: Automatically limits memory usage
2. **Resource optimization**: Controls concurrent processes to prevent resource exhaustion
3. **Project-scoped**: No system-wide impact or configuration needed
4. **Automatic operation**: Starts and stops automatically, requiring no user intervention
5. **Intelligent resource allocation**: Prioritizes processes based on type and importance
6. **Cross-platform**: Works consistently on macOS, Linux, and Windows

## Implementation Notes

The enhanced system is designed to be:

- **Non-invasive**: Only affects processes explicitly run through wrapper scripts
- **Lightweight**: Minimal overhead when monitoring processes
- **User-friendly**: Clear error messages and status reporting
- **Maintainable**: Modular design with clear separation of concerns
- **Resilient**: Handles edge cases like process crashes and unexpected terminations