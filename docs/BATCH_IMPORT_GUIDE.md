# 批量导入注册证号 - 完整流程指南

本文档介绍如何批量导入医疗器械注册证号到数据库，并创建采集任务。

---

## 📦 打包版本（推荐 - 无需 Python 环境）

适用于 `dist/browser-automation-platform/` 目录下的可执行程序。

### 步骤 1：初始化数据库

双击运行：
```
init_database.bat
```

这会创建所有必需的数据库表。

### 步骤 2：初始化 NHSA 配置

双击运行：
```
init_config.bat
```

这会在数据库中创建"国家医保局注册证号查询"配置。

### 步骤 3：准备导入文件

在 `import_data\` 目录下创建文本文件（例如 `jobs.txt`）：

```
川械注准20182010068
川械注准20182170152
川械注准20192220020
```

**文件格式要求**：
- 每行一个注册证号
- 支持 `.txt` 或 `.csv` 格式
- 以 `#` 开头的行会被忽略（可用作注释）

### 步骤 4：批量导入任务

双击运行：
```
batch_import.bat
```

脚本会：
1. 列出 `import_data\` 目录下所有可用文件
2. 让你输入文件名（例如：`jobs.txt`）
3. 自动导入所有注册证号为任务
4. 显示导入结果

### 步骤 5：启动服务

双击运行：
```
startup.bat
```

### 步骤 6：查看任务执行

浏览器访问：`http://127.0.0.1:8000/static/index.html`

任务会自动执行：
- 按配置的限流规则执行（默认：每小时 100 个）
- 失败任务自动重试（最多 3 次）
- 实时推送执行状态和日志

---

## 🔧 开发环境（需要 Python 环境）

适用于源代码目录的开发模式。

### 步骤 1：初始化数据库

```bash
cd D:\dev\PyCharmProjects\browser-automation-platform
alembic upgrade head
```

### 步骤 2：初始化 NHSA 配置

```bash
python scripts/init_nhsa_registration_config.py
```

### 步骤 3：批量导入注册证号

```bash
python scripts/batch_import_registration_jobs.py path/to/jobs.txt
```

或使用交互式脚本：

```bash
python scripts/import_registration_numbers_from_txt.py
```

### 步骤 4：启动服务

```bash
python -m app.main
```

---

## 📊 预期结果

```
总注册证号：1626 个
├─ 新增任务：1626 个（首次导入）
├─ 已存在：0 个（自动去重）
└─ 执行时间：取决于限流配置
    ├─ 默认限流：每小时 100 个 → 约 16 小时
    ├─ 宽松限流：每小时 300 个 → 约 5-6 小时
    └─ 无限流：约 1-2 小时（不推荐，可能被封）
```

---

## 🚀 快速开始（打包版）

首次使用完整流程：

```batch
# 1. 安装配置
install.bat

# 2. 初始化数据库
init_database.bat

# 3. 安装浏览器驱动
install_browser.bat

# 4. 初始化采集配置
init_config.bat

# 5. 准备数据文件
# 创建 import_data\jobs.txt，每行一个注册证号

# 6. 批量导入任务
batch_import.bat

# 7. 启动服务
startup.bat

# 8. 打开浏览器访问
http://127.0.0.1:8000/static/index.html
```

日常使用（已完成初始化）：

```batch
# 1. 导入新任务
batch_import.bat

# 2. 启动服务（如未运行）
startup.bat
```

---

## 🐛 常见问题

### Q1: 运行 batch_import.bat 报错 "'port' 不是内部或外部命令"

**原因**：批处理文件编码问题导致中文字符乱码。

**解决方案**：已修复，重新运行即可。

### Q2: 运行报错 "scripts 目录不存在"

**原因**：打包时未包含必需的脚本文件。

**解决方案**：
```bash
# 手动复制脚本（已自动完成）
cd dist/browser-automation-platform
mkdir scripts
copy ..\..\scripts\init_nhsa_registration_config.py scripts\
copy ..\..\scripts\batch_import_registration_jobs.py scripts\
```

或重新打包：
```bash
pyinstaller build.spec
```

### Q3: 运行 --import-jobs 报错 "未找到配置"

**原因**：未运行 `init_config.bat` 初始化配置。

**解决方案**：
```bash
# 先初始化配置
init_config.bat

# 再导入任务
batch_import.bat
```

### Q4: 数据库连接失败

**检查 .env 文件**：
```bash
# SQL Server 使用 aioodbc
DATABASE_URL=mssql+aioodbc://sa:YourPassword@localhost:1433/bap?driver=ODBC+Driver+17+for+SQL+Server
```

### Q5: 如何查看导入进度

导入完成后：
1. 运行 `startup.bat` 启动服务
2. 访问 `http://127.0.0.1:8000/static/index.html`
3. 查看"任务统计"和"执行日志"

### Q6: 任务导入后不执行

**可能原因**：
1. 限流设置过严格 → 检查 `.env` 中的 `RATE_LIMIT_*` 配置
2. 服务未启动 → 运行 `startup.bat`
3. pending 队列过长 → 查看智能重试配置

### Q7: 如何调整限流配置

编辑 `.env` 文件：
```bash
# 启用限流
RATE_LIMIT_ENABLED=true

# 每小时最多执行 100 个任务
RATE_LIMIT_WINDOW_MINUTES=60
RATE_LIMIT_MAX_TASKS=100

# 如需加快速度，可调整为：
# RATE_LIMIT_MAX_TASKS=300  # 每小时 300 个
```

修改后需要重启服务。

---

## 📝 数据文件格式

支持的文件格式：

**方式 1：纯文本（推荐）**
```
川械注准20182010068
川械注准20182170152
川械注准20192220020
# 这是注释，会被忽略
```

**方式 2：CSV 格式**
```
川械注准20182010068
川械注准20182170152
川械注准20192220020
```

**注意事项**：
- 每行一个注册证号
- 空行会被自动跳过
- 以 `#` 开头的行会被忽略
- 支持 UTF-8 和 GBK 编码

---

## 💡 手动执行命令（高级用户）

如果不想使用批处理文件，可以直接运行：

```bash
# 初始化配置
browser-automation-platform.exe --init-config

# 导入任务
browser-automation-platform.exe --import-jobs "import_data\jobs.txt"

# 启动服务
browser-automation-platform.exe
```

---

## 📚 相关文档

- **限流配置详解**：`docs/rate_limit_guide.md`
- **环境变量配置**：`docs/env_config_update.md`
- **智能重试优化**：`docs/smart_retry_optimization.md`
- **部署指南**：`docs/deployment_windows.md`

---

**最后更新**：2026-10-11
**支持的数据格式**：TXT, CSV
**推荐导入方式**：batch_import.bat（打包版）
