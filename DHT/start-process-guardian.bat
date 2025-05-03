@echo off
REM Start the Process Guardian Watchdog Service

SET SCRIPT_DIR=%~dp0

REM Create directory if it doesn't exist
if not exist "%USERPROFILE%\.process_guardian" mkdir "%USERPROFILE%\.process_guardian"

REM Check if the watchdog is already running
if exist "%USERPROFILE%\.process_guardian\watchdog.pid" (
    set /p PID=<"%USERPROFILE%\.process_guardian\watchdog.pid"
    wmic process where ProcessId=%PID% get ProcessId /value >nul 2>nul
    if %ERRORLEVEL% EQU 0 (
        echo Process Guardian Watchdog is already running with PID %PID%
        exit /b 0
    ) else (
        echo Removing stale PID file
        del "%USERPROFILE%\.process_guardian\watchdog.pid"
    )
)

REM Start the watchdog in daemon mode
echo Starting Process Guardian Watchdog...
start /b pythonw "%SCRIPT_DIR%\process-guardian-watchdog.py" --daemon

REM Check if it started successfully
timeout /t 1 >nul
if exist "%USERPROFILE%\.process_guardian\watchdog.pid" (
    set /p PID=<"%USERPROFILE%\.process_guardian\watchdog.pid"
    wmic process where ProcessId=%PID% get ProcessId /value >nul 2>nul
    if %ERRORLEVEL% EQU 0 (
        echo Process Guardian Watchdog started with PID %PID%
        exit /b 0
    )
)

echo Failed to start Process Guardian Watchdog
exit /b 1