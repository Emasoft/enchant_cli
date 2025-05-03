# Project Backups and Environment Restoration

This directory contains backups of the project, created before making significant changes or switching branches. Since untracked files are lost during branch switches, these backups serve as a safety mechanism.

## Backup Strategy

Before any potentially destructive Git operation (checkout, switch, reset, rebase, etc.), create a backup:

```bash
# Create a timestamped backup of the entire project directory
cd /Users/emanuelesabetta/Code/ENCHANT_BOOK_MANAGER/enchant_cli
zip -r backups/enchant_cli_backup_$(date +"%Y%m%d_%H%M%S").zip .
```

## Environment Restoration After Branch Switch

When switching branches, the `.venv` directory and other untracked files will be lost. Follow these steps to restore the environment:

### 1. Set up the virtual environment

```bash
# Create a new virtual environment
python -m venv .venv

# Activate the environment
source .venv/bin/activate  # On Linux/macOS
# or
.venv\Scripts\activate     # On Windows
```

### 2. Install and configure uv

```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install uv in the virtual environment
pip install uv

# Use uv to install dependencies from the lock file
uv sync

# Install the project in development mode
uv pip install -e .
```

### 3. Install development tools

```bash
# Install development tools
uv pip install -r requirements-dev.txt

# Install pre-commit hooks
pre-commit install
```

### 4. Restore DHT Process Guardian

```bash
# Ensure directory structure exists
mkdir -p DHT/.process_guardian

# Start the process guardian
./dhtl.sh guardian start
```

### 5. Install project-specific dependencies

```bash
# Install psutil for process guardian
pip install psutil

# Install tree-sitter for DHTL refactoring
pip install tree-sitter

# Install GitHub CLI (if needed)
# On macOS: brew install gh
# On Linux: See https://github.com/cli/cli/blob/trunk/docs/install_linux.md
# On Windows: winget install GitHub.cli
```

## Critical Files to Track

The following files/directories should always be tracked in Git to ensure they're preserved during branch switches:

1. **Configuration Files**:
   - `.bumpversion.toml`
   - `pyproject.toml`
   - `setup.cfg`
   - `setup.py`
   - `pytest.ini`
   - `tox.ini`
   - `.pre-commit-config.yaml`
   - `codecov.yml`

2. **Documentation Files**:
   - `README.md`
   - `CLAUDE.md`
   - `DHT_SCRIPTS_CATEGORIZATION.md`
   - `DHTL_REFACTORING_PLAN.md`
   - `ENHANCEMENT_SUMMARY.md`
   - `PROCESS_GUARDIAN_ENHANCEMENTS.md`
   - `ROADMAP.md`
   - `UV_INTEGRATION.md`
   - `tasks_checklist.md`
   - `uv_commands.md`

3. **DHT Scripts**:
   - All scripts in the `DHT/` directory
   - `dhtl.sh` and `dhtl.bat` launcher scripts

4. **GitHub Workflows**:
   - `.github/workflows/*.yml`

## Verifying Your Environment

After restoration, you can verify your environment setup:

```bash
# Verify the virtual environment
./dhtl.sh env

# Run tests to ensure functionality
./dhtl.sh test
```

Remember: Always commit all important files before switching branches to avoid data loss!