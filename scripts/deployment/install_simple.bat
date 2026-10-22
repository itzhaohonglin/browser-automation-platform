@echo off
REM Simplified version to isolate the issue

echo.
echo ======================================
echo   Browser Automation Platform
echo   Installation Test
echo ======================================
echo.

REM Test 1: Basic check
echo [Test 1] Checking for executable...
if exist browser-automation-platform.exe goto :check_ok
echo [ERROR] Main program not found
pause
exit /b 1
:check_ok
echo [OK] Executable found
echo.

REM Test 2: Check for .env
echo [Test 2] Checking for config file...
if exist .env (
    echo [OK] Config file exists
    goto :step2
)

if exist .env.example (
    copy .env.example .env >nul
    echo [OK] Config file created from template
) else (
    echo [ERROR] Config template not found
    pause
    exit /b 1
)

echo.
echo [Info] Configuration examples:
echo.
echo    DATABASE_URL=mssql+aioodbc://sa:Pass@localhost:1433/bap?driver=ODBC+Driver+17+for+SQL+Server^&charset=UTF-8
echo.
echo    MAX_WORKERS=3
echo    RATE_LIMIT_ENABLED=true
echo    RETRY_MIN_WAIT_MINUTES=60
echo.

:step2
echo.
echo [Test 3] Testing choice command...
choice /C YN /M "Continue with test"
if errorlevel 2 (
    echo You chose No
    goto :finish
)
echo You chose Yes
echo.

:finish
echo.
echo ======================================
echo   Test Complete
echo ======================================
echo.
echo If this script runs without errors,
echo then the issue is in a specific part
echo of the full install.bat
echo.
pause
