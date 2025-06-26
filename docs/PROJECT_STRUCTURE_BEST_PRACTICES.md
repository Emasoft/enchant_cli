# Project Structure Best Practices

This document outlines the best practices for organizing the EnChANT Book Manager project based on analysis of the current structure and Python packaging standards.

## Directory Structure

```
enchant-book-manager/
├── src/                      # Source code
│   └── enchant_book_manager/ # Main package
├── tests/                    # Test files
├── docs/                     # Documentation
│   ├── development/          # Development docs
│   └── workflows/            # Workflow guides
├── logs/                     # Log files (gitignored)
├── .github/                  # GitHub configuration
│   └── workflows/            # GitHub Actions
├── pyproject.toml            # Project configuration
├── uv.lock                   # Dependency lock file
├── README.md                 # Project readme
├── LICENSE                   # License file
├── CHANGELOG.md              # Version history
└── CONTRIBUTING.md           # Contribution guide
```

## Best Practices Implemented

### 1. Source Layout

✅ **src/ Layout**: Using `src/` layout prevents accidental imports from the project root:
```
src/
└── enchant_book_manager/
    ├── __init__.py
    ├── cli_*.py         # CLI modules
    ├── config_*.py      # Configuration modules
    ├── epub_*.py        # EPUB handling modules
    ├── translation_*.py # Translation modules
    └── ...
```

### 2. Module Organization

✅ **Functional Grouping**: Modules are grouped by functionality with clear prefixes:
- `cli_*` - Command-line interface modules
- `config_*` - Configuration handling
- `epub_*` - EPUB generation and validation
- `translation_*` - Translation services
- `workflow_*` - Workflow orchestration
- `common_*` - Shared utilities

### 3. File Size Management

✅ **Small Modules**: Each module should be under 10KB for maintainability
- Large modules have been split into smaller, focused files
- Each module has a single responsibility

### 4. Import Management

✅ **Relative Imports**: Use relative imports within the package:
```python
from .config_manager import ConfigManager
from .translation_service import ChineseAITranslator
```

✅ **No Circular Imports**: Careful module design prevents circular dependencies

### 5. Configuration Files

✅ **Standard Config Files**:
- `pyproject.toml` - Project metadata and tool configuration
- `uv.lock` - Locked dependencies
- `.gitignore` - Comprehensive ignore patterns
- `mypy.ini` - Type checking configuration

### 6. Documentation Organization

✅ **Structured Documentation**:
```
docs/
├── development/          # Development-related docs
│   ├── DEVELOPMENT_PLAN.md
│   ├── CODE_QUALITY_REVIEW.md
│   └── refactoring_log.md
├── workflows/            # Workflow documentation
│   └── GITHUB_WORKFLOWS_BEST_PRACTICES.md
└── testing-github-actions-locally.md
```

### 7. Test Organization

✅ **Comprehensive Test Coverage**:
```
tests/
├── test_*.py             # Test modules
├── conftest.py           # Pytest configuration
├── pytest.ini            # Pytest settings
├── test_utils.py         # Test utilities
└── sample_novel/         # Test data
```

### 8. Clean Repository

✅ **Files to Exclude**:
- ❌ `.DS_Store` files (macOS metadata)
- ❌ `*.bak`, `*.backup` files
- ❌ Log files in source directories
- ❌ Build artifacts (`dist/`, `build/`)
- ❌ Cache directories outside of `.venv`
- ❌ Temporary test output

### 9. Entry Points

✅ **Clear Entry Points**:
```toml
[project.scripts]
enchant-cli = "enchant_book_manager.enchant_cli:main"
enchant = "enchant_book_manager.enchant_cli:main"  # Shorter alias
```

### 10. Type Safety

✅ **Type Annotations**: All functions have type hints:
```python
def process_file(
    file_path: Path,
    encoding: str = "utf-8",
    max_chars: int = DEFAULT_MAX_CHARS
) -> tuple[bool, list[str]]:
    """Process file with proper type annotations."""
```

## Maintenance Guidelines

### 1. Regular Cleanup

Run these commands periodically:
```bash
# Remove .DS_Store files
find . -name ".DS_Store" -type f -delete

# Remove backup files
find . -name "*.bak" -o -name "*.backup" -type f -delete

# Clean build artifacts
rm -rf dist/ build/ *.egg-info

# Clean logs (keep logs/ directory)
rm -f *.log src/**/*.log
```

### 2. Before Commits

1. **Run formatters**:
   ```bash
   uv run ruff format src/ tests/
   ```

2. **Run linters**:
   ```bash
   uv run ruff check --fix src/ tests/
   uv run mypy src/
   ```

3. **Run tests**:
   ```bash
   uv run pytest
   ```

### 3. Module Size Check

Monitor module sizes:
```bash
find src -name "*.py" -size +10k -exec ls -lh {} \;
```

Consider refactoring modules larger than 10KB.

### 4. Import Organization

Keep imports organized:
```python
# Standard library imports
import os
import sys
from pathlib import Path

# Third-party imports
import requests
from rich.console import Console

# Local imports
from .config_manager import ConfigManager
from .models import Book, Chapter
```

## Anti-Patterns to Avoid

### 1. ❌ Files in Wrong Places
- Don't put log files in source directories
- Don't commit build artifacts
- Don't mix test data with source code

### 2. ❌ Large Monolithic Modules
- Split files larger than 500 lines
- Each module should have a single responsibility

### 3. ❌ Inconsistent Naming
- Use consistent prefixes for related modules
- Follow Python naming conventions (lowercase_with_underscores)

### 4. ❌ Missing __init__.py
- Every package directory needs `__init__.py`
- Can be empty but must exist

### 5. ❌ Hardcoded Paths
- Use `Path` from pathlib
- Make paths relative to project root
- Use configuration for changeable paths

## Summary

A well-organized project structure:
1. **Improves maintainability** - Easy to find and modify code
2. **Prevents errors** - No accidental imports or circular dependencies
3. **Speeds development** - Clear patterns for adding new features
4. **Helps collaboration** - New developers understand the layout quickly
5. **Enables automation** - Tools can process files predictably

Following these practices ensures the project remains clean, organized, and scalable as it grows.

