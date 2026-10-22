@echo off
REM ====================================
REM Install Browser Driver
REM ====================================

echo.
echo ======================================
echo   Install Browser Driver
echo ======================================
echo.

REM Check main executable
if exist browser-automation-platform.exe goto :check_ok_1
    echo [ERROR] Main program not found
    echo [INFO] Please run this script in the installation directory
    pause
    exit /b 1
:check_ok_1

REM Ensure config file exists (required by the main program)
if exist .env goto :check_ok_2
    if exist .env.example (
        copy .env.example .env >nul
    )
:check_ok_2

echo [INFO] Will download about 300MB Chromium browser
echo [INFO] Download speed depends on your network
echo.

choice /C YN /M "Continue"
if errorlevel 2 (
    echo Installation cancelled
    pause
    exit /b 0
)

echo.
echo [DOWNLOAD] Downloading and installing browser driver...
echo.

"%~dp0browser-automation-platform.exe" --install-browser
if errorlevel 1 (
    echo.
    echo [ERROR] Installation failed
    echo.
    echo Possible reasons:
    echo   1. Network connection issues
    echo   2. Firewall blocking
    echo   3. Insufficient disk space
    echo.
    echo Solutions:
    echo   1. Check network connection
    echo   2. Disable firewall/antivirus temporarily
    echo   3. Ensure at least 500MB free disk space
    echo.
    pause
    exit /b 1
)

echo.
echo ======================================
echo   Installation Complete!
echo ======================================
echo.

pause
