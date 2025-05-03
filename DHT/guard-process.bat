@echo off
REM Process Guardian Wrapper Script
REM 
REM This script provides a convenient way to run commands with the process guardian.
REM It prevents processes from using too much memory or running indefinitely.
REM
REM Usage: 
REM   guard-process.bat [options] -- command [args]
REM
REM Options:
REM   --timeout SECONDS     Maximum runtime in seconds (default: 900s/15min)
REM   --max-memory MB       Maximum memory usage in MB (default: 1024MB/1GB)
REM   --max-concurrent N    Maximum number of concurrent processes (default: 3)
REM   --max-total-memory MB Maximum total memory usage in MB (default: 3072MB/3GB)
REM   --monitor PROCESS     Specific process name to monitor
REM   --cmd-pattern PATTERN Command pattern to match (regex)
REM   --no-kill-duplicates  Don't kill duplicate process instances
REM   --log-file PATH       Path to log file
REM
REM Examples:
REM   guard-process.bat -- npm install
REM   guard-process.bat --timeout 300 --max-memory 1024 -- pytest tests/
REM   guard-process.bat --monitor bump-my-version -- hooks/bump_version.bat

SETLOCAL ENABLEDELAYEDEXPANSION

REM Get script directory
SET SCRIPT_DIR=%~dp0

REM Check if Python is available
WHERE python >nul 2>nul
IF %ERRORLEVEL% NEQ 0 (
    echo Python is not installed or not in PATH
    exit /b 1
)

REM Check if psutil is installed
python -c "import psutil" >nul 2>nul
IF %ERRORLEVEL% NEQ 0 (
    echo Installing required dependency: psutil
    python -m pip install psutil
)

REM Default values
SET TIMEOUT=900
SET MAX_MEMORY=1024
SET MAX_CONCURRENT=3
SET MAX_TOTAL_MEMORY=3072
SET MONITOR=
SET CMD_PATTERN=
SET KILL_DUPLICATES=true
SET LOG_FILE=%USERPROFILE%\.process_guardian\process_guardian.log

REM Process arguments
SET ARGS_PROCESSED=0
SET CMD_ARGS=
SET FOUND_SEPARATOR=0

:parse_args
IF "%~1"=="" GOTO :continue_execution
IF "%~1"=="--" (
    SET FOUND_SEPARATOR=1
    SHIFT
    GOTO :collect_cmd
)

IF %FOUND_SEPARATOR% EQU 1 (
    GOTO :collect_cmd
) ELSE (
    IF "%~1"=="--timeout" (
        SET TIMEOUT=%~2
        SET ARGS_PROCESSED=1
        SHIFT
        SHIFT
    ) ELSE IF "%~1"=="--max-memory" (
        SET MAX_MEMORY=%~2
        SET ARGS_PROCESSED=1
        SHIFT
        SHIFT
    ) ELSE IF "%~1"=="--max-concurrent" (
        SET MAX_CONCURRENT=%~2
        SET ARGS_PROCESSED=1
        SHIFT
        SHIFT
    ) ELSE IF "%~1"=="--max-total-memory" (
        SET MAX_TOTAL_MEMORY=%~2
        SET ARGS_PROCESSED=1
        SHIFT
        SHIFT
    ) ELSE IF "%~1"=="--monitor" (
        SET MONITOR=%~2
        SET ARGS_PROCESSED=1
        SHIFT
        SHIFT
    ) ELSE IF "%~1"=="--cmd-pattern" (
        SET CMD_PATTERN=%~2
        SET ARGS_PROCESSED=1
        SHIFT
        SHIFT
    ) ELSE IF "%~1"=="--no-kill-duplicates" (
        SET KILL_DUPLICATES=false
        SET ARGS_PROCESSED=1
        SHIFT
    ) ELSE IF "%~1"=="--log-file" (
        SET LOG_FILE=%~2
        SET ARGS_PROCESSED=1
        SHIFT
        SHIFT
    ) ELSE (
        echo Unknown option: %~1
        exit /b 1
    )
)

IF %ARGS_PROCESSED% EQU 1 (
    SET ARGS_PROCESSED=0
    GOTO :parse_args
)

:collect_cmd
SET CMD_ARGS=%CMD_ARGS% %1
SHIFT
IF NOT "%~1"=="" GOTO :collect_cmd

:continue_execution

REM Check if command is provided
IF "%CMD_ARGS%"=="" (
    echo Error: No command provided
    echo Usage: %0 [options] -- command [args]
    exit /b 1
)

REM Build process guardian command
SET GUARDIAN_CMD=python -m helpers.shell.process_guardian

IF NOT "%MONITOR%"=="" (
    SET GUARDIAN_CMD=%GUARDIAN_CMD% --monitor "%MONITOR%"
)

IF NOT "%CMD_PATTERN%"=="" (
    SET GUARDIAN_CMD=%GUARDIAN_CMD% --cmd-pattern "%CMD_PATTERN%"
)

SET GUARDIAN_CMD=%GUARDIAN_CMD% --timeout %TIMEOUT% --max-memory %MAX_MEMORY% --max-concurrent %MAX_CONCURRENT% --max-total-memory %MAX_TOTAL_MEMORY%

IF "%KILL_DUPLICATES%"=="false" (
    SET GUARDIAN_CMD=%GUARDIAN_CMD% --no-kill-duplicates
)

SET GUARDIAN_CMD=%GUARDIAN_CMD% --log-file "%LOG_FILE%"

REM Add the command to execute
SET GUARDIAN_CMD=%GUARDIAN_CMD%%CMD_ARGS%

REM Print summary
echo Process Guardian
echo    Command: %CMD_ARGS%
echo    Timeout: %TIMEOUT%s
echo    Max Memory: %MAX_MEMORY%MB per process
echo    Max Concurrent Processes: %MAX_CONCURRENT%
echo    Max Total Memory: %MAX_TOTAL_MEMORY%MB
IF NOT "%MONITOR%"=="" (
    echo    Monitoring: %MONITOR%
)
IF NOT "%CMD_PATTERN%"=="" (
    echo    Command Pattern: %CMD_PATTERN%
)
echo    Log: %LOG_FILE%
echo.

REM Run the process guardian
%GUARDIAN_CMD%
SET EXIT_CODE=%ERRORLEVEL%

REM Forward the exit code
exit /b %EXIT_CODE%