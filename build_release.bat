@echo off
REM ====================================
REM Build Release - Shortcut Script
REM ====================================
REM This is a shortcut to the actual build script

echo Launching build script...
call scripts\deployment\build_release.bat %*
