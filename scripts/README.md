# Memory-Safe Git Hooks

This directory contains portable scripts to prevent memory exhaustion issues caused by gitleaks running multiple times concurrently.

## Problem

When git hooks run gitleaks without proper resource management, multiple instances can spawn simultaneously, each consuming 2+ GB of RAM. This can lead to "application memory" exhaustion and system crashes.

## Solution

We provide three scripts that work together:

1. **`gitleaks-safe.sh`** - A wrapper around gitleaks that:
   - Prevents multiple concurrent runs using lock files
   - Adds timeout protection (default: 2 minutes)
   - **Kills ALL existing gitleaks processes system-wide** before starting
   - Provides clear feedback and process information
   - Works across different projects

2. **`install-safe-git-hooks.sh`** - Installs git hooks that use the safe wrapper:
   - Auto-detects and installs gitleaks for your platform
   - Configurable to install pre-commit, pre-push, or both
   - Automatically backs up existing hooks
   - Self-contained and portable

3. **`cleanup-gitleaks.sh`** - Manual cleanup utility:
   - Shows all running gitleaks processes with CPU/memory usage
   - Calculates total memory consumption
   - Safely terminates all gitleaks processes
   - Cleans up stale lock files

## Installation

### For this project:
```bash
./scripts/install-safe-git-hooks.sh
```

### For other projects:
1. Copy the entire `scripts` directory to your project
2. Run the installer:
   ```bash
   ./scripts/install-safe-git-hooks.sh
   ```

The installer will:
- Check if gitleaks is installed
- Offer to install gitleaks automatically for your platform
- Set up the memory-safe git hooks

### Automatic gitleaks installation

The installer supports automatic installation on:
- **macOS**: via Homebrew
- **Ubuntu/Debian**: via snap or direct binary download
- **Fedora/CentOS/RHEL**: via dnf/yum or direct binary
- **Arch Linux**: via yay (AUR)
- **Alpine Linux**: via apk
- **Windows**: via scoop or chocolatey
- **Docker containers**: direct binary download
- **Other systems**: attempts generic binary installation

### Installation options:
```bash
# Install pre-push hook only (recommended - default)
./scripts/install-safe-git-hooks.sh

# Install pre-commit hook only
./scripts/install-safe-git-hooks.sh --pre-commit

# Install both hooks
./scripts/install-safe-git-hooks.sh --both
```

## Configuration

Set these environment variables to customize behavior:

```bash
# Increase timeout to 5 minutes (default: 120 seconds)
export GITLEAKS_TIMEOUT=300

# Enable verbose output (default: false)
export GITLEAKS_VERBOSE=true

# Set retry attempts (default: 1)
export GITLEAKS_RETRIES=3
```

You can add these to your shell profile (`.zshrc`, `.bashrc`, etc.) for permanent configuration.

## Manual Usage

You can also run gitleaks manually with the wrapper:

```bash
# Scan staged changes
./scripts/gitleaks-safe.sh protect --staged

# Scan entire repository
./scripts/gitleaks-safe.sh detect --source .

# With custom config
./scripts/gitleaks-safe.sh protect --config .gitleaks.toml
```

## Troubleshooting

### "Gitleaks is already running" error
If you get this error and gitleaks is not actually running:
```bash
# Remove the lock file
rm /tmp/gitleaks-safe-*.lock
```

### Multiple gitleaks processes consuming memory
If you notice high memory usage from gitleaks:
```bash
# Run the cleanup utility
./scripts/cleanup-gitleaks.sh
```

This will:
- Show all running gitleaks processes with their memory usage
- Calculate total memory consumption
- Offer to terminate all processes safely
- Clean up any stale lock files

### Timeout issues
If scans are timing out:
```bash
# Increase timeout for large repositories
export GITLEAKS_TIMEOUT=600  # 10 minutes
```

### Debug mode
To see what's happening:
```bash
export GITLEAKS_VERBOSE=true
git commit -m "test"
```

## Why use the wrapper?

1. **Prevents memory exhaustion**: No more system crashes from multiple gitleaks instances
2. **Faster commits**: Timeouts prevent hanging on large repositories
3. **Better feedback**: Clear messages about what's happening
4. **Portable**: Works across all your projects
5. **Configurable**: Adjust timeout and verbosity as needed

## Best Practices

1. **Use pre-push instead of pre-commit**: Running gitleaks on every commit can slow down development. Pre-push provides a good balance.

2. **Configure .gitleaks.toml**: Add false positives to your `.gitleaks.toml` file to reduce noise:
   ```toml
   [[allowlist]]
   description = "Allow markdown examples"
   paths = ["README.md", "docs/"]
   ```

3. **CI/CD Integration**: Also run gitleaks in your CI/CD pipeline as a safety net:
   ```yaml
   - name: Run gitleaks
     run: |
       ./scripts/gitleaks-safe.sh detect --source . --verbose
   ```

## License

These scripts are provided as-is for use in any project. Feel free to modify and distribute as needed.
