# Testing GitHub Actions Locally with act

This guide explains how to test GitHub Actions workflows locally using [act](https://github.com/nektos/act).

## Prerequisites

1. Install act:
   ```bash
   brew install act
   ```

2. Install Docker (act requires Docker to run containers)

3. Ensure you have the project dependencies installed:
   ```bash
   uv sync --all-extras
   ```

## Configuration

The project includes an `.actrc` file that configures act to work with uv:

- Uses appropriate container images that match GitHub Actions
- Sets up environment variables for uv caching
- Enables container reuse for faster subsequent runs

## Running Workflows

### List Available Jobs
```bash
act -l
```

### Run Specific Jobs

1. **Lint job**:
   ```bash
   act -j lint
   ```

2. **Dependency check**:
   ```bash
   act -j dependency-check
   ```

3. **Pre-commit checks**:
   ```bash
   act -j pre-commit
   ```

4. **Tests**:
   ```bash
   act -j test
   ```

### Run Entire Workflows

```bash
# Run CI workflow on push event
act push

# Run pre-commit workflow
act workflow_run -W .github/workflows/pre-commit.yml

# Run dependency check workflow
act workflow_run -W .github/workflows/dependency-check.yml
```

### Using the Test Script

The project includes a `test-github-actions.sh` script for convenience:

```bash
./test-github-actions.sh
```

This script will test the main workflows and provide colored output.

## Troubleshooting

### Common Issues

1. **Docker not running**: Ensure Docker Desktop is running before using act

2. **Container download**: First run may take time as act downloads container images

3. **Secrets**: For workflows requiring secrets (e.g., PYPI_API_TOKEN), create a `.secrets` file:
   ```
   PYPI_API_TOKEN=your_token_here
   ```

4. **Memory issues**: If you encounter memory issues, try running individual jobs instead of entire workflows

### Debug Mode

Run act with verbose output:
```bash
act -v push
```

Or with even more detail:
```bash
act -vv push
```

## Notes

- act simulates GitHub Actions but isn't 100% identical
- Some GitHub-specific features (like caching actions) may behave differently
- Network-dependent tests may fail in containerized environments
- The `.actrc` file is configured for macOS/Linux; Windows users may need adjustments
