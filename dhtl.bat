@echo off
REM Development Helper Toolkit Launcher (DHTL) for Windows
REM A portable, project-independent toolkit for DevOps, process management,
REM GitHub workflows, and development environment enhancement.
REM
REM This script can be used in any project as a central command launcher with
REM automatic resource management and project-aware configuration.

SETLOCAL EnableDelayedExpansion

REM ===== Configuration =====

REM Get script directory (location of DHTL)
SET DHTL_DIR=%~dp0
SET DHTL_DIR=%DHTL_DIR:~0,-1%

REM Default resource limits
SET DEFAULT_MEM_LIMIT=512
SET NODE_MEM_LIMIT=768
SET PYTHON_MEM_LIMIT=512
SET TIMEOUT=900

REM DHT location relative to dhtl.bat
SET DHT_DIR=%DHTL_DIR%\DHT

REM Cache location for downloadable tools and artifacts
SET CACHE_DIR=%DHTL_DIR%\.dht_cache

REM Default virtual environment location
SET DEFAULT_VENV_DIR=%DHTL_DIR%\.venv

REM ===== Environment Detection =====

REM Find project root
CALL :FIND_PROJECT_ROOT
SET PROJECT_ROOT=%ERRORLEVEL%
IF "%PROJECT_ROOT%"=="0" (
    SET PROJECT_ROOT=%DHTL_DIR%
)

REM Check if Python is available
WHERE python >nul 2>nul
IF ERRORLEVEL 1 (
    echo Python not found. Please install Python 3.9 or newer.
    exit /b 1
)
SET PYTHON_CMD=python

REM Check if quiet mode and guardian flags are provided
SET USE_GUARDIAN=true
SET QUIET_MODE=false
CALL :PROCESS_FLAGS %*
SET ARGS=%RESULT_ARGS%

REM Add the script directory to PYTHONPATH
SET PYTHONPATH=%DHTL_DIR%;%PYTHONPATH%

REM Ensure cache directory exists
IF NOT EXIST "%CACHE_DIR%" mkdir "%CACHE_DIR%"

REM ===== Environment Detection Functions =====

:FIND_PROJECT_ROOT
REM Search up the directory tree for project markers
SET CURRENT_DIR=%DHTL_DIR%
:PROJECT_ROOT_LOOP
IF EXIST "%CURRENT_DIR%\.git" EXIT /B %CURRENT_DIR%
IF EXIST "%CURRENT_DIR%\pyproject.toml" EXIT /B %CURRENT_DIR%
IF EXIST "%CURRENT_DIR%\package.json" EXIT /B %CURRENT_DIR%
IF EXIST "%CURRENT_DIR%\go.mod" EXIT /B %CURRENT_DIR%
IF EXIST "%CURRENT_DIR%\Cargo.toml" EXIT /B %CURRENT_DIR%

REM Move up one directory
FOR %%I IN ("%CURRENT_DIR%\..") DO SET PARENT_DIR=%%~fI
IF "%PARENT_DIR%"=="%CURRENT_DIR%" EXIT /B 0
SET CURRENT_DIR=%PARENT_DIR%
GOTO PROJECT_ROOT_LOOP

:DETECT_ACTIVE_VENV
IF DEFINED VIRTUAL_ENV (
    EXIT /B %VIRTUAL_ENV%
)
IF DEFINED CONDA_PREFIX (
    EXIT /B %CONDA_PREFIX%
)
EXIT /B ""

:FIND_VIRTUAL_ENV
SET PROJECT_DIR=%~1
SET ENV_NAME=
REM Check common venv locations
FOR %%V IN (".venv" "venv" "env" ".env") DO (
    IF EXIST "%PROJECT_DIR%\%%V\Scripts\activate.bat" (
        SET ENV_NAME=%PROJECT_DIR%\%%V
        GOTO FOUND_VENV
    )
)
:FOUND_VENV
EXIT /B %ENV_NAME%

:PROCESS_FLAGS
SET RESULT_ARGS=
FOR %%a IN (%*) DO (
    IF "%%a"=="--no-guardian" (
        SET USE_GUARDIAN=false
    ) ELSE IF "%%a"=="--quiet" (
        SET QUIET_MODE=true
    ) ELSE (
        SET RESULT_ARGS=!RESULT_ARGS! %%a
    )
)
EXIT /B 0

REM ===== Environment Setup =====

:SETUP_ENVIRONMENT
SET PROJECT_ROOT=%~1
SET VENV_DIR=%~2
IF "%VENV_DIR%"=="" SET VENV_DIR=%DEFAULT_VENV_DIR%
SET TARGET_PYTHON=%~3
IF "%TARGET_PYTHON%"=="" SET TARGET_PYTHON=3.10

REM Check if uv is available
WHERE uv >nul 2>nul
IF ERRORLEVEL 1 (
    echo Installing uv tool...
    curl -LsSf https://astral.sh/uv/install.sh | sh
    REM Try again after installing
    WHERE uv >nul 2>nul
    IF ERRORLEVEL 1 (
        echo Failed to install uv tool
        EXIT /B 1
    )
)

REM Set environment-specific path based on platform
IF DEFINED UV_PROJECT_ENVIRONMENT (
    REM User has overridden the environment location
    SET VENV_DIR=%UV_PROJECT_ENVIRONMENT%
) ELSE (
    SET UV_PROJECT_ENVIRONMENT=%VENV_DIR%_windows
    SET VENV_DIR=%UV_PROJECT_ENVIRONMENT%
)

REM Create directory if it doesn't exist
IF NOT EXIST "%VENV_DIR%\.." mkdir "%VENV_DIR%\.."

REM Create virtual environment if it doesn't exist
IF NOT EXIST "%VENV_DIR%" (
    echo Creating new virtual environment at %VENV_DIR%...
    uv venv "%VENV_DIR%" --python %TARGET_PYTHON%
)

REM Activate the virtual environment
echo Activating virtual environment...
IF EXIST "%VENV_DIR%\Scripts\activate.bat" (
    call "%VENV_DIR%\Scripts\activate.bat"
) ELSE (
    echo Error: Virtual environment activation script not found
    EXIT /B 1
)

REM Install dependencies based on project type
echo Installing required dependencies...
IF EXIST "%PROJECT_ROOT%\pyproject.toml" (
    REM Python project - use uv to install
    IF EXIST "%PROJECT_ROOT%\uv.lock" (
        uv sync
    ) ELSE (
        uv pip install -e "%PROJECT_ROOT%"
    )
) ELSE IF EXIST "%PROJECT_ROOT%\package.json" (
    REM Node.js project - make sure node is available
    WHERE node >nul 2>nul
    IF ERRORLEVEL 1 (
        echo Error: Node.js is required but not found
        EXIT /B 1
    )
)

REM Install DHT-specific dependencies
uv pip install psutil requests

EXIT /B 0

:RESTORE_DEPENDENCIES
SET CACHE_DIR=%~1

IF NOT EXIST "%CACHE_DIR%" mkdir "%CACHE_DIR%"

REM Check if we need to download any dependencies
IF NOT EXIST "%CACHE_DIR%\.initialized" (
    echo Initializing dependency cache...
    
    REM Create a marker file to indicate cache is initialized
    echo Created at %DATE% %TIME% > "%CACHE_DIR%\.initialized"
)

EXIT /B 0

REM ===== Process Guardian =====

:ENSURE_PROCESS_GUARDIAN
IF "%USE_GUARDIAN%"=="true" (
    IF EXIST "%DHT_DIR%\process-guardian-watchdog.py" (
        REM Make sure .process_guardian directory exists
        SET GUARDIAN_DIR=%DHT_DIR%\.process_guardian
        SET PID_FILE=%GUARDIAN_DIR%\process_watchdog.pid
        
        IF NOT EXIST "%GUARDIAN_DIR%" mkdir "%GUARDIAN_DIR%"
        
        REM Check if watchdog is already running
        IF NOT EXIST "%PID_FILE%" (
            echo Starting Process Guardian Watchdog...
            %PYTHON_CMD% "%DHT_DIR%\process-guardian-watchdog.py" start
            timeout /t 1 >nul
        )
    )
)
EXIT /B 0

:RUN_WITH_GUARDIAN
SET COMMAND=%~1
SET PROCESS_TYPE=%~2
SET MEM_LIMIT=%~3
SHIFT & SHIFT & SHIFT

REM Determine memory limit based on process type
IF "%MEM_LIMIT%"=="" (
    IF "%PROCESS_TYPE%"=="node" (
        SET MEM_LIMIT=%NODE_MEM_LIMIT%
    ) ELSE IF "%PROCESS_TYPE%"=="python" (
        SET MEM_LIMIT=%PYTHON_MEM_LIMIT%
    ) ELSE (
        SET MEM_LIMIT=%DEFAULT_MEM_LIMIT%
    )
)

REM Check if guard-process.bat exists
IF EXIST "%DHT_DIR%\guard-process.bat" (
    IF "%USE_GUARDIAN%"=="true" (
        echo Running with Process Guardian (%PROCESS_TYPE%, %MEM_LIMIT%MB limit)
        CALL "%DHT_DIR%\guard-process.bat" --max-memory %MEM_LIMIT% --timeout %TIMEOUT% --monitor %PROCESS_TYPE% -- %COMMAND% %*
        EXIT /B !ERRORLEVEL!
    )
)

REM Fall back to running directly
%COMMAND% %*
EXIT /B !ERRORLEVEL!

REM ===== Main Commands =====

:RUN_NODE_COMMAND
CALL :ENSURE_PROCESS_GUARDIAN
REM Use node-wrapper.bat for Node.js commands if available
IF EXIST "%DHT_DIR%\node-wrapper.bat" (
    IF "%USE_GUARDIAN%"=="true" (
        echo Running Node.js command with wrapper
        CALL "%DHT_DIR%\node-wrapper.bat" %*
        EXIT /B !ERRORLEVEL!
    )
)
REM Fallback to running with generic guardian
CALL :RUN_WITH_GUARDIAN node node %NODE_MEM_LIMIT% %*
EXIT /B !ERRORLEVEL!

:RUN_PYTHON_DEV_COMMAND
SET SCRIPT_PATH=%~1
SHIFT

CALL :ENSURE_PROCESS_GUARDIAN
REM Use python-dev-wrapper.bat for Python dev scripts if available
IF EXIST "%DHT_DIR%\python-dev-wrapper.bat" (
    IF "%USE_GUARDIAN%"=="true" (
        echo Running Python dev script with wrapper
        CALL "%DHT_DIR%\python-dev-wrapper.bat" "%SCRIPT_PATH%" %*
        EXIT /B !ERRORLEVEL!
    )
)
REM Fallback to running with generic guardian
REM Check file extension
IF "%SCRIPT_PATH:~-3%"==".py" (
    CALL :RUN_WITH_GUARDIAN python python %PYTHON_MEM_LIMIT% "%SCRIPT_PATH%" %*
) ELSE (
    CALL :RUN_WITH_GUARDIAN "%SCRIPT_PATH%" script %DEFAULT_MEM_LIMIT% %*
)
EXIT /B !ERRORLEVEL!

:SHOW_HELP
echo Development Helper Toolkit Launcher (DHTL) v1.0.0
echo Usage: dhtl.bat [command] [options]
echo.
echo General Commands:
echo   setup       - Set up the toolkit for the current project
echo   restore     - Restore dependencies from cache or download them
echo   env         - Show environment information
echo   clean       - Clean caches and temporary files
echo   help        - Show this help message
echo.
echo Main Commands:
echo   node        - Run a Node.js command with resource limits
echo   script      - Run a development helper script
echo   guardian    - Process guardian commands (status, stop, etc.)
echo.
echo Global Options:
echo   --no-guardian  - Disable process guardian for this command
echo   --quiet        - Reduce output verbosity
echo.
echo Examples:
echo   dhtl.bat setup                    # Set up the toolkit
echo   dhtl.bat node script.js           # Run a Node.js script
echo   dhtl.bat script get_errorlogs     # Run error log analyzer script
echo   dhtl.bat guardian status          # Check process guardian status
echo.
echo This toolkit is portable and can be moved to any project.
EXIT /B 0

:SETUP_COMMAND
echo Setting up Development Helper Toolkit for project...

REM Create .dhtconfig file with project-specific settings
echo PROJECT_ROOT=%PROJECT_ROOT%> "%DHTL_DIR%\.dhtconfig"
echo CREATED_AT=%DATE% %TIME%>> "%DHTL_DIR%\.dhtconfig"

REM Create or ensure virtual environment
CALL :SETUP_ENVIRONMENT "%PROJECT_ROOT%" "%DEFAULT_VENV_DIR%"
IF ERRORLEVEL 1 EXIT /B 1

REM Set up .gitignore for DHT cache and env
IF EXIST "%PROJECT_ROOT%\.gitignore" (
    REM Check if already in gitignore
    FINDSTR /C:".dht_cache" "%PROJECT_ROOT%\.gitignore" >nul
    IF ERRORLEVEL 1 (
        echo.>> "%PROJECT_ROOT%\.gitignore"
        echo # Development Helper Toolkit>> "%PROJECT_ROOT%\.gitignore"
        echo .dht_cache>> "%PROJECT_ROOT%\.gitignore"
        echo .dht*>> "%PROJECT_ROOT%\.gitignore"
        echo.>> "%PROJECT_ROOT%\.gitignore"
    )
) ELSE (
    REM Create a new gitignore file
    echo # Development Helper Toolkit> "%PROJECT_ROOT%\.gitignore"
    echo .dht_cache>> "%PROJECT_ROOT%\.gitignore"
    echo .dht*>> "%PROJECT_ROOT%\.gitignore"
)

echo Setup complete. The toolkit is ready to use.
echo.
echo To run a command, use: dhtl.bat [command] [options]
echo For more information, use: dhtl.bat help

EXIT /B 0

:CLEAN_COMMAND
echo Cleaning Development Helper Toolkit caches and temporary files...

REM Clean cache directory
IF EXIST "%CACHE_DIR%" (
    REM Delete all files in cache directory
    DEL /Q /S "%CACHE_DIR%\*" >nul 2>nul
    IF NOT EXIST "%CACHE_DIR%" mkdir "%CACHE_DIR%"
)

REM Clean guardian logs
IF EXIST "%DHT_DIR%\.process_guardian" (
    DEL /Q /S "%DHT_DIR%\.process_guardian\*" >nul 2>nul
)

echo Cleaning complete.
EXIT /B 0

:ENV_COMMAND
REM Get active environment
CALL :DETECT_ACTIVE_VENV
SET ACTIVE_VENV=%ERRORLEVEL%
IF "%ACTIVE_VENV%"=="0" SET ACTIVE_VENV=None

REM Get project environment
CALL :FIND_VIRTUAL_ENV "%PROJECT_ROOT%"
SET PROJECT_VENV=%ERRORLEVEL%
IF "%PROJECT_VENV%"=="0" SET PROJECT_VENV=None

echo Development Helper Toolkit Environment Information
echo ==================================================
echo Platform:       Windows
echo Python:         %PYTHON_CMD%
echo DHTL Directory: %DHTL_DIR%
echo DHT Directory:  %DHT_DIR%
echo Project Root:   %PROJECT_ROOT%
echo.
echo Virtual Environments:
echo   Active:       %ACTIVE_VENV%
echo   Project:      %PROJECT_VENV%
echo   Default:      %DEFAULT_VENV_DIR%
echo.
echo API Keys Found:

REM Check for common API keys and tokens
FOR %%K IN (OPENROUTER_API_KEY OPENAI_API_KEY GITHUB_TOKEN PYPI_API_TOKEN CODECOV_API_TOKEN) DO (
    IF DEFINED %%K (
        echo   %%K:      √ (Set)
    ) ELSE (
        echo   %%K:      X (Not found)
    )
)

echo.
echo Development Tools:
FOR %%T IN (node npm python pip uv gh git) DO (
    WHERE %%T >nul 2>nul
    IF NOT ERRORLEVEL 1 (
        FOR /F "tokens=*" %%V IN ('%%T --version 2^>nul') DO (
            echo   %%T:      √ (Found - %%V)
            GOTO NEXT_TOOL_%%T
        )
        echo   %%T:      √ (Found - version unknown)
    ) ELSE (
        echo   %%T:      X (Not found)
    )
    :NEXT_TOOL_%%T
)

EXIT /B 0

:RESTORE_COMMAND
echo Restoring Development Helper Toolkit dependencies...
CALL :RESTORE_DEPENDENCIES "%CACHE_DIR%"
echo Dependencies restored.
EXIT /B 0

REM ===== Main Script Logic =====

REM Handle main commands
IF "%1"=="" (
    REM No arguments, show help
    CALL :SHOW_HELP
    EXIT /B 0
)

IF "%1"=="help" (
    CALL :SHOW_HELP
    EXIT /B 0
)

IF "%1"=="--help" (
    CALL :SHOW_HELP
    EXIT /B 0
)

IF "%1"=="-h" (
    CALL :SHOW_HELP
    EXIT /B 0
)

IF "%1"=="setup" (
    CALL :SETUP_COMMAND
    EXIT /B %ERRORLEVEL%
)

IF "%1"=="restore" (
    CALL :RESTORE_COMMAND
    EXIT /B %ERRORLEVEL%
)

IF "%1"=="env" (
    CALL :ENV_COMMAND
    EXIT /B %ERRORLEVEL%
)

IF "%1"=="clean" (
    CALL :CLEAN_COMMAND
    EXIT /B %ERRORLEVEL%
)

IF "%1"=="version" (
    echo Development Helper Toolkit Launcher (DHTL) v1.0.0
    EXIT /B 0
)

IF "%1"=="--version" (
    echo Development Helper Toolkit Launcher (DHTL) v1.0.0
    EXIT /B 0
)

IF "%1"=="-v" (
    echo Development Helper Toolkit Launcher (DHTL) v1.0.0
    EXIT /B 0
)

IF "%1"=="node" (
    SHIFT
    CALL :RUN_NODE_COMMAND %*
    EXIT /B %ERRORLEVEL%
)

IF "%1"=="script" (
    SHIFT
    IF "%1"=="" (
        echo Available scripts:
        FOR /F "tokens=*" %%i IN ('dir /b "%DHT_DIR%" ^| findstr /E ".sh .py .bat"') DO (
            SET "filename=%%i"
            SET "basename=!filename!"
            SET "basename=!basename:.sh=!"
            SET "basename=!basename:.py=!"
            SET "basename=!basename:.bat=!"
            echo   !basename!
        )
        EXIT /B 0
    )
    
    REM Find the script (with or without extension)
    SET SCRIPT_NAME=%1
    SHIFT
    
    IF EXIST "%DHT_DIR%\%SCRIPT_NAME%" (
        SET SCRIPT_PATH=%DHT_DIR%\%SCRIPT_NAME%
    ) ELSE IF EXIST "%DHT_DIR%\%SCRIPT_NAME%.bat" (
        SET SCRIPT_PATH=%DHT_DIR%\%SCRIPT_NAME%.bat
    ) ELSE IF EXIST "%DHT_DIR%\%SCRIPT_NAME%.py" (
        SET SCRIPT_PATH=%DHT_DIR%\%SCRIPT_NAME%.py
    ) ELSE IF EXIST "%DHT_DIR%\%SCRIPT_NAME%.sh" (
        SET SCRIPT_PATH=%DHT_DIR%\%SCRIPT_NAME%.sh
    ) ELSE (
        echo Error: Script not found: %SCRIPT_NAME%
        EXIT /B 1
    )
    
    REM Run the script with appropriate guardian
    CALL :RUN_PYTHON_DEV_COMMAND "%SCRIPT_PATH%" %*
    EXIT /B %ERRORLEVEL%
)

IF "%1"=="guardian" (
    SHIFT
    IF "%1"=="" (
        echo Process Guardian Commands:
        echo   status      - Check guardian status
        echo   stop        - Stop the guardian
        echo   start       - Start the guardian manually
        echo   list        - List monitored processes
        EXIT /B 0
    )
    
    REM Handle guardian subcommands
    SET GUARDIAN_SCRIPT=%DHT_DIR%\process-guardian-watchdog.py
    IF NOT EXIST "%GUARDIAN_SCRIPT%" (
        echo Error: Process guardian not found
        EXIT /B 1
    )
    
    IF "%1"=="status" (
        python "%GUARDIAN_SCRIPT%" status
    ) ELSE IF "%1"=="stop" (
        python "%GUARDIAN_SCRIPT%" stop
    ) ELSE IF "%1"=="start" (
        python "%GUARDIAN_SCRIPT%" start
    ) ELSE IF "%1"=="list" (
        python -m helpers.cli process --list
    ) ELSE (
        echo Unknown guardian command: %1
        echo Available commands: status, stop, start, list
        EXIT /B 1
    )
    
    EXIT /B %ERRORLEVEL%
)

REM Check if we're trying to run a helper CLI command directly
IF EXIST "%DHT_DIR%\helpers\cli.py" (
    REM First, try to set up the environment
    CALL :DETECT_ACTIVE_VENV
    SET ACTIVE_VENV=%ERRORLEVEL%
    
    IF DEFINED ACTIVE_VENV IF NOT "%ACTIVE_VENV%"=="0" (
        REM Already in an activated environment
        CALL :ENSURE_PROCESS_GUARDIAN
        CALL :RUN_WITH_GUARDIAN python python %PYTHON_MEM_LIMIT% -m helpers.cli %ARGS%
        EXIT /B %ERRORLEVEL%
    ) ELSE (
        REM Try to find and activate a virtual environment
        CALL :FIND_VIRTUAL_ENV "%PROJECT_ROOT%"
        SET PROJECT_VENV=%ERRORLEVEL%
        
        IF DEFINED PROJECT_VENV IF NOT "%PROJECT_VENV%"=="0" (
            REM Use the project's virtual environment
            call "%PROJECT_VENV%\Scripts\activate.bat"
            CALL :ENSURE_PROCESS_GUARDIAN
            CALL :RUN_WITH_GUARDIAN python python %PYTHON_MEM_LIMIT% -m helpers.cli %ARGS%
            EXIT /B %ERRORLEVEL%
        ) ELSE (
            REM No environment found, try to create one
            CALL :SETUP_ENVIRONMENT "%PROJECT_ROOT%" "%DEFAULT_VENV_DIR%"
            IF NOT ERRORLEVEL 1 (
                CALL :ENSURE_PROCESS_GUARDIAN
                CALL :RUN_WITH_GUARDIAN python python %PYTHON_MEM_LIMIT% -m helpers.cli %ARGS%
                EXIT /B %ERRORLEVEL%
            ) ELSE (
                REM Fall back to system Python
                CALL :ENSURE_PROCESS_GUARDIAN
                WHERE uv >nul 2>nul
                IF NOT ERRORLEVEL 1 (
                    uv pip install -e "%DHTL_DIR%"
                    uv sync
                    CALL :RUN_WITH_GUARDIAN python python %PYTHON_MEM_LIMIT% -m helpers.cli %ARGS%
                ) ELSE (
                    python -m pip install -e "%DHTL_DIR%"
                    CALL :RUN_WITH_GUARDIAN python python %PYTHON_MEM_LIMIT% -m helpers.cli %ARGS%
                )
                EXIT /B %ERRORLEVEL%
            )
        )
    )
) ELSE (
    echo Unknown command: %1
    echo Run 'dhtl.bat help' for usage information.
    EXIT /B 1
)

ENDLOCAL
EXIT /B %ERRORLEVEL%