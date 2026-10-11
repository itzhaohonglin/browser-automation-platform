@echo off
chcp 65001 >nul

echo ========================================
echo   停止浏览器自动化平台服务
echo ========================================
echo.

echo 正在查找服务进程...
echo.

REM 查找并终止进程
tasklist | find /i "browser-automation-platform.exe" >nul

if errorlevel 1 (
    echo [提示] 未发现运行中的服务
    goto :end
) else (
    echo 发现运行中的服务，正在停止...
    taskkill /f /im browser-automation-platform.exe >nul 2>&1

    if errorlevel 1 (
        echo [错误] 无法停止服务，可能需要管理员权限
        echo 请尝试手动关闭程序窗口
        goto :error
    ) else (
        echo [完成] 服务已停止
    )
)

echo.
goto :end

:error
echo.
pause
exit /b 1

:end
echo.
pause
