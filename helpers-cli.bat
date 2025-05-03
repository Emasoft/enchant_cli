@echo off
REM Helper CLI wrapper script for Windows

SETLOCAL

SET SCRIPT_DIR=%~dp0

REM Check if Python is available
WHERE python >nul 2>nul
IF ERRORLEVEL 1 (
    echo Python not found. Please install Python 3.9 or newer.
    exit /b 1
)

REM Add the script directory to PYTHONPATH
SET PYTHONPATH=%SCRIPT_DIR%;%PYTHONPATH%

REM Check if we're in an activated virtual environment
IF DEFINED VIRTUAL_ENV (
    REM Already in a virtual environment, just run the command
    python -m helpers.cli %*
    exit /b %ERRORLEVEL%
)

REM Check if the project has a virtual environment
IF EXIST "%SCRIPT_DIR%.venv\Scripts\activate.bat" (
    REM Activate the virtual environment and run the command
    call "%SCRIPT_DIR%.venv\Scripts\activate.bat"
    python -m helpers.cli %*
    ENDLOCAL
    exit /b %ERRORLEVEL%
)

REM If running directly with system Python, we should use uv if possible
WHERE uv >nul 2>nul
IF NOT ERRORLEVEL 1 (
    REM Use uv to install dependencies
    uv pip install -e "%SCRIPT_DIR%"
    uv sync
    python -m helpers.cli %*
) ELSE (
    REM Fall back to using pip (less preferred)
    python -m pip install -e "%SCRIPT_DIR%"
    python -m helpers.cli %*
)
ENDLOCAL
exit /b %ERRORLEVEL%