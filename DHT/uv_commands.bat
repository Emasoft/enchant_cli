@echo off
REM Windows batch file for common UV commands

SETLOCAL EnableDelayedExpansion

echo === UV Commands Helper ===
echo.

IF "%~1"=="" (
    GOTO :help
)

REM Check if uv is installed
WHERE uv >nul 2>&1
IF ERRORLEVEL 1 (
    echo ERROR: uv not found. Please install it first with install_uv.bat
    exit /b 1
)

REM Process command
IF "%~1"=="venv" (
    CALL :cmd_venv
) ELSE IF "%~1"=="sync" (
    CALL :cmd_sync
) ELSE IF "%~1"=="lock" (
    CALL :cmd_lock
) ELSE IF "%~1"=="install-dev" (
    CALL :cmd_install_dev
) ELSE IF "%~1"=="bump" (
    CALL :cmd_bump %2
) ELSE IF "%~1"=="bump-major" (
    CALL :cmd_bump major
) ELSE IF "%~1"=="bump-minor" (
    CALL :cmd_bump minor
) ELSE IF "%~1"=="bump-patch" (
    CALL :cmd_bump patch
) ELSE IF "%~1"=="test" (
    CALL :cmd_test %2
) ELSE IF "%~1"=="lint" (
    CALL :cmd_lint
) ELSE IF "%~1"=="pre-commit" (
    CALL :cmd_pre_commit
) ELSE IF "%~1"=="install-tools" (
    CALL :cmd_install_tools
) ELSE IF "%~1"=="help" (
    GOTO :help
) ELSE IF "%~1"=="--help" (
    GOTO :help
) ELSE IF "%~1"=="-h" (
    GOTO :help
) ELSE (
    echo ERROR: Unknown command: %1. Run 'uv_commands.bat help' for usage.
    exit /b 1
)

exit /b 0

:help
echo Usage: uv_commands.bat [command]
echo.
echo Available commands:
echo   venv          - Create a virtual environment with uv
echo   sync          - Sync dependencies from lock file
echo   lock          - Update lock file from pyproject.toml
echo   install-dev   - Install package in development mode
echo   bump          - Bump version (minor by default)
echo   bump-major    - Bump major version
echo   bump-minor    - Bump minor version
echo   bump-patch    - Bump patch version
echo   test          - Run tests with tox-uv
echo   lint          - Run linters with tox-uv
echo   pre-commit    - Run pre-commit checks on all files
echo   install-tools - Install common development tools
echo   help          - Show this help message
echo.
echo Examples:
echo   uv_commands.bat venv      # Create a virtual environment
echo   uv_commands.bat sync      # Sync dependencies
echo   uv_commands.bat bump      # Bump minor version
echo.
exit /b 0

:cmd_venv
echo Creating virtual environment with uv...
IF EXIST ".venv" (
    echo Removing existing virtual environment...
    rmdir /s /q .venv
)
uv venv .venv
echo Created virtual environment at .venv
echo Remember to activate it with: .venv\Scripts\activate.bat
exit /b 0

:cmd_sync
echo Syncing dependencies from lock file...
IF NOT EXIST "uv.lock" (
    echo ERROR: uv.lock not found. Run 'uv_commands.bat lock' first.
    exit /b 1
)
uv sync
echo Dependencies synced from lock file
exit /b 0

:cmd_lock
echo Updating lock file from pyproject.toml...
uv lock
echo Lock file updated
exit /b 0

:cmd_install_dev
echo Installing package in development mode...
uv pip install -e .
echo Package installed in development mode
exit /b 0

:cmd_bump
SET part=%~1
IF "%part%"=="" SET part=minor
echo Bumping %part% version...
uv tool run bump-my-version bump %part% --commit --tag --allow-dirty
echo Version bumped
exit /b 0

:cmd_test
SET py_version=%~1
IF "%py_version%"=="" (
    REM Get current Python version (e.g., py310)
    FOR /F "tokens=*" %%i IN ('python -c "import sys; print(f\"py{sys.version_info.major}{sys.version_info.minor}\")"') DO (
        SET py_version=%%i
    )
)
echo Running tests with tox-uv for %py_version%...
tox -e %py_version%
echo Tests completed
exit /b 0

:cmd_lint
echo Running linters with tox-uv...
tox -e lint
echo Linting completed
exit /b 0

:cmd_pre_commit
echo Running pre-commit checks on all files...
pre-commit run --all-files
echo Pre-commit checks completed
exit /b 0

:cmd_install_tools
echo Installing common development tools...
uv tool install bump-my-version
uv pip install pre-commit pre-commit-uv tox tox-uv ruff black
echo Development tools installed
exit /b 0

ENDLOCAL