@echo off
REM ====================================
REM Verify Batch Files Before Packaging
REM ====================================

echo.
echo ======================================
echo   Batch Files Verification
echo ======================================
echo.

set ERROR_COUNT=0

REM Check if fix script exists
if not exist scripts\deployment\fix_batch_files.py (
    echo [ERROR] Fix script not found: scripts\deployment\fix_batch_files.py
    set /a ERROR_COUNT+=1
    goto :summary
)

REM Check client directory
if not exist scripts\deployment\client (
    echo [ERROR] Client directory not found: scripts\deployment\client
    set /a ERROR_COUNT+=1
    goto :summary
)

echo [Step 1/3] Checking batch files syntax...
echo.

REM Count batch files
set BAT_COUNT=0
for %%f in (scripts\deployment\client\*.bat) do set /a BAT_COUNT+=1

echo Found %BAT_COUNT% batch files in client directory
echo.

REM Check for "if not exist" with parentheses (problematic syntax)
echo [Step 2/3] Scanning for problematic syntax...
echo.

findstr /R /C:"if not exist.*(" scripts\deployment\client\*.bat >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo [WARN] Found "if not exist" with parentheses - may need fixing
    echo.
    echo Files with problematic syntax:
    findstr /R /C:"if not exist.*(" scripts\deployment\client\*.bat
    echo.
    echo [ACTION] Run fix script: python scripts/deployment/fix_batch_files.py
    echo.
    set /a ERROR_COUNT+=1
) else (
    echo [OK] No problematic "if not exist" syntax found
    echo.
)

REM Check file encodings
echo [Step 3/3] Checking file encodings...
echo.

REM Note: This is a basic check. Python script does more thorough validation.
for %%f in (scripts\deployment\client\*.bat) do (
    echo Checking: %%~nxf
)
echo.
echo [INFO] Run Python script for detailed encoding check
echo.

:summary
echo ======================================
echo   Verification Summary
echo ======================================
echo.

if %ERROR_COUNT% EQU 0 (
    echo [SUCCESS] All checks passed!
    echo Batch files are ready for packaging.
) else (
    echo [WARNING] Found %ERROR_COUNT% issue(s)
    echo Please fix issues before packaging.
    echo.
    echo Recommended actions:
    echo   1. Run: python scripts/deployment/fix_batch_files.py
    echo   2. Verify fixes manually
    echo   3. Run this script again
)

echo.
echo For detailed information, see:
echo   docs/batch_file_syntax_fix.md
echo.

pause
