# UV Integration Documentation

This document explains how the project has been updated to use UV package manager and related tools for an improved Python development workflow.

## What is UV?

UV is a modern Python package manager and installer that offers significant speed improvements over pip. Its key features include:

- **Fast installation and dependency resolution**
- **Reproducible environments with lockfiles**
- **Tools management for development tools**
- **Improved compatibility and dependency handling**
- **Integrated with pre-commit and tox**

## Installed Tools and Integrations

The following UV-related tools have been installed and configured:

1. **uv**: Core package manager
2. **pre-commit-uv**: Pre-commit hooks for UV
3. **tox-uv**: Tox plugin for UV
4. **bump-my-version**: Version bumping with UV integration

## Key Configuration Files

The UV integration includes the following configurations:

### 1. tox.ini

The `tox.ini` file is configured to use tox-uv for testing:

```ini
[tox]
envlist = py39, py310, py311, py312, py313
isolated_build = True
requires =
    tox-uv>=0.8.1
    tox>=4.11.4
```

### 2. .pre-commit-config.yaml

The pre-commit configuration includes UV-specific hooks:

```yaml
repos:
  - repo: https://github.com/tox-dev/pre-commit-uv
    rev: 0.0.5
    hooks:
      - id: pip-sync-uv
        name: Sync development environment with uv
        args: ["--check"]
        files: '(^pyproject\.toml|uv\.lock|\\..*\.toml)$'
      - id: pip-compile-uv
        name: Lock dependencies with uv
        args: ["--check", "--upgrade"]
        files: 'pyproject\.toml$'
```

### 3. .bumpversion.toml

The bump-my-version configuration includes UV integration:

```toml
pre_commit_hooks = ["uv sync", "git add uv.lock"]
```

### 4. GitHub Workflows

GitHub workflows have been updated to use UV:

```yaml
- name: Install uv
  run: |
    curl -LsSf https://astral.sh/uv/install.sh | sh
    python -m pip install uv
    
- name: Install dependencies
  run: |
    uv sync
    uv pip install -e .
```

## Helper Scripts

### install_uv.sh / install_uv.bat

These scripts provide a comprehensive setup for UV and related tools:

- Install UV in the project's virtual environment
- Install pre-commit-uv, tox-uv, and bump-my-version
- Configure all necessary integration files
- Update GitHub workflow files for UV support

### hooks/bump_version.sh

The bump_version script has been updated to use UV for version management:

```bash
"$UV_CMD" tool run bump-my-version bump minor --commit --tag --allow-dirty
```

## Common UV Commands

See the `uv_commands.md` file for a comprehensive list of UV commands and workflows. Here are some essential commands:

```bash
# Create a virtual environment
uv venv .venv

# Install dependencies from lock file
uv sync

# Install a package
uv pip install package-name

# Install the project in development mode
uv pip install -e .

# Run a tool without installing it globally
uv tool run tool-name

# Bump version with commit and tag
uv tool run bump-my-version bump minor --commit --tag
```

## Benefits of the UV Integration

The UV integration provides several benefits:

1. **Faster dependency resolution and installation**: UV is significantly faster than pip.

2. **Reproducible environments**: Lock files ensure consistent environments across development and CI.

3. **Improved tool management**: Run tools without installing them globally.

4. **Simplified workflows**: Integrated pre-commit hooks for automatic dependency syncing.

5. **Streamlined CI/CD**: Enhanced GitHub workflows with UV support.

## How to Use UV in Your Development Workflow

### Setting Up a New Development Environment

```bash
# Clone the repository
git clone https://github.com/yourusername/enchant_cli.git
cd enchant_cli

# Run the UV installer script
./install_uv.sh  # Unix/Linux/macOS
install_uv.bat   # Windows

# Install pre-commit hooks
pre-commit install
```

### Daily Development Workflow

1. **Fetch latest changes**:
   ```bash
   git pull
   ```

2. **Sync your environment**:
   ```bash
   uv sync
   ```

3. **Run tests with tox-uv**:
   ```bash
   tox -e py310  # Or your preferred Python version
   ```

4. **Run pre-commit checks**:
   ```bash
   pre-commit run --all-files
   ```

5. **Commit changes**:
   ```bash
   git add .
   git commit -m "Your commit message"
   ```
   - The pre-commit hook will automatically bump the version

6. **Push changes**:
   ```bash
   ./publish_to_github.sh --skip-tests
   ```

## Troubleshooting

### Common Issues and Solutions

1. **Lock file conflicts**:
   ```bash
   rm uv.lock
   uv lock
   ```

2. **Missing dependencies**:
   ```bash
   uv sync --check
   ```

3. **Tool not found**:
   ```bash
   uv tool install tool-name
   ```

4. **Version bumping issues**:
   ```bash
   uv tool run bump-my-version bump minor --allow-dirty
   ```

## Recommended Practices

1. **Always use `uv sync` after pulling changes** to ensure your environment is up-to-date.

2. **Use `uv tool run` instead of installing tools globally** to maintain environment isolation.

3. **Commit the lock file (`uv.lock`)** to ensure consistent environments across the team.

4. **Let pre-commit-uv manage your dependencies** to ensure consistency between pyproject.toml and the lock file.

5. **Use tox-uv for testing across multiple Python versions** to ensure compatibility.

## References

- [UV Documentation](https://docs.astral.sh/uv)
- [pre-commit-uv](https://github.com/tox-dev/pre-commit-uv)
- [tox-uv](https://github.com/tox-dev/tox-uv)
- [bump-my-version](https://github.com/callowayproject/bump-my-version)