@echo off
chcp 65001 >nul
echo ========================================
echo 添加自动重新执行配置到打包目录
echo ========================================
echo.

REM 检查打包目录是否存在
if not exist "dist\browser-automation-platform\.env.example" (
    echo [错误] 打包目录不存在: dist\browser-automation-platform\.env.example
    echo 请先运行打包命令: scripts\deployment\build_release.bat
    pause
    exit /b 1
)

echo [检查] 检查配置文件是否包含 AUTO_RECREATE 配置...
findstr /C:"AUTO_RECREATE_SUCCESS_JOBS" "dist\browser-automation-platform\.env.example" >nul 2>&1

if %errorlevel% equ 0 (
    echo [成功] 配置已存在
    echo.
    echo 当前配置：
    findstr "AUTO_RECREATE" "dist\browser-automation-platform\.env.example"
    echo.
) else (
    echo [警告] 配置不存在，正在添加...
    echo.

    REM 添加配置到文件末尾
    echo. >> "dist\browser-automation-platform\.env.example"
    echo # =========================================== >> "dist\browser-automation-platform\.env.example"
    echo # 自动重新执行配置 >> "dist\browser-automation-platform\.env.example"
    echo # =========================================== >> "dist\browser-automation-platform\.env.example"
    echo # 是否启用自动重新执行（所有 success 任务会自动重新执行） >> "dist\browser-automation-platform\.env.example"
    echo AUTO_RECREATE_SUCCESS_JOBS=true >> "dist\browser-automation-platform\.env.example"
    echo. >> "dist\browser-automation-platform\.env.example"
    echo # 任务完成后多久重新执行（分钟） >> "dist\browser-automation-platform\.env.example"
    echo # 60 = 每小时, 360 = 每6小时, 720 = 每12小时, 1440 = 每天 >> "dist\browser-automation-platform\.env.example"
    echo AUTO_RECREATE_INTERVAL_MINUTES=1440 >> "dist\browser-automation-platform\.env.example"

    echo [成功] 配置已添加
    echo.
)

echo ========================================
echo 检查 .env.template 文件
echo ========================================
echo.

if exist "dist\browser-automation-platform\.env.template" (
    findstr /C:"AUTO_RECREATE_SUCCESS_JOBS" "dist\browser-automation-platform\.env.template" >nul 2>&1

    if %errorlevel% equ 0 (
        echo [OK] .env.template 已包含配置
    ) else (
        echo [操作] 同步到 .env.template...
        echo. >> "dist\browser-automation-platform\.env.template"
        echo # =========================================== >> "dist\browser-automation-platform\.env.template"
        echo # 自动重新执行配置 >> "dist\browser-automation-platform\.env.template"
        echo # =========================================== >> "dist\browser-automation-platform\.env.template"
        echo # 是否启用自动重新执行（所有 success 任务会自动重新执行） >> "dist\browser-automation-platform\.env.template"
        echo AUTO_RECREATE_SUCCESS_JOBS=true >> "dist\browser-automation-platform\.env.template"
        echo. >> "dist\browser-automation-platform\.env.template"
        echo # 任务完成后多久重新执行（分钟） >> "dist\browser-automation-platform\.env.template"
        echo # 60 = 每小时, 360 = 每6小时, 720 = 每12小时, 1440 = 每天 >> "dist\browser-automation-platform\.env.template"
        echo AUTO_RECREATE_INTERVAL_MINUTES=1440 >> "dist\browser-automation-platform\.env.template"
        echo [成功] 已同步到 .env.template
    )
) else (
    echo [提示] .env.template 不存在，跳过
)

echo.
echo ========================================
echo 完成！
echo ========================================
echo.
echo 配置已添加到打包目录，现在可以：
echo   1. 直接使用当前打包目录部署
echo   2. 或重新打包以确保配置包含在内
echo.
pause
