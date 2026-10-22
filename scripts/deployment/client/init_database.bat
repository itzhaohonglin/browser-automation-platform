@echo off
REM ====================================
REM Initialize Database
REM ====================================

echo.
echo ======================================
echo   Database Initialization
echo ======================================
echo.

REM Check main executable
if exist browser-automation-platform.exe goto :check_ok_1
    echo [ERROR] Main program not found
    echo [INFO] Please run this script in the installation directory
    pause
    exit /b 1
:check_ok_1

REM Check config file
if exist .env goto :check_ok_2
    echo [ERROR] Config file .env not found
    echo [INFO] Please run install.bat first
    pause
    exit /b 1
:check_ok_2

echo [INFO] Will execute database migration to create all tables
echo.
choice /C YN /M "Continue"
if errorlevel 2 (
    echo Operation cancelled
    pause
    exit /b 0
)

echo.
echo [RUN] Executing database migration...
echo.

"%~dp0browser-automation-platform.exe" --migrate
if errorlevel 1 (
    echo.
    echo [ERROR] Database migration failed
    echo.
    echo Please check:
    echo   1. SQL Server service is running
    echo   2. Database connection in .env is correct
    echo   3. Database is created
    echo.
    echo Database creation command (run in SQL Server):
    echo CREATE DATABASE bap COLLATE Chinese_PRC_CI_AS;
    echo.
    pause
    exit /b 1
)

echo.
echo ======================================
echo   Database Initialized!
echo ======================================
echo.

pause
