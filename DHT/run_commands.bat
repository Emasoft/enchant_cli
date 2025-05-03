@echo off
REM Windows batch file wrapper for run_commands
REM Automatically uses WSL/Git Bash if available or guides the user

SETLOCAL EnableDelayedExpansion

echo === Enchant CLI Platform Wrapper for Windows ===

REM Check for WSL
WHERE wsl >nul 2>nul
IF NOT ERRORLEVEL 1 (
    echo Found Windows Subsystem for Linux
    echo Running script through WSL...
    wsl ./run_commands.sh
    GOTO :END
)

REM Check for Git Bash
IF EXIST "%PROGRAMFILES%\Git\bin\bash.exe" (
    echo Found Git Bash
    echo Running script through Git Bash...
    "%PROGRAMFILES%\Git\bin\bash.exe" -c "./run_commands.sh"
    GOTO :END
) ELSE IF EXIST "%PROGRAMFILES(x86)%\Git\bin\bash.exe" (
    echo Found Git Bash
    echo Running script through Git Bash...
    "%PROGRAMFILES(x86)%\Git\bin\bash.exe" -c "./run_commands.sh"
    GOTO :END
)

REM No compatible environment found
echo No compatible Unix environment found.
echo.
echo To run this script on Windows, you need one of:
echo 1. Windows Subsystem for Linux (WSL) - Recommended
echo    Install from Microsoft Store or run: wsl --install
echo.
echo 2. Git Bash
echo    Install from https://gitforwindows.org/
echo.
echo After installing one of these tools, try running this script again.
echo.
echo For full Windows native support without WSL/Git Bash, please see the README.md
echo for manual setup instructions.

:END
ENDLOCAL