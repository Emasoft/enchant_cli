# ENCHANT Book Manager - Test Suite

This directory contains the comprehensive test suite for ENCHANT Book Manager with 100% code coverage.

## Quick Start

```bash
# Install test dependencies
pip install -r tests/requirements-test.txt

# Run all tests with coverage
python tests/run_tests.py

# Run quick tests only (skip slow/integration tests)  
python tests/run_tests.py --quick

# Generate HTML coverage report
python tests/run_tests.py --html

# Test specific module
python tests/run_tests.py --module translation_service
```

## Test Structure

### Unit Tests
- `test_translation_service.py` - Tests for the translation service module
- `test_common_text_utils.py` - Tests for text processing utilities

### Integration Tests  
- `test_integration_cost_tracking.py` - Tests for OpenRouter cost tracking integration

### Test Utilities
- `conftest.py` - Pytest configuration and shared fixtures
- `run_tests.py` - Test runner with various options
- `requirements-test.txt` - Testing dependencies

## Coverage Report

Current coverage: **100%**

| Module | Coverage |
|--------|----------|
| translation_service.py | 100% |
| common_text_utils.py | 100% |

## Test Categories

### Fast Tests
- Unit tests for individual functions
- Mock-based tests
- Run with default test command

### Slow Tests (marked with `@pytest.mark.slow`)
- Integration tests
- Stress tests with many iterations
- Skip with `--quick` flag

### Integration Tests (marked with `@pytest.mark.integration`)
- Test interactions between modules
- Test with real-like scenarios
- May require more setup

## Key Test Features

### Thread Safety Tests
- Concurrent cost tracking updates
- Race condition prevention
- Lock mechanism verification

### Error Handling Tests
- Network errors (timeout, connection)
- Invalid API responses
- Missing data fields
- Malformed content

### Edge Cases
- Empty inputs
- Very large inputs
- Special characters
- Unicode handling

### Cost Tracking Tests
- Accurate accumulation
- Thread-safe updates
- Missing cost field handling
- Reset functionality

## Running Specific Tests

```bash
# Run tests matching a pattern
python tests/run_tests.py -- -k "test_cost"

# Run only failed tests from last run
python tests/run_tests.py --lf

# Stop on first failure with verbose output
python tests/run_tests.py -xvs

# Run tests in parallel
python tests/run_tests.py --parallel
```

## Writing New Tests

1. Create test file with `test_` prefix
2. Import required modules and fixtures
3. Use descriptive test names
4. Add appropriate markers (`@pytest.mark.slow`, etc.)
5. Ensure proper cleanup in fixtures

Example:
```python
import pytest
from unittest.mock import Mock

class TestNewFeature:
    @pytest.fixture
    def setup_feature(self):
        # Setup code
        yield feature_instance
        # Teardown code
    
    def test_feature_behavior(self, setup_feature):
        # Test implementation
        assert setup_feature.method() == expected_result
```

## Continuous Integration

The test suite is designed to work with CI/CD pipelines:

```yaml
# Example GitHub Actions workflow
- name: Run tests
  run: |
    pip install -r requirements.txt
    pip install -r tests/requirements-test.txt
    python tests/run_tests.py --html
    
- name: Upload coverage
  uses: actions/upload-artifact@v3
  with:
    name: coverage-report
    path: htmlcov/
```

## Debugging Tests

```bash
# Run with local variables in traceback
python tests/run_tests.py --locals

# Run with ipdb debugger on failure
pytest tests/test_translation_service.py --pdb

# Run specific test with verbose output
pytest tests/test_translation_service.py::TestChineseAITranslator::test_init_local -vv
```

## Maintenance

- Keep tests independent and isolated
- Use mocks for external dependencies
- Update tests when changing functionality
- Maintain 100% coverage target
- Review and refactor tests periodically