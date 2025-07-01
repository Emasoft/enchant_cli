# Memory-Safe Git Hooks v2.0 - Multi-Instance Support

Enhanced version that supports multiple concurrent safe instances across different projects and Claude Code sessions.

## Key Enhancements in v2

### 1. **Multi-Instance Support**
- Run gitleaks safely in multiple projects simultaneously
- Each instance gets a unique session ID with environment marker
- Safe processes are identified by `GITLEAKS_SAFE_INSTANCE` environment variable

### 2. **Smart Process Management**
- Only kills **unsafe** gitleaks processes (those not managed by our wrapper)
- Preserves safe instances running in other projects/terminals
- Shows detailed process information with safety status

### 3. **Docker Container Awareness**
- Detects and kills gitleaks processes inside Docker containers
- Prevents memory leaks from containerized scans

### 4. **Installation Detection**
- Finds all gitleaks installations on the system
- Shows version and location of each installation
- Detects global, local, and node_modules installations

## Installation

### Quick Install (Recommended)
```bash
./scripts/install-safe-git-hooks-v2.sh
```

This will:
- Auto-detect your OS and install gitleaks if needed
- Install the v2 wrapper scripts
- Set up git hooks that use the safe wrapper

### Installation Options
```bash
# Install pre-push hook only (default, recommended)
./scripts/install-safe-git-hooks-v2.sh

# Install pre-commit hook only
./scripts/install-safe-git-hooks-v2.sh --pre-commit

# Install both hooks
./scripts/install-safe-git-hooks-v2.sh --both

# Non-interactive mode (auto-install gitleaks)
./scripts/install-safe-git-hooks-v2.sh --non-interactive

# Use v1 wrapper (single instance mode)
./scripts/install-safe-git-hooks-v2.sh --v1
```

## Usage

### Automatic (via Git Hooks)
Once installed, gitleaks will run safely on:
- `git commit` (if pre-commit hook installed)
- `git push` (if pre-push hook installed)

### Manual Scans
```bash
# Scan entire repository
./scripts/gitleaks-safe-v2.sh detect --source .

# Scan staged changes
./scripts/gitleaks-safe-v2.sh protect --staged

# Scan with custom config
./scripts/gitleaks-safe-v2.sh detect --config .gitleaks.toml

# Verbose mode
GITLEAKS_VERBOSE=true ./scripts/gitleaks-safe-v2.sh detect
```

### Process Management
```bash
# View and clean up unsafe processes
./scripts/cleanup-gitleaks-v2.sh

# This will show:
# - All gitleaks installations found
# - Safe vs unsafe processes
# - Memory usage per process
# - Docker container processes
```

## How It Works

### Process Identification
Each safe instance sets a unique environment variable:
```bash
GITLEAKS_SAFE_INSTANCE=<timestamp>-<pid>-<project-hash>
```

The wrapper checks for this marker to identify safe processes:
- **Safe processes**: Have the marker, won't be killed
- **Unsafe processes**: No marker, will be terminated

### Lock Files
Per-project lock files prevent multiple scans in the same directory:
```
/tmp/gitleaks-safe-<project-hash>.lock
```

### Docker Support
The scripts check all running containers:
```bash
docker exec <container> pgrep -f "gitleaks"
```

## Configuration

### Environment Variables
```bash
# Timeout for scans (default: 120 seconds)
export GITLEAKS_TIMEOUT=300

# Enable verbose output
export GITLEAKS_VERBOSE=true

# Number of retry attempts (default: 1)
export GITLEAKS_RETRIES=3
```

### Per-Project Configuration
Add to your shell profile for project-specific settings:
```bash
# In .zshrc or .bashrc
if [[ "$PWD" == *"my-sensitive-project"* ]]; then
    export GITLEAKS_TIMEOUT=600  # 10 minutes for large repos
fi
```

## Troubleshooting

### "Process already running" Error
This means a safe instance is already scanning this directory:
```bash
# Check lock file
cat /tmp/gitleaks-safe-*.lock

# If stale, remove it
rm /tmp/gitleaks-safe-*.lock
```

### Multiple Installations Detected
The tool will show all installations found:
```
📍 Gitleaks Installations Found:
  /opt/homebrew/bin/gitleaks
    Version: 8.27.2 | Size: 23M
  /usr/local/bin/gitleaks
    Version: 8.18.0 | Size: 22M
```

### Docker Container Issues
If gitleaks is running in containers:
```bash
# The cleanup script will offer to clean containers
./scripts/cleanup-gitleaks-v2.sh
# Answer 'y' to "Also clean up gitleaks in Docker containers?"
```

### High Memory Usage
Check which processes are unsafe:
```bash
./scripts/cleanup-gitleaks-v2.sh
# Shows memory usage per process
# Only terminates unsafe processes
```

## Multi-Project Workflow

### Scenario: Multiple Claude Code Sessions
When running Claude Code in multiple terminal tabs/windows:

1. **Project A** (Terminal 1):
   ```bash
   cd /path/to/project-a
   ./scripts/install-safe-git-hooks-v2.sh
   git commit -m "feature"  # Runs safe gitleaks
   ```

2. **Project B** (Terminal 2):
   ```bash
   cd /path/to/project-b
   ./scripts/install-safe-git-hooks-v2.sh
   git push  # Runs safe gitleaks concurrently
   ```

Both will run safely without killing each other's processes!

### Scenario: CI/CD Pipeline
```yaml
# GitHub Actions example
- name: Install safe gitleaks
  run: |
    ./scripts/install-safe-git-hooks-v2.sh --non-interactive

- name: Run security scan
  run: |
    GITLEAKS_TIMEOUT=600 ./scripts/gitleaks-safe-v2.sh detect
```

## Best Practices

1. **Use Pre-push over Pre-commit**
   - Less frequent scans
   - Better performance
   - Still catches secrets before they go remote

2. **Configure Timeouts Appropriately**
   ```bash
   # Small projects
   export GITLEAKS_TIMEOUT=60

   # Large monorepos
   export GITLEAKS_TIMEOUT=600
   ```

3. **Regular Cleanup**
   ```bash
   # Weekly cleanup of orphaned processes
   ./scripts/cleanup-gitleaks-v2.sh
   ```

4. **Monitor Multiple Instances**
   ```bash
   # See all safe instances running
   ps aux | grep GITLEAKS_SAFE_INSTANCE
   ```

## Migrating from v1

The v2 scripts are backward compatible. To upgrade:

1. Install v2:
   ```bash
   ./scripts/install-safe-git-hooks-v2.sh
   ```

2. Remove old scripts (optional):
   ```bash
   rm scripts/gitleaks-safe.sh
   rm scripts/cleanup-gitleaks.sh
   ```

3. Or keep both and choose at runtime:
   ```bash
   # Use v1 (single instance)
   ./scripts/install-safe-git-hooks-v2.sh --v1

   # Use v2 (multi-instance)
   ./scripts/install-safe-git-hooks-v2.sh
   ```

## Technical Details

### Process Detection Method

**macOS**:
```bash
ps -p <pid> -E | grep GITLEAKS_SAFE_INSTANCE
```

**Linux**:
```bash
grep GITLEAKS_SAFE_INSTANCE /proc/<pid>/environ
```

### Session ID Format
```
<timestamp>-<pid>-<project-hash>
1704123456-12345-a1b2c3d4
```

### Lock File Naming
```
/tmp/gitleaks-safe-<md5-of-pwd>.lock
```

## License

These enhanced scripts are provided as-is for use in any project. Feel free to modify and distribute as needed.
