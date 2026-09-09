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


def get_session():
    """
    提供数据库 session 的异步上下文管理器（用于非 FastAPI 场景）

    使用方式:
        async with get_session() as session:
            result = await session.execute(stmt)
            await session.commit()
    """
    return AsyncSessionLocal()


async def init_db():
    """
    创建所有表（仅用于开发测试）

    生产环境应使用 Alembic 迁移
    """
    from app.models.base import Base
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
