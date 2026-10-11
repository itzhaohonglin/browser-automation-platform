@echo off
chcp 65001 >nul

echo ========================================
echo   安装 Playwright 浏览器
echo ========================================
echo.

echo [提示] 此步骤将下载并安装 Chromium 浏览器
echo [提示] 下载大小约 150MB，请确保网络连接正常
echo.

set /p CONFIRM="确认安装？(Y/N): "
if /i not "%CONFIRM%"=="Y" (
    echo 已取消安装
    goto :end
)

echo.
echo 正在安装 Playwright 浏览器...
echo.

REM 检查是否在打包环境中
if exist browser-automation-platform.exe (
    REM 打包后的环境，需要特殊处理
    echo [检查] 检测到打包环境

    REM 尝试使用内置的 playwright 命令
    .\browser-automation-platform.exe --install-browsers >nul 2>&1

    if errorlevel 1 (
        echo [提示] 正在使用外部 Playwright 安装...

        REM 检查系统是否安装了 Python
        python --version >nul 2>&1
        if errorlevel 1 (
            echo.
            echo ========================================
            echo   需要手动安装
            echo ========================================
            echo.
            echo 系统未安装 Python，请访问以下地址手动下载浏览器：
            echo https://playwright.dev/docs/browsers
            echo.
            echo 或者安装 Python 后运行：
            echo   pip install playwright
            echo   playwright install chromium
            echo.
            goto :error
        )

        REM 检查 playwright 是否已安装
        python -c "import playwright" >nul 2>&1
        if errorlevel 1 (
            echo [安装] 正在安装 Playwright Python 包...
            pip install playwright
            if errorlevel 1 (
                echo [错误] Playwright 包安装失败
                goto :error
            )
        )

        REM 安装浏览器
        echo [安装] 正在下载 Chromium 浏览器...
        playwright install chromium

        if errorlevel 1 (
            echo [错误] 浏览器安装失败
            goto :error
        )
    )
) else (
    REM 开发环境，直接使用 playwright 命令
    playwright install chromium

    if errorlevel 1 (
        echo [错误] 浏览器安装失败
        echo.
        echo 请确保已安装 Playwright:
        echo   pip install playwright
        goto :error
    )
)

echo.
echo ========================================
echo   安装完成！
echo ========================================
echo.
echo Chromium 浏览器已成功安装
echo 现在可以运行 start.bat 启动服务
echo.
goto :end

:error
echo.
echo ========================================
echo   安装失败
echo ========================================
echo.
echo 请检查网络连接或手动安装
echo 详细说明请参考 README.txt
echo.
pause
exit /b 1

:end
pause
