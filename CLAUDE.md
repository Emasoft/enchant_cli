# Environment Configuration for enchant_cli

## Virtual Environment
- Project uses a Python virtual environment located at `.venv/`
- Created using uv: `.venv/pyvenv.cfg` shows version info 3.13.2
- Environment should NOT use system site-packages
- Project prompt is set to "enchant_cli"

## uv Tool Configuration
- Current project is using uv for dependency management
- uv version: 0.6.14 (as of April 2025)
- **IMPORTANT**: The `uv` command is being called directly, not through the virtual environment
- In the scripts, `uv` command is expected to be available in the PATH
- Python commands use the virtual environment's Python (`.venv/bin/python`)
- This mixed approach is intentional in the project setup

## Key Environment Variables
- Required API keys are configured in the user's environment:
  - OPENROUTER_API_KEY: For translation API functionality
  - PYPI_API_TOKEN: For PyPI package publishing (usually not needed directly with GitHub Actions)
  - CODECOV_API_TOKEN: For test coverage reporting

## Dependency Management
- Dependencies are defined in `pyproject.toml` 
- Lock files are maintained using uv:
  - `uv.lock`: Contains resolved dependencies for reproducible builds
- When changing dependencies:
  1. Update `pyproject.toml`
  2. Run `uv lock` to update the lock file
  3. Run `uv sync` to install dependencies according to the lock file

## Building and Publishing
- Package version is managed in `src/enchant_cli/__init__.py`
- Automatic version bumping with bump-my-version via pre-commit is temporarily disabled
  - Need to manually run `bump-my-version minor` before commit
  - Or manually update version in `src/enchant_cli/__init__.py`
- Build process:
  1. `uv build` creates both wheel and sdist packages
  2. GitHub Actions automates PyPI publishing on release

## Important Commands
- `./run_tests.sh`: Run tests using pytest
- `./release.sh`: Local validation script that checks code quality and builds package
- `./publish_to_github.sh`: Prepares and pushes to GitHub
- `uv sync`: Synchronize the environment with dependencies in lock file

## Script Sequence
1. `uv lock` - Update the lock file
2. `uv sync` - Apply dependency changes to the environment
3. Run pre-commit checks 
4. Commit changes (triggering automatic version bump)
5. Run validation with `./release.sh`
6. Push to GitHub with `./publish_to_github.sh`

## Notes
- Always work within the activated virtual environment
- Use `uv pip install -e .` for editable installs during development
- The `test_sample.txt` file must be included in both sdist and wheel packages