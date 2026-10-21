# app/core/database.py
import json
import logging
from typing import AsyncGenerator, Any
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import JSON, TypeDecorator, Text, event
from sqlalchemy.pool import Pool
from app.core.config import settings

logger = logging.getLogger(__name__)


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
    pool_pre_ping=True,            # 连接池健康检查（使用前检测连接有效性）
    pool_size=10,                  # 连接池大小（增加以支持并发任务）
    max_overflow=5,                # 最大溢出连接数（减少溢出，提高池管理效率）
    pool_recycle=1200,             # 连接回收时间（20分钟，避免 SQL Server 30分钟空闲超时）
    pool_timeout=30,               # 获取连接超时（秒）
    pool_reset_on_return='rollback',  # 归还连接时自动回滚未提交事务
    connect_args={
        "timeout": 30,             # 连接超时（秒）
        "autocommit": False        # 显式控制事务
    },
    echo_pool=settings.DEBUG       # 启用连接池事件日志（调试用）
)


# 添加连接池事件监听器（用于调试和监控）
@event.listens_for(async_engine.sync_engine, "connect")
def receive_connect(dbapi_conn, connection_record):
    """连接创建时的回调"""
    logger.debug(f"数据库连接已建立: {id(dbapi_conn)}")


@event.listens_for(async_engine.sync_engine, "close")
def receive_close(dbapi_conn, connection_record):
    """连接关闭时的回调"""
    logger.debug(f"数据库连接已关闭: {id(dbapi_conn)}")


@event.listens_for(async_engine.sync_engine, "checkin")
def receive_checkin(dbapi_conn, connection_record):
    """连接归还到池时的回调"""
    logger.debug(f"连接已归还到池: {id(dbapi_conn)}")


@event.listens_for(async_engine.sync_engine, "checkout")
def receive_checkout(dbapi_conn, connection_record, connection_proxy):
    """从池中取出连接时的回调"""
    logger.debug(f"连接已从池中取出: {id(dbapi_conn)}")


@event.listens_for(Pool, "close")
def receive_pool_close(dbapi_conn, connection_record):
    """连接池关闭连接时的回调（捕获并记录错误）"""
    try:
        logger.debug(f"连接池正在关闭连接: {id(dbapi_conn)}")
    except RuntimeError as e:
        # 特别处理 "Event loop is closed" 错误
        # 这通常发生在进程退出时，事件循环已经关闭但连接池还在清理
        # 可以安全忽略，因为进程即将结束
        if "Event loop is closed" in str(e):
            pass  # 静默忽略，避免日志污染
        else:
            logger.warning(f"关闭连接时出现运行时错误（已忽略）: {e}")
    except Exception as e:
        # 忽略其他关闭时的错误，防止影响应用运行
        logger.warning(f"关闭连接时出现错误（已忽略）: {e}")


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
