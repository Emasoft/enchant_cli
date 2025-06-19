# GitHub Actions Workflows

This directory contains CI/CD workflows for the ENCHANT Book Manager project. All workflows use [uv](https://github.com/astral-sh/uv) for fast, reliable Python dependency management.

## Workflows

### ci.yml
Main CI/CD pipeline that runs on every push and pull request:
- **Lint**: Runs ruff and mypy for code quality
- **Dependency Check**: Runs deptry and pip-audit for dependency analysis
- **Test**: Runs pytest with coverage reporting
- **Build**: Builds wheel and source distributions
- **Publish**: Publishes to PyPI using `uv publish`

### dependency-check.yml
Dedicated workflow for dependency checking:
- Runs on pushes to main/develop and pull requests
- Executes deptry to check for missing, unused, or misplaced dependencies
- Generates and uploads JSON report for analysis

### pre-commit.yml
Runs all pre-commit hooks on pull requests and pushes to main:
- Standard hooks (trailing whitespace, file fixing, format validation)
- uv-lock to ensure lockfile is up-to-date
- Ruff for linting and formatting
- Mypy for type checking
- Deptry for dependency checking
- Pip-audit for security vulnerability scanning
- Yamllint for YAML file validation
- Actionlint for GitHub Actions workflow validation

### release.yml
Dedicated release workflow that runs when a release is published:
- Runs all quality checks (lint, type check, dependency check, security audit, YAML lint, actionlint)
- Executes full test suite with coverage
- Builds and verifies distributions
- Publishes to PyPI using trusted publishing

### super-linter.yml
Comprehensive linting using GitHub Super-Linter for all file types:
- **Python**: ruff and mypy with project-specific configurations
- **YAML**: yamllint for all YAML files
- **Markdown**: markdown-lint for documentation
- **Shell**: shellcheck for shell scripts
- **GitHub Actions**: actionlint for workflow files
- **JSON**: JSON syntax validation
- **XML**: XML validation (useful for EPUB internals)
- Runs on pushes and pull requests
- Only validates changed files in PRs for efficiency

## Required Secrets

- `PYPI_API_TOKEN`: Required for publishing to PyPI (used in ci.yml for legacy publishing)
- Note: release.yml uses PyPI trusted publishing with OIDC, no token required

## Local Setup

All workflows use `uv` for dependency management. To run these checks locally:

```bash
# Install uv (if not already installed)
pip install uv

# Install dependencies
uv sync --all-extras

# Install pre-commit hooks
uv run pre-commit install

# Run all pre-commit checks
uv run pre-commit run --all-files

# Run individual checks
uv run deptry .
uv run mypy src --strict
uv run ruff check src tests
uv run pip-audit
uv run yamllint .
actionlint

# Run tests with coverage
uv run pytest tests --cov=src/enchant_book_manager

# Test GitHub Actions locally with act
./test-github-actions.sh

# Test Super-Linter locally (requires Docker)
docker run -e RUN_LOCAL=true -e USE_FIND_ALGORITHM=true \
  -v $PWD:/tmp/lint github/super-linter:v5
```

## Linter Configuration

Custom linter configurations are stored in:
- `.github/linters/` - Super-Linter specific configurations
  - `.ruff.toml` - Python linting rules
  - `.mypy.ini` - Type checking configuration
  - `.markdown-lint.yml` - Markdown style guide
  - `.shellcheckrc` - Shell script linting rules
- `.yamllint.yml` - YAML linting rules (repository root)
- `pyproject.toml` - Main Python project configuration

## Key Features

1. **Fast Dependency Installation**: Uses `uv` for 10-100x faster dependency resolution
2. **Comprehensive Checks**: Linting, formatting, type checking, dependency analysis, and security scanning
3. **Caching**: All workflows use `uv` caching for faster CI runs
4. **Frozen Runs**: Pre-commit hooks use `uv run --frozen` to ensure reproducible environments
5. **Modern Publishing**: Supports both token-based and trusted publishing to PyPI
