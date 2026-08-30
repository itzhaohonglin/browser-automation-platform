# 数据库 ORM 使用指南

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置数据库

创建 `.env` 文件：
```env
DATABASE_URL=mysql+aiomysql://root:your_password@localhost:3306/browser_automation
```

### 3. 创建数据库

```bash
mysql -u root -p -e "CREATE DATABASE browser_automation CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
```

### 4. 运行迁移

```bash
alembic upgrade head
```

## 在 FastAPI 中使用

### 依赖注入

```python
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
```

### 查询示例

```python
from sqlalchemy import select
from app.models import JobQueue, JobStatus

@router.get("/jobs/pending")
async def get_pending_jobs(db: AsyncSession = Depends(get_db)):
    stmt = select(JobQueue).where(JobQueue.status == JobStatus.PENDING)
    result = await db.execute(stmt)
    jobs = result.scalars().all()
    return [{"id": j.id, "query_params": j.query_params} for j in jobs]
```

### 关系查询

```python
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
```

## Alembic 常用命令

```bash
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
```

## 最佳实践

### 1. 事务管理

使用 `get_db()` 依赖注入时，事务自动管理：
- 正常结束：自动 commit
- 异常：自动 rollback

### 2. 避免 N+1 查询

使用 `selectinload` 或 `joinedload` 预加载关联对象：

```python
from sqlalchemy.orm import selectinload

stmt = select(JobQueue).options(
    selectinload(JobQueue.config),
    selectinload(JobQueue.results)
)
```

### 3. JSON 字段查询

```python
from sqlalchemy import cast, String

# 查询 JSON 字段中的值
stmt = select(JobQueue).where(
    cast(JobQueue.query_params["keyword"], String) == "手机"
)
```

### 4. 批量操作

```python
# 批量插入
jobs = [
    JobQueue(config_id=1, query_params={"keyword": f"kw{i}"})
    for i in range(100)
]
db.add_all(jobs)
await db.commit()
```

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
