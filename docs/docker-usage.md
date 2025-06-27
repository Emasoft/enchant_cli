#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Docker Usage Guide for EnChANT Book Manager

This guide explains how to use Docker to run tests and the application in isolated containers using `uv` for Python dependency management.

## Prerequisites

- Docker installed and running
- Docker Compose (usually included with Docker Desktop)
- `OPENROUTER_API_KEY` environment variable set (for remote API tests)

## Quick Start

### Running All Tests

```bash
# Using the convenience script
./scripts/docker-test.sh

# Or using docker-compose directly
docker-compose up test
```

### Running Specific Tests

```bash
# Run a specific test file
./scripts/docker-test.sh tests/test_translation_service.py

# Run a specific test function
./scripts/docker-test.sh tests/test_translation_service.py::TestChineseAITranslator::test_init_local -v

# Run with custom pytest options
./scripts/docker-test.sh -k "test_cost" -v --tb=short
```

### Interactive Shell

```bash
# Start an interactive shell in the container
./scripts/docker-test.sh -i

# Or using docker-compose
docker-compose run --rm shell
```

## Docker Services

The `docker-compose.yml` file defines three services:

1. **test** - Runs the full test suite with coverage
2. **test-specific** - For running specific tests with custom commands
3. **shell** - Interactive shell for debugging and exploration

## Building Images

```bash
# Build with cache (default)
docker-compose build

# Force rebuild without cache
./scripts/docker-test.sh -b

# Build production image
docker build -f Dockerfile.prod -t enchant-book-manager:latest .
```

## Production Usage

Use the production Dockerfile for running the application:

```bash
# Build production image
docker build -f Dockerfile.prod -t enchant-book-manager:latest .

# Run the CLI
docker run --rm enchant-book-manager:latest --help

# Process a novel with API key
docker run --rm \
  -e OPENROUTER_API_KEY="$OPENROUTER_API_KEY" \
  -v $(pwd)/novels:/app/novels \
  -v $(pwd)/translations:/app/translations \
  enchant-book-manager:latest \
  --input-dir /app/novels \
  --output-dir /app/translations
```

## Environment Variables

The following environment variables are supported:

- `OPENROUTER_API_KEY` - API key for translation services
- `SKIP_LOCAL_MODE_TESTS` - Set to `true` to skip local-only tests
- `PYTHONDONTWRITEBYTECODE` - Prevent Python from writing .pyc files
- `PYTHONUNBUFFERED` - Ensure stdout/stderr are unbuffered

## Test Output

Test results and coverage reports are saved to:

- `./htmlcov/` - HTML coverage report
- `./test-results/` - JUnit XML and coverage XML reports
- `./.coverage` - Raw coverage data

## Troubleshooting

### Docker not running
```
Error: Docker is not running
```
**Solution**: Start Docker Desktop or the Docker daemon

### Permission denied
```
permission denied while trying to connect to the Docker daemon
```
**Solution**: Add your user to the docker group or use sudo

### Out of space
```
no space left on device
```
**Solution**: Clean up Docker resources:
```bash
docker system prune -a
```

### Slow builds
**Solution**: The Dockerfile uses BuildKit cache mounts to speed up dependency installation. Ensure BuildKit is enabled:
```bash
export DOCKER_BUILDKIT=1
```

## Advanced Usage

### Custom pytest configuration

Create a custom pytest configuration:

```bash
docker-compose run --rm test uv run pytest \
  --cov-config=.coveragerc \
  --cov-report=term-missing:skip-covered \
  --tb=short \
  -vv
```

### Debugging tests

Use the shell service with debugger:

```bash
docker-compose run --rm shell
# Inside container:
uv run python -m pytest tests/test_translation_service.py -vv --pdb
```

### Running with different Python versions

Modify the base image in Dockerfile:

```dockerfile
# Change from:
FROM python:3.12-slim

# To:
FROM python:3.11-slim
```

## CI/CD Integration

The Docker setup can be used in CI/CD pipelines:

```yaml
# Example GitHub Actions workflow
- name: Run tests in Docker
  run: |
    docker-compose up --build --abort-on-container-exit test

- name: Upload coverage
  uses: actions/upload-artifact@v3
  with:
    name: coverage-report
    path: htmlcov/
```

## Best Practices

1. **Always use .dockerignore** - Prevents copying unnecessary files
2. **Layer caching** - Dependencies are installed before copying source code
3. **Multi-stage builds** - Production image is optimized for size
4. **Non-root user** - Production container runs as non-root for security
5. **Cache mounts** - BuildKit cache mounts speed up builds

## References

- [uv Docker Integration Guide](https://docs.astral.sh/uv/guides/integration/docker/)
- [uv Docker Example Repository](https://github.com/astral-sh/uv-docker-example)
- [Docker Best Practices](https://docs.docker.com/develop/dev-best-practices/)
