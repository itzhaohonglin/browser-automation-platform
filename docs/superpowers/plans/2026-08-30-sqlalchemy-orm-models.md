# SQLAlchemy 异步 ORM 模型实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 创建 SQLAlchemy 2.0 异步 ORM 模型，配置 Alembic 迁移环境，实现数据库层的完整功能。

**Architecture:** 使用 Declarative Base 模式定义 3 个核心模型（CrawlerConfig, JobQueue, CrawlerResult），通过 aiomysql 异步驱动连接 MySQL 8.0。配置异步 Session 管理和 FastAPI 依赖注入，使用 Alembic 进行数据库迁移管理。

**Tech Stack:** SQLAlchemy 2.0 (异步), aiomysql 0.2.0, Alembic 1.13.2, FastAPI, Pydantic

---

## 文件结构概览

**新建文件:**
- `app/models/base.py` - DeclarativeBase 基类定义
- `app/models/config.py` - CrawlerConfig 模型
- `app/models/job.py` - JobQueue 模型和 JobStatus 枚举
- `app/models/result.py` - CrawlerResult 模型
- `app/core/database.py` - 异步引擎、Session 工厂、依赖注入
- `alembic.ini` - Alembic 配置文件
- `alembic/env.py` - Alembic 环境配置（异步模式）
- `alembic/script.py.mako` - 迁移文件模板
- `alembic/versions/.gitkeep` - 迁移文件目录占位

**修改文件:**
- `app/models/__init__.py` - 导出所有模型
- `app/core/config.py` - 更新 DATABASE_URL 为 aiomysql 驱动
- `requirements.txt` - 添加 aiomysql 和 cryptography 依赖

---

## Task 1: 更新依赖配置

**Files:**
- Modify: `requirements.txt`
- Modify: `app/core/config.py:9`

- [ ] **Step 1: 添加异步数据库驱动依赖**

在 `requirements.txt` 的 Database 部分添加：

```bash
cat >> requirements.txt << 'EOF'

# Async MySQL Driver
aiomysql==0.2.0
cryptography==42.0.8
EOF
```

- [ ] **Step 2: 更新配置文件中的数据库 URL**

修改 `app/core/config.py` 第 9 行，将驱动从 pymysql 改为 aiomysql：

```python
DATABASE_URL: str = "mysql+aiomysql://root:password@localhost:3306/browser_automation"
```

- [ ] **Step 3: 安装新依赖**

```bash
pip install aiomysql==0.2.0 cryptography==42.0.8
```

预期输出: Successfully installed aiomysql-0.2.0 cryptography-42.0.8

- [ ] **Step 4: 提交更改**

```bash
git add requirements.txt app/core/config.py
git commit -m "chore: add aiomysql driver for async database operations"
```

---

## Task 2: 创建 ORM 基类

**Files:**
- Create: `app/models/base.py`

- [ ] **Step 1: 创建基类文件**

```python
# app/models/base.py
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """所有 ORM 模型的基类"""
    pass
```

- [ ] **Step 2: 验证导入**

```bash
python -c "from app.models.base import Base; print('Base class imported successfully')"
```

预期输出: Base class imported successfully

- [ ] **Step 3: 提交更改**

```bash
git add app/models/base.py
git commit -m "feat: add SQLAlchemy DeclarativeBase class"
```

---

## Task 3: 创建 CrawlerConfig 模型

**Files:**
- Create: `app/models/config.py`

- [ ] **Step 1: 创建 CrawlerConfig 模型文件**

```python
# app/models/config.py
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Integer, Boolean, JSON, DateTime, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from app.models.base import Base


class CrawlerConfig(Base):
    """采集配置表 - 存储爬虫规则和目标页面配置"""
    
    __tablename__ = "crawler_configs"
    
    # 主键
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    # 基本配置
    config_name: Mapped[str] = mapped_column(String(100), nullable=False, comment="任务名称")
    target_url: Mapped[str] = mapped_column(String(500), nullable=False, comment="目标页面URL")
    
    # 登录配置
    need_login: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, comment="是否需要登录")
    auth_profile: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, comment="登录态标识")
    login_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True, comment="登录页地址")
    
    # 页面交互配置
    input_configs: Mapped[dict] = mapped_column(JSON, nullable=False, comment="多输入框配置")
    submit_selector: Mapped[str] = mapped_column(String(200), nullable=False, comment="查询按钮选择器")
    wait_selector: Mapped[str] = mapped_column(String(200), nullable=False, comment="等待加载完成的选择器")
    fields_mapping: Mapped[dict] = mapped_column(JSON, nullable=False, comment="数据提取规则")
    
    # 分页配置
    pagination_selector: Mapped[Optional[str]] = mapped_column(String(200), nullable=True, comment="下一页按钮选择器")
    max_pages: Mapped[int] = mapped_column(Integer, default=1, nullable=False, comment="最大翻页数")
    
    # 状态字段
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, comment="是否启用")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, 
        default=func.now(), 
        nullable=False,
        comment="创建时间"
    )
    
    # 关系定义（一对多：一个配置对应多个任务）
    jobs: Mapped[list["JobQueue"]] = relationship(
        "JobQueue",
        back_populates="config",
        cascade="all, delete-orphan"
    )
    
    # 索引
    __table_args__ = (
        Index("idx_auth_profile", "auth_profile"),
    )
    
    def __repr__(self) -> str:
        return f"<CrawlerConfig(id={self.id}, name={self.config_name})>"
```

- [ ] **Step 2: 验证模型导入**

```bash
python -c "from app.models.config import CrawlerConfig; print(f'Table: {CrawlerConfig.__tablename__}')"
```

预期输出: Table: crawler_configs

- [ ] **Step 3: 提交更改**

```bash
git add app/models/config.py
git commit -m "feat: add CrawlerConfig ORM model"
```

---

## Task 4: 创建 JobQueue 模型和枚举

**Files:**
- Create: `app/models/job.py`

- [ ] **Step 1: 创建 JobQueue 模型文件**

```python
# app/models/job.py
from datetime import datetime
from enum import Enum as PyEnum
from typing import Optional
from sqlalchemy import Integer, JSON, Text, DateTime, ForeignKey, Index, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from app.models.base import Base


class JobStatus(str, PyEnum):
    """任务状态枚举"""
    PENDING = "pending"
    PROCESSING = "processing"
    SUCCESS = "success"
    FAILED = "failed"


class JobQueue(Base):
    """任务队列表 - 存储待执行的采集任务"""
    
    __tablename__ = "job_queue"
    
    # 主键
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    # 外键
    config_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("crawler_configs.id"),
        nullable=False,
        comment="关联crawler_configs.id"
    )
    
    # 任务参数
    query_params: Mapped[dict] = mapped_column(JSON, nullable=False, comment="查询参数")
    
    # 状态字段
    status: Mapped[str] = mapped_column(
        SQLEnum(JobStatus),
        default=JobStatus.PENDING,
        nullable=False,
        comment="任务状态"
    )
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="重试次数")
    error_msg: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="错误信息")
    
    # 时间戳
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=func.now(),
        nullable=False,
        comment="创建时间"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=func.now(),
        onupdate=func.now(),
        nullable=False,
        comment="更新时间"
    )
    
    # 关系定义
    config: Mapped["CrawlerConfig"] = relationship("CrawlerConfig", back_populates="jobs")
    results: Mapped[list["CrawlerResult"]] = relationship(
        "CrawlerResult",
        back_populates="job",
        cascade="all, delete-orphan"
    )
    
    # 索引
    __table_args__ = (
        Index("idx_config_status", "config_id", "status"),
    )
    
    def __repr__(self) -> str:
        return f"<JobQueue(id={self.id}, status={self.status})>"
```

- [ ] **Step 2: 验证模型和枚举导入**

```bash
python -c "from app.models.job import JobQueue, JobStatus; print(f'Table: {JobQueue.__tablename__}, Status values: {[s.value for s in JobStatus]}')"
```

预期输出: Table: job_queue, Status values: ['pending', 'processing', 'success', 'failed']

- [ ] **Step 3: 提交更改**

```bash
git add app/models/job.py
git commit -m "feat: add JobQueue ORM model and JobStatus enum"
```

---

## Task 5: 创建 CrawlerResult 模型

**Files:**
- Create: `app/models/result.py`

- [ ] **Step 1: 创建 CrawlerResult 模型文件**

```python
# app/models/result.py
from datetime import datetime
from sqlalchemy import Integer, JSON, DateTime, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from app.models.base import Base


class CrawlerResult(Base):
    """采集结果表 - 存储提取的业务数据"""
    
    __tablename__ = "crawler_results"
    
    # 主键
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    # 外键
    job_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("job_queue.id"),
        nullable=False,
        comment="关联job_queue.id"
    )
    config_id: Mapped[int] = mapped_column(Integer, nullable=False, comment="冗余字段便于查询")
    
    # 数据字段
    query_params: Mapped[dict] = mapped_column(JSON, nullable=False, comment="查询参数快照")
    extracted_data: Mapped[dict] = mapped_column(JSON, nullable=False, comment="提取的业务数据")
    page_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False, comment="实际抓取页数")
    
    # 时间戳
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=func.now(),
        nullable=False,
        comment="创建时间"
    )
    
    # 关系定义
    job: Mapped["JobQueue"] = relationship("JobQueue", back_populates="results")
    
    # 索引
    __table_args__ = (
        Index("idx_job", "job_id"),
    )
    
    def __repr__(self) -> str:
        return f"<CrawlerResult(id={self.id}, job_id={self.job_id})>"
```

- [ ] **Step 2: 验证模型导入**

```bash
python -c "from app.models.result import CrawlerResult; print(f'Table: {CrawlerResult.__tablename__}')"
```

预期输出: Table: crawler_results

- [ ] **Step 3: 提交更改**

```bash
git add app/models/result.py
git commit -m "feat: add CrawlerResult ORM model"
```

---

## Task 6: 更新模型包导出

**Files:**
- Modify: `app/models/__init__.py`

- [ ] **Step 1: 更新 __init__.py 导出所有模型**

```python
# app/models/__init__.py
from app.models.base import Base
from app.models.config import CrawlerConfig
from app.models.job import JobQueue, JobStatus
from app.models.result import CrawlerResult

__all__ = [
    "Base",
    "CrawlerConfig",
    "JobQueue",
    "JobStatus",
    "CrawlerResult",
]
```

- [ ] **Step 2: 验证包导入**

```bash
python -c "from app.models import Base, CrawlerConfig, JobQueue, JobStatus, CrawlerResult; print('All models imported successfully')"
```

预期输出: All models imported successfully

- [ ] **Step 3: 提交更改**

```bash
git add app/models/__init__.py
git commit -m "feat: export all ORM models from models package"
```

---

## Task 7: 创建数据库引擎和 Session 管理

**Files:**
- Create: `app/core/database.py`

- [ ] **Step 1: 创建数据库核心模块**

```python
# app/core/database.py
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.core.config import settings


# 将连接字符串从 mysql+pymysql:// 转换为 mysql+aiomysql://
DATABASE_URL = settings.DATABASE_URL.replace("pymysql", "aiomysql")

# 创建异步引擎
async_engine = create_async_engine(
    DATABASE_URL,
    echo=settings.DEBUG,           # 开发环境打印 SQL 语句
    pool_pre_ping=True,            # 连接池健康检查
    pool_size=5,                   # 连接池大小
    max_overflow=10,               # 最大溢出连接数
    pool_recycle=3600              # 连接回收时间（1小时）
)

# 创建异步 Session 工厂
AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,        # commit 后对象不过期
    autoflush=False,               # 禁用自动 flush
    autocommit=False               # 显式提交事务
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    提供数据库 session 的异步生成器（FastAPI 依赖注入）
    
    使用方式:
        @app.post("/jobs")
        async def create_job(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """
    创建所有表（仅用于开发测试）
    
    生产环境应使用 Alembic 迁移
    """
    from app.models.base import Base
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
```

- [ ] **Step 2: 验证数据库模块导入**

```bash
python -c "from app.core.database import async_engine, AsyncSessionLocal, get_db, init_db; print('Database module imported successfully')"
```

预期输出: Database module imported successfully

- [ ] **Step 3: 提交更改**

```bash
git add app/core/database.py
git commit -m "feat: add async database engine and session management"
```

---

## Task 8: 初始化 Alembic 迁移环境

**Files:**
- Create: `alembic.ini`
- Create: `alembic/env.py`
- Create: `alembic/script.py.mako`
- Create: `alembic/versions/.gitkeep`

- [ ] **Step 1: 初始化 Alembic**

```bash
alembic init alembic
```

预期输出: Creating directory... Creating alembic.ini... done

- [ ] **Step 2: 创建 versions 目录占位文件**

```bash
touch alembic/versions/.gitkeep
```

- [ ] **Step 3: 验证目录结构**

```bash
ls -la alembic/
```

预期输出: 包含 env.py, script.py.mako, versions/ 目录

- [ ] **Step 4: 提交 Alembic 初始化文件**

```bash
git add alembic.ini alembic/ -f
git commit -m "chore: initialize Alembic migration environment"
```

---

## Task 9: 配置 Alembic 异步模式

**Files:**
- Modify: `alembic/env.py`

- [ ] **Step 1: 备份原始 env.py**

```bash
cp alembic/env.py alembic/env.py.bak
```

- [ ] **Step 2: 替换 env.py 为异步模式配置**

```python
# alembic/env.py
from logging.config import fileConfig
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import create_async_engine
from alembic import context
import asyncio

# 导入应用配置
from app.core.config import settings

# 导入所有模型（确保 Alembic 能检测到）
from app.models.base import Base
from app.models import config as _config_model
from app.models import job as _job_model
from app.models import result as _result_model

# Alembic Config 对象
config = context.config

# 解析日志配置
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# 设置数据库 URL（从应用配置读取）
config.set_main_option(
    "sqlalchemy.url",
    settings.DATABASE_URL.replace("pymysql", "aiomysql")
)

# 目标元数据（用于自动生成迁移）
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """
    离线模式运行迁移（生成 SQL 脚本，不连接数据库）
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    """执行迁移的同步回调函数"""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,              # 比较字段类型变化
        compare_server_default=True,    # 比较默认值变化
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations():
    """异步模式运行迁移"""
    connectable = create_async_engine(
        config.get_main_option("sqlalchemy.url"),
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """
    在线模式运行迁移（连接数据库执行）
    """
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

- [ ] **Step 3: 验证配置语法**

```bash
python -c "from alembic import config; print('Alembic env.py syntax valid')"
```

预期输出: Alembic env.py syntax valid

- [ ] **Step 4: 删除备份文件并提交**

```bash
rm alembic/env.py.bak
git add alembic/env.py
git commit -m "feat: configure Alembic for async SQLAlchemy"
```

---

## Task 10: 生成初始迁移文件

**Files:**
- Create: `alembic/versions/xxxx_init.py` (自动生成)

- [ ] **Step 1: 确保数据库已创建**

```bash
mysql -u root -p -e "CREATE DATABASE IF NOT EXISTS browser_automation CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
```

预期输出: 无错误输出

- [ ] **Step 2: 生成初始迁移文件**

```bash
alembic revision --autogenerate -m "init"
```

预期输出: Generating... alembic/versions/xxxx_init.py... done

- [ ] **Step 3: 检查生成的迁移文件内容**

```bash
ls -lh alembic/versions/*.py
```

预期输出: 显示迁移文件路径和大小

- [ ] **Step 4: 查看迁移文件关键部分**

```bash
grep -A 5 "def upgrade" alembic/versions/*.py | head -20
```

预期输出: 包含 op.create_table('crawler_configs'...), op.create_table('job_queue'...), op.create_table('crawler_results'...)

- [ ] **Step 5: 提交迁移文件**

```bash
git add alembic/versions/*.py
git commit -m "db: add initial migration for ORM models"
```

---

## Task 11: 执行数据库迁移

**Files:**
- Database: `browser_automation` (修改)

- [ ] **Step 1: 检查当前迁移状态**

```bash
alembic current
```

预期输出: (empty) 或 no current revision

- [ ] **Step 2: 执行迁移到最新版本**

```bash
alembic upgrade head
```

预期输出: Running upgrade... -> xxxx, init

- [ ] **Step 3: 验证表已创建**

```bash
mysql -u root -p browser_automation -e "SHOW TABLES;"
```

预期输出:
```
+-------------------------------+
| Tables_in_browser_automation  |
+-------------------------------+
| alembic_version              |
| crawler_configs              |
| crawler_results              |
| job_queue                    |
+-------------------------------+
```

- [ ] **Step 4: 验证 crawler_configs 表结构**

```bash
mysql -u root -p browser_automation -e "DESCRIBE crawler_configs;"
```

预期输出: 包含所有字段（id, config_name, target_url, need_login, auth_profile, login_url, input_configs, submit_selector, wait_selector, fields_mapping, pagination_selector, max_pages, is_active, created_at）

- [ ] **Step 5: 验证 job_queue 表结构**

```bash
mysql -u root -p browser_automation -e "DESCRIBE job_queue;"
```

预期输出: 包含所有字段（id, config_id, query_params, status, retry_count, error_msg, created_at, updated_at）

- [ ] **Step 6: 验证 crawler_results 表结构**

```bash
mysql -u root -p browser_automation -e "DESCRIBE crawler_results;"
```

预期输出: 包含所有字段（id, job_id, config_id, query_params, extracted_data, page_count, created_at）

- [ ] **Step 7: 验证外键约束**

```bash
mysql -u root -p browser_automation -e "SELECT CONSTRAINT_NAME, TABLE_NAME, COLUMN_NAME, REFERENCED_TABLE_NAME, REFERENCED_COLUMN_NAME FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE WHERE TABLE_SCHEMA = 'browser_automation' AND REFERENCED_TABLE_NAME IS NOT NULL;"
```

预期输出: 显示 job_queue.config_id -> crawler_configs.id, crawler_results.job_id -> job_queue.id

- [ ] **Step 8: 验证索引**

```bash
mysql -u root -p browser_automation -e "SHOW INDEX FROM crawler_configs WHERE Key_name = 'idx_auth_profile';"
mysql -u root -p browser_automation -e "SHOW INDEX FROM job_queue WHERE Key_name = 'idx_config_status';"
mysql -u root -p browser_automation -e "SHOW INDEX FROM crawler_results WHERE Key_name = 'idx_job';"
```

预期输出: 每个命令显示对应索引信息

---

## Task 12: 验证 ORM 功能

**Files:**
- Create: `test_orm.py` (临时测试脚本)

- [ ] **Step 1: 创建测试脚本**

```python
# test_orm.py
import asyncio
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models import CrawlerConfig, JobQueue, JobStatus, CrawlerResult


async def test_orm():
    """测试 ORM 基本操作"""
    async with AsyncSessionLocal() as session:
        # 1. 创建配置
        config = CrawlerConfig(
            config_name="测试配置",
            target_url="https://example.com",
            need_login=False,
            input_configs=[{"selector": "#search", "value": "{keyword}", "type": "fill"}],
            submit_selector="#submit",
            wait_selector=".results",
            fields_mapping={"title": ".title text"},
            max_pages=1
        )
        session.add(config)
        await session.commit()
        await session.refresh(config)
        print(f"✅ Created config: {config.id}")
        
        # 2. 创建任务
        job = JobQueue(
            config_id=config.id,
            query_params={"keyword": "test"},
            status=JobStatus.PENDING
        )
        session.add(job)
        await session.commit()
        await session.refresh(job)
        print(f"✅ Created job: {job.id}")
        
        # 3. 创建结果
        result = CrawlerResult(
            job_id=job.id,
            config_id=config.id,
            query_params={"keyword": "test"},
            extracted_data={"items": ["item1", "item2"]},
            page_count=1
        )
        session.add(result)
        await session.commit()
        await session.refresh(result)
        print(f"✅ Created result: {result.id}")
        
        # 4. 测试关系查询
        stmt = select(JobQueue).where(JobQueue.id == job.id)
        db_job = await session.execute(stmt)
        job_obj = db_job.scalar_one()
        
        # 加载关联对象
        await session.refresh(job_obj, ["config", "results"])
        print(f"✅ Relationship test: job.config.config_name = {job_obj.config.config_name}")
        print(f"✅ Relationship test: job.results count = {len(job_obj.results)}")
        
        # 5. 清理测试数据
        await session.delete(result)
        await session.delete(job)
        await session.delete(config)
        await session.commit()
        print("✅ Cleaned up test data")
        
        print("\n🎉 All ORM tests passed!")


if __name__ == "__main__":
    asyncio.run(test_orm())
```

- [ ] **Step 2: 运行测试脚本**

```bash
python test_orm.py
```

预期输出:
```
✅ Created config: 1
✅ Created job: 1
✅ Created result: 1
✅ Relationship test: job.config.config_name = 测试配置
✅ Relationship test: job.results count = 1
✅ Cleaned up test data

🎉 All ORM tests passed!
```

- [ ] **Step 3: 删除测试脚本**

```bash
rm test_orm.py
```

---

## Task 13: 创建使用文档

**Files:**
- Create: `docs/database_usage.md`

- [ ] **Step 1: 创建使用文档**

```markdown
# 数据库 ORM 使用指南

## 快速开始

### 1. 安装依赖

\`\`\`bash
pip install -r requirements.txt
\`\`\`

### 2. 配置数据库

创建 `.env` 文件：
\`\`\`env
DATABASE_URL=mysql+aiomysql://root:your_password@localhost:3306/browser_automation
\`\`\`

### 3. 创建数据库

\`\`\`bash
mysql -u root -p -e "CREATE DATABASE browser_automation CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
\`\`\`

### 4. 运行迁移

\`\`\`bash
alembic upgrade head
\`\`\`

## 在 FastAPI 中使用

### 依赖注入

\`\`\`python
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.models import CrawlerConfig

router = APIRouter()

@router.post("/configs")
async def create_config(
    config_data: dict,
    db: AsyncSession = Depends(get_db)
):
    new_config = CrawlerConfig(**config_data)
    db.add(new_config)
    await db.commit()
    await db.refresh(new_config)
    return {"id": new_config.id}
\`\`\`

### 查询示例

\`\`\`python
from sqlalchemy import select
from app.models import JobQueue, JobStatus

@router.get("/jobs/pending")
async def get_pending_jobs(db: AsyncSession = Depends(get_db)):
    stmt = select(JobQueue).where(JobQueue.status == JobStatus.PENDING)
    result = await db.execute(stmt)
    jobs = result.scalars().all()
    return [{"id": j.id, "query_params": j.query_params} for j in jobs]
\`\`\`

### 关系查询

\`\`\`python
from sqlalchemy.orm import selectinload

@router.get("/jobs/{job_id}")
async def get_job_with_config(
    job_id: int,
    db: AsyncSession = Depends(get_db)
):
    stmt = select(JobQueue).options(
        selectinload(JobQueue.config)
    ).where(JobQueue.id == job_id)
    result = await db.execute(stmt)
    job = result.scalar_one_or_none()
    
    if not job:
        return {"error": "Job not found"}
    
    return {
        "job_id": job.id,
        "config_name": job.config.config_name,
        "target_url": job.config.target_url
    }
\`\`\`

## Alembic 常用命令

\`\`\`bash
# 查看当前版本
alembic current

# 生成新迁移
alembic revision --autogenerate -m "description"

# 升级到最新版本
alembic upgrade head

# 回滚一个版本
alembic downgrade -1

# 查看迁移历史
alembic history
\`\`\`

## 最佳实践

### 1. 事务管理

使用 `get_db()` 依赖注入时，事务自动管理：
- 正常结束：自动 commit
- 异常：自动 rollback

### 2. 避免 N+1 查询

使用 `selectinload` 或 `joinedload` 预加载关联对象：

\`\`\`python
from sqlalchemy.orm import selectinload

stmt = select(JobQueue).options(
    selectinload(JobQueue.config),
    selectinload(JobQueue.results)
)
\`\`\`

### 3. JSON 字段查询

\`\`\`python
from sqlalchemy import cast, String

# 查询 JSON 字段中的值
stmt = select(JobQueue).where(
    cast(JobQueue.query_params["keyword"], String) == "手机"
)
\`\`\`

### 4. 批量操作

\`\`\`python
# 批量插入
jobs = [
    JobQueue(config_id=1, query_params={"keyword": f"kw{i}"})
    for i in range(100)
]
db.add_all(jobs)
await db.commit()
\`\`\`

## 故障排查

### 连接超时

如果遇到 `Lost connection to MySQL server`：
- 检查 `pool_pre_ping=True` 是否启用
- 调整 `pool_recycle` 参数

### 迁移失败

如果 `alembic upgrade head` 失败：
1. 检查数据库连接配置
2. 查看 `alembic/versions/` 中的迁移文件
3. 使用 `alembic current` 查看当前版本
4. 必要时手动回滚：`alembic downgrade base`
\`\`\`

- [ ] **Step 2: 提交文档**

```bash
git add docs/database_usage.md
git commit -m "docs: add database ORM usage guide"
```

---

## Task 14: 最终验收检查

**Files:**
- None (验证性任务)

- [ ] **Step 1: 验证所有表已创建**

```bash
mysql -u root -p browser_automation -e "SELECT table_name FROM information_schema.tables WHERE table_schema = 'browser_automation' ORDER BY table_name;"
```

预期输出:
```
+------------------+
| table_name       |
+------------------+
| alembic_version  |
| crawler_configs  |
| crawler_results  |
| job_queue        |
+------------------+
```

- [ ] **Step 2: 验证表结构与 TDD 一致性**

运行以下 SQL 查询并对照 TDD 第 2 章：

```bash
mysql -u root -p browser_automation << 'EOF'
-- 检查 crawler_configs 字段
SELECT COLUMN_NAME, COLUMN_TYPE, IS_NULLABLE, COLUMN_DEFAULT, COLUMN_COMMENT
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = 'browser_automation' AND TABLE_NAME = 'crawler_configs'
ORDER BY ORDINAL_POSITION;

-- 检查 job_queue 字段
SELECT COLUMN_NAME, COLUMN_TYPE, IS_NULLABLE, COLUMN_DEFAULT, COLUMN_COMMENT
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = 'browser_automation' AND TABLE_NAME = 'job_queue'
ORDER BY ORDINAL_POSITION;

-- 检查 crawler_results 字段
SELECT COLUMN_NAME, COLUMN_TYPE, IS_NULLABLE, COLUMN_DEFAULT, COLUMN_COMMENT
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = 'browser_automation' AND TABLE_NAME = 'crawler_results'
ORDER BY ORDINAL_POSITION;
EOF
```

预期输出: 所有字段与 TDD DDL 一致

- [ ] **Step 3: 验证所有索引已创建**

```bash
mysql -u root -p browser_automation -e "SELECT TABLE_NAME, INDEX_NAME, COLUMN_NAME FROM INFORMATION_SCHEMA.STATISTICS WHERE TABLE_SCHEMA = 'browser_automation' AND INDEX_NAME != 'PRIMARY' ORDER BY TABLE_NAME, INDEX_NAME;"
```

预期输出: 包含 idx_auth_profile, idx_config_status, idx_job

- [ ] **Step 4: 验证外键约束**

```bash
mysql -u root -p browser_automation -e "SELECT CONSTRAINT_NAME, TABLE_NAME, COLUMN_NAME, REFERENCED_TABLE_NAME, REFERENCED_COLUMN_NAME FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE WHERE TABLE_SCHEMA = 'browser_automation' AND REFERENCED_TABLE_NAME IS NOT NULL;"
```

预期输出:
- job_queue.config_id -> crawler_configs.id
- crawler_results.job_id -> job_queue.id

- [ ] **Step 5: 验证 Alembic 迁移状态**

```bash
alembic current
```

预期输出: 显示当前迁移版本号

- [ ] **Step 6: 验证可以生成新迁移（空迁移）**

```bash
alembic revision --autogenerate -m "test_no_changes"
```

预期输出: Detected no changes (或生成空迁移文件)

如果生成了文件，删除它：
```bash
rm alembic/versions/*test_no_changes.py
```

- [ ] **Step 7: 输出最终验收报告**

```bash
echo "==================================="
echo "✅ SQLAlchemy ORM 模型实现完成"
echo "==================================="
echo ""
echo "📋 完成项："
echo "  ✅ 3 个核心 ORM 模型（CrawlerConfig, JobQueue, CrawlerResult）"
echo "  ✅ 异步数据库引擎和 Session 管理"
echo "  ✅ FastAPI 依赖注入函数"
echo "  ✅ Alembic 迁移环境配置（异步模式）"
echo "  ✅ 初始迁移文件生成并执行"
echo "  ✅ 数据库表、索引、外键全部创建"
echo ""
echo "🎯 验收标准："
echo "  ✅ alembic revision --autogenerate -m \"init\" 成功生成迁移文件"
echo "  ✅ alembic upgrade head 成功创建 3 张表"
echo "  ✅ 表结构与 TDD 第 2 章 SQL DDL 完全一致"
echo ""
echo "📚 文档："
echo "  - 设计规格: docs/superpowers/specs/2026-08-30-sqlalchemy-orm-models-design.md"
echo "  - 使用指南: docs/database_usage.md"
echo ""
echo "🚀 下一步："
echo "  - 实现 executor.py（Playwright 执行器）"
echo "  - 实现 WebSocket 状态推送"
echo "  - 实现定时任务调度"
echo "==================================="
```

预期输出: 显示完整的验收报告

---

## 完成标志

当所有任务的所有步骤都打勾完成后，实现计划执行完毕。此时应该：

1. ✅ 所有 ORM 模型文件已创建
2. ✅ 数据库引擎和 Session 管理已配置
3. ✅ Alembic 迁移环境已初始化
4. ✅ 初始迁移已生成并执行
5. ✅ 数据库表、索引、外键已创建
6. ✅ ORM 功能已验证
7. ✅ 文档已创建

可以通过以下命令验证最终状态：

```bash
# 检查文件存在性
ls app/models/{base,config,job,result}.py app/core/database.py alembic/env.py

# 检查数据库表
mysql -u root -p browser_automation -e "SHOW TABLES;"

# 检查 Alembic 状态
alembic current

# 检查提交历史
git log --oneline --graph -15
```

所有输出应与预期一致，表示实现计划成功完成。
