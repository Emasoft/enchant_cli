# Contributing to EnChANT Book Manager

We love your input! We want to make contributing to EnChANT Book Manager as easy and transparent as possible.

## Development Process

We use GitHub to host code, to track issues and feature requests, as well as accept pull requests.

1. Fork the repo and create your branch from `main`
2. If you've added code that should be tested, add tests
3. If you've changed APIs, update the documentation
4. Ensure the test suite passes
5. Make sure your code lints
6. Issue that pull request!

## Setting Up Development Environment

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/enchant_cli.git
cd enchant_cli

# Install uv (if not already installed)
pip install uv

# Create virtual environment and install dependencies
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv sync --all-extras

# Install pre-commit hooks
uv run pre-commit install
```

## Running Tests

```bash
# Run all tests
uv run pytest tests -v

# Run with coverage
uv run pytest tests --cov=src/enchant_book_manager

# Run specific test file
uv run pytest tests/test_specific.py -v
```

## Code Style

- We use `ruff` for Python linting and formatting
- Run `uv run ruff check src tests` to check for issues
- Run `uv run ruff format src tests` to format code
- Type hints are required for all new code
- All functions must have docstrings in Google style

## Pre-commit Checks

Before committing, the following checks will run automatically:
- Trailing whitespace removal
- File ending fixes
- YAML validation
- Python linting (ruff)
- Type checking (mypy)
- Dependency checking (deptry)
- Security scanning (pip-audit, gitleaks)

## Pull Request Process

1. Update the README.md with details of changes to the interface
2. Update the CHANGELOG.md with your changes
3. The PR will be merged once you have the sign-off of at least one maintainer

## Reporting Bugs

Report bugs using GitHub's [issue tracker](https://github.com/Emasoft/enchant_cli/issues)

**Great Bug Reports** tend to have:
- A quick summary and/or background
- Steps to reproduce
- What you expected would happen
- What actually happens
- Notes (possibly including why you think this might be happening)

## License

By contributing, you agree that your contributions will be licensed under the MIT License.