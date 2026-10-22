@echo off
REM Minimal test version of install.bat

echo Testing syntax...
echo.

REM Test 1: if exist goto
if exist test_file.txt goto :check_ok
echo File not found is OK
goto :step2
:check_ok
echo File found

:step2
echo.
echo Test 2: Echo statements
echo MAX_WORKERS=3
echo RATE_LIMIT_WINDOW_MINUTES=60
echo RETRY_MIN_WAIT_MINUTES=60

echo.
echo Test 3: Choice command
choice /C YN /M "Continue"
if errorlevel 2 (
    echo You selected No
    goto :finish
)
echo You selected Yes

:finish
echo.
echo All tests completed
pause
