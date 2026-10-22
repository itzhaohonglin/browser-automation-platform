@echo off
REM ====================================
REM Initialize Configuration Data
REM ====================================

echo.
echo ======================================
echo   Configuration Initialization
echo ======================================
echo.

REM Check if main executable exists
if exist browser-automation-platform.exe goto :check_ok_1
    echo [ERROR] Main program not found
    echo [INFO] Please run this script in the installation directory
    pause
    exit /b 1
:check_ok_1

REM Check config file
if exist .env goto :check_ok_2
    echo [ERROR] Config file .env not found
    echo [INFO] Please run install.bat first
    pause
    exit /b 1
:check_ok_2

echo This script will initialize sample configurations to help you get started.
echo.
echo Sample configurations included:
echo   1. NHSA Medical Device Query (Registration Number)
echo   2. Basic web scraping template
echo.
choice /C YN /M "Initialize sample configurations"
if errorlevel 2 (
    echo Operation cancelled
    pause
    exit /b 0
)

echo.
echo [RUN] Initializing configurations...
echo.

REM Run initialization via main program
"%~dp0browser-automation-platform.exe" --init-config
if errorlevel 1 (
    echo.
    echo [ERROR] Configuration initialization failed
    echo.
    echo Please check:
    echo   1. Database is initialized (run init_database.bat)
    echo   2. Database connection is correct in .env
    echo.
    pause
    exit /b 1
)

echo.
echo ======================================
echo   Initialization Complete!
echo ======================================
echo.
echo You can now:
echo   1. Start the service: startup.bat
echo   2. Visit dashboard: http://127.0.0.1:8000/static/index.html
echo   3. Create tasks using the web interface
echo.

pause
