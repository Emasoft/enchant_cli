@echo off
REM reinitialize_env.bat - Windows batch script to recreate a clean environment
REM without any external references

SETLOCAL EnableDelayedExpansion

echo === Enchant CLI Environment Reinitializer for Windows ===

REM Get the script directory for relative paths
SET "SCRIPT_DIR=%~dp0"
SET "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"
SET "VENV_DIR=%SCRIPT_DIR%\.venv"

echo Script directory: %SCRIPT_DIR%
echo Virtual environment directory: %VENV_DIR%

echo Cleaning up existing virtual environment...
IF EXIST "%VENV_DIR%" (
    RD /S /Q "%VENV_DIR%"
    echo Removed existing environment
) ELSE (
    echo No existing environment found at %VENV_DIR%
)

REM Find Python executable
WHERE python >nul 2>nul
IF %ERRORLEVEL% EQU 0 (
    SET "PYTHON_CMD=python"
) ELSE (
    WHERE py >nul 2>nul
    IF %ERRORLEVEL% EQU 0 (
        SET "PYTHON_CMD=py"
    ) ELSE (
        echo Error: Python not found. Please install Python 3.9 or newer.
        exit /b 1
    )
)

echo Using system Python to create environment: %PYTHON_CMD%

REM Check if uv is installed
%PYTHON_CMD% -m pip show uv >nul 2>nul
IF %ERRORLEVEL% NEQ 0 (
    echo Installing uv package...
    %PYTHON_CMD% -m pip install uv
    IF %ERRORLEVEL% NEQ 0 (
        echo Failed to install uv.
        exit /b 1
    )
)

echo Creating fresh virtual environment with uv...
%PYTHON_CMD% -m uv venv "%VENV_DIR%"
IF %ERRORLEVEL% NEQ 0 (
    echo Failed to create virtual environment.
    exit /b 1
)

echo Installing dependencies...
"%VENV_DIR%\Scripts\python.exe" -m pip install uv
"%VENV_DIR%\Scripts\uv.exe" pip install -e "%SCRIPT_DIR%"
"%VENV_DIR%\Scripts\python.exe" -m pip install pre-commit
"%VENV_DIR%\Scripts\python.exe" -m pip install bump-my-version

echo Setting up pre-commit hooks...
"%VENV_DIR%\Scripts\pre-commit.exe" install

echo Verifying environment...
echo Python version: 
"%VENV_DIR%\Scripts\python.exe" --version
echo uv version: 
"%VENV_DIR%\Scripts\uv.exe" --version
echo bump-my-version version: 
"%VENV_DIR%\Scripts\bump-my-version.exe" --version

echo Environment successfully reinitialized!
echo.
echo Next steps:
echo 1. Run %VENV_DIR%\Scripts\activate.bat to activate the environment
echo 2. Use run_commands.bat to execute commands in the isolated environment
echo.
echo The environment is now completely isolated and uses only relative paths.

ENDLOCAL