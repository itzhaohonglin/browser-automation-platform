@echo off
REM ====================================
REM Diagnose install.bat issue
REM ====================================

echo.
echo ======================================
echo   Diagnostic Tool
echo ======================================
echo.

echo [1] Checking Windows version...
ver
echo.

echo [2] Checking current directory...
cd
echo.

echo [3] Checking if files exist...
if exist browser-automation-platform.exe (
    echo [OK] browser-automation-platform.exe found
) else (
    echo [WARN] browser-automation-platform.exe NOT found
)

if exist .env.example (
    echo [OK] .env.example found
) else (
    echo [WARN] .env.example NOT found
)

if exist install.bat (
    echo [OK] install.bat found
) else (
    echo [WARN] install.bat NOT found
)
echo.

echo [4] Checking install.bat encoding...
for %%F in (install.bat) do echo File size: %%~zF bytes
echo.

echo [5] Testing simple batch commands...
echo Testing echo command...
echo This is a test
echo.

echo Testing if exist...
if exist install.bat (
    echo [OK] if exist works
)
echo.

echo Testing if not exist...
if not exist nonexistent_file.txt (
    echo [OK] if not exist works
)
echo.

echo [6] Testing problematic syntax from install.bat...
echo Testing: if not exist browser-automation-platform.exe
if not exist browser-automation-platform123.exe (
    echo [OK] This syntax works in your environment
) else (
    echo [FAIL] This syntax has issues
)
echo.

echo [7] Testing echo with brackets...
echo [ERROR] Test message with brackets
echo.

echo [8] Testing echo with not...
echo ERROR: File not found
echo.

echo ======================================
echo   Diagnostic Complete
echo ======================================
echo.
echo If you see errors above, please report:
echo   1. Which test failed
echo   2. The exact error message
echo   3. Your Windows version
echo.

pause
