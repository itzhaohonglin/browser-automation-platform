@echo off
REM ====================================
REM Configuration Validation Tool
REM ====================================

echo.
echo ======================================
echo   Configuration Validation Tool
echo ======================================
echo.

REM 1. Check config file
echo [Check 1/5] Config File
if exist .env (
    echo [OK] Config file exists
) else (
    echo [FAIL] Config file not found
    echo [INFO] Please run install.bat first
    pause
    exit /b 1
)
echo.

REM 2. Check database config
echo [Check 2/5] Database Configuration
findstr /i "DATABASE_URL" .env >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] Database configuration found

    REM Check if still using default password
    findstr /i "YourPassword" .env >nul 2>&1
    if %errorlevel% equ 0 (
        echo [WARN] Database password is still default, please modify
    )
) else (
    echo [FAIL] Database configuration not found
)
echo.

REM 3. Check port config
echo [Check 3/5] Port Configuration
findstr /i "APP_PORT" .env >nul 2>&1
if %errorlevel% equ 0 (
    for /f "tokens=2 delims==" %%a in ('findstr /i "^APP_PORT" .env') do (
        echo [OK] Port configured: %%a
        set PORT=%%a
    )
) else (
    echo [OK] Using default port: 8000
    set PORT=8000
)

REM Check if port is in use
netstat -ano | findstr ":%PORT%" >nul 2>&1
if %errorlevel% equ 0 (
    echo [WARN] Port %PORT% is already in use
    echo [INFO] Please modify APP_PORT in .env to another port
) else (
    echo [OK] Port %PORT% is available
)
echo.

REM 4. Check browser driver
echo [Check 4/5] Browser Driver
if exist "%USERPROFILE%\AppData\Local\ms-playwright\chromium-*" (
    echo [OK] Browser driver installed
) else (
    echo [FAIL] Browser driver not installed
    echo [INFO] Please run install_browser.bat
)
echo.

REM 5. Check directory structure
echo [Check 5/5] Directory Structure
if exist auth_files\ (
    echo [OK] auth_files directory exists
) else (
    echo [WARN] auth_files directory missing
    mkdir auth_files
    echo [OK] Created automatically
)

if exist logs\ (
    echo [OK] logs directory exists
) else (
    echo [WARN] logs directory missing
    mkdir logs
    echo [OK] Created automatically
)

if exist _internal\ (
    echo [OK] Program files directory exists
) else (
    echo [FAIL] Program files directory missing (critical error)
)
echo.

REM Summary
echo ======================================
echo   Check Complete
echo ======================================
echo.
echo Next Steps:
echo   1. Fix any warnings or errors above
echo   2. Run startup.bat after confirming all OK
echo   3. Visit http://127.0.0.1:%PORT%/static/index.html
echo.

pause
