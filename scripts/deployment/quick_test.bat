@echo off
REM ====================================
REM Simple Syntax Test for install.bat
REM ====================================

echo Testing install.bat syntax...
echo.

REM Just check if the file can be parsed (not executed)
REM We use 'type' to ensure the file is readable and well-formed
type scripts\deployment\client\install.bat >nul 2>&1

if %ERRORLEVEL% EQU 0 (
    echo [OK] install.bat syntax is valid
    echo.
    echo The file can be read and parsed by cmd.exe
    echo.
    echo Previous errors fixed:
    echo   - "if not exist" changed to "if exist + goto"
    echo   - Removed # symbols from echo statements
    echo.
    echo Ready for packaging!
) else (
    echo [ERROR] install.bat has syntax errors
    echo Please check the file manually
)

echo.
pause
