@echo off
chcp 65001 >nul
echo ========================================
echo 添加自动重新执行配置到 .env.example
echo ========================================
echo.

REM 检查文件是否存在
if not exist ".env.example" (
    echo [错误] .env.example 文件不存在
    pause
    exit /b 1
)

echo [检查] 检查 .env.example 是否包含 AUTO_RECREATE 配置...
findstr /C:"AUTO_RECREATE_SUCCESS_JOBS" ".env.example" >nul 2>&1

if %errorlevel% equ 0 (
    echo [成功] 配置已存在
    echo.
    echo 当前配置：
    findstr "AUTO_RECREATE" ".env.example"
    echo.
    echo ========================================
    echo 配置已经存在，无需添加
    echo ========================================
) else (
    echo [警告] 配置不存在，正在添加...
    echo.

    REM 添加配置到文件末尾
    echo. >> ".env.example"
    echo # =========================================== >> ".env.example"
    echo # 自动重新执行配置 >> ".env.example"
    echo # =========================================== >> ".env.example"
    echo # 是否启用自动重新执行（所有 success 任务会自动重新执行） >> ".env.example"
    echo AUTO_RECREATE_SUCCESS_JOBS=true >> ".env.example"
    echo. >> ".env.example"
    echo # 任务完成后多久重新执行（分钟） >> ".env.example"
    echo # 60 = 每小时, 360 = 每6小时, 720 = 每12小时, 1440 = 每天 >> ".env.example"
    echo AUTO_RECREATE_INTERVAL_MINUTES=1440 >> ".env.example"

    echo [成功] 配置已添加到 .env.example
    echo.
    echo ========================================
    echo 完成！
    echo ========================================
    echo.
    echo 现在可以重新打包：
    echo   scripts\deployment\build_release.bat
    echo.
    echo 或者直接修复已打包的版本：
    echo   add_config_to_dist.bat
)

echo.
pause
