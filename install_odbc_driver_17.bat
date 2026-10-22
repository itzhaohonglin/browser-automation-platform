@echo off
chcp 65001 > nul
echo ========================================
echo 下载并安装 ODBC Driver 17 for SQL Server
echo ========================================
echo.

echo 正在下载 ODBC Driver 17...
powershell -Command "Invoke-WebRequest -Uri 'https://go.microsoft.com/fwlink/?linkid=2187214' -OutFile '%TEMP%\msodbcsql_17.msi'"

if %ERRORLEVEL% NEQ 0 (
    echo 下载失败，请手动下载：
    echo https://go.microsoft.com/fwlink/?linkid=2187214
    pause
    exit /b 1
)

echo.
echo 正在安装 ODBC Driver 17...
msiexec /i "%TEMP%\msodbcsql_17.msi" /qn IACCEPTMSODBCSQLLICENSETERMS=YES

if %ERRORLEVEL% NEQ 0 (
    echo 安装失败，尝试以管理员身份运行此脚本
    pause
    exit /b 1
)

echo.
echo ========================================
echo 安装完成！
echo ========================================
echo.
echo 请在 .env 文件中设置：
echo DATABASE_URL=mssql+aioodbc://sa:密码@localhost/bap?driver=ODBC+Driver+17+for+SQL+Server
echo.
pause
