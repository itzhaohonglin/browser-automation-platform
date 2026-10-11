# app/core/database.py
import json
from typing import AsyncGenerator, Any
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import JSON, TypeDecorator, Text
from app.core.config import settings


class ChineseJSON(TypeDecorator):
    """自定义 JSON 类型，保留中文字符而不转义为 Unicode

    SQL Server 的 JSON 存储为 NVARCHAR，我们需要：
    1. 写入时：手动序列化为 JSON 字符串（ensure_ascii=False）
    2. 读取时：手动反序列化为 Python 对象
    """

    impl = Text  # 使用 Text 而不是 JSON，避免 SQLAlchemy 的自动序列化
    cache_ok = True

    def process_bind_param(self, value: Any, dialect) -> str | None:
        """写入数据库时：Python 对象 → JSON 字符串（保留中文）"""
        if value is not None:
            # ensure_ascii=False 确保中文不被转义为 \uXXXX
            return json.dumps(value, ensure_ascii=False, separators=(',', ':'))
        return value

    def process_result_value(self, value: str | None, dialect) -> Any:
        """从数据库读取时：JSON 字符串 → Python 对象"""
        if value is None:
            return value

        if isinstance(value, str):
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                # 如果解析失败，返回空字典而不是原始字符串
                return {}

        # 如果已经是 dict（某些驱动可能自动解析），直接返回
        if isinstance(value, dict):
            return value

        return value


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
