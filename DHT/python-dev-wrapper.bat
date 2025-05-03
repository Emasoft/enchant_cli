@echo off
:: Python Development Script Wrapper for Windows
::
:: This script wraps Python development-related scripts to provide memory management.
:: It only applies to development helper scripts, not the main application.
:: It starts the Process Guardian when needed and adds the process to the monitoring list.
::
:: Usage:
::   python-dev-wrapper.bat <script_path> [args...]
::
:: Examples:
::   python-dev-wrapper.bat helpers\errors\log_analyzer.py analyze logs\test.log

setlocal enabledelayedexpansion

:: Get script directory
set "SCRIPT_DIR=%~dp0"
:: Remove trailing backslash
set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"

:: Check if script path was provided
if "%~1"=="" (
    echo Usage: %0 ^<script_path^> [arguments...]
    exit /b 1
)

set "SCRIPT_PATH=%~1"
shift

:: If not an absolute path, make it relative to script dir
if not "%SCRIPT_PATH:~0,1%"=="/" (
    if not "%SCRIPT_PATH:~1,1%"==":" (
        set "SCRIPT_PATH=%SCRIPT_DIR%\%SCRIPT_PATH%"
    )
)

:: Replace forward slashes with backslashes in path
set "SCRIPT_PATH=%SCRIPT_PATH:/=\%"

:: Get the script name for display
for %%F in ("%SCRIPT_PATH%") do set "SCRIPT_NAME=%%~nxF"

:: Check if the script file exists
if not exist "%SCRIPT_PATH%" (
    echo Error: Script not found: %SCRIPT_PATH%
    echo Make sure to provide a valid script path.
    exit /b 1
)

:: Function to check for psutil
python -c "import psutil" 2>nul
if %ERRORLEVEL% neq 0 (
    echo Installing psutil...
    python -m pip install psutil
)

:: Function to determine if this is a dev script
call :is_dev_script "%SCRIPT_PATH%"
if %ERRORLEVEL% equ 0 (
    echo Running %SCRIPT_NAME% with Process Guardian (Python development script)...
    call :run_with_guardian %*
) else (
    echo Running %SCRIPT_NAME% directly (not a development script)...
    call :run_direct %*
)

exit /b %ERRORLEVEL%

:run_with_guardian
:: Determine the command to run based on file extension
set "FILE_EXT=%SCRIPT_PATH:~-3%"
if /i "%FILE_EXT%"==".py" (
    :: Start the python process
    start /b python "%SCRIPT_PATH%" %* > "%TEMP%\py_wrapper_output.txt" 2>&1
) else if /i "%FILE_EXT%"==".sh" (
    :: Check if bash is available
    where bash >nul 2>&1
    if %ERRORLEVEL% equ 0 (
        :: Start the bash process
        start /b bash "%SCRIPT_PATH%" %* > "%TEMP%\py_wrapper_output.txt" 2>&1
    ) else (
        echo Error: bash not found. Cannot execute .sh script.
        exit /b 1
    )
) else (
    echo Unsupported script type. Only .py and .sh files are supported.
    exit /b 1
)

:: Get the PID of the started process (this is a simplified approach for Windows)
:: In a real implementation, this would use a more robust method to track the PID
for /f "tokens=2" %%P in ('tasklist /FI "IMAGENAME eq python.exe" /NH ^| findstr python') do (
    set "SCRIPT_PID=%%P"
    goto :got_pid
)
:got_pid

:: Register the process with the guardian as a Python script
python "%SCRIPT_DIR%\process-guardian-watchdog.py" register %SCRIPT_PID% python

:: Wait for the process to complete by monitoring its existence
:wait_loop
tasklist /FI "PID eq %SCRIPT_PID%" /NH | find "%SCRIPT_PID%" >nul 2>&1
if %ERRORLEVEL% equ 0 (
    timeout /t 1 /nobreak >nul
    goto :wait_loop
)

:: Unregister the process from the guardian
python "%SCRIPT_DIR%\process-guardian-watchdog.py" unregister %SCRIPT_PID% python

:: Display output from the subprocess
type "%TEMP%\py_wrapper_output.txt"
del "%TEMP%\py_wrapper_output.txt" >nul 2>&1

:: Check guardian status if interactive
if not "%~1"=="" (
    python "%SCRIPT_DIR%\process-guardian-watchdog.py" status
)

exit /b 0

:run_direct
:: Run the script directly based on extension
set "FILE_EXT=%SCRIPT_PATH:~-3%"
if /i "%FILE_EXT%"==".py" (
    python "%SCRIPT_PATH%" %*
) else if /i "%FILE_EXT%"==".sh" (
    :: Check if bash is available
    where bash >nul 2>&1
    if %ERRORLEVEL% equ 0 (
        bash "%SCRIPT_PATH%" %*
    ) else (
        echo Error: bash not found. Cannot execute .sh script.
        exit /b 1
    )
) else (
    echo Unsupported script type. Only .py and .sh files are supported.
    exit /b 1
)

exit /b %ERRORLEVEL%

:is_dev_script
set "CHECK_PATH=%~1"
:: Helper functions that should be monitored
echo %CHECK_PATH% | findstr /i "helper process guard get_errorlogs publish build analyze" >nul
if %ERRORLEVEL% equ 0 (
    exit /b 0
)

:: Skip wrapping if it's the main application code
echo %CHECK_PATH% | findstr /i "\src\ enchant_cli.py" >nul
if %ERRORLEVEL% equ 0 (
    exit /b 1
)

:: By default, consider it a dev script
exit /b 0