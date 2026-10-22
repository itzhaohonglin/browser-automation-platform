@echo off
REM ====================================
REM Test Batch File Syntax
REM ====================================

echo Testing batch file syntax...
echo.

REM Test 1: Simple if exist
if exist test_bat_syntax.bat (
    echo [PASS] Test 1: if exist works
) else (
    echo [FAIL] Test 1: if exist failed
)

REM Test 2: if not exist using goto style (recommended)
if exist nonexistent_file.txt goto :test2_fail
echo [PASS] Test 2: if exist + goto works
goto :test3
:test2_fail
echo [FAIL] Test 2: if exist + goto failed

:test3
REM Test 3: errorlevel check
echo test > temp_test.txt
if errorlevel 0 (
    echo [PASS] Test 3: errorlevel works
) else (
    echo [FAIL] Test 3: errorlevel failed
)
del temp_test.txt >nul 2>&1

echo.
echo All syntax tests completed!
echo.
pause
