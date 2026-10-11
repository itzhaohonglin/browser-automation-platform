@echo off
REM ====================================
REM Verify Build Output
REM ====================================

REM Switch to project root directory (works from any working directory)
cd /d "%~dp0..\.."

echo.
echo ======================================
echo   Verifying Build Output
echo ======================================
echo.

set BUILD_DIR=dist\browser-automation-platform

if not exist "%BUILD_DIR%" (
    echo [ERROR] Build directory not found: %BUILD_DIR%
    echo [INFO] Please run build_release.bat first
    pause
    exit /b 1
)

echo [Check 1/6] Main executable
if exist "%BUILD_DIR%\browser-automation-platform.exe" (
    echo [OK] browser-automation-platform.exe found
) else (
    echo [FAIL] Main executable not found
)

echo.
echo [Check 2/6] Configuration templates
if exist "%BUILD_DIR%\.env.template" (
    echo [OK] .env.template found
) else (
    echo [WARN] .env.template not found
)

if exist "%BUILD_DIR%\.env.example" (
    echo [OK] .env.example found
) else (
    echo [WARN] .env.example not found
)

echo.
echo [Check 3/6] Client scripts
if exist "%BUILD_DIR%\startup.bat" (
    echo [OK] startup.bat found
) else (
    echo [FAIL] startup.bat not found
)

if exist "%BUILD_DIR%\install.bat" (
    echo [OK] install.bat found
) else (
    echo [FAIL] install.bat not found
)

echo.
echo [Check 4/6] Documentation
if exist "%BUILD_DIR%\*.txt" (
    echo [OK] Documentation files found
) else (
    echo [WARN] No documentation files found
)

echo.
echo [Check 5/6] Directories
if exist "%BUILD_DIR%\_internal\static" (
    echo [OK] static directory found
) else (
    echo [FAIL] static directory not found
)

if exist "%BUILD_DIR%\_internal\alembic" (
    echo [OK] alembic directory found
) else (
    echo [FAIL] alembic directory not found
)

if exist "%BUILD_DIR%\auth_files" (
    echo [OK] auth_files directory found
) else (
    echo [WARN] auth_files directory not found
)

if exist "%BUILD_DIR%\logs" (
    echo [OK] logs directory found
) else (
    echo [WARN] logs directory not found
)

echo.
echo [Check 6/7] Playwright browser
if exist "%BUILD_DIR%\_internal\playwright\driver\package\.local-browsers\chromium-*\chrome-win\chrome.exe" (
    echo [OK] Chromium browser bundled
) else (
    echo [FAIL] Chromium browser not bundled
    echo [INFO] Run: browser-automation-platform.exe --install-browser
)

echo.
echo [Check 7/7] File sizes
for %%F in ("%BUILD_DIR%\browser-automation-platform.exe") do (
    echo Main executable: %%~zF bytes
)

echo.
echo ======================================
echo   Verification Complete
echo ======================================
echo.
echo Output directory: %BUILD_DIR%
echo.
echo Next steps:
echo   1. If all checks OK, test run: cd %BUILD_DIR% ^&^& startup.bat
echo   2. Package for distribution: compress the directory
echo.

pause
