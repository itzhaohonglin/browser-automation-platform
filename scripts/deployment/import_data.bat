@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

title 数据导入工具 - 浏览器自动化平台

echo ========================================
echo   数据导入工具
echo   Data Import Utility
echo ========================================
echo.

REM ==========================================
REM 检查服务是否运行
REM ==========================================
echo [检查] 服务状态...

tasklist | find /i "browser-automation-platform.exe" >nul

if errorlevel 1 (
    echo [警告] 服务未运行
    echo.
    echo 请先启动服务：
    echo   双击运行 start.bat
    echo.
    pause
    exit /b 1
)

echo [完成] 服务正在运行
echo.

REM ==========================================
REM 选择导入方式
REM ==========================================
echo ========================================
echo   请选择导入方式
echo ========================================
echo.
echo 1. 从文件导入注册证号（推荐）
echo 2. 从 Excel 文件导入
echo 3. 从 CSV 文件导入
echo 4. 手动输入注册证号
echo 5. 查看导入模板
echo 6. 退出
echo.

set /p CHOICE="请输入选择 (1-6): "

if "%CHOICE%"=="1" goto :import_from_file
if "%CHOICE%"=="2" goto :import_from_excel
if "%CHOICE%"=="3" goto :import_from_csv
if "%CHOICE%"=="4" goto :manual_input
if "%CHOICE%"=="5" goto :show_templates
if "%CHOICE%"=="6" goto :end

echo [错误] 无效选择
pause
exit /b 1

REM ==========================================
REM 方式1：从文本文件导入
REM ==========================================
:import_from_file
echo.
echo ========================================
echo   从文件导入注册证号
echo ========================================
echo.

echo 文件格式要求：
echo   - 纯文本文件（.txt）
echo   - 每行一个注册证号
echo   - 支持 # 开头的注释行
echo   - 空行会被自动忽略
echo.

echo 示例文件内容：
echo   # 国家医保局注册证号列表
echo   滇械注准20192140008
echo   京械注准20210001234
echo   沪械注准20200005678
echo.

set /p FILE_PATH="请输入文件路径（或拖拽文件到此窗口）: "

REM 去除引号
set FILE_PATH=%FILE_PATH:"=%

if not exist "%FILE_PATH%" (
    echo [错误] 文件不存在: %FILE_PATH%
    pause
    goto :import_from_file
)

echo.
echo [读取] 正在读取文件...

REM 统计行数（排除注释和空行）
set COUNT=0
for /f "usebackq tokens=*" %%i in ("%FILE_PATH%") do (
    set LINE=%%i
    REM 跳过注释行
    if not "!LINE:~0,1!"=="#" (
        REM 跳过空行
        if not "!LINE!"=="" (
            set /a COUNT+=1
        )
    )
)

echo [完成] 找到 %COUNT% 个注册证号
echo.

if %COUNT% EQU 0 (
    echo [错误] 文件中没有有效的注册证号
    pause
    goto :end
)

set /p CONFIRM="确认导入这 %COUNT% 个注册证号？(Y/N): "
if /i not "%CONFIRM%"=="Y" (
    echo 已取消导入
    goto :end
)

echo.
echo [导入] 正在调用导入脚本...
echo.

REM 调用 Python 导入脚本
python scripts\import_data.py --file "%FILE_PATH%" --config-id 44

if errorlevel 1 (
    echo.
    echo [错误] 导入失败
    echo 请检查错误信息或查看日志文件
    pause
    exit /b 1
)

echo.
echo ========================================
echo   导入完成！
echo ========================================
echo.
echo 任务已创建，可以通过以下方式查看和执行：
echo   - 前端看板：http://127.0.0.1:8000/static/index.html
echo   - API 文档：http://127.0.0.1:8000/docs
echo.

goto :end

REM ==========================================
REM 方式2：从 Excel 导入
REM ==========================================
:import_from_excel
echo.
echo ========================================
echo   从 Excel 文件导入
echo ========================================
echo.

echo Excel 格式要求：
echo   - 文件格式：.xlsx 或 .xls
echo   - 必须包含名为"注册证号"的列
echo   - 第一行为列名（表头）
echo   - 从第二行开始为数据
echo.

echo 示例表格：
echo   +--+----------------+------------+
echo   |  | 注册证号        | 备注       |
echo   +--+----------------+------------+
echo   | 1| 滇械注准2019... | 需要查询   |
echo   | 2| 京械注准2021... |            |
echo   +--+----------------+------------+
echo.

set /p EXCEL_PATH="请输入 Excel 文件路径: "
set EXCEL_PATH=%EXCEL_PATH:"=%

if not exist "%EXCEL_PATH%" (
    echo [错误] 文件不存在: %EXCEL_PATH%
    pause
    goto :import_from_excel
)

echo.
echo [导入] 正在处理 Excel 文件...
echo.

python scripts\import_data.py --excel "%EXCEL_PATH%" --column "注册证号" --config-id 44

if errorlevel 1 (
    echo [错误] 导入失败
    pause
    exit /b 1
)

echo.
echo [完成] Excel 数据导入成功
goto :end

REM ==========================================
REM 方式3：从 CSV 导入
REM ==========================================
:import_from_csv
echo.
echo ========================================
echo   从 CSV 文件导入
echo ========================================
echo.

echo CSV 格式要求：
echo   - 文件格式：.csv
echo   - 编码：UTF-8
echo   - 分隔符：逗号
echo   - 第一行为列名
echo.

set /p CSV_PATH="请输入 CSV 文件路径: "
set CSV_PATH=%CSV_PATH:"=%

if not exist "%CSV_PATH%" (
    echo [错误] 文件不存在: %CSV_PATH%
    pause
    goto :import_from_csv
)

echo.
echo [导入] 正在处理 CSV 文件...
echo.

python scripts\import_data.py --csv "%CSV_PATH%" --column "注册证号" --config-id 44

if errorlevel 1 (
    echo [错误] 导入失败
    pause
    exit /b 1
)

echo.
echo [完成] CSV 数据导入成功
goto :end

REM ==========================================
REM 方式4：手动输入
REM ==========================================
:manual_input
echo.
echo ========================================
echo   手动输入注册证号
echo ========================================
echo.

echo 请输入注册证号（每行一个，输入空行结束）：
echo.

set COUNT=0
set TEMP_FILE=%TEMP%\bap_import_%RANDOM%.txt

:input_loop
set /p REG_NO="注册证号 %COUNT%: "

if "%REG_NO%"=="" (
    if %COUNT% GTR 0 goto :confirm_manual
    echo [提示] 至少输入一个注册证号
    goto :input_loop
)

echo %REG_NO%>> "%TEMP_FILE%"
set /a COUNT+=1
goto :input_loop

:confirm_manual
echo.
echo 共输入 %COUNT% 个注册证号
echo.

set /p CONFIRM="确认导入？(Y/N): "
if /i not "%CONFIRM%"=="Y" (
    del "%TEMP_FILE%"
    echo 已取消导入
    goto :end
)

echo.
echo [导入] 正在创建任务...
echo.

python scripts\import_data.py --file "%TEMP_FILE%" --config-id 44

del "%TEMP_FILE%"

if errorlevel 1 (
    echo [错误] 导入失败
    pause
    exit /b 1
)

echo.
echo [完成] 手动输入数据导入成功
goto :end

REM ==========================================
REM 方式5：查看模板
REM ==========================================
:show_templates
echo.
echo ========================================
echo   导入模板说明
echo ========================================
echo.

echo 1. 文本文件模板 (registration_numbers.txt)
echo    ----------------------------------------
echo    # 注册证号列表
echo    # 井号开头的行为注释，会被忽略
echo    滇械注准20192140008
echo    京械注准20210001234
echo    沪械注准20200005678
echo.

echo 2. Excel 模板 (registration_numbers.xlsx)
echo    ----------------------------------------
echo    需要包含"注册证号"列：
echo.
echo    ^| 注册证号                ^| 备注     ^|
echo    ^|-------------------------^|---------^|
echo    ^| 滇械注准20192140008      ^| 需要查询 ^|
echo    ^| 京械注准20210001234      ^|         ^|
echo.

echo 3. CSV 模板 (registration_numbers.csv)
echo    ----------------------------------------
echo    注册证号,备注
echo    滇械注准20192140008,需要查询
echo    京械注准20210001234,
echo.

set /p CREATE_TEMPLATE="是否创建示例模板文件？(Y/N): "

if /i "%CREATE_TEMPLATE%"=="Y" (
    echo.
    echo [创建] 正在生成模板文件...

    REM 创建文本模板
    (
        echo # 注册证号导入模板
        echo # 格式：每行一个注册证号
        echo # 井号开头的行为注释，会被忽略
        echo.
        echo 滇械注准20192140008
        echo 京械注准20210001234
        echo 沪械注准20200005678
    ) > registration_numbers_template.txt

    echo [完成] 已创建：registration_numbers_template.txt

    REM 创建 CSV 模板
    (
        echo 注册证号,备注
        echo 滇械注准20192140008,需要查询
        echo 京械注准20210001234,
        echo 沪械注准20200005678,
    ) > registration_numbers_template.csv

    echo [完成] 已创建：registration_numbers_template.csv
    echo.
    echo 模板文件已创建在当前目录
)

echo.
pause
goto :end

REM ==========================================
REM 结束
REM ==========================================
:end
echo.
pause
