@echo off
chcp 65001 >nul
title 浏览器自动化数据采集平台

echo ========================================
echo   浏览器自动化数据采集平台
echo   Browser Automation Platform v1.0
echo ========================================
echo.

REM ==========================================
REM 步骤1：检查配置文件
REM ==========================================
echo [检查] 配置文件...

if not exist .env (
    echo [警告] 未找到 .env 配置文件
    echo.

    if exist .env.example (
        echo 正在从模板创建配置文件...
        copy .env.example .env >nul
        echo [完成] 已创建 .env 文件
    ) else (
        echo [错误] 未找到 .env.example 模板文件
        echo 请确保文件完整性
        goto :error
    )

    echo.
    echo ========================================
    echo   首次运行配置
    echo ========================================
    echo.
    echo 请按以下步骤配置：
    echo.
    echo 1. 用记事本打开 .env 文件
    echo 2. 修改 DATABASE_URL 为实际数据库地址
    echo    格式：mysql+aiomysql://用户名:密码@主机:端口/数据库名
    echo    示例：mysql+aiomysql://root:123456@localhost:3306/bap
    echo.
    echo 3. 可选：修改其他配置项
    echo    - APP_PORT: 服务端口（默认 8000）
    echo    - HEADLESS_MODE: 无头模式（默认 true）
    echo    - LOG_LEVEL: 日志级别（默认 INFO）
    echo.
    echo 4. 保存文件后重新运行本脚本
    echo.

    notepad .env

    echo.
    echo 配置完成后，请重新运行本脚本
    goto :end
)

echo [完成] 配置文件存在
echo.

REM ==========================================
REM 步骤2：检查 Playwright 浏览器
REM ==========================================
echo [检查] Playwright 浏览器...

set PLAYWRIGHT_BROWSERS=%USERPROFILE%\AppData\Local\ms-playwright

if not exist "%PLAYWRIGHT_BROWSERS%" (
    echo [警告] 未找到 Playwright 浏览器
    echo.
    echo Playwright 浏览器尚未安装，这是首次运行的必要步骤。
    echo 安装大约需要下载 150MB 的浏览器文件。
    echo.

    set /p INSTALL_NOW="现在安装？(Y/N): "
    if /i "!INSTALL_NOW!"=="Y" (
        echo.
        echo 正在安装，请稍候...
        call install_playwright.bat
        if errorlevel 1 (
            echo [错误] Playwright 安装失败
            goto :error
        )
        echo.
    ) else (
        echo.
        echo 请稍后运行 install_playwright.bat 安装浏览器
        goto :end
    )
) else (
    echo [完成] Playwright 浏览器已安装
    echo.
)

REM ==========================================
REM 步骤3：检查必要目录
REM ==========================================
echo [检查] 必要目录...

if not exist auth_files mkdir auth_files
if not exist logs mkdir logs

echo [完成] 目录检查通过
echo.

REM ==========================================
REM 步骤4：启动服务
REM ==========================================
echo ========================================
echo   正在启动服务...
echo ========================================
echo.

echo [提示] 服务启动需要几秒钟时间
echo [提示] 看到 "Application startup complete" 表示启动成功
echo.
echo 访问地址：
echo   - 前端看板：http://127.0.0.1:8000/static/index.html
echo   - API 文档：http://127.0.0.1:8000/docs
echo   - 健康检查：http://127.0.0.1:8000/health
echo.
echo 按 Ctrl+C 停止服务
echo.
echo ========================================
echo.

REM 启动主程序
browser-automation-platform.exe

goto :end

:error
echo.
echo ========================================
echo   启动失败
echo ========================================
echo.
echo 请检查以上错误信息，或联系技术支持
echo.
pause
exit /b 1

:end
echo.
pause
