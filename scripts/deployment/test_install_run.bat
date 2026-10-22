@echo off
REM Test install.bat in isolated environment

echo Creating test environment...
mkdir test_install 2>nul
cd test_install

REM Copy install.bat
copy ..\scripts\deployment\client\install.bat . >nul

REM Create dummy files to pass checks
echo dummy > browser-automation-platform.exe
echo dummy > .env.example

echo.
echo ======================================
echo Running install.bat...
echo ======================================
echo.

REM Run install.bat
call install.bat

echo.
echo ======================================
echo Test completed
echo ======================================
