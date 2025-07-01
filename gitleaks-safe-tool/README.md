# Gitleaks Safe - Memory-Safe Git Hooks for Gitleaks

A Python-based tool that provides memory-safe wrappers for [gitleaks](https://github.com/gitleaks/gitleaks), preventing system crashes from concurrent processes and memory exhaustion.

## Features

- **Multi-Instance Support**: Run gitleaks safely in multiple projects simultaneously
- **Smart Process Management**: Only kills unsafe gitleaks processes, preserves managed ones
- **Docker Container Support**: Detects and manages gitleaks processes in containers
- **Cross-Platform**: Works on macOS, Linux, Windows, and Docker
- **Easy Installation**: Install globally with `uv tool install`

## Installation

### Using uv (Recommended)

```bash
# Install globally as a uv tool
uv tool install gitleaks-safe

# Or install from local directory
uv tool install --from ./gitleaks-safe-tool
```

### Using pip

```bash
pip install gitleaks-safe
```

## Quick Start

### 1. Install Git Hooks

```bash
# Install in current repository
install-safe-git-hooks

# Install with options
install-safe-git-hooks --pre-push     # Default: pre-push only
install-safe-git-hooks --pre-commit   # Pre-commit only
install-safe-git-hooks --both         # Both hooks
install-safe-git-hooks --non-interactive  # Auto-install gitleaks if missing
```

### 2. Run Gitleaks Safely

```bash
# All gitleaks commands work through the wrapper
gitleaks-safe detect --source .
gitleaks-safe protect --staged
gitleaks-safe detect --config .gitleaks.toml
```

### 3. Clean Up Processes

```bash
# Smart cleanup (preserves safe instances)
cleanup-gitleaks

# Force cleanup all processes
cleanup-gitleaks --all

# Skip confirmation
cleanup-gitleaks --force
```

## How It Works

### Process Identification

Each safe instance sets a unique environment variable:
```
GITLEAKS_SAFE_INSTANCE=<timestamp>-<pid>-<project-hash>
```

The wrapper identifies processes as:
- **Safe**: Has the environment marker (preserved)
- **Unsafe**: No marker (terminated)

### Multi-Project Support

Run gitleaks in multiple terminals/projects simultaneously:

```bash
# Terminal 1 - Project A
cd /path/to/project-a
git commit -m "feature"  # Runs safe gitleaks

# Terminal 2 - Project B
cd /path/to/project-b
git push  # Also runs safe gitleaks

# Both run without interference!
```

## Configuration

Set environment variables to customize behavior:

```bash
# Timeout for scans (default: 120 seconds)
export GITLEAKS_TIMEOUT=300

# Enable verbose output
export GITLEAKS_VERBOSE=true

# Number of retry attempts (default: 1)
export GITLEAKS_RETRIES=3
```

## Commands

### `gitleaks-safe`
Memory-safe wrapper for gitleaks. All arguments are passed through.

```bash
gitleaks-safe [gitleaks arguments]

# Examples
gitleaks-safe detect --source .
gitleaks-safe protect --staged --verbose
GITLEAKS_TIMEOUT=600 gitleaks-safe detect
```

### `install-safe-git-hooks`
Install git hooks that use the safe wrapper.

```bash
install-safe-git-hooks [options]

Options:
  --pre-commit       Install pre-commit hook only
  --pre-push         Install pre-push hook only (default)
  --both             Install both hooks
  --non-interactive  Don't prompt for input
```

### `cleanup-gitleaks`
Clean up gitleaks processes intelligently.

```bash
cleanup-gitleaks [options]

Options:
  -f, --force  Skip confirmation prompts
  -a, --all    Kill all processes (including safe ones)
```

## Features in Detail

### Automatic Gitleaks Installation

The installer can automatically install gitleaks for your platform:
- macOS: via Homebrew
- Ubuntu/Debian: via snap or binary
- Fedora/CentOS: via dnf/yum
- Arch Linux: via AUR
- Windows: via scoop/chocolatey
- Docker: direct binary download

### Process Analysis

The cleanup tool shows detailed process information:
- Safe vs unsafe status
- CPU and memory usage
- Elapsed time
- Full command line

### Docker Support

Automatically detects and manages gitleaks in Docker containers:
- Lists containers with gitleaks processes
- Offers to clean up container processes
- Prevents hidden memory leaks

## Best Practices

1. **Use Pre-push over Pre-commit**: Less frequent scans, better performance
2. **Configure Timeouts**: Adjust based on repository size
3. **Regular Cleanup**: Run `cleanup-gitleaks` weekly
4. **Monitor Installations**: Check for duplicate gitleaks installations

## Troubleshooting

### "Process already running" Error
```bash
# Check and clean lockfiles
cleanup-gitleaks
```

### Timeout Issues
```bash
# Increase timeout for large repositories
export GITLEAKS_TIMEOUT=600  # 10 minutes
```

### Multiple Installations
The tool will show all gitleaks installations found. Remove duplicates if needed.

## Development

### Project Structure
```
gitleaks-safe-tool/
├── pyproject.toml
├── README.md
└── src/
    └── gitleaks_safe/
        ├── __init__.py
        ├── cli.py          # Main wrapper CLI
        ├── installer.py    # Git hooks installer
        ├── cleanup.py      # Process cleanup utility
        ├── wrapper.py      # Core wrapper logic
        └── utils.py        # Shared utilities
```

### Building
```bash
# Build with uv
uv build

# Install locally for testing
uv pip install -e .
```

## License

MIT License - Feel free to use and modify as needed.

## Credits

Created to solve memory exhaustion issues when running gitleaks across multiple projects in concurrent sessions.
