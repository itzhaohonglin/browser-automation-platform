# 客户端批量导入使用说明（无需 Python 环境）

## ✅ 客户端环境要求

- ✅ **不需要** Python 环境
- ✅ **不需要** 安装任何依赖
- ✅ 只需要打包后的 `browser-automation-platform.exe`

所有 Python 脚本都已经打包到 exe 文件中！

---

## 📂 客户端目录结构

```
browser-automation-platform/          # 打包后的根目录
├── browser-automation-platform.exe   # 主程序（包含所有 Python 脚本）
├── _internal/                        # 依赖库（PyInstaller 自动生成）
├── .env                              # 配置文件（首次运行 install.bat 生成）
├── alembic/                          # 数据库迁移文件
├── static/                           # 前端文件
├── logs/                             # 日志目录（自动创建）
├── auth_files/                       # 登录态存储（自动创建）
├── import_data/                      # 导入数据目录（自动创建）
│   └── jobs.txt                      # 待导入的注册证号列表
├── install.bat                       # 初始化安装脚本
├── init_database.bat                 # 创建数据库表
├── install_browser.bat               # 安装浏览器驱动
├── init_config.bat                   # 初始化采集配置
├── batch_import.bat                  # 批量导入任务 ⭐
├── startup.bat                       # 启动服务
└── check_config.bat                  # 检查配置
```

---

## 🚀 批量导入完整流程

### 步骤 1：首次部署（一次性操作）

```batch
# 1. 配置环境变量和数据库连接
install.bat

# 2. 创建数据库表结构
init_database.bat

# 3. 安装浏览器驱动
install_browser.bat

# 4. 初始化 NHSA 采集配置
init_config.bat
```

### 步骤 2：准备数据文件

在 `import_data\` 目录下创建 `jobs.txt` 文件：

**支持的格式：**

```text
# 格式1：纯注册证号
川械注准20182010068
川械注准20182170152
川械注准20192220020

# 格式2：带序号（Excel 导出）
1	川械注准20182010068
2	川械注准20182170152
3	川械注准20192220020
```

### 步骤 3：批量导入

双击运行：
```batch
batch_import.bat
```

**执行过程：**
```
1. 脚本列出 import_data\ 目录下的所有文件
2. 输入文件名（例如：jobs.txt）
3. 调用 browser-automation-platform.exe --import-jobs "import_data\jobs.txt"
4. exe 内部执行打包的 Python 脚本
5. 读取文件 → 解析注册证号 → 创建任务
6. 显示导入结果
```

### 步骤 4：启动服务

```batch
startup.bat
```

服务启动后，任务会自动执行。

---

## 🔧 工作原理详解

### 为什么客户端不需要 Python？

**答案：所有代码都打包到了 exe 文件中！**

#### PyInstaller 打包过程

```
开发环境：
├── app/main.py                          # 主程序
├── scripts/batch_import_*.py            # 导入脚本
└── Python 解释器 + 所有依赖库

            ↓  打包（pyinstaller build.spec）

打包后：
└── browser-automation-platform.exe
    ├── Python 解释器（内嵌）
    ├── app/main.py（编译后）
    ├── scripts/batch_import_*.py（打包为资源）
    └── 所有依赖库（打包）
```

#### 执行流程

```python
# 1. 客户端运行 batch_import.bat
# batch_import.bat 内部调用：
browser-automation-platform.exe --import-jobs "import_data\jobs.txt"

# 2. exe 主程序（app/main.py）解析命令行参数
if action == ACTION_IMPORT_JOBS:
    run_import_jobs(extra_args[0])

# 3. CLI 模块（app/core/cli.py）执行打包的脚本
def run_import_jobs(file_path: str):
    # 从 exe 内部提取 scripts/batch_import_registration_jobs.py
    # 在临时目录执行（用户不可见）
    run_bundled_script("batch_import_registration_jobs.py", [file_path])

# 4. 脚本执行：
# - 读取 import_data\jobs.txt
# - 连接数据库
# - 批量创建 job_queue 记录
# - 返回结果
```

### 关键代码片段

**app/core/cli.py**
```python
def run_bundled_script(script_name: str, args: list[str] | None = None):
    """从 exe 内部执行打包的脚本"""
    # PyInstaller 打包后，脚本位于临时解压目录
    path = get_bundle_base_path() / "scripts" / script_name
    
    # 使用 runpy 执行脚本（类似 python script.py）
    runpy.run_path(str(path), run_name="__main__")
```

**build.spec（打包配置）**
```python
datas=[
    # 将脚本打包到 exe 资源中
    ('scripts/batch_import_registration_jobs.py', 'scripts'),
]
```

---

## 📋 命令行参考（高级用户）

### 所有支持的命令

```batch
# 1. 初始化配置
browser-automation-platform.exe --init-config

# 2. 批量导入任务
browser-automation-platform.exe --import-jobs "import_data\jobs.txt"
browser-automation-platform.exe --import-jobs "D:\data\注册证号.txt"  # 绝对路径

# 3. 安装浏览器驱动
browser-automation-platform.exe --install-browser

# 4. 执行数据库迁移
browser-automation-platform.exe --migrate

# 5. 启动 Web 服务（默认行为）
browser-automation-platform.exe
```

### 等价关系

| 批处理脚本 | 等价命令 |
|-----------|---------|
| `init_config.bat` | `browser-automation-platform.exe --init-config` |
| `batch_import.bat` | `browser-automation-platform.exe --import-jobs "文件路径"` |
| `install_browser.bat` | `browser-automation-platform.exe --install-browser` |
| `init_database.bat` | `browser-automation-platform.exe --migrate` |
| `startup.bat` | `browser-automation-platform.exe` |

---

## ❓ 常见疑问

### Q1: 客户端没有 Python，如何执行 .py 脚本？

**A:** PyInstaller 已经将 Python 解释器和所有脚本打包到 exe 中。exe 运行时会：
1. 解压到临时目录（如 `C:\Users\用户名\AppData\Local\Temp\_MEI123456\`）
2. 使用内嵌的 Python 解释器执行脚本
3. 执行完成后清理临时文件

### Q2: 如何验证脚本已打包？

**方法1：查看 exe 大小**
- 未打包脚本：~20MB
- 已打包脚本：~100MB+（包含 Python + 所有依赖）

**方法2：运行命令**
```batch
# 如果脚本未打包，会报错 "脚本不存在"
browser-automation-platform.exe --import-jobs "test.txt"
```

### Q3: 导入脚本可以修改吗？

**A:** 不能直接修改。脚本已编译到 exe 中，如需修改：
1. 修改源代码（开发环境）
2. 重新打包（`pyinstaller build.spec`）
3. 分发新的 exe 给客户端

### Q4: 打包后性能如何？

**A:** 几乎无差异：
- 首次运行略慢（解压 3-5 秒）
- 后续运行与开发环境相同
- 导入 1626 个任务约 10-20 秒

### Q5: 如何调试客户端问题？

**查看日志：**
```batch
# 日志文件位置
logs\app.log

# 查看最新日志
type logs\app.log

# 实时监控
powershell Get-Content logs\app.log -Wait -Tail 50
```

---

## 🎯 最佳实践

### 1. 测试导入（小批量）

首次使用建议先测试：

**test_data.txt**
```text
川械注准20182010068
川械注准20182170152
川械注准20192220020
```

```batch
# 导入测试数据
browser-automation-platform.exe --import-jobs "import_data\test_data.txt"

# 检查结果
# 打开 Web 看板确认任务创建成功
start http://127.0.0.1:8000/static/index.html
```

### 2. 批量导入（生产环境）

确认测试通过后，导入完整数据：

```batch
# 备份数据文件
copy import_data\jobs.txt import_data\jobs_backup_20261011.txt

# 批量导入
batch_import.bat
```

### 3. 自动化导入（可选）

**auto_import.bat**（放在客户端目录）
```batch
@echo off
REM 自动化导入脚本

echo [INFO] Starting auto import...

REM 检查文件存在
if not exist import_data\jobs.txt (
    echo [ERROR] File not found: import_data\jobs.txt
    exit /b 1
)

REM 执行导入
browser-automation-platform.exe --import-jobs "import_data\jobs.txt"
if errorlevel 1 (
    echo [ERROR] Import failed
    exit /b 1
)

echo [OK] Import completed successfully

REM 可选：导入后自动启动服务
REM call startup.bat
```

---

## 📖 相关文档

- **批处理文件手册**：`docs/batch_files_reference.md`
- **完整使用指南**：`docs/client_batch_import_guide.md`
- **环境配置**：`docs/env_config_examples.md`
- **打包说明**：`build.spec`（开发环境）

---

## 📞 技术支持

如有问题，请提供：
1. 错误截图
2. 日志文件 `logs/app.log`
3. 数据文件示例（前 10 行）
4. 系统环境信息
