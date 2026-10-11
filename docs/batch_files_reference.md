# 批处理文件使用手册

本文档介绍打包版本（`dist/browser-automation-platform/`）中所有批处理文件的功能和使用方法。

---

## 📋 批处理文件清单

| 文件名 | 功能 | 使用场景 | 执行频率 |
|--------|------|---------|---------|
| `install.bat` | 初始化安装 | 首次部署 | 一次 |
| `init_database.bat` | 创建数据库表 | 首次部署或数据库迁移 | 按需 |
| `install_browser.bat` | 安装浏览器驱动 | 首次部署或更新浏览器 | 按需 |
| `init_config.bat` | 初始化采集配置 | 首次部署或添加新配置 | 按需 |
| `batch_import.bat` | 批量导入任务 | 导入注册证号 | 频繁 |
| `startup.bat` | 启动服务 | 每次启动服务 | 频繁 |
| `check_config.bat` | 检查配置 | 排查问题 | 按需 |

---

## 🚀 首次部署完整流程

按以下顺序执行：

### 1. install.bat - 初始化安装
```batch
install.bat
```

**功能**：
- 配置 `.env` 环境变量文件
- 设置数据库连接信息
- 配置系统参数（并发数、限流等）

**交互项**：
- 数据库服务器地址（默认：localhost）
- 数据库用户名（默认：sa）
- 数据库密码
- 其他可选配置项

**输出**：
- 创建 `.env` 配置文件

---

### 2. init_database.bat - 创建数据库表
```batch
init_database.bat
```

**功能**：
- 执行数据库迁移脚本
- 创建所有必需的表结构：
  - `crawler_configs` - 采集配置表
  - `job_queue` - 任务队列表
  - `crawler_results` - 采集结果表
  - 其他系统表

**前置条件**：
- SQL Server 已安装并运行
- 数据库 `bap` 已创建
- `.env` 文件已配置

**等效命令**：
```bash
browser-automation-platform.exe --migrate
```

---

### 3. install_browser.bat - 安装浏览器驱动
```batch
install_browser.bat
```

**功能**：
- 下载并安装 Playwright Chromium 浏览器
- 安装浏览器驱动程序

**注意事项**：
- 首次安装约需下载 150-200MB
- 需要网络连接
- 安装路径：`C:\Users\<用户名>\AppData\Local\ms-playwright\`

**等效命令**：
```bash
browser-automation-platform.exe --install-browser
```

---

### 4. init_config.bat - 初始化采集配置
```batch
init_config.bat
```

**功能**：
- 在数据库中创建"国家医保局注册证号查询"配置
- 配置包括：
  - 目标网站 URL
  - 输入框配置
  - 数据提取规则
  - iframe 处理规则
  - 详情采集配置

**交互项**：
- 确认是否创建示例配置（Y/N）

**输出**：
- 在 `crawler_configs` 表中插入配置记录
- 返回配置 ID（通常为 44）

**等效命令**：
```bash
browser-automation-platform.exe --init-config
```

---

## 📥 日常使用流程

### 5. batch_import.bat - 批量导入任务
```batch
batch_import.bat
```

**功能**：
- 从文件批量导入注册证号
- 自动创建采集任务
- 支持去重检查

**使用步骤**：

1. **准备数据文件**

在 `import_data\` 目录创建文本文件（例如 `jobs.txt`）：
```
川械注准20182010068
川械注准20182170152
川械注准20192220020
# 这是注释，会被忽略
```

2. **运行脚本**
```batch
batch_import.bat
```

3. **选择文件**
```
Available import files:
jobs.txt
test_data.csv

Enter filename (without path): jobs.txt
```

**支持的文件格式**：
- `.txt` - 纯文本文件
- `.csv` - CSV 文件
- 每行一个注册证号
- 以 `#` 开头的行会被忽略

**等效命令**：
```bash
browser-automation-platform.exe --import-jobs "import_data\jobs.txt"
```

---

### 6. startup.bat - 启动服务
```batch
startup.bat
```

**功能**：
- 启动 FastAPI Web 服务
- 启动任务调度器
- 启动进程池管理器
- 启动 WebSocket 服务

**默认配置**：
- 监听地址：`0.0.0.0:8000`
- API 文档：`http://127.0.0.1:8000/docs`
- 监控看板：`http://127.0.0.1:8000/static/index.html`
- WebSocket：`ws://127.0.0.1:8000/ws`

**日志输出**：
- 实时显示任务执行状态
- 显示调度器运行信息
- 显示 API 请求日志

**停止服务**：
- 按 `Ctrl+C` 停止服务
- 关闭命令行窗口

**等效命令**：
```bash
browser-automation-platform.exe
```

---

## 🔧 维护和排查

### 7. check_config.bat - 检查配置
```batch
check_config.bat
```

**功能**：
- 验证 `.env` 配置文件
- 检查数据库连接
- 检查浏览器驱动安装
- 显示系统状态

**输出示例**：
```
[OK] Configuration file exists
[OK] Database connection successful
[OK] Browser driver installed
[OK] All checks passed
```

---

## 📝 常见使用场景

### 场景 1：首次部署

```batch
# 1. 安装配置
install.bat

# 2. 创建数据库表
init_database.bat

# 3. 安装浏览器驱动
install_browser.bat

# 4. 初始化采集配置
init_config.bat

# 5. 导入任务数据
batch_import.bat

# 6. 启动服务
startup.bat
```

---

### 场景 2：日常导入任务

```batch
# 1. 准备数据文件（import_data\jobs.txt）

# 2. 批量导入
batch_import.bat

# 3. 启动服务（如未运行）
startup.bat
```

---

### 场景 3：更新配置

```batch
# 1. 修改 .env 文件

# 2. 检查配置是否正确
check_config.bat

# 3. 重启服务
# 先关闭旧服务（Ctrl+C）
startup.bat
```

---

### 场景 4：数据库迁移

```batch
# 1. 执行迁移
init_database.bat

# 2. 检查数据库连接
check_config.bat

# 3. 重启服务
startup.bat
```

---

## 🐛 故障排查

### 问题 1：批处理文件报错 "不是内部或外部命令"

**原因**：文件编码问题

**解决方案**：
- 已修复，直接运行新版本
- 或手动转换文件编码为 ANSI/GBK

---

### 问题 2：运行报错 "scripts 目录不存在"

**原因**：打包时缺少脚本文件

**解决方案**：
```batch
# 手动创建并复制脚本
cd dist\browser-automation-platform
mkdir scripts
copy ..\..\scripts\init_nhsa_registration_config.py scripts\
copy ..\..\scripts\batch_import_registration_jobs.py scripts\
```

---

### 问题 3：导入报错 "未找到配置"

**原因**：未运行 `init_config.bat`

**解决方案**：
```batch
# 先初始化配置
init_config.bat

# 再导入任务
batch_import.bat
```

---

### 问题 4：数据库连接失败

**检查步骤**：
1. SQL Server 是否运行
2. `.env` 中的连接字符串是否正确
3. 数据库 `bap` 是否已创建
4. 用户权限是否足够

**修复方法**：
```batch
# 1. 检查配置
check_config.bat

# 2. 重新配置
install.bat

# 3. 测试连接
check_config.bat
```

---

### 问题 5：任务导入后不执行

**可能原因**：
1. 限流配置过严格
2. 服务未启动
3. pending 队列过长

**排查方法**：
```batch
# 1. 检查服务是否运行
# 访问：http://127.0.0.1:8000/health

# 2. 查看限流状态
# 访问：http://127.0.0.1:8000/api/rate-limit/status

# 3. 调整限流配置（.env）
RATE_LIMIT_MAX_TASKS=300  # 提高限额
```

---

## 📚 相关文档

- **批量导入详细指南**：`docs/batch_import_guide.md`
- **限流配置说明**：`docs/rate_limit_guide.md`
- **环境变量配置**：`docs/env_config_update.md`
- **部署指南**：`docs/deployment_windows.md`
- **项目总览**：`CLAUDE.md`

---

## 💡 高级用户

如果熟悉命令行，可以直接使用主程序：

```bash
# 查看帮助
browser-automation-platform.exe --help

# 执行特定操作
browser-automation-platform.exe --migrate
browser-automation-platform.exe --init-config
browser-automation-platform.exe --import-jobs "file.txt"
browser-automation-platform.exe --install-browser

# 启动服务
browser-automation-platform.exe
```

---

**文档版本**：v1.0  
**最后更新**：2026-10-11  
**适用版本**：browser-automation-platform 打包版
