# MySQL 到 SQL Server 迁移设计文档

**日期**: 2026-09-30  
**项目**: 浏览器自动化数据采集平台  
**状态**: 已批准

## 概述

将浏览器自动化平台的数据库从 MySQL 迁移到 SQL Server，以符合企业标准化要求。项目尚未上线，无需数据迁移，采用完全重置方案。

## 背景

**迁移原因**:
- 企业标准要求统一使用 SQL Server
- 项目处于开发阶段，未上线，无生产数据

**当前技术栈**:
- 数据库: MySQL 8.0+
- Python 驱动: aiomysql (异步) + pymysql (同步)
- ORM: SQLAlchemy 2.0.35 (异步)
- 迁移工具: Alembic 1.13.2
- 迁移文件数量: 6 个

**目标环境**:
- 数据库: SQL Server on Windows
- 认证方式: SQL Server 身份验证（用户名 + 密码）

## 技术方案

### 1. 数据库驱动变更

#### 移除的依赖
```txt
pymysql==1.1.1          # 同步 MySQL 驱动
aiomysql==0.2.0         # 异步 MySQL 驱动
```

#### 新增的依赖
```txt
pyodbc==5.0.1           # 同步 ODBC 驱动（Alembic 使用）
aioodbc==0.5.0          # 异步 ODBC 驱动（应用使用）
```

#### 前置条件
- 必须安装 **Microsoft ODBC Driver 17 for SQL Server**（或更高版本）
- Windows 环境原生支持
- 下载地址: https://docs.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server

### 2. 连接字符串变更

#### MySQL 格式（当前）
```
mysql+aiomysql://user:password@host:3306/database?charset=utf8mb4
```

#### SQL Server 格式（目标）
```
mssql+aioodbc://user:password@host:1433/database?driver=ODBC+Driver+17+for+SQL+Server&TrustServerCertificate=yes
```

**参数说明**:
- `mssql+aioodbc://` - SQLAlchemy 异步 SQL Server 方言
- `driver=ODBC+Driver+17+for+SQL+Server` - 指定 ODBC 驱动版本
- `TrustServerCertificate=yes` - 信任自签名证书（开发环境）

### 3. 代码文件修改

#### 3.1 数据库连接层 (`app/core/database.py`)

**变更内容**:
1. 移除 MySQL 驱动替换逻辑
2. 更新连接字符串格式
3. 添加 SQL Server 特定优化参数

**关键代码变更**:
```python
# 当前（MySQL）
DATABASE_URL = settings.DATABASE_URL.replace("pymysql", "aiomysql")

# 变更为（SQL Server）
DATABASE_URL = settings.DATABASE_URL  # 直接使用配置

# 引擎配置添加 SQL Server 优化
async_engine = create_async_engine(
    DATABASE_URL,
    echo=settings.DEBUG,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
    pool_recycle=3600,
    connect_args={
        "fast_executemany": True  # SQL Server 批量插入优化
    }
)
```

#### 3.2 配置类 (`app/core/config.py`)

**变更内容**:
- 更新 `DATABASE_URL` 的文档注释
- 添加 SQL Server 连接示例

#### 3.3 Alembic 配置 (`alembic/env.py`)

**变更内容**:
```python
# 当前（MySQL）
url = config.get_main_option("sqlalchemy.url").replace("mysql+pymysql", "mysql+aiomysql")

# 变更为（SQL Server）
url = config.get_main_option("sqlalchemy.url").replace("mssql+pyodbc", "mssql+aioodbc")
```

**注意**: 
- 同步连接使用 `pyodbc`
- 异步连接使用 `aioodbc`

#### 3.4 环境变量模板 (`.env.example`)

**新增 SQL Server 示例**:
```ini
# SQL Server 配置（Windows 本地开发）
DATABASE_URL=mssql+aioodbc://sa:YourPassword@localhost:1433/bap?driver=ODBC+Driver+17+for+SQL+Server&TrustServerCertificate=yes

# SQL Server 配置（企业服务器）
# DATABASE_URL=mssql+aioodbc://bap_user:password@sqlserver.company.com:1433/bap_prod?driver=ODBC+Driver+17+for+SQL+Server
```

#### 3.5 依赖文件 (`requirements.txt`)

完整变更见"数据库驱动变更"章节。

### 4. 数据库迁移重置

#### 4.1 删除现有迁移

**操作**:
```bash
# 删除所有现有迁移文件
rm alembic/versions/*.py

# 保留 versions 目录
# 保留 alembic/env.py, alembic/script.py.mako 等配置文件
```

**删除的文件**（共 6 个）:
- `2309ee286fa1_add_deleted_at_field_for_soft_delete.py`
- `453bb849db00_add_monitoring_tables.py`
- `4c6fb90372b0_add_flexible_config_and_monitoring.py`
- 以及其他 3 个迁移文件

#### 4.2 创建新的初始迁移

**操作**:
```bash
# 基于当前模型生成初始迁移
alembic revision --autogenerate -m "initial schema for sql server"
```

**预期结果**:
- 生成一个新的迁移文件（如 `abc123def456_initial_schema_for_sql_server.py`）
- 包含所有表的创建语句：
  - `crawler_configs` - 采集配置表
  - `job_queue` - 任务队列表
  - `crawler_results` - 采集结果表
  - 以及其他相关表

#### 4.3 验证生成的迁移

**检查清单**:
- [ ] 所有表定义完整
- [ ] 主键、外键正确
- [ ] 索引正确生成
- [ ] JSON 字段映射为 `NVARCHAR(MAX)`
- [ ] ENUM 字段映射为 `NVARCHAR` + CHECK 约束
- [ ] 时间字段映射为 `DATETIME2`

### 5. 数据类型映射

SQLAlchemy 自动处理以下类型映射：

| MySQL 类型 | SQL Server 类型 | Python 类型 | 说明 |
|-----------|----------------|------------|------|
| `VARCHAR(n)` | `NVARCHAR(n)` | `str` | 支持 Unicode |
| `TEXT` | `NVARCHAR(MAX)` | `str` | 大文本字段 |
| `JSON` | `NVARCHAR(MAX)` | `dict/list` | 自动序列化 |
| `DATETIME` | `DATETIME2` | `datetime` | 更高精度 |
| `INTEGER` | `INT` | `int` | 32 位整数 |
| `BOOLEAN` | `BIT` | `bool` | True/False |
| `ENUM` | `NVARCHAR(20)` + CHECK | `str` | 枚举约束 |

**重要说明**:
- 所有模型文件（`app/models/*.py`）**无需修改**
- SQLAlchemy ORM 自动处理类型转换
- 业务逻辑代码完全兼容

### 6. 初始化流程

#### 步骤 1: 安装 ODBC Driver
```bash
# 下载并安装 Microsoft ODBC Driver 17 for SQL Server
# 安装后验证：打开"ODBC 数据源管理器" (odbcad32.exe)
# 检查"驱动程序"选项卡中是否有 "ODBC Driver 17 for SQL Server"
```

#### 步骤 2: 创建数据库
```sql
-- 连接到 SQL Server Management Studio 或使用 sqlcmd
CREATE DATABASE bap
COLLATE Chinese_PRC_CI_AS;  -- 支持中文，不区分大小写

-- 创建应用用户（可选）
CREATE LOGIN bap_user WITH PASSWORD = 'YourStrongPassword123!';
USE bap;
CREATE USER bap_user FOR LOGIN bap_user;
ALTER ROLE db_owner ADD MEMBER bap_user;
```

#### 步骤 3: 更新 Python 依赖
```bash
# 卸载旧驱动
pip uninstall pymysql aiomysql -y

# 安装新驱动
pip install pyodbc==5.0.1 aioodbc==0.5.0
```

#### 步骤 4: 配置环境变量
```bash
# 修改 .env 文件
DATABASE_URL=mssql+aioodbc://sa:YourPassword@localhost:1433/bap?driver=ODBC+Driver+17+for+SQL+Server&TrustServerCertificate=yes
```

#### 步骤 5: 删除旧迁移文件
```bash
rm alembic/versions/*.py
```

#### 步骤 6: 生成新的初始迁移
```bash
alembic revision --autogenerate -m "initial schema for sql server"
```

#### 步骤 7: 执行迁移
```bash
alembic upgrade head
```

#### 步骤 8: 验证数据库结构
```sql
-- 检查表是否创建成功
SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_TYPE = 'BASE TABLE';

-- 检查字段定义
EXEC sp_help 'crawler_configs';
EXEC sp_help 'job_queue';
EXEC sp_help 'crawler_results';
```

#### 步骤 9: 启动应用测试
```bash
# 启动服务
uvicorn app.main:app --reload

# 测试健康检查
curl http://localhost:8000/health

# 测试 API 文档
# 浏览器访问: http://localhost:8000/docs
```

### 7. SQL Server 与 MySQL 关键差异

#### 7.1 字符串比较
- **MySQL**: 默认不区分大小写
- **SQL Server**: 取决于 COLLATE 设置
- **建议**: 使用 `Chinese_PRC_CI_AS`（CI = Case Insensitive）

#### 7.2 自增主键
- **MySQL**: `AUTO_INCREMENT`
- **SQL Server**: `IDENTITY(1,1)`
- **影响**: 无，SQLAlchemy 自动处理

#### 7.3 布尔类型
- **MySQL**: `TINYINT(1)` 或 `BOOLEAN`
- **SQL Server**: `BIT`
- **影响**: 无，Python 中仍使用 `True/False`

#### 7.4 JSON 字段
- **MySQL**: 原生 `JSON` 类型，支持 JSON 函数
- **SQL Server**: 存储为 `NVARCHAR(MAX)`，需要用 `JSON_VALUE()` 等函数查询
- **影响**: 
  - ORM 层面无影响（SQLAlchemy 自动序列化）
  - 如果有原生 JSON 查询需要重写

#### 7.5 时区处理
- 两者都存储本地时间，不包含时区信息
- **建议**: 统一使用 UTC 时间存储，显示时转换

#### 7.6 连接池行为
- SQL Server 连接建立比 MySQL 稍慢
- 建议保持现有配置：`pool_size=5`, `max_overflow=10`

### 8. 兼容性保证

**无需修改的代码**（100% 兼容）:
- ✅ 所有 ORM 模型（`app/models/`）
- ✅ 所有业务逻辑（`app/services/`）
- ✅ 所有 API 端点（`app/api/`）
- ✅ WebSocket 管理器
- ✅ 调度器逻辑
- ✅ 前端代码

**需要修改的代码**（仅底层配置）:
- ❌ `app/core/database.py` - 连接字符串
- ❌ `app/core/config.py` - 文档注释
- ❌ `alembic/env.py` - Alembic 配置
- ❌ `.env` 文件 - 环境变量
- ❌ `requirements.txt` - 依赖包

### 9. 风险评估

#### 低风险
- 项目未上线，无数据迁移风险
- SQLAlchemy ORM 抽象层保证兼容性
- 完全重置方案，无历史包袱

#### 中等风险
- ODBC Driver 安装和配置可能遇到权限问题
- 初次连接 SQL Server 可能需要调整防火墙
- 连接字符串格式需要准确配置

#### 缓解措施
- 提供详细的安装和配置文档
- 在测试环境完整验证后再应用到开发环境
- 保留 MySQL 版本代码作为备份（Git 分支）

### 10. 测试计划

#### 单元测试
- 数据库连接测试
- 模型 CRUD 操作测试
- JSON 字段序列化/反序列化测试

#### 集成测试
- 完整任务执行流程
- WebSocket 推送功能
- 调度器失败重试
- 登录态管理

#### 端到端测试
- 使用 `scripts/final_e2e_test.py`
- 创建配置 → 创建任务 → 执行任务 → 验证结果

### 11. 回滚方案

如果迁移遇到严重问题，可以快速回滚到 MySQL：

```bash
# 1. 切换到 MySQL 分支
git checkout main  # 或迁移前的 commit

# 2. 恢复依赖
pip uninstall pyodbc aioodbc -y
pip install pymysql==1.1.1 aiomysql==0.2.0

# 3. 恢复环境变量
# 修改 .env 为 MySQL 连接字符串

# 4. 恢复数据库
mysql -u root -p bap < backup.sql  # 如有备份
```

### 12. 文档更新

需要更新的文档：
- `CLAUDE.md` - 技术栈和常用命令
- `README.md` - 快速开始指南
- `docs/database_usage.md` - 数据库操作指南
- `.env.example` - 环境变量示例

### 13. 实施时间线

1. **准备阶段**（1 小时）
   - 安装 ODBC Driver
   - 创建 SQL Server 数据库
   - 创建 Git 分支

2. **代码修改**（1 小时）
   - 修改连接配置
   - 更新依赖文件
   - 删除旧迁移

3. **测试验证**（1 小时）
   - 生成新迁移
   - 执行迁移
   - 运行完整测试

4. **文档更新**（30 分钟）
   - 更新 CLAUDE.md
   - 更新 README.md

**总计**: 约 3.5 小时

## 总结

采用完全重置方案将数据库从 MySQL 迁移到 SQL Server，利用 SQLAlchemy ORM 的抽象能力，最小化代码修改范围。项目未上线的优势使我们能够采用最简洁、最易维护的方案。

**关键优势**:
- 代码改动最小（仅配置层）
- 业务逻辑零修改
- 干净的数据库迁移历史
- 完全符合企业标准

**成功标准**:
- 应用正常启动
- 健康检查通过
- 所有测试用例通过
- 完整的端到端流程验证成功
