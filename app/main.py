import sys
import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Optional
from pathlib import Path
from fastapi import FastAPI, WebSocket
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

# Windows 平台设置事件循环策略（必须在任何异步操作之前）
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from app.core.config import settings
from app.api.endpoints import router
from app.api.config_endpoints import router as config_router
from app.api.metrics import router as metrics_router
from app.api.config_test import router as config_test_router
from app.api.websocket import websocket_manager
from app.services.scheduler import TaskScheduler
from app.services.process_pool import ProcessPoolManager


def get_base_path() -> Path:
    """获取应用基础路径（兼容开发环境和 PyInstaller 打包）"""
    if getattr(sys, 'frozen', False):
        # PyInstaller 打包后的环境
        # sys._MEIPASS 指向临时解压目录
        base_path = Path(sys._MEIPASS)
    else:
        # 开发环境
        base_path = Path(__file__).parent.parent
    return base_path


# 配置日志
log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
log_datefmt = "%Y-%m-%d %H:%M:%S"

# 创建 formatter
formatter = logging.Formatter(log_format, datefmt=log_datefmt)

# 配置 root logger
root_logger = logging.getLogger()
root_logger.setLevel(log_level)

# 如果配置了日志文件，使用 TimedRotatingFileHandler
if settings.LOG_FILE:
    from logging.handlers import TimedRotatingFileHandler
    import os

    # 确保日志目录存在
    log_dir = os.path.dirname(settings.LOG_FILE)
    if log_dir:
        os.makedirs(log_dir, exist_ok=True)

    # 根据配置选择轮转策略
    if settings.LOG_ROTATION == "hourly":
        # 按小时轮转
        file_handler = TimedRotatingFileHandler(
            filename=settings.LOG_FILE,
            when="H",  # 按小时
            interval=1,  # 每1小时
            backupCount=settings.LOG_RETENTION_DAYS * 24,  # 保留指定天数的小时日志
            encoding="utf-8",
            delay=False,
            utc=False
        )
        file_handler.suffix = "%Y%m%d_%H"  # 文件名后缀: YYYYMMDD_HH
    elif settings.LOG_ROTATION == "daily":
        # 按天轮转
        file_handler = TimedRotatingFileHandler(
            filename=settings.LOG_FILE,
            when="midnight",  # 每天午夜
            interval=1,  # 每1天
            backupCount=settings.LOG_RETENTION_DAYS,  # 保留指定天数
            encoding="utf-8",
            delay=False,
            utc=False
        )
        file_handler.suffix = "%Y%m%d"  # 文件名后缀: YYYYMMDD
    else:
        # 不轮转，使用普通 FileHandler
        from logging import FileHandler
        file_handler = FileHandler(
            filename=settings.LOG_FILE,
            mode="a",
            encoding="utf-8"
        )

    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)

    # 同时输出到控制台
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
else:
    # 只输出到控制台
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

# Windows 平台 Playwright 兼容性设置
if sys.platform == "win32":
    # 使用 WindowsProactorEventLoopPolicy 以支持子进程（Playwright 需要）
    # 注意：Windows 上 SelectorEventLoop 不支持 asyncio 子进程
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

# 全局调度器实例
scheduler: Optional[TaskScheduler] = None
# 全局进程池管理器（任务分发依赖它，缺失时 pending 任务永远不会执行）
pool_manager: Optional[ProcessPoolManager] = None

logger = logging.getLogger(__name__)


def create_scheduler(ws_manager=None):
    """创建调度器并接线进程池管理器"""
    pm = ProcessPoolManager(
        max_workers=settings.MAX_WORKERS,
        memory_limit_mb=settings.WORKER_MEMORY_LIMIT_MB
    )
    sched = TaskScheduler(ws_manager=ws_manager, pool_manager=pm)
    return sched, pm


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    global scheduler, pool_manager

    # Startup
    logger.info("应用启动中...")
    try:
        # 自动执行数据库迁移（已是最新版本时为无操作）
        # 在独立线程中运行：alembic env.py 内部使用 asyncio.run，
        # 不能在事件循环内直接调用
        from app.core.migrations import run_migrations

        await asyncio.to_thread(run_migrations)
        logger.info("数据库迁移检查完成")

        scheduler, pool_manager = create_scheduler(ws_manager=websocket_manager)
        await pool_manager.start()
        await scheduler.start()
        logger.info("调度器与进程池已启动")
    except Exception as e:
        logger.error(f"启动初始化失败: {e}", exc_info=True)
        # 清理部分初始化的资源
        if scheduler:
            try:
                await scheduler.shutdown()
            except Exception:
                pass
        if pool_manager:
            try:
                await pool_manager.shutdown(wait=False)
            except Exception:
                pass
        raise  # 重新抛出异常，阻止应用启动

    yield

    # Shutdown
    logger.info("应用关闭中...")
    if scheduler:
        try:
            await scheduler.shutdown()
            logger.info("调度器已停止")
        except Exception as e:
            logger.error(f"调度器停止失败: {e}", exc_info=True)
            # 继续关闭流程，不重新抛出异常

    if pool_manager:
        try:
            await pool_manager.shutdown(wait=False)
            logger.info("进程池已停止")
        except Exception as e:
            logger.error(f"进程池停止失败: {e}", exc_info=True)


# 创建 FastAPI 应用实例
app = FastAPI(
    title="浏览器自动化数据采集平台",
    description="配置驱动的 RPA 数据采集系统（支持登录态管理和任务执行）",
    version="1.0.0",
    debug=settings.DEBUG,
    lifespan=lifespan
)

# CORS 中间件配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 挂载静态文件目录（必须在路由之前）
base_path = get_base_path()
static_dir = base_path / "static"
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# 注册路由
app.include_router(router)
app.include_router(config_router)
app.include_router(metrics_router)
app.include_router(config_test_router)

# 注册 WebSocket 路由
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket_manager.websocket_endpoint(websocket)


@app.get("/")
async def root():
    """根路径"""
    return {
        "message": "浏览器自动化数据采集平台",
        "version": "1.0.0",
        "docs": "/docs",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """健康检查接口"""
    return {"status": "healthy"}


if __name__ == "__main__":
    import multiprocessing
    import uvicorn

    # PyInstaller 打包环境：进程池子进程依赖 multiprocessing 支持
    multiprocessing.freeze_support()

    # 确保 Windows 使用正确的事件循环策略
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    # 处理命令行动作（客户端无 Python 环境，通过 exe 参数代替命令行工具）
    from app.core.cli import (
        ACTION_IMPORT_JOBS,
        ACTION_INIT_CONFIG,
        ACTION_INSTALL_BROWSER,
        ACTION_MIGRATE,
        install_browser,
        parse_cli_args,
        run_import_jobs,
        run_init_config,
    )

    action, extra_args = parse_cli_args(sys.argv[1:])
    if action == ACTION_INSTALL_BROWSER:
        install_browser()
        sys.exit(0)
    if action == ACTION_MIGRATE:
        from app.core.migrations import run_migrations

        run_migrations()
        print("数据库迁移完成")
        sys.exit(0)
    if action == ACTION_INIT_CONFIG:
        run_init_config()
        sys.exit(0)
    if action == ACTION_IMPORT_JOBS:
        if not extra_args:
            print("[ERROR] --import-jobs 需要指定文件路径")
            sys.exit(1)
        run_import_jobs(extra_args[0])
        sys.exit(0)

    # 直接传递 app 对象，而不是字符串路径
    # 这样可以兼容 PyInstaller 打包
    uvicorn.run(
        app,  # 直接传递 app 对象
        host=settings.APP_HOST,
        port=settings.APP_PORT,
        reload=False  # 打包后禁用热重载
    )
