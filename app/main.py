import logging
from fastapi import FastAPI
from app.api import endpoints

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

# 创建 FastAPI 应用
app = FastAPI(
    title="Browser Automation Platform",
    description="基于 Playwright 的浏览器自动化采集平台",
    version="1.0.0"
)

# 注册路由
app.include_router(endpoints.router)


@app.get("/")
async def root():
    """根路径"""
    return {
        "message": "Browser Automation Platform API",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy"}
