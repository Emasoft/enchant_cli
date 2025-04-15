@echo off
REM Windows batch file wrapper for run_tests
REM Automatically uses WSL/Git Bash if available or guides the user

SETLOCAL EnableDelayedExpansion

echo === Enchant CLI Test Runner for Windows ===

REM Check for WSL
WHERE wsl >nul 2>nul
IF NOT ERRORLEVEL 1 (
    echo Found Windows Subsystem for Linux
    echo Running tests through WSL...
    wsl ./run_tests.sh
    GOTO :END
)

REM Check for Git Bash
IF EXIST "%PROGRAMFILES%\Git\bin\bash.exe" (
    echo Found Git Bash
    echo Running tests through Git Bash...
    "%PROGRAMFILES%\Git\bin\bash.exe" -c "./run_tests.sh"
    GOTO :END
) ELSE IF EXIST "%PROGRAMFILES(x86)%\Git\bin\bash.exe" (
    echo Found Git Bash
    echo Running tests through Git Bash...
    "%PROGRAMFILES(x86)%\Git\bin\bash.exe" -c "./run_tests.sh"
    GOTO :END
)

REM Native Windows fallback
echo No compatible Unix environment found. Attempting native Windows Python test...
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

echo Running tests...
pytest tests/ -v --cov=enchant_cli --cov-report=xml --cov-report=term-missing:skip-covered --cov-fail-under=80 --strict-markers --durations=10 --html=report.html --self-contained-html

:END
ENDLOCAL