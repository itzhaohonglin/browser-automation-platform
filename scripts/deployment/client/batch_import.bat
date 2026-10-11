@echo off
REM ====================================
REM Batch Import Jobs from File
REM ====================================

echo.
echo ======================================
echo   Batch Import Jobs
echo ======================================
echo.

REM Check if main executable exists
if not exist browser-automation-platform.exe (
    echo [ERROR] Main program not found
    echo [INFO] Please run this script in the installation directory
    pause
    exit /b 1
)

REM Check config file
if not exist .env (
    echo [ERROR] Config file .env not found
    echo [INFO] Please run install.bat first
    pause
    exit /b 1
)

REM Check if import data directory exists
if not exist import_data mkdir import_data

echo This script imports tasks from a text or CSV file.
echo.
echo Supported formats:
echo   - Text (.txt): one registration number per line
echo   - CSV (.csv): one registration number per line
echo.
echo File location: import_data\
echo.
echo Example file content (import_data\jobs.txt):
echo   滇械注准20192140008
echo   京械注准20210001234
echo   沪械注准20200005678
echo.
echo Lines starting with # are ignored.
echo.
pause

REM List available files
echo.
echo Available import files:
echo.
dir /b import_data\*.txt import_data\*.csv 2>nul
if errorlevel 1 (
    echo [INFO] No import files found in import_data\ directory
    echo.
    echo Please:
    echo   1. Create a TXT or CSV file (one registration number per line)
    echo   2. Place it in the import_data\ directory
    echo   3. Run this script again
    echo.
    pause
    exit /b 0
)

echo.
set /p FILENAME="Enter filename (without path): "

if not exist "import_data\%FILENAME%" (
    echo [ERROR] File not found: import_data\%FILENAME%
    pause
    exit /b 1
)

echo.
echo [RUN] Importing jobs from import_data\%FILENAME%...
echo.

REM Run batch import via main program
"%~dp0browser-automation-platform.exe" --import-jobs "import_data\%FILENAME%"
if errorlevel 1 (
    echo.
    echo [ERROR] Import failed
    echo.
    echo Please check:
    echo   1. File format is correct (one registration number per line)
    echo   2. The NHSA config is initialized (run init_config.bat)
    echo   3. Database connection is correct in .env
    echo.
    pause
    exit /b 1
)

echo.
echo ======================================
echo   Import Complete!
echo ======================================
echo.
echo You can now:
echo   1. Start the service: startup.bat
echo   2. View tasks in dashboard: http://127.0.0.1:8000/static/index.html
echo   3. Tasks will be executed automatically
echo.

pause
