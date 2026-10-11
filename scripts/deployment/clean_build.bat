@echo off
REM ====================================
REM Clean Build Directories
REM ====================================

REM Switch to project root directory (works from any working directory)
cd /d "%~dp0..\.."

echo.
echo ======================================
echo   Cleaning Build Directories
echo ======================================
echo.

REM Kill any running instances
echo [1/3] Stopping any running instances...
taskkill /F /IM browser-automation-platform.exe >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] Stopped running instance
    timeout /t 2 /nobreak >nul
) else (
    echo [OK] No running instance found
)

REM Remove build directory
echo [2/3] Removing build directory...
if exist build (
    rmdir /s /q build
    if %errorlevel% equ 0 (
        echo [OK] Build directory removed
    ) else (
        echo [WARN] Could not remove build directory
    )
) else (
    echo [OK] Build directory does not exist
)

REM Remove dist directory
echo [3/3] Removing dist directory...
if exist dist (
    rmdir /s /q dist
    if %errorlevel% equ 0 (
        echo [OK] Dist directory removed
    ) else (
        echo [ERROR] Could not remove dist directory
        echo.
        echo Possible causes:
        echo   - File Explorer is open in that directory
        echo   - A program is using files in that directory
        echo   - Command prompt is in that directory
        echo.
        echo Please:
        echo   1. Close File Explorer windows in dist/
        echo   2. Close any programs using files in dist/
        echo   3. Run this script again
        echo.
        pause
        exit /b 1
    )
) else (
    echo [OK] Dist directory does not exist
)

echo.
echo ======================================
echo   Cleanup Complete!
echo ======================================
echo.
echo You can now run build_release.bat
echo.

pause
