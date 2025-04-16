@echo off
REM get_errorlogs.bat - CLAUDE HELPER SCRIPT for GitHub Actions workflow log analysis
REM Version 1.1.0 - Enhanced to be fully portable and auto-detect repository details

setlocal enabledelayedexpansion

REM Parse command-line options
set DO_TRUNCATE=false
for %%a in (%*) do (
    if "%%a"=="--truncate" (
        set DO_TRUNCATE=true
    )
)

REM Display version information
IF "%1"=="version" goto :show_version
IF "%1"=="--version" goto :show_version
IF "%1"=="-v" goto :show_version

REM Display enhanced help message
IF "%1"=="help" goto :show_help
IF "%1"=="--help" goto :show_help
IF "%1"=="-h" goto :show_help

REM Check if we can use WSL
WHERE wsl >nul 2>&1
IF %ERRORLEVEL% EQU 0 (
    echo Using WSL to run the script...
    set "args=%*"
    if "%DO_TRUNCATE%"=="true" (
        wsl ./get_errorlogs.sh --truncate !args:--truncate=!
    ) else (
        wsl ./get_errorlogs.sh %*
    )
    exit /b %ERRORLEVEL%
)

REM Check if we can use Git Bash
WHERE bash >nul 2>&1
IF %ERRORLEVEL% EQU 0 (
    echo Using Git Bash to run the script...
    set "args=%*"
    if "%DO_TRUNCATE%"=="true" (
        bash ./get_errorlogs.sh --truncate !args:--truncate=!
    ) else (
        bash ./get_errorlogs.sh %*
    )
    exit /b %ERRORLEVEL%
)

:show_version
echo [93m🔶 CLAUDE HELPER SCRIPT: GitHub Actions Workflow Logs Tool v1.1.0[0m
echo.
echo This script is part of the CLAUDE HELPER SCRIPTS collection.
echo For more information, see the CLAUDE.md documentation.
exit /b 0

:show_help
echo [93m🔶 CLAUDE HELPER SCRIPT: GitHub Actions Workflow Logs Tool v1.1.0[0m
echo Usage: %0 [global_options] ^<command^> [command_options]
echo.
echo [94m📣 Global Options:[0m
echo   --truncate                Truncate output for readability (by default, full output is shown)
echo.
echo [94m📣 Commands:[0m
echo   list                      List recent workflow runs from GitHub
echo   logs [RUN_ID]             Get logs for a specific workflow run
echo   tests                     Get logs for the latest test workflow run
echo   build^|release             Get logs for the latest build/release workflow run
echo   lint                      Get logs for the latest linting workflow run
echo   docs                      Get logs for the latest documentation workflow run
echo   saved                     List all saved log files
echo   latest                    Get the 3 most recent logs after last commit
echo   workflow^|workflows        List detected workflows in the repository
echo   search PATTERN [CASE_SENSITIVE] [MAX_RESULTS]
echo                             Search all log files for a pattern
echo   stats                     Show statistics about saved log files
echo   cleanup [DAYS] [--dry-run] Clean up logs older than DAYS (default: 30)
echo   classify [LOG_FILE]       Classify errors in a specific log file
echo   detect                    Detect repository info and workflows without fetching logs
echo   version^|--version^|-v      Show script version and configuration
echo   help^|--help^|-h            Show this help message
echo.
echo [94m📣 Features:[0m
echo   ✓ Auto-detection of repository info from git, project files, etc.
echo   ✓ Dynamic workflow detection and categorization by type (test, release, etc.)
echo   ✓ Intelligent error classification with context and root cause analysis
echo   ✓ Full output by default, with optional truncation via --truncate flag
echo   ✓ Works across projects - fully portable with zero configuration
echo.
echo [94m📣 Examples:[0m
echo   %0 list                   List all recent workflow runs
echo   %0 logs 123456789         Get logs for workflow run ID 123456789
echo   %0 tests                  Get logs for the latest test workflow run
echo   %0 saved                  List all saved log files
echo   %0 detect                 Detect repository info and available workflows
echo   %0 --truncate latest      Get the 3 most recent logs with truncated output
echo   %0 search "error"         Search all logs for 'error' (case insensitive)
echo   %0 search "Exception" true  Search logs for 'Exception' (case sensitive)
echo   %0 cleanup 10             Delete logs older than 10 days
echo   %0 cleanup --dry-run      Show what logs would be deleted without deleting
echo   %0 classify logs\workflow_12345.log  Classify errors in a specific log file
echo.
echo [93mNOTE:[0m For full functionality, run this script using WSL or Git Bash,
echo       which will provide access to all features of the bash version.
exit /b 0

REM Fall back to Windows native commands
echo Using Windows native commands...

REM Check if gh CLI is installed
WHERE gh >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo GitHub CLI ^(gh^) is not installed. Please install it from https://cli.github.com
    exit /b 1
)

REM Check authentication status
gh auth status >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo Not authenticated with GitHub CLI. Please run 'gh auth login' first.
    exit /b 1
)

echo ==========================================
echo Fetching GitHub Actions Workflow Logs
echo ==========================================

REM Create logs directory if it doesn't exist
IF NOT EXIST logs mkdir logs

REM Process commands
IF "%1"=="list" (
    call :list_workflows
    exit /b 0
)

IF "%1"=="logs" (
    call :get_workflow_logs "%2"
    exit /b 0
)

IF "%1"=="saved" (
    echo Listing saved workflow logs:
    echo ----------------------------------------
    for %%f in (logs\workflow_*.log) do (
        if exist "%%f" (
            echo %%f
        )
    )
    echo ----------------------------------------
    exit /b 0
)

IF "%1"=="latest" (
    echo Finding the most recent workflow logs
    echo ----------------------------------------
    
    REM This is limited in batch, but will list the most recent logs by file date
    REM Sort the files by date, newest first and take the first 3
    dir logs\workflow_*.log /b /o-d 2>nul | findstr /v "\.errors$" | find "workflow_" > temp_logs.txt
    
    set count=0
    for /f "delims=" %%f in (temp_logs.txt) do (
        if !count! LSS 3 (
            echo ----------------------------------------
            echo Log file: logs\%%f
            echo ----------------------------------------
            type "logs\%%f" | findstr /i /c:"error" /c:"failed" /c:"failure"
            echo ----------------------------------------
            echo [Log truncated, see full file at logs\%%f]
            echo.
            set /a count+=1
        )
    )
    del temp_logs.txt
    
    if !count! EQU 0 (
        echo No saved log files found.
        call :list_workflows
    )
    
    exit /b 0
)

IF "%1"=="tests" (
    echo Looking for saved test workflow logs...
    
    REM Try to find a saved test workflow log
    set "found_test_log="
    for %%f in (logs\workflow_*.log) do (
        if exist "%%f" (
            findstr /i /c:"Tests" "%%f" >nul 2>&1
            if !ERRORLEVEL! EQU 0 (
                set "found_test_log=%%f"
                goto :found_test
            )
        )
    )
    
    :found_test
    if defined found_test_log (
        echo Using saved test log file: !found_test_log!
        echo ----------------------------------------
        type "!found_test_log!" | findstr /i /c:"error" /c:"failed" /c:"failure"
        echo ----------------------------------------
        echo [Log truncated, see full file at !found_test_log!]
    ) else (
        echo No saved test logs found. Finding the latest test workflow run...
        FOR /F %%i IN ('gh run list --repo "%REPO_FULL_NAME%" --workflow "tests.yml" --limit 1 --json databaseId -q ".[0].databaseId"') DO set "test_run_id=%%i"
        IF "!test_run_id!"=="" (
            echo No tests workflow runs found.
        ) ELSE (
            call :get_workflow_logs "!test_run_id!"
        )
    )
    exit /b 0
)

IF "%1"=="build" (
    echo Looking for saved build workflow logs...
    
    REM Try to find a saved build workflow log
    set "found_build_log="
    for %%f in (logs\workflow_*.log) do (
        if exist "%%f" (
            findstr /i /c:"Auto Release" "%%f" >nul 2>&1
            if !ERRORLEVEL! EQU 0 (
                set "found_build_log=%%f"
                goto :found_build
            )
        )
    )
    
    :found_build
    if defined found_build_log (
        echo Using saved build log file: !found_build_log!
        echo ----------------------------------------
        type "!found_build_log!" | findstr /i /c:"error" /c:"failed" /c:"failure"
        echo ----------------------------------------
        echo [Log truncated, see full file at !found_build_log!]
    ) else (
        echo No saved build logs found. Finding the latest build/release workflow run...
        FOR /F %%i IN ('gh run list --repo "%REPO_FULL_NAME%" --workflow "auto_release.yml" --limit 1 --json databaseId -q ".[0].databaseId"') DO set "build_run_id=%%i"
        IF "!build_run_id!"=="" (
            echo No build workflow runs found.
        ) ELSE (
            call :get_workflow_logs "!build_run_id!"
        )
    )
    exit /b 0
)

REM Default action - help and check for saved logs
echo Usage: %0 [command]
echo.
echo Commands:
echo   list               List recent workflow runs from GitHub
echo   logs [RUN_ID]      Get logs for a specific workflow run
echo   tests              Get logs for the latest test workflow run
echo   build              Get logs for the latest build/release workflow run
echo   saved              List all saved log files
echo   latest             Get the 3 most recent logs (default action)
echo.
echo Examples:
echo   %0 list            List all recent workflow runs
echo   %0 logs 123456789  Get logs for workflow run ID 123456789
echo   %0 tests           Get logs for the latest test workflow run
echo   %0 saved           List all saved log files
echo   %0 latest          Get the 3 most recent logs
echo.

REM Check if we have any saved logs first
set "found_logs=0"
for %%f in (logs\workflow_*.log) do (
    if exist "%%f" (
        if !found_logs! EQU 0 (
            echo Found saved workflow logs:
            echo ----------------------------------------
        )
        set /a found_logs+=1
        
        REM Determine workflow type
        set "workflow_type=Unknown"
        findstr /i /c:"Tests" "%%f" >nul 2>&1
        if !ERRORLEVEL! EQU 0 (
            set "workflow_type=Tests"
        ) else (
            findstr /i /c:"Auto Release" "%%f" >nul 2>&1
            if !ERRORLEVEL! EQU 0 (
                set "workflow_type=Auto Release"
            )
        )
        
        echo [!workflow_type!] Log file: %%f
    )
)

if !found_logs! GTR 0 (
    echo ----------------------------------------
    echo To view a specific log type:
    echo   %0 tests     - View test workflow logs
    echo   %0 build     - View build workflow logs
    echo   %0 latest    - View the 3 most recent logs
    echo ----------------------------------------
    exit /b 0
)

REM If no saved logs, fall back to GitHub
echo No saved logs found. Trying to fetch logs from GitHub instead...

call :list_workflows

echo ==========================================
echo Fetching latest test workflow logs
echo ==========================================
FOR /F %%i IN ('gh run list --repo "%REPO_FULL_NAME%" --workflow "tests.yml" --limit 1 --json databaseId -q ".[0].databaseId"') DO set "test_run_id=%%i"
IF "!test_run_id!"=="" (
    echo No tests workflow runs found.
) ELSE (
    call :get_workflow_logs "!test_run_id!"
)

echo ==========================================
echo Fetching latest build/release workflow logs
echo ==========================================
FOR /F %%i IN ('gh run list --repo "%REPO_FULL_NAME%" --workflow "auto_release.yml" --limit 1 --json databaseId -q ".[0].databaseId"') DO set "build_run_id=%%i"
IF "!build_run_id!"=="" (
    echo No build workflow runs found.
) ELSE (
    call :get_workflow_logs "!build_run_id!"
)
exit /b 0

:list_workflows
echo Recent workflow runs:
echo -------------------------------------------------------------
echo ID        STATUS    WORKFLOW            CREATED             BRANCH
echo -------------------------------------------------------------
gh run list --repo "%REPO_FULL_NAME%" --limit 10 --json databaseId,status,name,createdAt,headBranch
echo -------------------------------------------------------------
goto :eof

:get_workflow_logs
set "run_id=%~1"

if "%run_id%"=="" (
    for /f %%i in ('gh run list --repo "%REPO_FULL_NAME%" --status failure --limit 1 --json databaseId -q ".[0].databaseId"') do set "run_id=%%i"
    
    if "!run_id!"=="" (
        echo No failed workflow runs found.
        exit /b 1
    )
    
    echo Using most recent failed workflow run: !run_id!
) else (
    echo Fetching logs for workflow run: %run_id%
)

REM First check if we already have this log saved
set "found_existing_log="
for %%f in (logs\workflow_%run_id%_*.log) do (
    if exist "%%f" (
        set "found_existing_log=%%f"
        goto :found_log
    )
)

:found_log
if defined found_existing_log (
    echo Using existing saved log file: !found_existing_log!
    
    REM Check if we have an error file
    if exist "!found_existing_log!.errors" (
        echo Found error log file: !found_existing_log!.errors
        type "!found_existing_log!.errors"
    ) else (
        echo Processing log file to extract errors:
        findstr /i /c:"error" /c:"failed" /c:"failure" "!found_existing_log!"
    )
    
    goto :eof
)

REM Get current timestamp in format YYYYMMDD-HHMMSS
for /f "tokens=2 delims==" %%a in ('wmic OS Get localdatetime /value') do set "dt=%%a"
set "timestamp=%dt:~0,8%-%dt:~8,6%"

REM Create log filename
set "log_file=logs\workflow_%run_id%_%timestamp%.log"

echo Downloading logs to %log_file%...

REM Download the logs
gh run view "%run_id%" --repo "%REPO_FULL_NAME%" --log > "%log_file%"

echo Logs downloaded successfully: %log_file%

REM Try to find errors in the log file
findstr /i /C:"error" /C:"failed" /C:"failure" "%log_file%" > "%log_file%.errors"

IF %ERRORLEVEL% EQU 0 (
    echo Found potential errors in the log file. See %log_file%.errors for details.
) ELSE (
    echo No obvious errors found in the log file.
)

echo.
echo To view full logs, open: %log_file%
echo.

goto :eof