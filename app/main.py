import sys
import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Optional
from fastapi import FastAPI, WebSocket
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.endpoints import router
from app.api.websocket import websocket_manager
from app.services.scheduler import TaskScheduler

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

# Windows 平台 Playwright 兼容性设置
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

# 全局调度器实例
scheduler: Optional[TaskScheduler] = None

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    global scheduler

    # Startup
    logger.info("应用启动中...")
    scheduler = TaskScheduler(ws_manager=websocket_manager)
    await scheduler.start()
    logger.info("调度器已启动")

    yield

    # Shutdown
    logger.info("应用关闭中...")
    if scheduler:
        await scheduler.shutdown()
    logger.info("调度器已停止")


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

# 注册路由
app.include_router(router)

# 注册 WebSocket 路由
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket_manager.websocket_endpoint(websocket)

# 挂载静态文件目录
app.mount("/static", StaticFiles(directory="static"), name="static")


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
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.APP_HOST,
        port=settings.APP_PORT,
        reload=settings.DEBUG
    )
