# GitHub Workflows Best Practices

This document synthesizes the patterns and practices from successful GitHub Actions workflows in the EnChANT Book Manager project.

## Successful Workflow Patterns

Based on analysis of workflow runs, the following workflows have the highest success rate:
- **Pre-commit** (100% success)
- **Format** (100% success)
- **Build** (100% success)
- **Lint** (high success rate)
- **Security Checks** (high success rate)

## Key Success Patterns

### 1. UV Package Manager Integration

All successful Python workflows use UV for dependency management:

```yaml
- name: Install uv
  uses: astral-sh/setup-uv@v4
  with:
    enable-cache: true

- name: Set up Python environment
  run: |
    uv python install 3.12
    uv venv
    uv sync --all-extras
```

**Why it works:**
- UV is faster than pip
- Built-in caching reduces CI time
- Lockfile ensures reproducible builds

### 2. Tool Installation in /tmp

Always install external tools in /tmp to avoid overwriting project files:

```yaml
- name: Install gitleaks
  run: |
    cd /tmp
    wget https://github.com/gitleaks/gitleaks/releases/download/v8.21.2/gitleaks_8.21.2_linux_x64.tar.gz
    tar -xzf gitleaks_8.21.2_linux_x64.tar.gz
    sudo mv gitleaks /usr/local/bin/
    cd -
```

### 3. Explicit Tool Versions

Pin tool versions for reproducibility:

```yaml
- name: Set up Python
  uses: actions/setup-python@v5
  with:
    python-version: '3.12'

- name: Set up Go
  uses: actions/setup-go@v5
  with:
    go-version: 'stable'
```

### 4. Pre-commit Integration

Use pre-commit with UV for consistent local/CI behavior:

```yaml
- name: Install pre-commit
  run: |
    uv tool install pre-commit --with pre-commit-uv

- name: Run pre-commit
  run: |
    export PATH="$HOME/.local/bin:$PATH"
    pre-commit run --all-files --show-diff-on-failure
```

### 5. Formatting Configuration

Keep formatting commands consistent:

```yaml
# Python formatting
uv run ruff format --line-length=320 --check src/ tests/

# Python linting
uv run ruff check --ignore E203,E402,E501,E266,W505,F841,F842,F401,W293,I001,UP015,C901,W291 --isolated --fix

# YAML formatting (GitHub workflows only)
yamlfmt -lint .github/workflows/
```

### 6. Security Scanning

Always include security checks:

```yaml
# Secret scanning
gitleaks detect --source . --verbose

# Dependency scanning
uv run pip-audit

# YAML validation
actionlint .github/workflows/*.yml
```

## Common Pitfalls to Avoid

### 1. ❌ Using Super-Linter
Super-Linter has configuration issues and is overly complex. Use individual linters instead.

### 2. ❌ Installing in Project Root
Never extract archives in the project root - always use `/tmp`.

### 3. ❌ Missing Tool PATH
Always ensure tools are in PATH:

```yaml
export PATH="$PATH:$(go env GOPATH)/bin"
export PATH="$HOME/.local/bin:$PATH"
```

### 4. ❌ Inconsistent Python Versions
Always use the same Python version (3.12) across all workflows.

## Workflow Structure Template

```yaml
name: Workflow Name

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]

permissions:
  contents: read

jobs:
  job-name:
    runs-on: ubuntu-latest

    steps:
    - name: Checkout code
      uses: actions/checkout@v4

    - name: Install uv
      uses: astral-sh/setup-uv@v4
      with:
        enable-cache: true

    - name: Set up Python
      uses: actions/setup-python@v5
      with:
        python-version: '3.12'

    - name: Install dependencies
      run: |
        uv venv
        uv sync --all-extras

    - name: Run task
      run: |
        uv run <command>
```

## Testing Best Practices

### 1. Environment Detection

Tests should detect CI environment and adjust:

```python
def is_ci_environment() -> bool:
    return os.environ.get("CI") == "true" or os.environ.get("GITHUB_ACTIONS") == "true"

# CI: fewer retries, shorter timeouts
# Local: more retries, longer timeouts
```

### 2. Test Collection

Always verify tests can be collected before running:

```yaml
- name: Collect tests
  run: uv run pytest --collect-only
```

### 3. Test Timeout

Use pytest-timeout to prevent hanging tests:

```yaml
- name: Run tests
  run: uv run pytest --timeout=300
```

## Dependency Management

### 1. Use Lockfiles

Always commit `uv.lock` for reproducible builds.

### 2. Separate Dev Dependencies

Use `[dependency-groups]` in pyproject.toml:

```toml
[dependency-groups]
dev = [
    "pytest>=8.4.0",
    "ruff>=0.8.7",
    "mypy>=1.11.2",
    # ...
]
```

### 3. Type Stubs

Include type stubs for better type checking:

```toml
"types-pyyaml>=6.0.12",
"types-requests>=2.32.4",
```

## Performance Optimization

### 1. Parallel Jobs

Run independent checks in parallel:

```yaml
jobs:
  lint:
    # ...
  format:
    # ...
  security:
    # ...
```

### 2. Caching

Enable UV caching:

```yaml
uses: astral-sh/setup-uv@v4
with:
  enable-cache: true
```

### 3. Conditional Runs

Skip workflows when not needed:

```yaml
on:
  push:
    paths:
      - '**.py'
      - 'pyproject.toml'
      - '.github/workflows/test.yml'
```

## Monitoring and Debugging

### 1. Verbose Output

Use verbose flags for debugging:

```bash
gitleaks detect --verbose
pytest -xvs
```

### 2. Error Context

Show full error context:

```bash
mypy --show-error-context --pretty
pre-commit run --show-diff-on-failure
```

### 3. Artifact Upload

Save logs for debugging:

```yaml
- name: Upload logs
  if: failure()
  uses: actions/upload-artifact@v4
  with:
    name: logs
    path: |
      *.log
      .pytest_cache/
```

## Summary

The key to successful GitHub workflows is:
1. **Consistency** - Use the same tools and versions everywhere
2. **Isolation** - Install tools in /tmp, use virtual environments
3. **Caching** - Enable UV caching for faster builds
4. **Simplicity** - Use individual tools instead of complex meta-tools
5. **Security** - Always scan for secrets and vulnerabilities
6. **Debugging** - Include verbose output and save artifacts on failure

Following these patterns has resulted in highly reliable CI/CD pipelines with fast execution times and clear error messages when issues occur.
