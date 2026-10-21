@echo off
chcp 65001 >nul
echo ========================================
echo 同步自动重新执行配置到 .env 文件
echo ========================================
echo.

REM 检查 .env 文件是否存在
if not exist .env (
    echo [错误] .env 文件不存在
    echo 请先从 .env.example 复制创建 .env 文件
    pause
    exit /b 1
)

REM 检查是否已经有配置
findstr /C:"AUTO_RECREATE_SUCCESS_JOBS" .env >nul 2>&1
if %errorlevel% equ 0 (
    echo [提示] .env 文件中已存在 AUTO_RECREATE_SUCCESS_JOBS 配置
    echo.
    set /p choice="是否覆盖更新？(Y/N): "
    if /i not "%choice%"=="Y" (
        echo 已取消
        goto check_dist
    )
    echo.
    echo [操作] 删除旧配置...
    powershell -Command "(Get-Content .env) | Where-Object { $_ -notmatch 'AUTO_RECREATE' } | Set-Content .env.tmp"
    move /y .env.tmp .env >nul
)

echo [操作] 添加自动重新执行配置到 .env...
echo. >> .env
echo # =========================================== >> .env
echo # 自动重新执行配置 >> .env
echo # =========================================== >> .env
echo AUTO_RECREATE_SUCCESS_JOBS=true >> .env
echo AUTO_RECREATE_INTERVAL_MINUTES=1440 >> .env

echo [成功] 已添加配置到 .env
echo.

:check_dist
REM 检查打包目录是否存在
if not exist "dist\browser-automation-platform\.env.example" (
    echo [提示] 打包目录不存在，跳过同步
    goto end
)

echo [操作] 同步到打包目录 .env.example...
findstr /C:"AUTO_RECREATE_SUCCESS_JOBS" "dist\browser-automation-platform\.env.example" >nul 2>&1
if %errorlevel% equ 0 (
    echo [提示] 打包目录 .env.example 已存在配置
    echo [操作] 删除旧配置...
    powershell -Command "(Get-Content 'dist\browser-automation-platform\.env.example') | Where-Object { $_ -notmatch 'AUTO_RECREATE' } | Set-Content 'dist\browser-automation-platform\.env.example.tmp'"
    move /y "dist\browser-automation-platform\.env.example.tmp" "dist\browser-automation-platform\.env.example" >nul
)

echo [操作] 添加配置到打包目录...
echo. >> "dist\browser-automation-platform\.env.example"
echo # =========================================== >> "dist\browser-automation-platform\.env.example"
echo # 自动重新执行配置 >> "dist\browser-automation-platform\.env.example"
echo # =========================================== >> "dist\browser-automation-platform\.env.example"
echo AUTO_RECREATE_SUCCESS_JOBS=true >> "dist\browser-automation-platform\.env.example"
echo AUTO_RECREATE_INTERVAL_MINUTES=1440 >> "dist\browser-automation-platform\.env.example"

echo [成功] 已同步到打包目录
echo.

:end
echo ========================================
echo 同步完成！
echo ========================================
echo.
echo 配置内容：
echo   AUTO_RECREATE_SUCCESS_JOBS=true
echo   AUTO_RECREATE_INTERVAL_MINUTES=1440
echo.
echo 修改间隔时间请编辑 .env 文件中的 AUTO_RECREATE_INTERVAL_MINUTES
echo 常用值：60=每小时, 360=每6小时, 1440=每天
echo.
pause
