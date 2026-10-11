# Windows 客户端部署指南

> 本文档面向需要将浏览器自动化平台部署到客户 Windows 电脑的开发人员

## 部署方案概述

由于客户电脑**没有 Python 运行环境**，采用 **PyInstaller 打包方案**，将应用打包成独立的可执行文件（.exe）。

### 方案优势

✅ **开箱即用** - 客户无需安装 Python 环境  
✅ **单文件分发** - 整个目录打包成一个压缩包  
✅ **自动化安装** - 提供交互式安装脚本  
✅ **配置灵活** - 通过 .env 文件配置数据库连接、端口等参数，无需修改代码  
✅ **易于维护** - 配置和数据与程序分离  

### 方案限制

⚠️ **浏览器驱动独立** - Playwright 浏览器驱动（约300MB）无法打包进 exe，需首次运行时下载  
⚠️ **打包体积** - 打包后约 150-200MB（包含所有 Python 依赖）  
⚠️ **更新成本** - 每次更新需重新打包并分发完整包

### 核心特性

✨ **配置文件驱动** - 所有运行参数通过 `.env` 文件配置：
- 数据库连接字符串（DATABASE_URL，**重要：必须添加 &charset=UTF-8 支持中文**）
- 服务端口（APP_PORT，默认 8000，可自定义）
- 日志级别（LOG_LEVEL）
- 浏览器模式（HEADLESS_MODE：有头/无头）
- 告警配置（邮件、钉钉、企业微信）

客户可以随时修改 `.env` 文件调整这些参数，无需重新打包程序。

⚠️ **中文编码重要提示**：SQL Server 数据库连接字符串必须添加 `&charset=UTF-8` 参数，否则中文会显示为乱码！详见 `docs/FIX_CHINESE_ENCODING.md`。  

---

## 一、开发端：打包发布版本

### 1.1 环境准备

确保开发环境已安装：
- Python 3.10+
- 所有项目依赖（`pip install -r requirements.txt`）
- PyInstaller（`pip install pyinstaller`）
- pyinstaller-hooks-contrib（`pip install pyinstaller-hooks-contrib`，打包 Playwright node 驱动必需；`build_release.bat` 会自动检测并安装）

### 1.2 执行打包

```bash
# 方式一：使用打包脚本（推荐）
cd D:\dev\PyCharmProjects\browser-automation-platform
.\scripts\deployment\build_release.bat

# 方式二：手动打包
pyinstaller build.spec
```

打包过程说明：
1. 清理旧的构建文件（`build/`, `dist/`）
2. 使用 PyInstaller 打包主程序（静态资源与迁移脚本打包在 exe 内部）
3. 复制客户端脚本（`startup.bat`, `install.bat` 等）
4. 创建必要目录（`auth_files/`, `logs/`）

### 1.3 打包输出

```
dist/browser-automation-platform/
├── browser-automation-platform.exe  # 主程序（约150MB）
├── _internal/                        # 依赖库与内置资源（PyInstaller自动生成）
│   ├── static/                       # 前端资源（打包在 exe 内部）
│   └── alembic/                      # 数据库迁移脚本（打包在 exe 内部）
├── auth_files/                       # 登录态目录（空）
├── logs/                             # 日志目录（空）
├── import_data/                      # 批量导入数据目录
├── .env.example                      # 配置模板
├── startup.bat                       # 启动脚本（启动时自动执行数据库迁移）
├── install.bat                       # 首次安装脚本
├── init_database.bat                 # 数据库初始化（调用 exe --migrate）
├── init_config.bat                   # 配置初始化（调用 exe --init-config）
├── batch_import.bat                  # 批量导入任务（调用 exe --import-jobs）
├── install_browser.bat               # 浏览器驱动安装（调用 exe --install-browser）
├── 使用说明.txt                      # 用户手册
├── 配置说明.txt                      # 配置文件详细说明
├── VERSION.txt                       # 版本信息
└── README.md                         # 项目说明
```

### 1.4 测试打包结果

```bash
# 进入打包目录
cd dist\browser-automation-platform

# 测试启动（需先配置.env和数据库）
.\startup.bat
```

### 1.5 创建分发包

```bash
# 压缩整个目录
# 使用 7-Zip 或 WinRAR 将 dist/browser-automation-platform/ 压缩为：
browser-automation-platform-v1.0.0.zip
```

---

## 二、客户端：安装部署

### 2.1 系统要求

**必需**：
- Windows 10/11 或 Windows Server 2016+
- 磁盘空间：至少 1GB 可用空间
- 网络连接：首次安装需下载浏览器驱动
- SQL Server 数据库（本地或远程）

**可选**：
- ODBC Driver 17 for SQL Server（如未安装，需先安装）

### 2.2 安装步骤

#### 步骤1：解压安装包

将 `browser-automation-platform-v1.0.0.zip` 解压到任意目录（建议英文路径）：

```
C:\Programs\browser-automation-platform\
```

#### 步骤2：运行安装向导

双击 `install.bat`，按提示完成以下操作：

1. **配置数据库连接**
   - 脚本会自动创建 `.env` 文件
   - 手动编辑 `.env`，修改以下配置：

   ```ini
   # 数据库连接（必填 - 注意添加 &charset=UTF-8 支持中文）
   DATABASE_URL=mssql+aioodbc://sa:MyPassword@localhost:1433/bap?driver=ODBC+Driver+17+for+SQL+Server&charset=UTF-8
   
   # 服务端口（可选，默认 8000）
   APP_PORT=8000
   
   # 其他配置（可选）
   HEADLESS_MODE=true
   LOG_LEVEL=INFO
   ```

   **重要提示**：
   - **必须添加 `&charset=UTF-8`** 参数，否则中文会显示为乱码
   - 端口可以自定义（如改为 9000），修改后访问地址变为 `http://127.0.0.1:9000`
   - 密码中的特殊字符需要 URL 编码（@ → %40，# → %23）
   - 详细配置说明请查看打包目录中的 `配置说明.txt`

2. **安装浏览器驱动**（约300MB，需网络连接）
   - 选择 "Y" 开始下载
   - 等待下载完成（时间取决于网络速度）
   - 说明：此步骤由主程序内置的 Playwright CLI 完成（`exe --install-browser`），客户端无需安装 Python

3. **初始化数据库**
   - 确保 SQL Server 中已创建数据库 `bap`（**重要：必须指定 COLLATE 支持中文**）：
     ```sql
     CREATE DATABASE bap COLLATE Chinese_PRC_CI_AS;
     ```
   - 选择 "Y" 执行数据库迁移（由主程序内置的 alembic 完成，`exe --migrate`）

#### 步骤3：启动服务

双击 `startup.bat` 启动服务。

看到以下信息表示启动成功：

```
======================================
  服务已启动
======================================

访问地址:
  - 监控看板: http://127.0.0.1:8000/static/index.html
  - API 文档: http://127.0.0.1:8000/docs

按 Ctrl+C 停止服务
======================================
```

#### 步骤4：验证安装

打开浏览器，访问：`http://127.0.0.1:8000/static/index.html`

应能看到监控看板界面。

---

## 三、常见问题排查

### 3.1 启动失败

**现象**：双击 `startup.bat` 后立即退出

**排查**：
1. 检查 `.env` 文件是否存在
2. 检查 `DATABASE_URL` 是否正确
3. 检查 SQL Server 服务是否运行
4. 查看 `logs/` 目录中的错误日志

**解决**：
```bash
# 重新配置
.\install.bat

# 手动测试数据库连接
sqlcmd -S localhost -U sa -P YourPassword -Q "SELECT @@VERSION"
```

### 3.2 浏览器驱动下载慢

**现象**：执行 `playwright install chromium` 长时间无响应

**原因**：
- 国内网络访问 Playwright CDN 较慢
- 防火墙/杀毒软件拦截

**解决方案一（镜像源）**：
```bash
# 设置国内镜像
set PLAYWRIGHT_DOWNLOAD_HOST=https://npmmirror.com/mirrors/playwright
playwright install chromium
```

**解决方案二（离线安装）**：
1. 在有网络的机器上下载浏览器驱动
2. 复制到客户端：
   ```
   C:\Users\{用户名}\AppData\Local\ms-playwright\
   ```

### 3.3 数据库连接失败

**现象**：启动时报错 "Unable to connect to database"

**排查清单**：

| 检查项 | 验证命令 |
|--------|----------|
| SQL Server 服务运行 | `services.msc` 查看 SQL Server 服务状态 |
| 端口开放（默认1433） | `telnet localhost 1433` |
| 用户名密码正确 | 使用 SSMS 尝试登录 |
| 数据库已创建 | `SELECT name FROM sys.databases` |
| ODBC 驱动已安装 | 控制面板 → ODBC 数据源 |

**快速修复**：
```bash
# 测试连接
sqlcmd -S localhost -U sa -P YourPassword -d bap -Q "SELECT 1"

# 重新创建数据库
sqlcmd -S localhost -U sa -P YourPassword -Q "CREATE DATABASE bap COLLATE Chinese_PRC_CI_AS;"

# 重新初始化
.\init_database.bat
```

### 3.4 ODBC 驱动缺失

**现象**：启动时报错 "driver={ODBC Driver 17 for SQL Server}" not found

**解决**：下载并安装 ODBC Driver：
- [官方下载](https://docs.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server)
- 选择 ODBC Driver 17 for SQL Server

### 3.5 数据库迁移失败

**现象**：`init_database.bat` 或启动时数据库迁移报错

**排查**：
1. 确认 SQL Server 服务已启动、数据库 `bap` 已创建
2. 确认 `.env` 中 `DATABASE_URL` 使用 `mssql+aioodbc://` 前缀
3. 查看窗口中的错误信息（如 "TCP 提供程序: 目标计算机积极拒绝" 表示数据库服务未启动）

**说明**：
- 数据库迁移由主程序内置的 alembic 执行，客户端**不需要**安装 Python 或 alembic 命令
- 服务每次启动时会自动检查并执行迁移（已是最新版本时无操作）
- 手动执行迁移：运行 `init_database.bat`，或命令行执行 `browser-automation-platform.exe --migrate`

---

## 四、客户端脚本说明

| 脚本文件 | 功能说明 | 使用场景 |
|---------|---------|---------|
| `startup.bat` | 启动服务（启动时自动检查数据库迁移） | 每次使用时运行 |
| `install.bat` | 首次安装向导（.env 已存在时自动跳过配置步骤） | 初次部署时运行一次 |
| `install_browser.bat` | 单独安装浏览器驱动 | 浏览器驱动损坏或需重装 |
| `init_database.bat` | 初始化/更新数据库（exe --migrate） | 数据库损坏或版本升级 |
| `init_config.bat` | 创建示例配置（exe --init-config） | 首次使用时体验功能 |
| `batch_import.bat` | 批量导入任务（exe --import-jobs，每行一个注册证号的 TXT/CSV） | 批量创建任务时使用 |

主程序支持的维护参数（可在 cmd 中直接调用，均无需 Python 环境）：

```
browser-automation-platform.exe --migrate            # 执行数据库迁移
browser-automation-platform.exe --install-browser    # 安装 Playwright 浏览器驱动
browser-automation-platform.exe --init-config        # 初始化示例配置
browser-automation-platform.exe --import-jobs <文件>  # 从文件批量导入任务
```

---

## 五、版本更新

### 5.1 更新流程

1. **开发端重新打包**
   ```bash
   .\scripts\deployment\build_release.bat
   ```

2. **创建更新包**
   - 仅打包变更的文件（如果仅代码变更）
   - 或打包完整包

3. **客户端更新**
   ```bash
   # 停止服务
   Ctrl+C

   # 备份数据
   copy .env .env.backup
   xcopy /E /I auth_files auth_files_backup

   # 替换程序文件
   # 解压新版本，覆盖除 .env 和 auth_files/ 外的所有文件

   # 更新数据库（如有数据库变更）
   .\init_database.bat

   # 重启服务
   .\startup.bat
   ```

### 5.2 保留的文件

更新时**不要覆盖**以下文件和目录：
- `.env` - 配置文件
- `auth_files/` - 登录态数据
- `logs/` - 历史日志（可选保留）

---

## 六、高级配置

### 6.1 注册为 Windows 服务

使用 NSSM 将应用注册为系统服务，实现开机自启：

```bash
# 下载 NSSM: https://nssm.cc/download

# 安装服务
nssm install BrowserAutomation "C:\Programs\browser-automation-platform\browser-automation-platform.exe"

# 配置服务
nssm set BrowserAutomation AppDirectory "C:\Programs\browser-automation-platform"
nssm set BrowserAutomation DisplayName "浏览器自动化平台"
nssm set BrowserAutomation Start SERVICE_AUTO_START

# 启动服务
nssm start BrowserAutomation

# 查看状态
nssm status BrowserAutomation
```

### 6.2 修改端口

**无需重新打包**！直接编辑 `.env` 文件：

```ini
# 修改端口为 9000
APP_PORT=9000
```

然后重启服务即可。访问地址变为：`http://127.0.0.1:9000/static/index.html`

**验证端口是否占用**：
```bash
netstat -ano | findstr ":9000"
```

如果有输出，说明端口已被占用，需要更换其他端口。

### 6.3 配置日志级别

编辑 `.env` 文件：

```ini
# 日志级别
LOG_LEVEL=INFO   # DEBUG | INFO | WARNING | ERROR

# 日志文件路径
LOG_FILE=logs/app.log
```

---

## 七、性能优化建议

### 7.1 数据库优化

```sql
-- 定期清理历史数据（6个月前的记录）
DELETE FROM crawler_results WHERE created_at < DATEADD(MONTH, -6, GETDATE());
DELETE FROM job_queue WHERE status = 'success' AND created_at < DATEADD(MONTH, -6, GETDATE());

-- 重建索引
ALTER INDEX ALL ON job_queue REBUILD;
ALTER INDEX ALL ON crawler_results REBUILD;
```

### 7.2 日志管理

```bash
# 定期清理日志（保留最近30天）
forfiles /p "logs" /s /m *.log /d -30 /c "cmd /c del @path"
```

### 7.3 任务调度优化

编辑数据库中的配置：
- 降低失败任务重试频率（修改调度器配置）
- 设置任务优先级
- 分时段执行（避免高峰期）

---

## 八、安全建议

1. **数据库访问控制**
   - 使用独立的数据库账号（非 sa）
   - 限制账号权限（仅访问 bap 数据库）

2. **文件权限**
   - 限制 `auth_files/` 目录访问权限
   - 保护 `.env` 文件（包含数据库密码）

3. **网络安全**
   - 如需远程访问，使用 VPN 或 SSH 隧道
   - 避免直接暴露 8000 端口到公网

4. **备份策略**
   - 定期备份数据库
   - 定期备份 `auth_files/` 目录

---

## 九、技术支持检查清单

当客户遇到问题时，请提供：

```
【环境信息】
- Windows 版本：
- 软件版本：
- SQL Server 版本：

【错误信息】
- 错误截图：
- 错误日志（logs/最新日志文件）：

【配置信息】
- .env 配置（隐藏密码）：
- 是否能访问监控看板：
- 数据库连接是否正常：

【操作步骤】
1. 
2. 
3. 
```

---

## 附录：PyInstaller 打包注意事项

### A.1 隐藏导入

`build.spec` 中的 `hiddenimports` 列表包含了 PyInstaller 无法自动检测的依赖。如果遇到运行时 ImportError，需要在此添加缺失的模块。

### A.2 数据文件

使用 `datas` 列表包含所有非 Python 文件：
- 前端静态文件（`static/`）
- 数据库迁移脚本（`alembic/`）
- 配置模板（`.env.example`）

使用 conda 环境打包时，`build.spec` 的 `binaries` 列表还包含 `Library\bin` 下的依赖 DLL（ffi.dll、sqlite3.dll 等）。PyInstaller 不会自动搜索该目录，缺失会导致 exe 运行时 `ImportError: DLL load failed`。

另外注意：打包必须使用**项目虚拟环境**的 Python（`build_release.bat` 已自动选择 `.venv`），用未安装项目依赖的 Python 打包会产出缺少 fastapi 等模块的残缺包。

### A.3 已知限制

1. **Playwright 浏览器驱动无法打包**
   - 必须在客户端首次运行时下载
   - 大小约 300MB
   - 通过 `exe --install-browser` 安装（`install_browser.bat` 已封装），无需 Python 环境

2. **数据库迁移内置化**
   - 客户端无 Python 环境，`alembic` 命令行不可用
   - 已通过主程序内置迁移解决：启动时自动执行 + `exe --migrate` 手动触发

3. **动态导入**
   - 避免在代码中使用 `importlib.import_module()`
   - 使用静态 import 语句

---

**文档版本**：v1.0.0  
**更新日期**：2026-09-30  
**适用版本**：browser-automation-platform v1.0.0
