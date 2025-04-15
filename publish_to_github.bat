@echo off
REM Windows batch file wrapper for publish_to_github
REM Automatically uses WSL/Git Bash if available or guides the user

SETLOCAL EnableDelayedExpansion

echo === Enchant CLI GitHub Publisher for Windows ===

REM Check for WSL
WHERE wsl >nul 2>nul
IF NOT ERRORLEVEL 1 (
    echo Found Windows Subsystem for Linux
    echo Running publish script through WSL...
    wsl ./publish_to_github.sh
    GOTO :END
)

REM Check for Git Bash
IF EXIST "%PROGRAMFILES%\Git\bin\bash.exe" (
    echo Found Git Bash
    echo Running publish script through Git Bash...
    "%PROGRAMFILES%\Git\bin\bash.exe" -c "./publish_to_github.sh"
    GOTO :END
) ELSE IF EXIST "%PROGRAMFILES(x86)%\Git\bin\bash.exe" (
    echo Found Git Bash
    echo Running publish script through Git Bash...
    "%PROGRAMFILES(x86)%\Git\bin\bash.exe" -c "./publish_to_github.sh"
    GOTO :END
)

REM Native Windows fallback - simplified, recommend WSL/Git Bash
echo No compatible Unix environment found.
echo.
echo For full GitHub publishing functionality, please install either:
echo 1. Windows Subsystem for Linux (WSL) - Recommended
echo    Install from Microsoft Store or run: wsl --install
echo.
echo 2. Git Bash
echo    Install from https://gitforwindows.org/
echo.
echo This script requires Unix shell capabilities for complete functionality.
echo See README.md for manual publishing instructions if you cannot install
echo WSL or Git Bash.

:END
ENDLOCAL