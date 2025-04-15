@echo off
REM Windows batch file wrapper for major_release
REM Automatically uses WSL/Git Bash if available or guides the user

SETLOCAL EnableDelayedExpansion

echo === Enchant CLI Major Release for Windows ===
echo This script creates a major version increment for breaking changes.

REM Check for WSL
WHERE wsl >nul 2>nul
IF NOT ERRORLEVEL 1 (
    echo Found Windows Subsystem for Linux
    echo Running major release through WSL...
    wsl ./major_release.sh
    GOTO :END
)

REM Check for Git Bash
IF EXIST "%PROGRAMFILES%\Git\bin\bash.exe" (
    echo Found Git Bash
    echo Running major release through Git Bash...
    "%PROGRAMFILES%\Git\bin\bash.exe" -c "./major_release.sh"
    GOTO :END
) ELSE IF EXIST "%PROGRAMFILES(x86)%\Git\bin\bash.exe" (
    echo Found Git Bash
    echo Running major release through Git Bash...
    "%PROGRAMFILES(x86)%\Git\bin\bash.exe" -c "./major_release.sh"
    GOTO :END
)

REM Native Windows fallback
echo No compatible Unix environment found. Attempting native Windows major release...
echo.

REM Check if Python is installed
WHERE python >nul 2>nul
IF ERRORLEVEL 1 (
    echo Python not found. Please install Python 3.9 or newer.
    GOTO :END
)

REM Check for virtual environment
IF EXIST ".venv\Scripts\activate.bat" (
    echo Found virtual environment, activating...
    call .venv\Scripts\activate.bat
) ELSE (
    echo Virtual environment not found.
    echo Creating a new virtual environment...
    python -m venv .venv
    call .venv\Scripts\activate.bat
    
    echo Installing dependencies...
    python -m pip install -e .[dev]
)

echo Installing bump-my-version if needed...
python -m pip install bump-my-version

echo Running major version bump...
bump-my-version major --allow-dirty

REM Get the new version from __init__.py
FOR /F "tokens=2 delims==" %%G IN ('type src\enchant_cli\__init__.py ^| findstr "__version__"') DO (
    SET VERSION=%%G
    SET VERSION=!VERSION:"=!
    SET VERSION=!VERSION: =!
)

echo Bumped to version !VERSION!

echo Running validation...
python -m pytest tests/ -v --cov=enchant_cli --cov-report=xml --cov-report=term-missing:skip-covered --cov-fail-under=80 --strict-markers --durations=10 --html=report.html --self-contained-html

echo.
echo Major version bump complete!
echo.
echo Next steps:
echo 1. Review changes: git log -p
echo 2. Commit the changes: git commit -am "BREAKING CHANGE: Major version bump to !VERSION!"
echo 3. Push to GitHub: git push origin main --tags
echo 4. Create a release on GitHub
echo.
echo IMPORTANT: Update CHANGELOG.md with all breaking changes!

:END
ENDLOCAL