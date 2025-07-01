# Publishing Gitleaks-Safe to PyPI

This guide explains how to publish the gitleaks-safe package to PyPI so it can be installed globally.

## Prerequisites

1. Create a PyPI account at https://pypi.org/account/register/
2. Create an API token at https://pypi.org/manage/account/token/
3. Install build tools:
   ```bash
   uv pip install build twine
   ```

## Building the Package

```bash
cd gitleaks-safe-tool
uv build
```

This creates:
- `dist/gitleaks_safe-2.0.0.tar.gz` (source distribution)
- `dist/gitleaks_safe-2.0.0-py3-none-any.whl` (wheel)

## Testing Locally

Before publishing, test the package locally:

```bash
# Install as uv tool from local directory
uv tool install .

# Or install with pip
pip install dist/gitleaks_safe-2.0.0-py3-none-any.whl
```

## Publishing to Test PyPI (Recommended First)

1. Upload to Test PyPI:
   ```bash
   python -m twine upload --repository testpypi dist/*
   ```

2. Test installation from Test PyPI:
   ```bash
   pip install --index-url https://test.pypi.org/simple/ gitleaks-safe
   ```

## Publishing to PyPI

1. Upload to PyPI:
   ```bash
   python -m twine upload dist/*
   ```

2. Enter your PyPI username and API token when prompted.

## Installing Globally After Publishing

Once published to PyPI, users can install globally using:

### With uv (Recommended)
```bash
# Install as global tool
uv tool install gitleaks-safe

# Run directly with uvx
uvx --from gitleaks-safe install-safe-git-hooks
```

### With pip
```bash
pip install gitleaks-safe
```

### With pipx
```bash
pipx install gitleaks-safe
```

## Version Management

To release a new version:

1. Update version in `pyproject.toml`
2. Update version in `src/gitleaks_safe/__init__.py`
3. Build and publish:
   ```bash
   uv build
   python -m twine upload dist/*
   ```

## GitHub Release

Consider creating a GitHub release with:

1. Tag the version:
   ```bash
   git tag v2.0.0
   git push origin v2.0.0
   ```

2. Create release on GitHub with:
   - Release notes
   - Link to PyPI package
   - Installation instructions

## Automated Publishing

For automated publishing, add this GitHub Action:

```yaml
name: Publish to PyPI

on:
  release:
    types: [published]

jobs:
  publish:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4

    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'

    - name: Install uv
      run: pip install uv

    - name: Build package
      run: uv build

    - name: Publish to PyPI
      uses: pypa/gh-action-pypi-publish@release/v1
      with:
        password: ${{ secrets.PYPI_API_TOKEN }}
```
