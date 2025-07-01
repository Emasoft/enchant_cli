# Gitleaks Safe Wrapper - Upgrade Summary

## What's New in v2

We've created an enhanced version of the memory-safe git hooks that addresses your requirement for **multiple concurrent instances** across different Claude Code sessions.

### Key Improvements

1. **Multi-Instance Support**
   - Multiple projects can run gitleaks simultaneously
   - Each safe instance is marked with a unique environment variable
   - Safe processes are preserved while unsafe ones are terminated

2. **Smart Process Detection**
   - Uses `GITLEAKS_SAFE_INSTANCE` environment marker
   - Identifies which processes are managed by our wrapper
   - Only kills processes that aren't marked as safe

3. **Docker Container Support**
   - Scans all running Docker containers for gitleaks
   - Terminates gitleaks processes inside containers
   - Prevents hidden memory leaks from containerized processes

4. **Installation Discovery**
   - Finds all gitleaks installations on the system
   - Shows version and location of each installation
   - Helps identify duplicate or outdated installations

## File Structure

```
scripts/
├── gitleaks-safe.sh           # Original v1 (single instance)
├── gitleaks-safe-v2.sh        # NEW: Multi-instance wrapper
├── cleanup-gitleaks.sh        # Original v1 cleanup
├── cleanup-gitleaks-v2.sh     # NEW: Smart cleanup (preserves safe)
├── install-safe-git-hooks.sh  # Original v1 installer
├── install-safe-git-hooks-v2.sh # NEW: Enhanced installer
├── README.md                  # Original documentation
├── README-v2.md              # NEW: v2 documentation
└── UPGRADE-SUMMARY.md        # This file
```

## How It Works

### Process Marking
When v2 wrapper starts gitleaks, it sets an environment variable:
```bash
GITLEAKS_SAFE_INSTANCE=1704123456-12345-a1b2c3d4
```

### Process Identification
Before killing any process, the wrapper checks:
- macOS: `ps -p <pid> -E | grep GITLEAKS_SAFE_INSTANCE`
- Linux: `grep GITLEAKS_SAFE_INSTANCE /proc/<pid>/environ`

### Multi-Project Example
```
Terminal 1: Project A
├─ gitleaks (PID 1234) [SAFE - has marker]
│
Terminal 2: Project B
├─ gitleaks (PID 5678) [SAFE - has marker]
│
Terminal 3: Manual run
└─ gitleaks (PID 9999) [UNSAFE - no marker] ← Will be killed
```

## Migration Guide

### Option 1: Full Upgrade (Recommended)
```bash
# Install v2 wrapper
./scripts/install-safe-git-hooks-v2.sh

# This automatically uses v2 wrapper
```

### Option 2: Test First
```bash
# Test v2 wrapper manually
./scripts/gitleaks-safe-v2.sh detect --source .

# Check process management
./scripts/cleanup-gitleaks-v2.sh

# If satisfied, install hooks
./scripts/install-safe-git-hooks-v2.sh
```

### Option 3: Keep Both Versions
```bash
# Use v1 for single project work
./scripts/install-safe-git-hooks.sh

# Use v2 for multi-project work
./scripts/install-safe-git-hooks-v2.sh

# Or explicitly choose v1 mode with v2 installer
./scripts/install-safe-git-hooks-v2.sh --v1
```

## Usage Scenarios

### Scenario 1: Multiple Claude Code Sessions
```bash
# Terminal 1 - Project A
cd /path/to/project-a
git commit -m "feature"  # Runs safe gitleaks

# Terminal 2 - Project B (concurrent)
cd /path/to/project-b
git push  # Also runs safe gitleaks

# Both run without interference!
```

### Scenario 2: Cleanup Only Unsafe
```bash
# See all processes with safety status
./scripts/cleanup-gitleaks-v2.sh

# Output shows:
# ✅ SAFE: PID 1234 (Project A)
# ✅ SAFE: PID 5678 (Project B)
# ⚠️  UNSAFE: PID 9999 (unknown)
#
# Only PID 9999 will be terminated
```

### Scenario 3: Docker Containers
```bash
# v2 automatically checks containers
./scripts/cleanup-gitleaks-v2.sh

# Shows processes in containers:
# Container: my-app - 2 process(es)
# Offers to clean them up
```

## Benefits

1. **No More Conflicts**: Run gitleaks in multiple projects simultaneously
2. **Intelligent Cleanup**: Only terminates problematic processes
3. **Complete Coverage**: Includes Docker container processes
4. **Better Visibility**: Shows all installations and process details
5. **Backward Compatible**: Can still use v1 mode if needed

## Recommendations

1. **Use v2 for Multi-Project Work**: Essential for multiple Claude Code sessions
2. **Regular Cleanup**: Run `cleanup-gitleaks-v2.sh` weekly
3. **Monitor Installations**: Check for duplicate gitleaks installations
4. **Configure Timeouts**: Adjust `GITLEAKS_TIMEOUT` per project size

## Next Steps

1. Test the v2 wrapper in one project
2. If satisfied, roll out to all projects
3. Copy the `scripts/` folder to other projects
4. Run the installer in each project

The v2 wrapper is production-ready and thoroughly handles the multi-instance requirements you specified.
