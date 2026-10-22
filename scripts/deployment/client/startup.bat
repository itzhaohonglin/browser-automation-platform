@echo off
REM ====================================
REM Startup Script
REM ====================================

echo.
echo ======================================
echo   Starting Browser Automation Platform
echo ======================================
echo.

REM Check config file
if exist .env goto :check_ok_1
    echo [WARN] Config file .env not found
    echo Creating from template...
    if exist .env.example (
        copy .env.example .env >nul
        echo [INFO] Config file created: .env
        echo [INFO] Please edit .env to configure database and port
        echo.
        echo Main settings:
        echo   - DATABASE_URL: Database connection string
        echo   - APP_PORT: Service port (default 8000)
        echo.
        pause
        exit /b 1
    ) else (
        echo [ERROR] Config template (.env.example) not found
        pause
        exit /b 1
    )
:check_ok_1

REM Note: Browser driver installation
echo [INFO] Note: First run requires Playwright browser driver
echo [INFO] If program fails to start, run install_browser.bat first
echo.

REM Start application
echo [START] Starting service...
echo.

REM Read port from config
set PORT=8000
for /f "tokens=2 delims==" %%a in ('findstr /i "^APP_PORT" .env 2^>nul') do set PORT=%%a

echo ======================================
echo   Service Started
echo ======================================
echo.
echo Access URLs:
echo   - Dashboard: http://127.0.0.1:%PORT%/static/index.html
echo   - API Docs: http://127.0.0.1:%PORT%/docs
echo.
echo Press Ctrl+C to stop
echo ======================================
echo.

REM Start main program
"%~dp0browser-automation-platform.exe"

pause
