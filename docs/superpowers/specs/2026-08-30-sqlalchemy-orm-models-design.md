# SQLAlchemy 异步 ORM 模型设计规格

**文档版本**: 1.0  
**创建日期**: 2026-08-30  
**对应需求**: PRD V2.0 第 3.1 章节、TDD 第 2 章数据库设计  
**实现目标**: 创建 SQLAlchemy 异步 ORM 模型，支持 Alembic 迁移

---

## 1. 概述

本规格定义了浏览器自动化数据采集平台的数据库 ORM 层实现方案，基于 SQLAlchemy 2.0 异步 API，使用 aiomysql 驱动连接 MySQL 8.0 数据库。

### 1.1 核心目标

- 创建 3 个核心 ORM 模型（CrawlerConfig, JobQueue, CrawlerResult）
- 实现异步数据库引擎和 Session 管理
- 配置 Alembic 迁移环境（异步模式）
- 确保模型关系映射正确（外键、索引）
- 提供 FastAPI 依赖注入接口

### 1.2 验收标准

1. 执行 `alembic revision --autogenerate -m "init"` 能生成迁移文件
2. 执行 `alembic upgrade head` 在数据库中成功创建 3 张表
3. 表结构与 TDD 第 2 章的 SQL DDL 完全一致

---

## 2. 技术选型

### 2.1 核心依赖

| 组件 | 版本 | 用途 |
|------|------|------|
| SQLAlchemy | 2.0.35 | ORM 框架（异步模式） |
| aiomysql | 0.2.0 | 异步 MySQL 驱动 |
| Alembic | 1.13.2 | 数据库迁移工具 |
| cryptography | 42.0.8 | aiomysql 依赖 |

### 2.2 架构模式

**方案**: 标准 Declarative Base 模式

**理由**:
- 符合 SQLAlchemy 2.0 最佳实践
- 类型提示友好，IDE 自动补全完善
- 支持复杂关系映射（relationship）
- JSON 字段类型支持完善
- 便于 Alembic 自动检测表结构变化

---

## 3. 文件结构设计

```
browser-automation-platform/
├── app/
│   ├── core/
│   │   ├── database.py          # 异步引擎、session 工厂、依赖注入
│   │   └── config.py            # 现有配置（需更新 DATABASE_URL）
│   └── models/
│       ├── __init__.py          # 导出所有模型
│       ├── base.py              # DeclarativeBase 基类
│       ├── config.py            # CrawlerConfig ORM 模型
│       ├── job.py               # JobQueue ORM 模型
│       └── result.py            # CrawlerResult ORM 模型
├── alembic/
│   ├── env.py                   # Alembic 环境配置（异步模式）
│   ├── script.py.mako           # 迁移文件模板
│   └── versions/                # 迁移文件存放目录
├── alembic.ini                  # Alembic 主配置文件
└── requirements.txt             # 需添加 aiomysql、cryptography
```

---

## 4. 核心组件设计

### 4.1 数据库引擎与 Session 管理 (`app/core/database.py`)

#### 4.1.1 异步引擎创建

```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.core.config import settings

# 将连接字符串从 mysql+pymysql:// 转换为 mysql+aiomysql://
DATABASE_URL = settings.DATABASE_URL.replace("pymysql", "aiomysql")

async_engine = create_async_engine(
    DATABASE_URL,
    echo=settings.DEBUG,        # 开发环境打印 SQL 语句
    pool_pre_ping=True,         # 连接池健康检查（防止连接超时）
    pool_size=5,                # 连接池大小
    max_overflow=10,            # 最大溢出连接数
    pool_recycle=3600           # 连接回收时间（1小时）
)
```

**设计要点**:
- `pool_pre_ping=True`: 每次从连接池获取连接时先检查有效性
- `echo=settings.DEBUG`: 开发环境自动打印 SQL，便于调试
- 连接池参数根据并发需求调整（初期 5+10 足够）

#### 4.1.2 Session 工厂

```python
AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,     # commit 后对象不过期，可继续访问属性
    autoflush=False,            # 禁用自动 flush（手动控制更精确）
    autocommit=False            # 显式提交事务
)
```

**设计要点**:
- `expire_on_commit=False`: 避免 commit 后访问对象属性时触发额外查询
- `autoflush=False`: 在复杂业务逻辑中手动控制 flush 时机

#### 4.1.3 FastAPI 依赖注入

```python
from typing import AsyncGenerator

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    提供数据库 session 的异步生成器
    
    使用方式：
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
```

**设计要点**:
- 自动处理事务提交/回滚
- 异常时自动回滚，确保数据一致性
- 使用 `async with` 确保资源正确释放

#### 4.1.4 数据库初始化辅助函数

```python
async def init_db():
    """
    创建所有表（仅用于开发测试）
    
    生产环境应使用 Alembic 迁移
    """
    from app.models.base import Base
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
```

---

### 4.2 ORM 模型设计

#### 4.2.1 基类定义 (`app/models/base.py`)

```python
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    """所有 ORM 模型的基类"""
    pass
```

**设计说明**:
- 使用 SQLAlchemy 2.0 的 `DeclarativeBase` 替代旧版 `declarative_base()`
- 所有模型继承此基类，共享元数据（metadata）

#### 4.2.2 CrawlerConfig 模型 (`app/models/config.py`)

映射表：`crawler_configs`

**字段映射**:

| 字段名 | Python 类型 | SQLAlchemy 类型 | 约束 | 说明 |
|--------|-------------|-----------------|------|------|
| id | int | Integer | PRIMARY KEY, AUTO_INCREMENT | 主键 |
| config_name | str | String(100) | NOT NULL | 任务名称 |
| target_url | str | String(500) | NOT NULL | 目标页面 URL |
| need_login | bool | Boolean | DEFAULT False | 是否需要登录 |
| auth_profile | str \| None | String(50) | nullable | 登录态标识 |
| login_url | str \| None | String(500) | nullable | 登录页地址 |
| input_configs | dict | JSON | NOT NULL | 多输入框配置（JSON 数组） |
| submit_selector | str | String(200) | NOT NULL | 查询按钮选择器 |
| wait_selector | str | String(200) | NOT NULL | 等待加载完成的选择器 |
| fields_mapping | dict | JSON | NOT NULL | 数据提取规则 |
| pagination_selector | str \| None | String(200) | nullable | 下一页按钮选择器 |
| max_pages | int | Integer | DEFAULT 1 | 最大翻页数 |
| is_active | bool | Boolean | DEFAULT True | 是否启用 |
| created_at | datetime | DateTime | DEFAULT CURRENT_TIMESTAMP | 创建时间 |

**关系定义**:
- `jobs`: relationship 到 `JobQueue`（一对多）
  - `back_populates="config"`
  - `cascade="all, delete-orphan"` - 删除配置时级联删除关联任务

**索引**:
- `idx_auth_profile`: 索引字段 `auth_profile`

**示例代码结构**:
```python
from sqlalchemy import String, Integer, Boolean, JSON, DateTime, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from app.models.base import Base

class CrawlerConfig(Base):
    __tablename__ = "crawler_configs"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    config_name: Mapped[str] = mapped_column(String(100), nullable=False)
    # ... 其他字段
    
    # 关系
    jobs: Mapped[list["JobQueue"]] = relationship(
        back_populates="config",
        cascade="all, delete-orphan"
    )
    
    # 索引
    __table_args__ = (
        Index("idx_auth_profile", "auth_profile"),
    )
```

#### 4.2.3 JobQueue 模型 (`app/models/job.py`)

映射表：`job_queue`

**字段映射**:

| 字段名 | Python 类型 | SQLAlchemy 类型 | 约束 | 说明 |
|--------|-------------|-----------------|------|------|
| id | int | Integer | PRIMARY KEY, AUTO_INCREMENT | 主键 |
| config_id | int | Integer | NOT NULL, FOREIGN KEY | 关联 crawler_configs.id |
| query_params | dict | JSON | NOT NULL | 查询参数字典 |
| status | str | Enum | DEFAULT 'pending' | 任务状态 |
| retry_count | int | Integer | DEFAULT 0 | 重试次数 |
| error_msg | str \| None | Text | nullable | 错误信息 |
| created_at | datetime | DateTime | DEFAULT CURRENT_TIMESTAMP | 创建时间 |
| updated_at | datetime | DateTime | DEFAULT NOW, ON UPDATE NOW | 更新时间 |

**Enum 定义**:
```python
from enum import Enum as PyEnum

class JobStatus(str, PyEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    SUCCESS = "success"
    FAILED = "failed"
```

**关系定义**:
- `config`: relationship 到 `CrawlerConfig`（多对一）
  - `back_populates="jobs"`
- `results`: relationship 到 `CrawlerResult`（一对多）
  - `back_populates="job"`
  - `cascade="all, delete-orphan"`

**外键**:
- `config_id` → `crawler_configs.id`

**索引**:
- `idx_config_status`: 复合索引 `(config_id, status)`

**示例代码结构**:
```python
from sqlalchemy import Integer, JSON, Text, DateTime, ForeignKey, Index, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from enum import Enum as PyEnum

class JobStatus(str, PyEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    SUCCESS = "success"
    FAILED = "failed"

class JobQueue(Base):
    __tablename__ = "job_queue"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    config_id: Mapped[int] = mapped_column(
        Integer, 
        ForeignKey("crawler_configs.id"),
        nullable=False
    )
    status: Mapped[str] = mapped_column(
        SQLEnum(JobStatus),
        default=JobStatus.PENDING,
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=func.now(),
        onupdate=func.now(),
        nullable=False
    )
    
    # 关系
    config: Mapped["CrawlerConfig"] = relationship(back_populates="jobs")
    results: Mapped[list["CrawlerResult"]] = relationship(
        back_populates="job",
        cascade="all, delete-orphan"
    )
    
    # 索引
    __table_args__ = (
        Index("idx_config_status", "config_id", "status"),
    )
```

#### 4.2.4 CrawlerResult 模型 (`app/models/result.py`)

映射表：`crawler_results`

**字段映射**:

| 字段名 | Python 类型 | SQLAlchemy 类型 | 约束 | 说明 |
|--------|-------------|-----------------|------|------|
| id | int | Integer | PRIMARY KEY, AUTO_INCREMENT | 主键 |
| job_id | int | Integer | NOT NULL, FOREIGN KEY | 关联 job_queue.id |
| config_id | int | Integer | NOT NULL | 冗余字段，便于直接查询 |
| query_params | dict | JSON | NOT NULL | 查询参数快照 |
| extracted_data | dict | JSON | NOT NULL | 提取的业务数据 |
| page_count | int | Integer | DEFAULT 1 | 实际抓取页数 |
| created_at | datetime | DateTime | DEFAULT CURRENT_TIMESTAMP | 创建时间 |

**关系定义**:
- `job`: relationship 到 `JobQueue`（多对一）
  - `back_populates="results"`

**外键**:
- `job_id` → `job_queue.id`

**索引**:
- `idx_job`: 索引字段 `job_id`

**示例代码结构**:
```python
from sqlalchemy import Integer, JSON, DateTime, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

class CrawlerResult(Base):
    __tablename__ = "crawler_results"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("job_queue.id"),
        nullable=False
    )
    config_id: Mapped[int] = mapped_column(Integer, nullable=False)
    extracted_data: Mapped[dict] = mapped_column(JSON, nullable=False)
    page_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=func.now(),
        nullable=False
    )
    
    # 关系
    job: Mapped["JobQueue"] = relationship(back_populates="results")
    
    # 索引
    __table_args__ = (
        Index("idx_job", "job_id"),
    )
```

#### 4.2.5 模型导出 (`app/models/__init__.py`)

```python
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

**设计要点**:
- 显式导出所有模型，确保 Alembic 能检测到
- 导出 `JobStatus` 枚举供业务代码使用

---

### 4.3 Alembic 迁移配置

#### 4.3.1 `alembic.ini` 配置要点

```ini
[alembic]
script_location = alembic
file_template = %%(rev)s_%%(slug)s
prepend_sys_path = .

# 数据库连接字符串（从环境变量读取）
# sqlalchemy.url = 留空，在 env.py 中动态设置

[loggers]
keys = root,sqlalchemy,alembic

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine
```

**设计说明**:
- `sqlalchemy.url` 留空，在 `env.py` 中从 `app.core.config` 读取
- 日志级别设置为 WARN，避免迁移时输出过多信息

#### 4.3.2 `alembic/env.py` 异步模式配置

**关键设计点**:

1. **导入所有模型确保自动检测**
```python
from app.models.base import Base
# 显式导入所有模型，确保元数据注册
from app.models import config, job, result

target_metadata = Base.metadata
```

2. **从应用配置读取数据库 URL**
```python
from app.core.config import settings

config.set_main_option(
    "sqlalchemy.url",
    settings.DATABASE_URL.replace("pymysql", "aiomysql")
)
```

3. **异步迁移函数**
```python
from sqlalchemy.ext.asyncio import create_async_engine
import asyncio

def run_migrations_online():
    """异步模式下执行迁移"""
    connectable = create_async_engine(
        config.get_main_option("sqlalchemy.url")
    )
    
    async def do_run_migrations(connection):
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,              # 比较字段类型变化
            compare_server_default=True,    # 比较默认值变化
        )
        
        async with context.begin_transaction():
            await context.run_migrations()
    
    async def run_async_migrations():
        async with connectable.connect() as connection:
            await connection.run_sync(do_run_migrations)
    
    asyncio.run(run_async_migrations())
```

4. **支持的命令**
```bash
# 初始化 Alembic（首次运行）
alembic init alembic

# 自动生成迁移文件
alembic revision --autogenerate -m "init tables"

# 查看当前版本
alembic current

# 升级到最新版本
alembic upgrade head

# 回滚一个版本
alembic downgrade -1

# 查看迁移历史
alembic history
```

---

## 5. 配置更新

### 5.1 `requirements.txt` 更新

**需要添加的依赖**:
```
aiomysql==0.2.0          # 异步 MySQL 驱动
cryptography==42.0.8     # aiomysql 的加密依赖
```

**完整依赖列表**:
```
# Web Framework
fastapi==0.115.0
uvicorn[standard]==0.30.6

# Browser Automation
playwright==1.47.0

# Database
sqlalchemy==2.0.35
aiomysql==0.2.0         # 新增
pymysql==1.1.1          # 可保留（用于同步场景）
alembic==1.13.2
cryptography==42.0.8    # 新增

# Task Scheduling
apscheduler==3.10.4

# Environment & Utils
python-dotenv==1.0.1
pydantic==2.9.2
pydantic-settings==2.5.2

# WebSocket Support
websockets==13.1
```

### 5.2 `app/core/config.py` 更新

**需要修改的字段**:
```python
class Settings(BaseSettings):
    # 数据库配置（修改驱动为 aiomysql）
    DATABASE_URL: str = "mysql+aiomysql://root:password@localhost:3306/browser_automation"
    
    # ... 其他配置保持不变
```

---

## 6. 初始化与验收流程

### 6.1 安装依赖
```bash
pip install -r requirements.txt
playwright install
```

### 6.2 配置数据库
创建 `.env` 文件（参考 `.env.example`）：
```env
DATABASE_URL=mysql+aiomysql://root:your_password@localhost:3306/browser_automation
```

确保 MySQL 服务已启动，并创建数据库：
```sql
CREATE DATABASE browser_automation CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

### 6.3 初始化 Alembic
```bash
alembic init alembic
```

此命令会生成：
- `alembic/` 目录
- `alembic.ini` 文件

### 6.4 配置 Alembic
按照第 4.3 节的设计修改 `alembic/env.py`，确保：
- 导入所有模型
- 使用异步引擎
- 从 `app.core.config` 读取数据库 URL

### 6.5 生成初始迁移文件（验收点 1）
```bash
alembic revision --autogenerate -m "init"
```

**预期结果**:
- 在 `alembic/versions/` 目录生成迁移文件（如 `abc123_init.py`）
- 文件中包含 3 个 `op.create_table()` 操作：
  - `crawler_configs`
  - `job_queue`
  - `crawler_results`
- 包含外键约束定义：
  - `job_queue.config_id` → `crawler_configs.id`
  - `crawler_results.job_id` → `job_queue.id`
- 包含索引定义：
  - `idx_auth_profile` (crawler_configs)
  - `idx_config_status` (job_queue)
  - `idx_job` (crawler_results)

### 6.6 执行迁移（验收点 2）
```bash
alembic upgrade head
```

**预期结果**:
- 控制台输出迁移执行日志
- 数据库中成功创建 3 张表及 `alembic_version` 表

**验证命令**:
```sql
-- 查看所有表
SHOW TABLES;
-- 输出应包含：
-- crawler_configs
-- job_queue
-- crawler_results
-- alembic_version

-- 验证表结构
DESCRIBE crawler_configs;
DESCRIBE job_queue;
DESCRIBE crawler_results;

-- 验证索引
SHOW INDEX FROM crawler_configs;
SHOW INDEX FROM job_queue;
SHOW INDEX FROM crawler_results;

-- 验证外键
SELECT 
    CONSTRAINT_NAME, 
    TABLE_NAME, 
    COLUMN_NAME, 
    REFERENCED_TABLE_NAME, 
    REFERENCED_COLUMN_NAME
FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
WHERE TABLE_SCHEMA = 'browser_automation'
AND REFERENCED_TABLE_NAME IS NOT NULL;
```

---

## 7. 使用示例

### 7.1 FastAPI 路由中使用

```python
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.models import CrawlerConfig, JobQueue, JobStatus

router = APIRouter()

@router.post("/configs")
async def create_config(
    config_data: dict,
    db: AsyncSession = Depends(get_db)
):
    """创建采集配置"""
    new_config = CrawlerConfig(**config_data)
    db.add(new_config)
    await db.commit()
    await db.refresh(new_config)
    return {"id": new_config.id}

@router.get("/jobs/pending")
async def get_pending_jobs(db: AsyncSession = Depends(get_db)):
    """获取待处理任务"""
    stmt = select(JobQueue).where(JobQueue.status == JobStatus.PENDING)
    result = await db.execute(stmt)
    jobs = result.scalars().all()
    return [{"id": j.id, "query_params": j.query_params} for j in jobs]

@router.get("/jobs/{job_id}/config")
async def get_job_with_config(
    job_id: int,
    db: AsyncSession = Depends(get_db)
):
    """获取任务及其关联配置（使用 relationship）"""
    stmt = select(JobQueue).where(JobQueue.id == job_id)
    result = await db.execute(stmt)
    job = result.scalar_one_or_none()
    
    if not job:
        return {"error": "Job not found"}
    
    # 通过 relationship 访问关联对象（需要先 await 加载）
    await db.refresh(job, ["config"])
    
    return {
        "job_id": job.id,
        "query_params": job.query_params,
        "config_name": job.config.config_name,
        "target_url": job.config.target_url
    }
```

### 7.2 执行器服务中使用

```python
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models import JobQueue, JobStatus, CrawlerResult

async def process_job(job_id: int, session: AsyncSession):
    """处理任务示例"""
    # 获取任务
    stmt = select(JobQueue).where(JobQueue.id == job_id)
    result = await session.execute(stmt)
    job = result.scalar_one()
    
    # 更新状态为处理中
    job.status = JobStatus.PROCESSING
    await session.commit()
    
    try:
        # 执行采集逻辑...
        extracted_data = {"title": "示例数据"}
        
        # 保存结果
        result = CrawlerResult(
            job_id=job.id,
            config_id=job.config_id,
            query_params=job.query_params,
            extracted_data=extracted_data,
            page_count=1
        )
        session.add(result)
        
        # 标记任务成功
        job.status = JobStatus.SUCCESS
        await session.commit()
        
    except Exception as e:
        job.status = JobStatus.FAILED
        job.error_msg = str(e)
        job.retry_count += 1
        await session.commit()
```

---

## 8. 错误处理与最佳实践

### 8.1 连接池管理

**问题**: 长时间空闲连接被 MySQL 服务器关闭

**解决方案**:
- 启用 `pool_pre_ping=True`（已在设计中包含）
- 设置 `pool_recycle=3600`（1 小时回收连接）

### 8.2 事务管理

**原则**:
- 短事务：尽快提交，避免长时间持有锁
- 显式控制：使用 `async with session.begin()` 明确事务边界
- 异常回滚：在 `except` 块中显式 `await session.rollback()`

### 8.3 关系加载

**问题**: 访问 relationship 属性时触发 lazy loading，导致 N+1 查询

**解决方案**:
```python
from sqlalchemy.orm import selectinload

# 预加载关联对象
stmt = select(JobQueue).options(selectinload(JobQueue.config))
result = await session.execute(stmt)
jobs = result.scalars().all()

# 现在可以直接访问 job.config，不会触发额外查询
for job in jobs:
    print(job.config.config_name)
```

### 8.4 JSON 字段操作

**查询 JSON 字段内容**:
```python
from sqlalchemy import cast, String

# 查询 query_params 中包含特定关键词的任务
stmt = select(JobQueue).where(
    cast(JobQueue.query_params["keyword"], String) == "手机"
)
```

---

## 9. 后续扩展建议

### 9.1 添加软删除功能

可为模型添加 `deleted_at` 字段，实现软删除：
```python
from sqlalchemy import DateTime

class CrawlerConfig(Base):
    # ... 现有字段
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
```

### 9.2 添加审计字段

可添加 `updated_by`、`created_by` 字段记录操作人：
```python
class CrawlerConfig(Base):
    # ... 现有字段
    created_by: Mapped[str | None] = mapped_column(String(50), nullable=True)
    updated_by: Mapped[str | None] = mapped_column(String(50), nullable=True)
```

### 9.3 性能优化

- 为高频查询字段添加复合索引
- 使用 Redis 缓存配置表数据（`is_active=True` 的配置）
- 定期归档历史数据到冷存储

---

## 10. 检查清单

- [ ] 所有模型字段与 TDD SQL DDL 一致
- [ ] 外键约束正确配置
- [ ] 索引按 TDD 定义创建
- [ ] JSON 字段类型正确映射
- [ ] Enum 类型正确定义
- [ ] relationship 双向关联配置完整
- [ ] 时间戳字段自动更新配置正确
- [ ] Alembic 环境配置为异步模式
- [ ] 数据库连接字符串使用 aiomysql 驱动
- [ ] FastAPI 依赖注入函数实现完整
- [ ] 验收标准 1 通过（生成迁移文件）
- [ ] 验收标准 2 通过（执行迁移成功）

---

## 11. 参考资料

- [SQLAlchemy 2.0 文档](https://docs.sqlalchemy.org/en/20/)
- [SQLAlchemy 异步 ORM 指南](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html)
- [Alembic 文档](https://alembic.sqlalchemy.org/en/latest/)
- [aiomysql GitHub](https://github.com/aio-libs/aiomysql)
- TDD 文档：`docs/02_tech_design.md`
- PRD 文档：`docs/01_prd.md`
