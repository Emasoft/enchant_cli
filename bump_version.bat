@echo off
REM Windows batch file for manually bumping version
REM Allows specifying minor/major/patch

SETLOCAL EnableDelayedExpansion

echo === Enchant CLI Version Bumper for Windows ===

REM Check for command-line argument
IF "%~1"=="" (
    echo Error: Version part not specified.
    echo Usage: bump_version.bat [major^|minor^|patch]
    exit /b 1
)

SET VERSION_PART=%~1

REM Check for WSL
WHERE wsl >nul 2>nul
IF NOT ERRORLEVEL 1 (
    echo Found Windows Subsystem for Linux
    echo Running bump-my-version through WSL...
    wsl ./bump_version.sh %VERSION_PART%
    GOTO :END
)

REM Check for Git Bash
IF EXIST "%PROGRAMFILES%\Git\bin\bash.exe" (
    echo Found Git Bash
    echo Running bump-my-version through Git Bash...
    "%PROGRAMFILES%\Git\bin\bash.exe" -c "./bump_version.sh %VERSION_PART%"
    GOTO :END
) ELSE IF EXIST "%PROGRAMFILES(x86)%\Git\bin\bash.exe" (
    echo Found Git Bash
    echo Running bump-my-version through Git Bash...
    "%PROGRAMFILES(x86)%\Git\bin\bash.exe" -c "./bump_version.sh %VERSION_PART%"
    GOTO :END
)

REM Native Windows fallback
echo No compatible Unix environment found. Attempting native Windows bump...
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

echo Running bump-my-version...
bump-my-version bump %VERSION_PART% --allow-dirty

REM Get the new version from __init__.py
FOR /F "tokens=2 delims==" %%G IN ('type src\enchant_cli\__init__.py ^| findstr "__version__"') DO (
    SET VERSION=%%G
    SET VERSION=!VERSION:"=!
    SET VERSION=!VERSION: =!
)

echo.
echo Version bumped to: !VERSION!
echo.

:END
ENDLOCAL