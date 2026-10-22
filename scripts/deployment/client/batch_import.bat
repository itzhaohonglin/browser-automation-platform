@echo off
echo.
echo ======================================
echo   Batch Import Jobs
echo ======================================
echo.

REM Check if we are in the correct directory
if exist browser-automation-platform.exe goto :check_ok_1
    echo [ERROR] Please run this script in the dist\browser-automation-platform directory
    pause
    exit /b 1
:check_ok_1

REM Check config
if exist .env goto :check_ok_2
    echo [ERROR] Config file .env not found. Please run install.bat first.
    pause
    exit /b 1
:check_ok_2

REM Create import_data directory if not exists
if not exist import_data mkdir import_data

echo Available import files in import_data\:
echo.

REM List files - use simple dir command
dir /b import_data\*.txt 2>nul
dir /b import_data\*.csv 2>nul

echo.
set /p FILENAME="Enter filename (e.g., jobs.txt): "

if "%FILENAME%"=="" (
    echo [ERROR] No filename entered
    pause
    exit /b 1
)

if exist "import_data\%FILENAME%" goto :check_ok_3
    echo [ERROR] File not found: import_data\%FILENAME%
    pause
    exit /b 1
:check_ok_3

echo.
echo [INFO] Importing from: import_data\%FILENAME%
echo.

REM Run import
"%~dp0browser-automation-platform.exe" --import-jobs "import_data\%FILENAME%"

if errorlevel 1 (
    echo.
    echo [ERROR] Import failed. Check the error message above.
    echo.
    echo Common issues:
    echo   1. NHSA config not initialized - run init_config.bat
    echo   2. Database connection issue - check .env file
    echo   3. File format issue - one registration number per line
    echo.
    pause
    exit /b 1
)

echo.
echo ======================================
echo   Import Complete!
======================================
echo.
echo Next steps:
echo   1. Run startup.bat to start the service
echo   2. Open http://127.0.0.1:8000/static/index.html
echo   3. Tasks will execute automatically
echo.

pause
