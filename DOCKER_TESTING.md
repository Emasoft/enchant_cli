# Docker Testing Environment

This project includes a robust Docker testing environment with multiple profiles optimized for different scenarios.

## Test Profiles

### 1. Local Profile (`test-local`)
- **Purpose**: Development and debugging
- **Characteristics**:
  - Longer timeouts (60s)
  - More retries (10)
  - Verbose output
  - All tests enabled
  - Environment: `TEST_PROFILE=local`

### 2. Remote Profile (`test-remote`)
- **Purpose**: Mimics CI/GitHub Actions environment
- **Characteristics**:
  - Short timeouts (5s)
  - Fewer retries (2)
  - Quiet output
  - Skips local-only tests
  - Environment: `TEST_PROFILE=remote`, `CI=true`, `GITHUB_ACTIONS=true`

### 3. Full Profile (`test-full`)
- **Purpose**: Complete test coverage with reports
- **Characteristics**:
  - Extended timeouts (300s)
  - Full coverage reporting
  - All optional dependencies
  - Generates HTML and XML reports
  - Environment: `TEST_PROFILE=full`

## Quick Start

### Run Tests with Specific Profile

```bash
# Run local profile tests
docker-compose -f docker-compose.test.yml run --rm test-local

# Run remote profile tests
docker-compose -f docker-compose.test.yml run --rm test-remote

# Run full test suite with coverage
docker-compose -f docker-compose.test.yml run --rm test-full

# Interactive shell for debugging
docker-compose -f docker-compose.test.yml run --rm test-shell
```

### Use the Profile Script

```bash
# Run all profiles
./scripts/docker-test-profiles.sh

# Run specific profile
./scripts/docker-test-profiles.sh local
./scripts/docker-test-profiles.sh remote
./scripts/docker-test-profiles.sh full
./scripts/docker-test-profiles.sh build
```

## Test Configuration

Tests automatically adapt based on the profile using `test_config.py`:

```python
from test_config import TEST_CONFIG, should_skip_test

# Skip tests based on profile
@pytest.mark.skipif(should_skip_test("remote"), reason="Skipping remote tests")
def test_remote_api():
    pass

# Use profile-specific settings
timeout = get_timeout()  # Returns 60 for local, 5 for remote
retries = get_retry_count()  # Returns 10 for local, 2 for remote
```

## GitHub Actions Integration

The remote profile is automatically used in GitHub Actions:

```yaml
# .github/workflows/docker-profile-test.yml
- name: Run remote profile tests
  run: |
    docker run --rm \
      -e TEST_PROFILE=remote \
      enchant-remote-test:latest
```

## Building and Testing Projects

The test suite includes functionality to test project setup and builds:

```python
# tests/test_project_build.py
- Clone repositories
- Set up virtual environments with uv
- Build projects with uv build
- Verify package installation
```

## Test Results

- **JUnit XML**: `./test-results/junit.xml`
- **Coverage XML**: `./test-results/coverage.xml`
- **Coverage HTML**: `./htmlcov/index.html`

## Environment Variables

- `TEST_PROFILE`: Set the active profile (local/remote/full)
- `SKIP_REMOTE_TESTS`: Skip tests requiring remote APIs
- `SKIP_LOCAL_MODE_TESTS`: Skip local-only tests
- `OPENROUTER_API_KEY`: API key for remote translation tests

## Tips

1. Use local profile for development and debugging
2. Use remote profile to verify CI compatibility
3. Use full profile for comprehensive testing before releases
4. Tests automatically skip based on profile settings
5. Each profile has optimized timeout and retry settings
