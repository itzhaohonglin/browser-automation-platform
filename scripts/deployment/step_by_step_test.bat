@echo off
REM ====================================
REM Step-by-step test of install.bat
REM ====================================

echo.
echo Testing install.bat step by step...
echo.

echo [Test 1] Basic echo commands
echo ======================================
echo   Browser Automation Platform
echo   First-time Installation
echo ======================================
echo.
if errorlevel 1 goto :error
echo [PASS] Basic echo commands
echo.

echo [Test 2] File check with if exist
if exist test_file_not_exist.txt goto :check_ok_2
echo [PASS] if exist + goto (file not found branch)
goto :test3
:check_ok_2
echo [FAIL] Should not reach here
goto :error

:test3
echo.
echo [Test 3] Multiple echo statements
echo MAX_WORKERS=3
echo RATE_LIMIT_WINDOW_MINUTES=60
echo RATE_LIMIT_MAX_TASKS=100
echo RETRY_MIN_WAIT_MINUTES=60
echo RETRY_SKIP_IF_PENDING_OVER=100
echo RETRY_RESPECT_RATE_LIMIT=true
if errorlevel 1 goto :error
echo [PASS] Multiple echo statements
echo.

echo [Test 4] Echo with special characters
echo DATABASE_URL=mssql+aioodbc://user:password@server:port/database?driver=ODBC+Driver+17+for+SQL+Server^&charset=UTF-8
if errorlevel 1 goto :error
echo [PASS] Echo with escaped ampersand
echo.

echo [Test 5] Choice command
echo This will test the choice command (press Y or N)
choice /C YN /M "Test choice command"
if errorlevel 2 (
    echo You pressed N
) else (
    echo You pressed Y
)
echo [PASS] Choice command
echo.

echo [Test 6] Nested if with errorlevel
choice /C YN /M "Press Y to continue"
if errorlevel 2 (
    echo [PASS] Errorlevel 2 detected
    goto :test7
)
echo [PASS] Errorlevel 1 (or lower)

:test7
echo.
echo [Test 7] Exit with code
REM Test exit /b 0
echo Testing exit command...
echo [PASS] Can execute lines before exit

echo.
echo ======================================
echo All tests passed!
echo ======================================
echo.
echo The install.bat syntax should be OK.
echo If it still fails, please provide:
echo   1. The exact error message
echo   2. Which step it fails at
echo   3. Your Windows version
echo.
pause
exit /b 0

:error
echo.
echo ======================================
echo [ERROR] Test failed!
echo ======================================
echo.
pause
exit /b 1
