@echo off
REM ====================================
REM Installation Script
REM ====================================

echo.
echo ======================================
echo   Browser Automation Platform
echo   First-time Installation
echo ======================================
echo.

REM Check main executable
if not exist browser-automation-platform.exe (
    echo [ERROR] Main program not found
    echo [INFO] Please run this script in the installation directory
    pause
    exit /b 1
)

REM Step 1: Configure environment
echo [Step 1/3] Configure Database and Port
echo.
if exist .env (
    echo [SKIP] Config file .env already exists, keeping current configuration
    echo.
    goto :step2
)

if exist .env.template (
    copy .env.template .env >nul
    echo [DONE] Config file created: .env
    echo.
) else if exist .env.example (
    copy .env.example .env >nul
    echo [DONE] Config file created: .env
    echo.
) else (
    echo [ERROR] Config template not found
    pause
    exit /b 1
)

echo [IMPORTANT] Please configure the following:
echo.
echo 1. Open .env file in current directory
echo 2. Modify these settings:
echo.
echo    ===== Required Configuration =====
echo.
echo    [Database] (Required - IMPORTANT: Add charset=UTF-8 for Chinese support)
echo    DATABASE_URL=mssql+aioodbc://user:password@server:port/database?driver=ODBC+Driver+17+for+SQL+Server^&charset=UTF-8
echo.
echo    Example:
echo    DATABASE_URL=mssql+aioodbc://sa:MyPassword@localhost:1433/bap?driver=ODBC+Driver+17+for+SQL+Server^&charset=UTF-8
echo.
echo    ===== Optional Configuration =====
echo.
echo    [Port] (Optional, default 8000)
echo    APP_PORT=8000
echo    After port change, access: http://127.0.0.1:NewPort/static/index.html
echo.
echo    [Concurrency] (Optional, default 3)
echo    MAX_WORKERS=3  # Number of concurrent tasks
echo.
echo    [Rate Limiting] (Optional but RECOMMENDED for target sites with restrictions)
echo    RATE_LIMIT_ENABLED=true
echo    RATE_LIMIT_WINDOW_MINUTES=60  # Time window in minutes
echo    RATE_LIMIT_MAX_TASKS=100      # Max tasks per window
echo.
echo    Example: 100 tasks per hour to avoid being blocked
echo.
echo    [Smart Retry] (Optional, optimizes retry behavior)
echo    RETRY_MIN_WAIT_MINUTES=60           # Min wait before retry
echo    RETRY_SKIP_IF_PENDING_OVER=100      # Skip retry if too many pending
echo    RETRY_RESPECT_RATE_LIMIT=true       # Respect rate limit when retrying
echo.
echo    For detailed configuration guide, see:
echo    - docs/env_config_update.md
echo    - docs/rate_limit_guide.md
echo.
choice /C YN /M "Configuration completed"
if errorlevel 2 (
    echo.
    echo [INFO] Please complete configuration and run this script again
    pause
    exit /b 0
)

:step2

REM Step 2: Install browser driver
echo.
echo [Step 2/3] Install Browser Driver
echo.
echo [INFO] Need to download about 300MB Chromium browser
echo [INFO] Only required for first installation
echo.
choice /C YN /M "Install now"
if errorlevel 2 (
    echo.
    echo [SKIP] Browser driver installation
    echo [INFO] You can run install_browser.bat later
    goto :init_database
)

echo.
echo [INSTALL] Downloading browser driver, please wait...
"%~dp0browser-automation-platform.exe" --install-browser
if errorlevel 1 (
    echo [ERROR] Browser driver installation failed
    echo [INFO] Please check network connection and retry
    pause
    exit /b 1
)
echo [DONE] Browser driver installed successfully
echo.

:init_database
REM Step 3: Initialize database
echo [Step 3/3] Initialize Database
echo.
echo [INFO] Will create database tables
echo.
choice /C YN /M "Initialize now"
if errorlevel 2 (
    echo.
    echo [SKIP] Database initialization
    echo [INFO] You can run init_database.bat later
    goto :finish
)

echo.
echo [RUN] Initializing database...
"%~dp0browser-automation-platform.exe" --migrate
if errorlevel 1 (
    echo [ERROR] Database initialization failed
    echo [INFO] Please check:
    echo   1. SQL Server service is running
    echo   2. Database connection in .env is correct
    echo   3. Database bap is created
    echo.
    pause
    exit /b 1
)
echo [DONE] Database initialized successfully
echo.

:finish
REM Installation complete
echo.
echo ======================================
echo   Installation Complete!
echo ======================================
echo.
echo Next Steps:
echo   1. Run startup.bat to start service
echo   2. Visit http://127.0.0.1:PORT/static/index.html
echo   3. Read usage guide in Help.txt
echo.
echo Available Scripts:
echo   - startup.bat: Start service
echo   - init_config.bat: Initialize sample config
echo   - install_browser.bat: Install browser driver
echo   - init_database.bat: Initialize database
echo.

pause
