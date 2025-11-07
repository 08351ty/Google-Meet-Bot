@echo off
REM Script to start Chrome with remote debugging enabled using your existing profile
REM This script will automatically detect your Chrome installation and profile directory

set DEBUG_PORT=9222

REM Try to find Chrome executable
set CHROME_PATH=
if exist "C:\Program Files\Google\Chrome\Application\chrome.exe" (
    set CHROME_PATH=C:\Program Files\Google\Chrome\Application\chrome.exe
) else if exist "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe" (
    set CHROME_PATH=C:\Program Files (x86)\Google\Chrome\Application\chrome.exe
)

if "%CHROME_PATH%"=="" (
    echo ERROR: Chrome executable not found!
    echo Please set CHROME_PATH environment variable or install Chrome.
    pause
    exit /b 1
)

REM Get user profile directory
set USER_PROFILE=%USERPROFILE%
set USER_DATA_DIR=%USER_PROFILE%\AppData\Local\Google\Chrome\User Data

echo Starting Chrome with remote debugging on port %DEBUG_PORT%...
echo Using profile: %USER_DATA_DIR%
echo.

REM Start Chrome with remote debugging
"%CHROME_PATH%" --remote-debugging-port=%DEBUG_PORT% --user-data-dir="%USER_DATA_DIR%"

