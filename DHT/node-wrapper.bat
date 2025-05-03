@echo off
:: Node.js Process Wrapper for Windows
::
:: This script wraps Node.js commands to provide automatic memory management.
:: It starts the Process Guardian when needed and stops it when all Node.js
:: processes have completed.
::
:: Usage:
::   node-wrapper.bat node [args...]
::   node-wrapper.bat npm [args...]
::   node-wrapper.bat npx [args...]

setlocal enabledelayedexpansion

:: Get script directory
set "SCRIPT_DIR=%~dp0"
:: Remove trailing backslash
set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"

:: Check if command was provided
if "%~1"=="" (
    echo Usage: %0 node^|npm^|npx [arguments...]
    exit /b 1
)

set "COMMAND=%~1"
shift

:: Check if the command is a Node.js related command
if not "%COMMAND%"=="node" (
    if not "%COMMAND%"=="npm" (
        if not "%COMMAND%"=="npx" (
            echo Error: This wrapper only supports node, npm, and npx commands.
            exit /b 1
        )
    )
)

:: Function to check for psutil
python -c "import psutil" 2>nul
if %ERRORLEVEL% neq 0 (
    echo Installing psutil...
    python -m pip install psutil
)

:: Run the command with the guardian
echo Running %COMMAND% with Node.js Process Guardian...

:: Start the node process
start /b %COMMAND% %* > "%TEMP%\node_wrapper_output.txt" 2>&1
for /f "tokens=2" %%P in ('tasklist /FI "IMAGENAME eq %COMMAND%.exe" /NH ^| findstr %COMMAND%') do (
    set "NODE_PID=%%P"
    goto :got_pid
)
:got_pid

:: Register the process with the guardian
python "%SCRIPT_DIR%\process-guardian-watchdog.py" register %NODE_PID%

:: Wait for the process to complete
:wait_loop
tasklist /FI "PID eq %NODE_PID%" /NH | find "%NODE_PID%" >nul 2>&1
if %ERRORLEVEL% equ 0 (
    timeout /t 1 /nobreak >nul
    goto :wait_loop
)

:: Unregister the process from the guardian
python "%SCRIPT_DIR%\process-guardian-watchdog.py" unregister %NODE_PID%

:: Display output from the subprocess
type "%TEMP%\node_wrapper_output.txt"
del "%TEMP%\node_wrapper_output.txt" >nul 2>&1

:: Check guardian status
python "%SCRIPT_DIR%\process-guardian-watchdog.py" status

exit /b 0
EOL < /dev/null