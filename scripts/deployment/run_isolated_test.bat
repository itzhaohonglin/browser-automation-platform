@echo off
REM Create isolated test environment and run install.bat

echo Creating test environment...
echo.

REM Create test directory
if exist test_env rmdir /s /q test_env
mkdir test_env
cd test_env

REM Copy install.bat
copy ..\client\install.bat . >nul

REM Create dummy files
echo dummy > browser-automation-platform.exe
echo dummy > .env.example

REM Create a response file for automation
echo Y > responses.txt
echo Y >> responses.txt
echo N >> responses.txt

echo.
echo Test environment created
echo.
echo ======================================
echo Running install.bat...
echo ======================================
echo.

REM Run install.bat with automated responses
type responses.txt | install.bat > output.log 2>&1

echo.
echo ======================================
echo Execution completed
echo ======================================
echo.

REM Show output
echo Output from install.bat:
echo.
type output.log

echo.
echo.
echo Check output.log in test_env directory for details
echo.

cd ..
pause
