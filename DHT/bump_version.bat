@echo off
REM Enhanced Windows batch file for manually bumping version
REM Allows specifying minor/major/patch and handles uv

SETLOCAL EnableDelayedExpansion

echo === Enchant CLI Version Bumper for Windows ===

REM Default to minor if no argument provided
IF "%~1"=="" (
    SET VERSION_PART=minor
    echo No version part specified, defaulting to minor.
) ELSE (
    SET VERSION_PART=%~1
)

REM Validate version part
IF NOT "%VERSION_PART%"=="major" IF NOT "%VERSION_PART%"=="minor" IF NOT "%VERSION_PART%"=="patch" (
    echo ❌ Error: Invalid version part. Use one of: major, minor, patch
    echo Usage: bump_version.bat [major^|minor^|patch]
    exit /b 1
)

REM Check for helpers-cli.bat
IF EXIST "helpers-cli.bat" (
    echo 🔄 Using helpers-cli.bat to run bump-my-version...
    call helpers-cli.bat repo --bump-version %VERSION_PART%
    exit /b %ERRORLEVEL%
)

REM Check for WSL
WHERE wsl >nul 2>nul
IF NOT ERRORLEVEL 1 (
    echo 🔄 Found Windows Subsystem for Linux
    echo 🔄 Running bump-my-version through WSL...
    wsl ./bump_version.sh %VERSION_PART%
    exit /b %ERRORLEVEL%
)

REM Check for Git Bash
IF EXIST "%PROGRAMFILES%\Git\bin\bash.exe" (
    echo 🔄 Found Git Bash
    echo 🔄 Running bump-my-version through Git Bash...
    "%PROGRAMFILES%\Git\bin\bash.exe" -c "./bump_version.sh %VERSION_PART%"
    exit /b %ERRORLEVEL%
) ELSE IF EXIST "%PROGRAMFILES(x86)%\Git\bin\bash.exe" (
    echo 🔄 Found Git Bash
    echo 🔄 Running bump-my-version through Git Bash...
    "%PROGRAMFILES(x86)%\Git\bin\bash.exe" -c "./bump_version.sh %VERSION_PART%"
    exit /b %ERRORLEVEL%
)

REM Native Windows fallback
echo 🔄 No compatible Unix environment found. Attempting native Windows bump...
echo.

REM Check if Python is installed
WHERE python >nul 2>nul
IF ERRORLEVEL 1 (
    echo ❌ Python not found. Please install Python 3.9 or newer.
    exit /b 1
)

REM Check for virtual environment
IF EXIST ".venv\Scripts\activate.bat" (
    echo 🔄 Found virtual environment, activating...
    call .venv\Scripts\activate.bat
) ELSE (
    echo 🔄 Virtual environment not found.
    echo 🔄 Creating a new virtual environment...
    python -m venv .venv
    call .venv\Scripts\activate.bat
    
    echo 🔄 Installing dependencies...
    python -m pip install uv
)

REM Check if uv is available
WHERE uv >nul 2>nul
IF NOT ERRORLEVEL 1 (
    echo 🔄 Found uv, using it to run bump-my-version...
    uv tool install bump-my-version
    uv tool run bump-my-version bump %VERSION_PART% --commit --tag --allow-dirty
    
    REM Get the new version
    FOR /F "tokens=*" %%G IN ('uv tool run bump-my-version show current_version') DO (
        SET VERSION=%%G
    )
    
    echo ✅ Version bumped to: !VERSION!
    echo ℹ️ Remember to 'git push --follow-tags' to push the changes and the new tag.
    exit /b 0
)

REM Check for bump-my-version
WHERE bump-my-version >nul 2>nul
IF NOT ERRORLEVEL 1 (
    echo 🔄 Running bump-my-version directly...
    bump-my-version bump %VERSION_PART% --commit --tag --allow-dirty
    
    REM Get the new version
    FOR /F "tokens=*" %%G IN ('bump-my-version show current_version') DO (
        SET VERSION=%%G
    )
    
    echo ✅ Version bumped to: !VERSION!
    echo ℹ️ Remember to 'git push --follow-tags' to push the changes and the new tag.
    exit /b 0
)

REM If we get here, we need to install bump-my-version
echo 🔄 bump-my-version not found, installing...
pip install bump-my-version

REM Run bump-my-version
echo 🔄 Running bump-my-version...
bump-my-version bump %VERSION_PART% --commit --tag --allow-dirty

REM Get the new version from __init__.py
FOR /F "tokens=2 delims==" %%G IN ('type src\enchant_cli\__init__.py ^| findstr "__version__"') DO (
    SET VERSION=%%G
    SET VERSION=!VERSION:"=!
    SET VERSION=!VERSION: =!
)

echo ✅ Version bumped to: !VERSION!
echo ℹ️ Remember to 'git push --follow-tags' to push the changes and the new tag.

:END
ENDLOCAL