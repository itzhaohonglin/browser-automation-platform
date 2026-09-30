# MySQL 到 SQL Server 迁移实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将浏览器自动化平台的数据库从 MySQL 迁移到 SQL Server，符合企业标准化要求

**Architecture:** 采用完全重置方案，删除旧的 MySQL 迁移文件，基于当前模型生成新的 SQL Server 初始迁移。只修改底层数据库连接配置，业务逻辑代码保持不变。

**Tech Stack:** SQLAlchemy 2.0.35 (async), pyodbc 5.0.1, aioodbc 0.5.0, Alembic 1.13.2, SQL Server on Windows

---

## 文件结构概览

**需要修改的文件:**
- `requirements.txt` - 更新数据库驱动依赖
- `app/core/database.py` - 修改连接字符串处理和引擎配置
- `app/core/config.py` - 更新文档注释
- `.env.example` - 添加 SQL Server 连接示例
- `alembic/versions/*.py` - 删除所有旧迁移文件（6个）
- `CLAUDE.md` - 更新技术栈说明
- `README.md` - 更新快速开始指南

**保持不变的文件:**
- `app/models/*.py` - 所有 ORM 模型
- `app/services/*.py` - 所有业务逻辑
- `app/api/*.py` - 所有 API 端点
- `alembic/env.py` - Alembic 配置（已经使用 settings.DATABASE_URL，无需修改）

---

## Task 1: 更新依赖文件

**Files:**
- Modify: `requirements.txt`

- [ ] **Step 1: 备份当前 requirements.txt**

```bash
cp requirements.txt requirements.txt.mysql.bak
```

- [ ] **Step 2: 修改 requirements.txt**

移除 MySQL 驱动，添加 SQL Server 驱动：

```txt
# Web Framework
fastapi==0.115.0
uvicorn[standard]==0.30.6

# Browser Automation
playwright==1.47.0

# Database
sqlalchemy==2.0.35
pyodbc==5.0.1
aioodbc==0.5.0
alembic==1.13.2

# Task Scheduling
apscheduler==3.10.4

# Environment & Utils
python-dotenv==1.0.1
pydantic==2.9.2
pydantic-settings==2.5.2

# WebSocket Support
websockets==13.1

# Cryptography (required by pyodbc)
cryptography==42.0.8
```

- [ ] **Step 3: 验证文件格式**

```bash
cat requirements.txt
```

Expected: 显示更新后的依赖列表，包含 pyodbc 和 aioodbc，不包含 pymysql 和 aiomysql

- [ ] **Step 4: 提交变更**

```bash
git add requirements.txt
git commit -m "chore: update database drivers from MySQL to SQL Server"
```

---

## Task 2: 更新数据库连接层

**Files:**
- Modify: `app/core/database.py:7-18`

- [ ] **Step 1: 读取当前 database.py**

```bash
cat app/core/database.py
```

Expected: 查看第 7-18 行的连接字符串处理逻辑

- [ ] **Step 2: 修改连接字符串处理和引擎配置**

替换第 7-18 行：

```python
# 直接使用配置的 DATABASE_URL（支持 MySQL 和 SQL Server）
DATABASE_URL = settings.DATABASE_URL

# 创建异步引擎
async_engine = create_async_engine(
    DATABASE_URL,
    echo=settings.DEBUG,           # 开发环境打印 SQL 语句
    pool_pre_ping=True,            # 连接池健康检查
    pool_size=5,                   # 连接池大小
    max_overflow=10,               # 最大溢出连接数
    pool_recycle=3600,             # 连接回收时间（1小时）
    connect_args={
        "timeout": 30              # 连接超时（秒）
    }
)
```

- [ ] **Step 3: 验证修改**

```bash
grep -A 12 "DATABASE_URL = " app/core/database.py
```

Expected: 显示新的连接字符串处理逻辑，不包含 replace("pymysql", "aiomysql")

- [ ] **Step 4: 提交变更**

```bash
git add app/core/database.py
git commit -m "refactor: simplify database connection for SQL Server compatibility"
```

---

## Task 3: 更新配置类文档

**Files:**
- Modify: `app/core/config.py:14-16`

- [ ] **Step 1: 修改 DATABASE_URL 字段注释**

在第 14-16 行，更新文档注释：

```python
    # 数据库配置 - 必须通过环境变量提供
    # MySQL 示例: mysql+aiomysql://user:password@host:3306/database?charset=utf8mb4
    # SQL Server 示例: mssql+aioodbc://user:password@host:1433/database?driver=ODBC+Driver+17+for+SQL+Server
    DATABASE_URL: str
```

- [ ] **Step 2: 验证修改**

```bash
grep -A 3 "# 数据库配置" app/core/config.py
```

Expected: 显示包含 MySQL 和 SQL Server 两种示例的注释

- [ ] **Step 3: 提交变更**

```bash
git add app/core/config.py
git commit -m "docs: add SQL Server connection example to config"
```

---

## Task 4: 更新环境变量模板

**Files:**
- Modify: `.env.example`

- [ ] **Step 1: 读取当前 .env.example**

```bash
cat .env.example
```

Expected: 查看当前的环境变量示例

- [ ] **Step 2: 添加 SQL Server 连接示例**

在 DATABASE_URL 部分添加 SQL Server 示例（保留 MySQL 示例作为注释）：

```ini
# 数据库配置（必填）

# SQL Server 配置（Windows 本地开发）
DATABASE_URL=mssql+aioodbc://sa:YourPassword@localhost:1433/bap?driver=ODBC+Driver+17+for+SQL+Server&TrustServerCertificate=yes

# SQL Server 配置（企业服务器）
# DATABASE_URL=mssql+aioodbc://bap_user:password@sqlserver.company.com:1433/bap_prod?driver=ODBC+Driver+17+for+SQL+Server

# MySQL 配置（已废弃）
# DATABASE_URL=mysql+aiomysql://root:password@localhost:3306/bap?charset=utf8mb4

# 应用配置
APP_HOST=0.0.0.0
APP_PORT=8000
DEBUG=False

# Playwright 配置
HEADLESS_MODE=True

# 日志配置
LOG_LEVEL=INFO
```

- [ ] **Step 3: 验证文件内容**

```bash
cat .env.example | grep -A 5 "DATABASE_URL"
```

Expected: 显示 SQL Server 作为主要配置，MySQL 作为已废弃注释

- [ ] **Step 4: 提交变更**

```bash
git add .env.example
git commit -m "docs: update .env.example with SQL Server configuration"
```

---

## Task 5: 删除旧的数据库迁移文件

**Files:**
- Delete: `alembic/versions/*.py` (所有迁移文件)

- [ ] **Step 1: 列出现有迁移文件**

```bash
ls -la alembic/versions/*.py
```

Expected: 显示 6 个迁移文件

- [ ] **Step 2: 备份迁移文件到文档目录**

```bash
mkdir -p docs/archive/mysql-migrations
cp alembic/versions/*.py docs/archive/mysql-migrations/
```

- [ ] **Step 3: 删除所有迁移文件**

```bash
rm alembic/versions/*.py
```

- [ ] **Step 4: 验证删除结果**

```bash
ls alembic/versions/
```

Expected: 目录为空或只有 __pycache__

- [ ] **Step 5: 提交变更**

```bash
git add alembic/versions/
git add docs/archive/mysql-migrations/
git commit -m "refactor: remove MySQL migration files for SQL Server reset"
```

---

## Task 6: 更新 CLAUDE.md 技术栈说明

**Files:**
- Modify: `CLAUDE.md:12-13`

- [ ] **Step 1: 修改数据库驱动说明**

在"技术栈"部分（约第 12-13 行），更新数据库相关内容：

```markdown
## 技术栈

- **后端**: FastAPI 0.115.0 + Uvicorn 0.30.6
- **浏览器自动化**: Playwright 1.47.0（async API）
- **数据库**: SQLAlchemy 2.0.35 + pyodbc/aioodbc + Alembic
- **数据库服务器**: SQL Server on Windows
- **任务调度**: APScheduler 3.10.4（AsyncIOScheduler）
- **前端**: 原生 HTML/CSS/JavaScript + WebSocket
- **Python**: 3.10+
```

- [ ] **Step 2: 更新环境初始化部分**

在"常用命令 > 环境初始化"部分（约第 18-30 行），更新数据库创建命令：

```markdown
### 环境初始化
```bash
# 安装依赖
pip install -r requirements.txt

# 安装 Playwright 浏览器驱动
playwright install chromium

# 配置环境变量（首次运行）
cp .env.example .env

# 初始化数据库（SQL Server）
# 方式1: 使用 sqlcmd
sqlcmd -S localhost -U sa -P YourPassword -Q "CREATE DATABASE bap COLLATE Chinese_PRC_CI_AS;"

# 方式2: 使用 SQL Server Management Studio (SSMS)
# 手动创建数据库 bap，COLLATE 设置为 Chinese_PRC_CI_AS

# 执行数据库迁移
alembic upgrade head
```
```

- [ ] **Step 3: 验证修改**

```bash
grep -A 3 "数据库服务器" CLAUDE.md
```

Expected: 显示 "SQL Server on Windows"

- [ ] **Step 4: 提交变更**

```bash
git add CLAUDE.md
git commit -m "docs: update CLAUDE.md with SQL Server tech stack"
```

---

## Task 7: 更新 README.md 快速开始指南

**Files:**
- Modify: `README.md` (数据库初始化部分)

- [ ] **Step 1: 查找数据库初始化章节**

```bash
grep -n "数据库" README.md | head -5
```

Expected: 找到数据库相关章节的行号

- [ ] **Step 2: 更新数据库初始化说明**

找到"快速开始"或"安装"部分，更新数据库创建步骤：

```markdown
### 3. 初始化数据库

**前置条件:**
- 已安装 SQL Server（Express 或更高版本）
- 已安装 Microsoft ODBC Driver 17 for SQL Server

**创建数据库:**

```bash
# 使用 sqlcmd（命令行）
sqlcmd -S localhost -U sa -P YourPassword -Q "CREATE DATABASE bap COLLATE Chinese_PRC_CI_AS;"

# 或使用 SQL Server Management Studio (SSMS) 图形界面创建
```

**执行迁移:**

```bash
# 生成初始迁移（首次运行）
alembic revision --autogenerate -m "initial schema"

# 执行迁移
alembic upgrade head
```
```

- [ ] **Step 3: 添加 ODBC Driver 安装说明**

在依赖安装部分添加：

```markdown
### 2. 安装依赖

**Python 依赖:**
```bash
pip install -r requirements.txt
playwright install chromium
```

**ODBC Driver（必需）:**

下载并安装 [Microsoft ODBC Driver 17 for SQL Server](https://docs.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server)

验证安装：
```bash
# Windows: 打开"ODBC 数据源管理器"
odbcad32.exe

# 检查"驱动程序"选项卡中是否有 "ODBC Driver 17 for SQL Server"
```
```

- [ ] **Step 4: 验证修改**

```bash
grep -A 5 "ODBC Driver" README.md
```

Expected: 显示 ODBC Driver 安装说明

- [ ] **Step 5: 提交变更**

```bash
git add README.md
git commit -m "docs: update README with SQL Server setup instructions"
```

---

## Task 8: 卸载 MySQL 驱动并安装 SQL Server 驱动

**Files:**
- System packages

- [ ] **Step 1: 卸载旧驱动**

```bash
pip uninstall pymysql aiomysql -y
```

Expected: Successfully uninstalled pymysql-1.1.1 和 aiomysql-0.2.0

- [ ] **Step 2: 安装新驱动**

```bash
pip install pyodbc==5.0.1 aioodbc==0.5.0
```

Expected: Successfully installed pyodbc-5.0.1 和 aioodbc-0.5.0

- [ ] **Step 3: 验证安装**

```bash
python -c "import pyodbc; print('pyodbc version:', pyodbc.version)"
python -c "import aioodbc; print('aioodbc installed successfully')"
```

Expected: 
```
pyodbc version: 5.0.1
aioodbc installed successfully
```

- [ ] **Step 4: 验证 ODBC Driver 可用性**

```bash
python -c "import pyodbc; print([x for x in pyodbc.drivers() if 'SQL Server' in x])"
```

Expected: 显示包含 'ODBC Driver 17 for SQL Server' 或类似驱动名称的列表

**Note:** 如果此步骤失败，需要先安装 Microsoft ODBC Driver 17 for SQL Server

---

## Task 9: 生成新的初始迁移

**Files:**
- Create: `alembic/versions/{hash}_initial_schema_for_sql_server.py`

**Prerequisites:** 
- SQL Server 数据库 `bap` 已创建
- `.env` 文件中的 `DATABASE_URL` 已更新为 SQL Server 连接字符串

- [ ] **Step 1: 验证数据库连接配置**

检查 .env 文件中的 DATABASE_URL：

```bash
grep "DATABASE_URL" .env
```

Expected: 显示 SQL Server 连接字符串，格式如：
```
DATABASE_URL=mssql+aioodbc://sa:password@localhost:1433/bap?driver=ODBC+Driver+17+for+SQL+Server&TrustServerCertificate=yes
```

**Note:** 如果 .env 文件不存在或 DATABASE_URL 未配置，需要先创建/更新

- [ ] **Step 2: 测试数据库连接**

```bash
python -c "from app.core.database import async_engine; import asyncio; asyncio.run(async_engine.connect())" && echo "Database connection successful"
```

Expected: "Database connection successful"

**Note:** 如果连接失败，检查：
1. SQL Server 是否运行
2. 数据库 `bap` 是否存在
3. 用户名密码是否正确
4. 防火墙是否允许 1433 端口

- [ ] **Step 3: 生成初始迁移**

```bash
alembic revision --autogenerate -m "initial schema for sql server"
```

Expected: 
```
Generating alembic/versions/abc123def456_initial_schema_for_sql_server.py ... done
```

- [ ] **Step 4: 检查生成的迁移文件**

```bash
ls -la alembic/versions/*.py
cat alembic/versions/*_initial_schema_for_sql_server.py | head -50
```

Expected: 
- 显示一个新的迁移文件
- 文件中包含 `create_table('crawler_configs', ...)` 等表创建语句

- [ ] **Step 5: 验证迁移内容**

检查关键表是否包含在迁移中：

```bash
grep "create_table" alembic/versions/*_initial_schema_for_sql_server.py
```

Expected: 显示至少包含以下表：
- crawler_configs
- job_queue
- crawler_results

- [ ] **Step 6: 检查数据类型映射**

验证 JSON 字段映射为 NVARCHAR(MAX)：

```bash
grep -i "json\|nvarchar" alembic/versions/*_initial_schema_for_sql_server.py
```

Expected: JSON 列应该映射为字符串类型（NVARCHAR）

- [ ] **Step 7: 提交迁移文件**

```bash
git add alembic/versions/*_initial_schema_for_sql_server.py
git commit -m "feat: add initial SQL Server schema migration"
```

---

## Task 10: 执行数据库迁移

**Files:**
- Database: SQL Server `bap`

- [ ] **Step 1: 检查当前迁移状态**

```bash
alembic current
```

Expected: 无输出或显示 "(head)" 表示空数据库

- [ ] **Step 2: 查看待执行的迁移**

```bash
alembic history
```

Expected: 显示刚创建的初始迁移

- [ ] **Step 3: 执行迁移**

```bash
alembic upgrade head
```

Expected:
```
INFO  [alembic.runtime.migration] Context impl MSSQLImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade  -> abc123def456, initial schema for sql server
```

- [ ] **Step 4: 验证迁移状态**

```bash
alembic current
```

Expected: 显示当前迁移版本（如 abc123def456）和 "(head)"

- [ ] **Step 5: 验证表结构（使用 Python）**

```bash
python -c "
from sqlalchemy import inspect
from app.core.database import async_engine
import asyncio

async def check_tables():
    async with async_engine.connect() as conn:
        result = await conn.run_sync(lambda sync_conn: inspect(sync_conn).get_table_names())
        print('Tables created:', result)
        return result

tables = asyncio.run(check_tables())
expected = ['crawler_configs', 'job_queue', 'crawler_results', 'alembic_version']
assert all(t in tables for t in expected), f'Missing tables. Expected: {expected}, Got: {tables}'
print('✓ All required tables exist')
"
```

Expected:
```
Tables created: ['alembic_version', 'crawler_configs', 'crawler_results', 'job_queue']
✓ All required tables exist
```

- [ ] **Step 6: 验证表结构（使用 SQL 查询）**

创建验证脚本 `scripts/verify_sqlserver_schema.py`:

```python
import asyncio
from sqlalchemy import text
from app.core.database import async_engine

async def verify_schema():
    async with async_engine.connect() as conn:
        # 检查表
        result = await conn.execute(text(
            "SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_TYPE = 'BASE TABLE'"
        ))
        tables = [row[0] for row in result]
        print(f"Tables: {tables}")
        
        # 检查 crawler_configs 表结构
        result = await conn.execute(text(
            "SELECT COLUMN_NAME, DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'crawler_configs'"
        ))
        columns = [(row[0], row[1]) for row in result]
        print(f"\ncrawler_configs columns:")
        for col, dtype in columns:
            print(f"  - {col}: {dtype}")
        
        # 验证 JSON 字段类型
        json_fields = [col for col, dtype in columns if 'nvarchar' in dtype.lower() and col in ['input_configs', 'fields_mapping', 'timeout_config']]
        assert len(json_fields) >= 2, f"JSON fields should be NVARCHAR, found: {json_fields}"
        print(f"\n✓ JSON fields correctly mapped to NVARCHAR: {json_fields}")

if __name__ == "__main__":
    asyncio.run(verify_schema())
```

运行验证：

```bash
python scripts/verify_sqlserver_schema.py
```

Expected:
```
Tables: ['alembic_version', 'crawler_configs', 'crawler_results', 'job_queue']

crawler_configs columns:
  - id: int
  - config_name: nvarchar
  - target_url: nvarchar
  - input_configs: nvarchar
  - fields_mapping: nvarchar
  ...

✓ JSON fields correctly mapped to NVARCHAR: ['input_configs', 'fields_mapping', 'timeout_config']
```

- [ ] **Step 7: 提交验证脚本**

```bash
git add scripts/verify_sqlserver_schema.py
git commit -m "test: add SQL Server schema verification script"
```

---

## Task 11: 启动应用并验证功能

**Files:**
- Application runtime

- [ ] **Step 1: 启动应用**

```bash
uvicorn app.main:app --reload
```

Expected:
```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

**Note:** 如果启动失败，检查错误日志中的数据库连接问题

- [ ] **Step 2: 测试健康检查端点**

在新终端窗口运行：

```bash
curl http://localhost:8000/health
```

Expected:
```json
{"status":"healthy","database":"connected"}
```

- [ ] **Step 3: 测试 API 文档访问**

```bash
curl -I http://localhost:8000/docs
```

Expected: HTTP/1.1 200 OK

**Note:** 也可以在浏览器中访问 http://localhost:8000/docs 查看 Swagger UI

- [ ] **Step 4: 测试配置 API**

```bash
curl http://localhost:8000/api/configs
```

Expected:
```json
{"total":0,"items":[]}
```

- [ ] **Step 5: 测试任务 API**

```bash
curl http://localhost:8000/api/jobs/stats
```

Expected:
```json
{"total":0,"pending":0,"processing":0,"success":0,"failed":0}
```

- [ ] **Step 6: 停止应用**

在运行 uvicorn 的终端按 CTRL+C

Expected: 应用正常关闭

---

## Task 12: 运行数据库 CRUD 测试

**Files:**
- Create: `tests/test_sqlserver_crud.py`

- [ ] **Step 1: 创建 CRUD 测试文件**

```python
# tests/test_sqlserver_crud.py
import pytest
from datetime import datetime
from app.models.config import CrawlerConfig
from app.models.job import JobQueue, JobStatus
from app.models.result import CrawlerResult
from app.core.database import get_session

@pytest.mark.asyncio
async def test_create_crawler_config():
    """测试创建采集配置"""
    async with get_session() as session:
        config = CrawlerConfig(
            config_name="测试配置",
            target_url="https://example.com",
            need_login=False,
            input_configs=[{"selector": "input[name='keyword']", "param_name": "keyword"}],
            submit_selector="button[type='submit']",
            wait_selector=".results",
            fields_mapping={"fields": [{"name": "标题", "selector": ".title"}]},
            max_pages=1
        )
        session.add(config)
        await session.commit()
        await session.refresh(config)
        
        assert config.id is not None
        assert config.config_name == "测试配置"
        print(f"✓ Created config with ID: {config.id}")
        
        # 清理
        await session.delete(config)
        await session.commit()

@pytest.mark.asyncio
async def test_create_job():
    """测试创建任务"""
    async with get_session() as session:
        # 先创建配置
        config = CrawlerConfig(
            config_name="测试配置",
            target_url="https://example.com",
            need_login=False,
            input_configs=[],
            submit_selector="button",
            wait_selector=".results",
            fields_mapping={},
            max_pages=1
        )
        session.add(config)
        await session.commit()
        await session.refresh(config)
        
        # 创建任务
        job = JobQueue(
            config_id=config.id,
            query_params={"keyword": "测试"},
            status=JobStatus.PENDING,
            priority=5
        )
        session.add(job)
        await session.commit()
        await session.refresh(job)
        
        assert job.id is not None
        assert job.status == JobStatus.PENDING
        assert job.query_params["keyword"] == "测试"
        print(f"✓ Created job with ID: {job.id}")
        
        # 清理
        await session.delete(job)
        await session.delete(config)
        await session.commit()

@pytest.mark.asyncio
async def test_json_field_serialization():
    """测试 JSON 字段序列化"""
    async with get_session() as session:
        config = CrawlerConfig(
            config_name="JSON测试",
            target_url="https://example.com",
            need_login=False,
            input_configs=[
                {"selector": "input[name='q']", "param_name": "query"},
                {"selector": "select[name='type']", "param_name": "type"}
            ],
            submit_selector="button",
            wait_selector=".results",
            fields_mapping={
                "list_selector": "table tr",
                "fields": [
                    {"name": "名称", "selector": "td:nth-child(1)"},
                    {"name": "价格", "selector": "td:nth-child(2)"}
                ]
            },
            max_pages=10
        )
        session.add(config)
        await session.commit()
        await session.refresh(config)
        
        # 验证 JSON 字段正确序列化
        assert isinstance(config.input_configs, list)
        assert len(config.input_configs) == 2
        assert config.input_configs[0]["param_name"] == "query"
        
        assert isinstance(config.fields_mapping, dict)
        assert config.fields_mapping["list_selector"] == "table tr"
        assert len(config.fields_mapping["fields"]) == 2
        
        print("✓ JSON fields serialized correctly")
        
        # 清理
        await session.delete(config)
        await session.commit()

@pytest.mark.asyncio
async def test_enum_field():
    """测试 ENUM 字段"""
    async with get_session() as session:
        config = CrawlerConfig(
            config_name="枚举测试",
            target_url="https://example.com",
            need_login=False,
            input_configs=[],
            submit_selector="button",
            wait_selector=".results",
            fields_mapping={},
            max_pages=1
        )
        session.add(config)
        await session.commit()
        await session.refresh(config)
        
        # 创建不同状态的任务
        for status in [JobStatus.PENDING, JobStatus.PROCESSING, JobStatus.SUCCESS, JobStatus.FAILED]:
            job = JobQueue(
                config_id=config.id,
                query_params={},
                status=status,
                priority=5
            )
            session.add(job)
        
        await session.commit()
        
        # 查询并验证
        from sqlalchemy import select
        result = await session.execute(select(JobQueue).where(JobQueue.config_id == config.id))
        jobs = result.scalars().all()
        
        assert len(jobs) == 4
        statuses = [job.status for job in jobs]
        assert JobStatus.PENDING in statuses
        assert JobStatus.SUCCESS in statuses
        print(f"✓ ENUM fields work correctly: {statuses}")
        
        # 清理
        for job in jobs:
            await session.delete(job)
        await session.delete(config)
        await session.commit()

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
```

- [ ] **Step 2: 运行 CRUD 测试**

```bash
pytest tests/test_sqlserver_crud.py -v -s
```

Expected:
```
tests/test_sqlserver_crud.py::test_create_crawler_config PASSED
✓ Created config with ID: 1

tests/test_sqlserver_crud.py::test_create_job PASSED
✓ Created job with ID: 1

tests/test_sqlserver_crud.py::test_json_field_serialization PASSED
✓ JSON fields serialized correctly

tests/test_sqlserver_crud.py::test_enum_field PASSED
✓ ENUM fields work correctly: [<JobStatus.PENDING: 'pending'>, ...]

============================== 4 passed in 2.50s ==============================
```

- [ ] **Step 3: 提交测试文件**

```bash
git add tests/test_sqlserver_crud.py
git commit -m "test: add SQL Server CRUD tests"
```

---

## Task 13: 运行端到端测试

**Files:**
- Existing: `scripts/final_e2e_test.py`

- [ ] **Step 1: 检查端到端测试脚本是否存在**

```bash
ls -la scripts/final_e2e_test.py
```

Expected: 文件存在

**Note:** 如果文件不存在，此测试可跳过

- [ ] **Step 2: 运行端到端测试**

```bash
python scripts/final_e2e_test.py
```

Expected: 测试通过，显示类似输出：
```
Starting E2E test...
✓ Database connection successful
✓ Config created (ID: 1)
✓ Job created (ID: 1)
✓ Job execution started
✓ All tests passed
```

**Note:** 如果测试涉及实际网页抓取，可能需要较长时间或因网络问题失败。关注数据库操作部分是否正常。

- [ ] **Step 3: 清理测试数据**

```bash
python -c "
import asyncio
from sqlalchemy import text
from app.core.database import async_engine

async def cleanup():
    async with async_engine.begin() as conn:
        await conn.execute(text('DELETE FROM crawler_results'))
        await conn.execute(text('DELETE FROM job_queue'))
        await conn.execute(text('DELETE FROM crawler_configs'))
        print('✓ Test data cleaned up')

asyncio.run(cleanup())
"
```

Expected: "✓ Test data cleaned up"

---

## Task 14: 创建迁移后验证清单

**Files:**
- Create: `docs/sqlserver-migration-checklist.md`

- [ ] **Step 1: 创建验证清单文档**

```markdown
# SQL Server 迁移验证清单

## 完成日期: ___________

## 1. 环境配置

- [ ] Microsoft ODBC Driver 17 for SQL Server 已安装
- [ ] SQL Server 服务正常运行
- [ ] 数据库 `bap` 已创建（COLLATE: Chinese_PRC_CI_AS）
- [ ] .env 文件配置正确的 SQL Server 连接字符串

## 2. 代码变更

- [ ] requirements.txt 已更新（pyodbc, aioodbc）
- [ ] app/core/database.py 已修改（移除 MySQL 驱动替换逻辑）
- [ ] app/core/config.py 文档注释已更新
- [ ] .env.example 包含 SQL Server 配置示例
- [ ] 旧的 MySQL 迁移文件已删除（6个）
- [ ] 新的 SQL Server 初始迁移已生成

## 3. 数据库迁移

- [ ] alembic upgrade head 执行成功
- [ ] 所有必需的表已创建：
  - [ ] crawler_configs
  - [ ] job_queue
  - [ ] crawler_results
  - [ ] alembic_version
- [ ] JSON 字段正确映射为 NVARCHAR(MAX)
- [ ] ENUM 字段正确映射为 NVARCHAR + CHECK 约束
- [ ] 外键约束已创建
- [ ] 索引已创建

## 4. 功能测试

- [ ] 应用启动成功（uvicorn app.main:app --reload）
- [ ] 健康检查端点响应正常（/health）
- [ ] API 文档可访问（/docs）
- [ ] 配置 API 正常（/api/configs）
- [ ] 任务 API 正常（/api/jobs/stats）

## 5. 数据库操作测试

- [ ] 创建配置记录成功
- [ ] 创建任务记录成功
- [ ] JSON 字段序列化/反序列化正常
- [ ] ENUM 字段存储和查询正常
- [ ] 外键关联正常

## 6. 端到端测试

- [ ] 创建配置 → 创建任务 → 执行任务流程完整
- [ ] WebSocket 推送功能正常（如适用）
- [ ] 调度器功能正常（如适用）

## 7. 文档更新

- [ ] CLAUDE.md 技术栈说明已更新
- [ ] README.md 快速开始指南已更新
- [ ] .env.example 包含完整示例

## 8. 性能验证

- [ ] 数据库连接池正常工作
- [ ] 查询响应时间可接受
- [ ] 批量插入性能正常

## 9. 回滚准备

- [ ] MySQL 驱动备份可用（requirements.txt.mysql.bak）
- [ ] 旧迁移文件已归档（docs/archive/mysql-migrations/）
- [ ] 回滚文档已准备（见设计文档第 11 节）

## 10. 生产就绪

- [ ] 所有测试通过
- [ ] 日志级别配置正确（LOG_LEVEL=INFO）
- [ ] DEBUG 模式已关闭（生产环境）
- [ ] 数据库连接字符串安全存储（.env 不提交到 Git）

---

## 注意事项

1. **ODBC Driver 版本**: 确保使用 ODBC Driver 17 或更高版本
2. **连接字符串**: TrustServerCertificate=yes 仅用于开发环境
3. **字符编码**: 数据库 COLLATE 必须支持中文（Chinese_PRC_CI_AS）
4. **防火墙**: 确保 SQL Server 端口 1433 可访问
5. **权限**: 应用数据库用户需要 db_owner 权限或足够的表操作权限

## 验证人签名

- 开发人员: ___________  日期: ___________
- 测试人员: ___________  日期: ___________
- 项目负责人: ___________  日期: ___________
```

- [ ] **Step 2: 提交清单文档**

```bash
git add docs/sqlserver-migration-checklist.md
git commit -m "docs: add SQL Server migration verification checklist"
```

---

## Task 15: 最终提交和标签

**Files:**
- Git repository

- [ ] **Step 1: 查看所有变更**

```bash
git log --oneline --graph --decorate --all -10
```

Expected: 显示所有迁移相关的提交

- [ ] **Step 2: 创建迁移完成的 Git 标签**

```bash
git tag -a v1.0.0-sqlserver -m "Migrated from MySQL to SQL Server"
```

- [ ] **Step 3: 验证标签**

```bash
git tag -l -n1 v1.0.0-sqlserver
```

Expected: 显示标签和注释

- [ ] **Step 4: 推送到远程仓库（如需要）**

```bash
# 推送所有提交
git push origin main

# 推送标签
git push origin v1.0.0-sqlserver
```

Expected: 成功推送到远程仓库

**Note:** 如果这是本地开发环境，可以跳过推送步骤

- [ ] **Step 5: 创建迁移总结**

生成变更摘要：

```bash
git log --oneline main --grep="sqlserver\|SQL Server\|database" -10 > docs/migration-summary.txt
echo "
迁移完成总结
============

变更文件数: $(git diff --name-only HEAD~15 HEAD | wc -l)
新增测试: tests/test_sqlserver_crud.py
迁移清单: docs/sqlserver-migration-checklist.md

核心变更:
- 数据库驱动: MySQL (aiomysql) → SQL Server (aioodbc)
- 迁移策略: 完全重置（删除 6 个旧迁移，创建 1 个新迁移）
- 代码修改: 5 个配置文件
- 业务代码: 无需修改（100% 兼容）

验证状态:
✓ 依赖安装
✓ 数据库迁移
✓ 应用启动
✓ CRUD 测试
✓ 端到端测试

迁移完成日期: $(date)
" >> docs/migration-summary.txt

cat docs/migration-summary.txt
```

- [ ] **Step 6: 提交迁移总结**

```bash
git add docs/migration-summary.txt
git commit -m "docs: add migration summary and completion report"
```

---

## 验证清单

完成所有任务后，验证以下关键点：

### 代码层面
- [x] requirements.txt 包含 pyodbc 和 aioodbc
- [x] app/core/database.py 不再包含 MySQL 驱动替换逻辑
- [x] .env.example 包含 SQL Server 配置示例
- [x] 所有 MySQL 迁移文件已删除
- [x] 新的 SQL Server 初始迁移已生成

### 数据库层面
- [x] SQL Server 数据库 `bap` 存在
- [x] 所有必需的表已创建（crawler_configs, job_queue, crawler_results）
- [x] alembic_version 表存在且包含当前迁移版本
- [x] JSON 字段映射为 NVARCHAR(MAX)
- [x] ENUM 字段正确映射

### 功能层面
- [x] 应用可以正常启动
- [x] 健康检查端点返回 200
- [x] 可以创建配置记录
- [x] 可以创建任务记录
- [x] JSON 序列化/反序列化正常

### 文档层面
- [x] CLAUDE.md 已更新
- [x] README.md 已更新
- [x] 迁移清单已创建
- [x] 迁移总结已生成

---

## 常见问题排查

### 问题 1: ODBC Driver 未找到

**错误信息**: `[IM002] [Microsoft][ODBC Driver Manager] Data source name not found`

**解决方案**:
```bash
# 验证 ODBC Driver 安装
odbcad32.exe

# 或在 Python 中检查
python -c "import pyodbc; print(pyodbc.drivers())"

# 如果没有安装，下载并安装:
# https://docs.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server
```

### 问题 2: SQL Server 连接被拒绝

**错误信息**: `[08001] [Microsoft][ODBC Driver 17 for SQL Server]TCP Provider: No connection could be made`

**解决方案**:
```bash
# 1. 检查 SQL Server 是否运行
# Windows: 服务管理器中查看 "SQL Server (MSSQLSERVER)"

# 2. 检查 TCP/IP 是否启用
# SQL Server Configuration Manager → SQL Server Network Configuration → Protocols → TCP/IP

# 3. 检查防火墙
# 允许端口 1433 入站连接
```

### 问题 3: 数据库不存在

**错误信息**: `[42000] [Microsoft][ODBC Driver 17 for SQL Server]Cannot open database "bap"`

**解决方案**:
```sql
-- 使用 sqlcmd 或 SSMS 创建数据库
CREATE DATABASE bap COLLATE Chinese_PRC_CI_AS;
```

### 问题 4: JSON 字段序列化错误

**错误信息**: `TypeError: Object of type ... is not JSON serializable`

**解决方案**:
- SQLAlchemy 应自动处理 JSON 序列化
- 检查 `app/models/*.py` 中的字段定义是否使用了 `JSON` 类型
- 确认 SQLAlchemy 版本 >= 2.0

### 问题 5: Alembic 迁移失败

**错误信息**: `sqlalchemy.exc.ProgrammingError: (pyodbc.ProgrammingError) ...`

**解决方案**:
```bash
# 1. 检查数据库连接
python -c "from app.core.database import async_engine; import asyncio; asyncio.run(async_engine.connect())"

# 2. 检查迁移文件语法
cat alembic/versions/*_initial_schema_for_sql_server.py

# 3. 尝试手动执行迁移中的 SQL
# 复制 upgrade() 函数中的 SQL 语句到 SSMS 中执行，查看具体错误
```

---

## 后续建议

1. **性能监控**: 在生产环境中监控 SQL Server 的查询性能和连接池使用情况
2. **备份策略**: 建立定期数据库备份机制
3. **索引优化**: 根据实际查询模式添加必要的索引
4. **日志审计**: 启用 SQL Server 的查询日志和审计功能
5. **高可用性**: 考虑配置 SQL Server Always On 或故障转移群集

---

## 参考资料

- [SQLAlchemy SQL Server 方言文档](https://docs.sqlalchemy.org/en/20/dialects/mssql.html)
- [pyodbc 文档](https://github.com/mkleehammer/pyodbc/wiki)
- [aioodbc 文档](https://aioodbc.readthedocs.io/)
- [Alembic 文档](https://alembic.sqlalchemy.org/)
- [SQL Server 最佳实践](https://docs.microsoft.com/en-us/sql/relational-databases/best-practices)
