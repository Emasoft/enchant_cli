@echo off
REM get_errorlogs.bat - CLAUDE HELPER SCRIPT for GitHub Actions workflow log analysis
REM Version 1.2.0 - Enhanced workflow detection and improved GitHub API integration

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
echo [93m🔶 CLAUDE HELPER SCRIPT: GitHub Actions Workflow Logs Tool v1.2.0[0m
echo.
echo This script is part of the CLAUDE HELPER SCRIPTS collection.
echo For more information, see the CLAUDE.md documentation.
exit /b 0

:show_help
echo [93m🔶 CLAUDE HELPER SCRIPT: GitHub Actions Workflow Logs Tool v1.2.0[0m
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
echo   ✓ Advanced workflow detection with multi-signal categorization
echo   ✓ Enhanced GitHub API integration for better workflow analysis
echo   ✓ Intelligent error classification with context and root cause analysis
echo   ✓ Full output by default, with optional truncation via --truncate flag
echo   ✓ Works across projects - fully portable with zero configuration
echo   ✓ Improved shell compatibility for all platforms
echo   ✓ Better CodeCov integration with custom reporting
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

REM Detect repository info from git (similar to bash version)
FOR /F "tokens=*" %%g IN ('git config --get remote.origin.url 2^>nul') do (SET "GIT_REMOTE_URL=%%g")

IF "%GIT_REMOTE_URL%"=="" (
    echo Failed to detect repository from git remote.
    echo Please specify your repository explicitly with --repo owner/name
    exit /b 1
)

REM Try to extract owner and name from remote URL
REM This is a simplified version that works for the most common cases
FOR /F "tokens=4,5 delims=/:." %%a IN ("%GIT_REMOTE_URL%") DO (
    SET REPO_OWNER=%%a
    SET REPO_NAME=%%b
)

REM Handle GitHub URLs with .git extension
IF "%REPO_NAME:~-4%"==".git" (
    SET REPO_NAME=%REPO_NAME:~0,-4%
)

REM Form full repository name
SET REPO_FULL_NAME=%REPO_OWNER%/%REPO_NAME%
echo Using repository: %REPO_FULL_NAME%

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

IF "%1"=="workflows" (
    echo [93m🔶 Detecting GitHub Workflows[0m
    echo.
    
    REM Try to find workflows in this repo
    set "workflow_count=0"
    
    REM Check local .github/workflows directory
    if exist ".github\workflows" (
        for %%f in (.github\workflows\*.yml .github\workflows\*.yaml) do (
            if exist "%%f" (
                set /a workflow_count+=1
                
                REM Try to determine workflow type
                set "workflow_type=Other"
                findstr /i /c:"test" /c:"ci" "%%f" >nul 2>&1
                if !ERRORLEVEL! EQU 0 (
                    set "workflow_type=Test"
                ) else (
                    findstr /i /c:"release" /c:"deploy" /c:"publish" /c:"build" "%%f" >nul 2>&1
                    if !ERRORLEVEL! EQU 0 (
                        set "workflow_type=Release"
                    ) else (
                        findstr /i /c:"lint" /c:"style" /c:"format" "%%f" >nul 2>&1
                        if !ERRORLEVEL! EQU 0 (
                            set "workflow_type=Lint"
                        ) else (
                            findstr /i /c:"doc" "%%f" >nul 2>&1
                            if !ERRORLEVEL! EQU 0 (
                                set "workflow_type=Documentation"
                            )
                        )
                    )
                )
                
                echo Detected workflow: %%f (Type: !workflow_type!)
            )
        )
    )
    
    REM If no workflows found locally, try to get from GitHub
    if !workflow_count! EQU 0 (
        echo No local workflows found. Checking GitHub API...
        gh workflow list --repo "%REPO_FULL_NAME%" --json name,path,state
    ) else (
        echo.
        echo Found !workflow_count! workflow files locally.
    )
    
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

IF "%1"=="search" (
    set "search_pattern=%~2"
    set "case_sensitive=%~3"
    set "max_results=%~4"
    
    if "%search_pattern%"=="" (
        echo Error: No search pattern provided.
        echo Usage: %0 search "pattern" [case_sensitive] [max_results]
        exit /b 1
    )
    
    if "%max_results%"=="" (
        set "max_results=100"
    )
    
    echo Searching for pattern: "%search_pattern%" in saved logs
    echo Max results: %max_results%
    echo Case sensitive: %case_sensitive%
    echo ----------------------------------------
    
    set "found_matches=0"
    
    for %%f in (logs\workflow_*.log) do (
        if exist "%%f" (
            if "%case_sensitive%"=="true" (
                findstr /n /c:"%search_pattern%" "%%f" > search_results.tmp
            ) else (
                findstr /n /i /c:"%search_pattern%" "%%f" > search_results.tmp
            )
            
            if not !ERRORLEVEL! EQU 1 (
                set /a found_matches+=1
                echo.
                echo [File: %%f]
                echo ----------------------------------------
                type search_results.tmp
                echo ----------------------------------------
                echo.
            )
        )
    )
    
    del search_results.tmp
    
    if !found_matches! EQU 0 (
        echo No matches found.
    ) else (
        echo Found matches in !found_matches! files.
    )
    
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

IF "%1"=="lint" (
    echo Looking for saved lint workflow logs...
    
    REM Try to find a saved lint workflow log
    set "found_lint_log="
    for %%f in (logs\workflow_*.log) do (
        if exist "%%f" (
            findstr /i /c:"Lint" /c:"Style" "%%f" >nul 2>&1
            if !ERRORLEVEL! EQU 0 (
                set "found_lint_log=%%f"
                goto :found_lint
            )
        )
    )
    
    :found_lint
    if defined found_lint_log (
        echo Using saved lint log file: !found_lint_log!
        echo ----------------------------------------
        type "!found_lint_log!" | findstr /i /c:"error" /c:"failed" /c:"failure"
        echo ----------------------------------------
        echo [Log truncated, see full file at !found_lint_log!]
    ) else (
        echo No saved lint logs found.
        echo Looking for a lint workflow in the repository...
        
        REM Try to find a lint workflow file
        set "lint_workflow="
        if exist ".github\workflows" (
            for %%f in (.github\workflows\*.yml .github\workflows\*.yaml) do (
                if exist "%%f" (
                    findstr /i /c:"lint" /c:"style" /c:"format" "%%f" >nul 2>&1
                    if !ERRORLEVEL! EQU 0 (
                        set "lint_workflow=%%~nf"
                        echo Found potential lint workflow: %%f
                    )
                )
            )
        )
        
        if not "!lint_workflow!"=="" (
            echo Fetching logs for !lint_workflow! workflow...
            FOR /F %%i IN ('gh run list --repo "%REPO_FULL_NAME%" --workflow "!lint_workflow!.yml" --limit 1 --json databaseId -q ".[0].databaseId"') DO set "lint_run_id=%%i"
            IF "!lint_run_id!"=="" (
                echo No lint workflow runs found.
            ) ELSE (
                call :get_workflow_logs "!lint_run_id!"
            )
        ) else (
            echo No lint workflow found. Please check GitHub repository.
        )
    )
    exit /b 0
)

IF "%1"=="docs" (
    echo Looking for saved documentation workflow logs...
    
    REM Try to find a saved docs workflow log
    set "found_docs_log="
    for %%f in (logs\workflow_*.log) do (
        if exist "%%f" (
            findstr /i /c:"Documentation" /c:"Docs" "%%f" >nul 2>&1
            if !ERRORLEVEL! EQU 0 (
                set "found_docs_log=%%f"
                goto :found_docs
            )
        )
    )
    
    :found_docs
    if defined found_docs_log (
        echo Using saved documentation log file: !found_docs_log!
        echo ----------------------------------------
        type "!found_docs_log!" | findstr /i /c:"error" /c:"failed" /c:"failure"
        echo ----------------------------------------
        echo [Log truncated, see full file at !found_docs_log!]
    ) else (
        echo No saved documentation logs found.
        echo Looking for a documentation workflow in the repository...
        
        REM Try to find a docs workflow file
        set "docs_workflow="
        if exist ".github\workflows" (
            for %%f in (.github\workflows\*.yml .github\workflows\*.yaml) do (
                if exist "%%f" (
                    findstr /i /c:"docs" /c:"documentation" "%%f" >nul 2>&1
                    if !ERRORLEVEL! EQU 0 (
                        set "docs_workflow=%%~nf"
                        echo Found potential documentation workflow: %%f
                    )
                )
            )
        )
        
        if not "!docs_workflow!"=="" (
            echo Fetching logs for !docs_workflow! workflow...
            FOR /F %%i IN ('gh run list --repo "%REPO_FULL_NAME%" --workflow "!docs_workflow!.yml" --limit 1 --json databaseId -q ".[0].databaseId"') DO set "docs_run_id=%%i"
            IF "!docs_run_id!"=="" (
                echo No documentation workflow runs found.
            ) ELSE (
                call :get_workflow_logs "!docs_run_id!"
            )
        ) else (
            echo No documentation workflow found. Please check GitHub repository.
        )
    )
    exit /b 0
)

IF "%1"=="detect" (
    echo [93m🔶 CLAUDE HELPER SCRIPT: Repository and Workflow Detection[0m
    echo.
    echo [94mℹ️ Repository Information[0m
    echo Using repository: %REPO_FULL_NAME%
    echo Owner: %REPO_OWNER%
    echo Name: %REPO_NAME%
    echo.
    
    echo [94mℹ️ Detecting Available Workflows[0m
    
    REM Try to find workflows in this repo
    set "workflow_count=0"
    set "test_workflows=0"
    set "release_workflows=0"
    
    REM Check local .github/workflows directory
    if exist ".github\workflows" (
        for %%f in (.github\workflows\*.yml .github\workflows\*.yaml) do (
            if exist "%%f" (
                set /a workflow_count+=1
                
                REM Try to determine workflow type
                set "workflow_type=Other"
                findstr /i /c:"test" /c:"ci" "%%f" >nul 2>&1
                if !ERRORLEVEL! EQU 0 (
                    set "workflow_type=Test"
                    set /a test_workflows+=1
                ) else (
                    findstr /i /c:"release" /c:"deploy" /c:"publish" /c:"build" "%%f" >nul 2>&1
                    if !ERRORLEVEL! EQU 0 (
                        set "workflow_type=Release"
                        set /a release_workflows+=1
                    )
                )
                
                echo Detected workflow: %%f (Type: !workflow_type!)
            )
        )
    )
    
    REM If no workflows found locally, try to get from GitHub
    if !workflow_count! EQU 0 (
        echo No local workflows found. Checking GitHub API...
        gh workflow list --repo "%REPO_FULL_NAME%" --json name,path,state
    )
    
    echo.
    echo [94mℹ️ Configuration Summary[0m
    echo Working directory: %CD%
    echo Repository: %REPO_FULL_NAME%
    echo Total workflows detected: !workflow_count!
    echo Test workflows: !test_workflows!
    echo Release workflows: !release_workflows!
    echo.
    echo [92m✅ Detection complete.[0m
    
    exit /b 0
)

REM Automatic workflow analysis in Windows Batch mode
echo [93m🔶 CLAUDE HELPER SCRIPT: Automatic Workflow Analysis[0m
echo.
echo This script automatically:
echo   1. Detects repository information and available workflows
echo   2. Categorizes workflows by type (test, release, lint, docs)
echo   3. Prioritizes finding failed workflows that need attention
echo   4. Analyzes logs with intelligent error classification
echo   5. Shows workflow run statistics and activity summary
echo.
echo [94mℹ️ IMPORTANT:[0m For full functionality on Windows, please use WSL or Git Bash:
echo   wsl ./get_errorlogs.sh    [Using WSL]
echo   bash ./get_errorlogs.sh   [Using Git Bash]
echo.
echo [94mℹ️ Available Commands:[0m
echo   %0 detect          Auto-detect repository info and workflows
echo   %0 workflows       List detected workflows with types
echo   %0 tests           Get logs for test workflows
echo   %0 build           Get logs for build/release workflows
echo   %0 lint            Get logs for linting workflows
echo   %0 docs            Get logs for documentation workflows
echo   %0 latest          Get the 3 most recent logs
echo   %0 search "pattern" Search all logs for a specific pattern
echo   %0 saved           List all saved log files
echo   %0 list            List all workflow runs from GitHub
echo   %0 help            Show complete help with all commands
echo.
echo [94mℹ️ ENHANCED AUTOMATIC DETECTION:[0m
echo   This script features improved detection:
echo   - Multi-signal workflow categorization for better accuracy
echo   - Enhanced GitHub API integration for detailed workflow information
echo   - Automatic repository detection from git remote URLs
echo   - Smart workflow classification based on file content and naming
echo   - Improved workflow analysis with failure prioritization
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