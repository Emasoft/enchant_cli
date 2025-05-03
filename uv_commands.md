# uv Commands and Workflows Reference

This document provides a quick reference for common uv commands and workflows for this project.

## Basic uv Commands

### Environment Management

```bash
# Create a virtual environment
uv venv .venv

# Activate the virtual environment (Unix/Linux/macOS)
source .venv/bin/activate

# Activate the virtual environment (Windows)
.venv\Scripts\activate.bat

# Install dependencies from lock file
uv sync

# Install development dependencies
uv pip install -e .
```

### Package Management

```bash
# Install a package
uv pip install package-name

# Install a specific version
uv pip install package-name==1.2.3

# Install from requirements.txt
uv pip install -r requirements.txt

# Install with extras
uv pip install -e ".[dev,test]"
```

### Dependency Locking

```bash
# Compile dependencies from pyproject.toml to lock file
uv lock 

# Upgrade all dependencies
uv lock --upgrade

# Upgrade specific packages
uv lock --upgrade-package package-name
```

### Tool Management

```bash
# Install a tool
uv tool install tool-name

# Run a tool without installing it globally
uv tool run tool-name [arguments]

# List installed tools
uv tool list

# Uninstall a tool
uv tool uninstall tool-name
```

## bump-my-version Commands

```bash
# Show current version
uv tool run bump-my-version show

# Bump version (major, minor, patch)
uv tool run bump-my-version bump minor

# Bump version with commit and tag
uv tool run bump-my-version bump minor --commit --tag

# Allow dirty working directory
uv tool run bump-my-version bump minor --allow-dirty

# Custom commit message
uv tool run bump-my-version bump minor --message "Version {new_version}"
```

## pre-commit Commands

```bash
# Install pre-commit hooks
pre-commit install

# Run pre-commit hooks on all files
pre-commit run --all-files

# Run specific hook
pre-commit run hook-id --all-files

# Update hook versions
pre-commit autoupdate
```

## tox Commands with tox-uv

```bash
# Run all test environments
tox

# Run specific environment
tox -e py310

# Run with specific interpreter
tox -e py311

# Run linting environment
tox -e lint

# Run type checking environment
tox -e typecheck

# Run with custom arguments for pytest
tox -e py310 -- -xvs tests/test_specific.py
```

## GitHub CI/CD Workflows

The CI/CD workflows are configured to use uv for:

1. **Setting Up Environment**:
   ```yaml
   - name: Install uv
     run: |
       curl -LsSf https://astral.sh/uv/install.sh | sh
       pip install uv
   ```

2. **Installing Dependencies**:
   ```yaml
   - name: Install dependencies
     run: |
       uv sync
       uv pip install -e .
   ```

3. **Running Tests**:
   ```yaml
   - name: Run tests
     run: |
       uv tool run pytest tests/ --cov=enchant_cli --cov-report=xml
   ```

4. **Building and Publishing**:
   ```yaml
   - name: Build package
     run: |
       uv build
       
   - name: Publish to PyPI
     run: |
       uv publish --no-build
   ```

## Common Workflows

### Setting Up Development Environment

```bash
# Clone the repository
git clone <repository-url>
cd <repository-directory>

# Run the uv installer script
./install_uv.sh  # Unix/Linux/macOS
install_uv.bat   # Windows

# Install pre-commit hooks
pre-commit install
```

### Adding Dependencies

```bash
# Add a dependency to pyproject.toml manually
# Then update the lock file
uv lock

# Sync your environment with the new dependencies
uv sync
```

### Running Tests

```bash
# Using pytest directly
uv tool run pytest tests/

# Using tox with uv backend
tox -e py310
```

### Publishing a New Release

```bash
# Bump version
uv tool run bump-my-version bump minor --commit --tag

# Push changes and tags to GitHub
git push --follow-tags
```

## Environment Variables

uv respects the following environment variables:

- `UV_CACHE_DIR`: Sets the cache directory for uv
- `UV_NATIVE_TLS`: Controls whether to use native TLS (default: true)
- `UV_SYSTEM_PYTHON`: Sets the system Python interpreter to use
- `UV_EXCLUDE_NEWER`: Exclude Python versions newer than a specific version

## Project-Specific Workflows

### Updating Pre-commit Config

```bash
# Update pre-commit-uv hooks
pre-commit autoupdate
```

### Fixing Dependencies

```bash
# Regenerate lock file from scratch
rm uv.lock
uv lock

# Sync environment with fixed dependencies
uv sync
```

## Troubleshooting

### Common Issues

1. **Missing tools**: If a tool is not found, install it with `uv tool install <tool-name>`
2. **Sync issues**: If uv sync fails, try removing the lock file and recreating it with `uv lock`
3. **Virtual environment problems**: If you encounter issues with the virtual environment, recreate it with `uv venv --force .venv`

### Getting Help

```bash
# View uv command help
uv --help

# View help for a specific command
uv pip --help

# View pip command help
uv pip install --help
```