@echo off
REM ====================================
REM Build Release Package Script
REM ====================================

REM Switch to project root directory (works from any working directory)
cd /d "%~dp0..\.."

echo.
echo ======================================
echo   Browser Automation Platform
echo   Release Build Tool
echo ======================================
echo.

REM Select Python interpreter: prefer the project venv (contains all project dependencies)
set "PYTHON=python"
if exist ".venv\python.exe" set "PYTHON=.venv\python.exe"
if exist ".venv\Scripts\python.exe" set "PYTHON=.venv\Scripts\python.exe"

echo Using Python: %PYTHON%

%PYTHON% --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found
    echo Please install Python 3.10 or higher
    pause
    exit /b 1
)

REM Verify project dependencies are installed in the selected Python
%PYTHON% -c "import fastapi, playwright, sqlalchemy" >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Project dependencies not found: fastapi / playwright / sqlalchemy
    echo [ERROR] The selected Python does not have the project packages installed
    echo [INFO] Install them with: %PYTHON% -m pip install -r requirements.txt
    pause
    exit /b 1
)

REM Check PyInstaller
%PYTHON% -m pip show pyinstaller >nul 2>&1
if errorlevel 1 (
    echo [INFO] Installing PyInstaller...
    %PYTHON% -m pip install pyinstaller
    if errorlevel 1 (
        echo [ERROR] PyInstaller installation failed
        pause
        exit /b 1
    )
)

REM Check pyinstaller-hooks-contrib (required to bundle the Playwright node driver)
%PYTHON% -m pip show pyinstaller-hooks-contrib >nul 2>&1
if errorlevel 1 (
    echo [INFO] Installing pyinstaller-hooks-contrib...
    %PYTHON% -m pip install pyinstaller-hooks-contrib
    if errorlevel 1 (
        echo [ERROR] pyinstaller-hooks-contrib installation failed
        pause
        exit /b 1
    )
)

REM Clean old builds
echo [1/5] Cleaning old build files...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

REM Build executable
echo [2/6] Building application...
%PYTHON% -m PyInstaller build.spec
if errorlevel 1 (
    echo [ERROR] Build failed
    pause
    exit /b 1
)

REM Bundle Playwright browsers
REM Playwright detects PyInstaller frozen mode and sets PLAYWRIGHT_BROWSERS_PATH=0,
REM which resolves browsers to driver/package/.local-browsers inside the bundle.
echo [3/6] Bundling Playwright Chromium browser...
set "MS_PLAYWRIGHT=%LOCALAPPDATA%\ms-playwright"
set "PW_BROWSERS=dist\browser-automation-platform\_internal\playwright\driver\package\.local-browsers"

if exist "%MS_PLAYWRIGHT%" (
    for /d %%B in ("%MS_PLAYWRIGHT%\chromium-*") do (
        if exist "%%B" (
            echo [INFO] Copying %%~nxB ...
            robocopy "%%B" "%PW_BROWSERS%\%%~nxB" /E /NFL /NDL /NJH /NJS /NP >nul
            if errorlevel 8 (
                echo [ERROR] Failed to copy %%~nxB
                pause
                exit /b 1
            )
        )
    )
) else (
    echo [WARN] Playwright browsers not found at %MS_PLAYWRIGHT%
    echo [WARN] Install them with: %PYTHON% -m playwright install chromium
    echo [WARN] Client machines without bundled browser can run: browser-automation-platform.exe --install-browser
)

REM Create directories
echo [4/6] Creating directory structure...
if not exist "dist\browser-automation-platform\auth_files" mkdir "dist\browser-automation-platform\auth_files"
if not exist "dist\browser-automation-platform\logs" mkdir "dist\browser-automation-platform\logs"

REM Copy client scripts
echo [5/6] Copying client scripts...
copy "scripts\deployment\client\*.bat" "dist\browser-automation-platform\" >nul
copy "scripts\deployment\client\*.txt" "dist\browser-automation-platform\" >nul

REM Create import_data directory with README
if not exist "dist\browser-automation-platform\import_data" mkdir "dist\browser-automation-platform\import_data"
copy "scripts\deployment\client\import_data_README.txt" "dist\browser-automation-platform\import_data\README.txt" >nul

REM Copy config template (use Python to preserve UTF-8 encoding)
echo [INFO] Copying configuration template...
if exist .env.example (
    %PYTHON% scripts\deployment\copy_utf8_file.py .env.example dist\browser-automation-platform\.env.example
    if errorlevel 1 (
        echo [ERROR] Failed to copy .env.example
        pause
        exit /b 1
    )
    echo [OK] Configuration template copied successfully
) else (
    echo [ERROR] .env.example not found in project root
    pause
    exit /b 1
)

REM Verify config template exists in output
if not exist "dist\browser-automation-platform\.env.example" (
    echo [ERROR] Configuration template not found in output directory!
    pause
    exit /b 1
)

REM Create version info
echo [6/6] Generating version info...
echo Browser Automation Platform v1.0.0 > "dist\browser-automation-platform\VERSION.txt"
echo Build Time: %date% %time% >> "dist\browser-automation-platform\VERSION.txt"
echo Build Host: %COMPUTERNAME% >> "dist\browser-automation-platform\VERSION.txt"

echo.
echo ======================================
echo   Build Complete!
echo ======================================
echo.
echo Output: dist\browser-automation-platform\
echo.
echo Next Steps:
echo 1. Test: cd dist\browser-automation-platform ^&^& startup.bat
echo 2. Package: Compress the directory and send to client
echo.

pause
