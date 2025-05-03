@echo off
REM Windows batch file for installing uv and related tools

SETLOCAL EnableDelayedExpansion

echo === UV Toolchain Installer and Configuration ===
echo.

REM Check if WSL is available
WHERE wsl >nul 2>&1
IF NOT ERRORLEVEL 1 (
    echo Using Windows Subsystem for Linux to install uv...
    wsl ./install_uv.sh
    exit /b %ERRORLEVEL%
)

REM Check if Git Bash is available
IF EXIST "%PROGRAMFILES%\Git\bin\bash.exe" (
    echo Using Git Bash to install uv...
    "%PROGRAMFILES%\Git\bin\bash.exe" -c "./install_uv.sh"
    exit /b %ERRORLEVEL%
) ELSE IF EXIST "%PROGRAMFILES(x86)%\Git\bin\bash.exe" (
    echo Using Git Bash to install uv...
    "%PROGRAMFILES(x86)%\Git\bin\bash.exe" -c "./install_uv.sh"
    exit /b %ERRORLEVEL%
)

REM Use native Windows implementation
echo No compatible Unix environment found. Using native Windows implementation...
echo.

REM Check if Python is installed
WHERE python >nul 2>&1
IF ERRORLEVEL 1 (
    echo Python not found. Please install Python 3.9 or newer.
    exit /b 1
)

REM Create virtual environment if it doesn't exist
IF NOT EXIST ".venv\Scripts\activate.bat" (
    echo Creating virtual environment...
    python -m venv .venv
)

REM Activate the virtual environment
call .venv\Scripts\activate.bat

REM Install uv
echo Installing uv...
pip install uv

REM Install tools using uv
echo Installing pre-commit-uv...
uv pip install pre-commit-uv

echo Installing tox-uv...
uv pip install tox tox-uv

echo Installing bump-my-version via uv tool...
uv tool install bump-my-version

REM Install project dependencies
echo Setting up development environment...
IF EXIST "uv.lock" (
    echo Syncing dependencies from lock file...
    uv sync
)

echo Installing package in development mode...
uv pip install -e .

REM Create or update configuration files
echo Setting up configuration files...

REM Create tox.ini if it doesn't exist
IF NOT EXIST "tox.ini" (
    echo Creating tox.ini with uv support...
    (
        echo [tox]
        echo envlist = py39, py310, py311, py312, py313
        echo isolated_build = True
        echo requires =
        echo     tox-uv^>=0.8.1
        echo     tox^>=4.11.4
        echo.
        echo [testenv]
        echo deps =
        echo     pytest^>=7.3.1
        echo     pytest-cov^>=4.1.0
        echo     pytest-timeout^>=2.1.0
        echo commands =
        echo     pytest {posargs:tests} --cov=enchant_cli --cov-report=term --cov-report=xml --timeout=900
        echo.
        echo [testenv:lint]
        echo deps =
        echo     ruff^>=0.3.0
        echo     black^>=23.3.0
        echo commands =
        echo     ruff check .
        echo     ruff format --check .
        echo.
        echo [testenv:typecheck]
        echo deps =
        echo     mypy^>=1.0.0
        echo commands =
        echo     mypy src/enchant_cli
    ) > tox.ini
    echo Created tox.ini with uv support
) ELSE (
    echo tox.ini already exists, please check it for tox-uv configuration
)

REM Setup hooks directory if it doesn't exist
IF NOT EXIST "hooks" (
    mkdir hooks
)

REM Create or update bump_version.bat
echo Updating bump_version.bat to use uv...
(
    echo @echo off
    echo REM Windows batch file for bumping version
    echo SETLOCAL EnableDelayedExpansion
    echo.
    echo SET VERSION_PART=%%1
    echo IF "%%VERSION_PART%%"=="" SET VERSION_PART=minor
    echo.
    echo REM Validate version part
    echo IF NOT "%%VERSION_PART%%"=="major" IF NOT "%%VERSION_PART%%"=="minor" IF NOT "%%VERSION_PART%%"=="patch" (
    echo     echo ERROR: Invalid version part. Use one of: major, minor, patch
    echo     exit /b 1
    echo )
    echo.
    echo REM Try to use uv tool run
    echo WHERE uv ^>nul 2^>^&1
    echo IF NOT ERRORLEVEL 1 (
    echo     echo Running bump-my-version via uv tool...
    echo     uv tool run bump-my-version bump %%VERSION_PART%% --commit --tag --allow-dirty
    echo     exit /b %%ERRORLEVEL%%
    echo )
    echo.
    echo REM Try the virtual environment
    echo IF EXIST ".venv\Scripts\uv.exe" (
    echo     echo Running bump-my-version via .venv\Scripts\uv tool...
    echo     .venv\Scripts\uv tool run bump-my-version bump %%VERSION_PART%% --commit --tag --allow-dirty
    echo     exit /b %%ERRORLEVEL%%
    echo )
    echo.
    echo REM Fall back to direct bump-my-version if available
    echo IF EXIST ".venv\Scripts\bump-my-version.exe" (
    echo     echo Running bump-my-version directly...
    echo     .venv\Scripts\bump-my-version bump %%VERSION_PART%% --commit --tag --allow-dirty
    echo     exit /b %%ERRORLEVEL%%
    echo )
    echo.
    echo echo ERROR: Neither uv nor bump-my-version found in path or virtual environment
    echo echo Please run install_uv.bat to set up the environment properly
    echo exit /b 1
) > bump_version.bat

echo.
echo === Installation and Configuration Complete ===
echo.
echo Next steps:
echo 1. Run 'pre-commit install' to install the pre-commit hooks
echo 2. Use 'uv sync' to keep your environment in sync with dependencies
echo.

ENDLOCAL