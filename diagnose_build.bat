@echo off
REM ====================================
REM 打包问题快速诊断脚本
REM ====================================

echo.
echo ========================================
echo   打包环境诊断
echo ========================================
echo.

REM 1. 检查 Python
echo [1/6] 检查 Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo   [失败] Python 未安装或不在 PATH 中
    echo   请安装 Python 3.10+ 并添加到 PATH
    pause
    exit /b 1
) else (
    python --version
    echo   [通过] Python 已安装
)

REM 2. 检查项目依赖
echo.
echo [2/6] 检查项目依赖...
python -c "import fastapi, playwright, sqlalchemy" >nul 2>&1
if errorlevel 1 (
    echo   [失败] 项目依赖未安装
    echo   运行: pip install -r requirements.txt
    pause
    exit /b 1
) else (
    echo   [通过] 项目依赖已安装
)

REM 3. 检查 PyInstaller
echo.
echo [3/6] 检查 PyInstaller...
python -m pip show pyinstaller >nul 2>&1
if errorlevel 1 (
    echo   [失败] PyInstaller 未安装
    echo   运行: pip install pyinstaller
    pause
    exit /b 1
) else (
    python -m PyInstaller --version
    echo   [通过] PyInstaller 已安装
)

REM 4. 检查 build.spec
echo.
echo [4/6] 检查 build.spec...
if not exist "build.spec" (
    echo   [失败] build.spec 文件不存在
    echo   请确保在项目根目录运行此脚本
    pause
    exit /b 1
) else (
    echo   [通过] build.spec 文件存在
)

REM 5. 检查模块导入
echo.
echo [5/6] 检查关键模块导入...
python -c "from app.api.websocket import websocket_manager; from app.services.scheduler import TaskScheduler; from app.services.executor import PlaywrightExecutor; print('所有模块导入正常')" >nul 2>&1
if errorlevel 1 (
    echo   [失败] 模块导入失败
    echo   请检查代码是否有语法错误
    python -c "from app.api.websocket import websocket_manager; from app.services.scheduler import TaskScheduler; from app.services.executor import PlaywrightExecutor"
    pause
    exit /b 1
) else (
    echo   [通过] 所有模块导入正常
)

REM 6. 检查 Playwright 浏览器
echo.
echo [6/6] 检查 Playwright 浏览器...
if exist "%LOCALAPPDATA%\ms-playwright\chromium-*" (
    echo   [通过] Playwright 浏览器已安装
) else (
    echo   [警告] Playwright 浏览器未找到
    echo   建议运行: python -m playwright install chromium
    echo   客户端可在部署后运行: browser-automation-platform.exe --install-browser
)

echo.
echo ========================================
echo   诊断完成
echo ========================================
echo.
echo 所有检查通过！可以运行打包脚本:
echo   build_release.bat
echo.
pause
