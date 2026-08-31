import asyncio
import logging
import os
from typing import Optional, Dict, List, Tuple
from datetime import datetime

from playwright.async_api import async_playwright, Browser, Page, TimeoutError as PlaywrightTimeoutError

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.job import JobQueue, JobStatus
from app.models.config import CrawlerConfig
from app.models.result import CrawlerResult

# 配置日志
logger = logging.getLogger(__name__)

# 超时配置（毫秒）
TIMEOUTS = {
    "page_load": 30000,      # 页面加载超时 30秒
    "wait_selector": 15000,  # 元素等待超时 15秒
    "navigation": 30000,     # 页面跳转超时 30秒
    "click": 10000,          # 点击操作超时 10秒
}


class PlaywrightExecutor:
    """Playwright 浏览器自动化执行器"""

    def __init__(self, ws_manager=None):
        """
        初始化执行器

        Args:
            ws_manager: WebSocket 管理器（可选，用于状态推送）
        """
        self.ws_manager = ws_manager
        self.logger = logger

    async def _launch_browser(self, config: CrawlerConfig) -> Tuple[Browser, object, object]:
        """
        启动浏览器（根据登录态配置）

        Args:
            config: 配置对象

        Returns:
            (Browser, Context, Playwright) 实例元组，用于后续清理
        """
        # Validate auth_profile when need_login=True
        if config.need_login:
            if not config.auth_profile:
                raise ValueError("auth_profile 必须在 need_login=True 时提供")

        p = await async_playwright().start()
        try:
            browser = await p.chromium.launch(
                headless=True,
                args=['--disable-blink-features=AutomationControlled']
            )

            if config.need_login:
                auth_file = f"auth_files/auth_{config.auth_profile}.json"

                if not os.path.exists(auth_file):
                    raise FileNotFoundError(
                        f"登录态文件不存在: {auth_file}，请先通过 /auth/start 接口更新登录态"
                    )

                self.logger.info(f"加载登录态: {auth_file}")
                context = await browser.new_context(storage_state=auth_file)
            else:
                self.logger.info("使用匿名浏览器上下文")
                context = await browser.new_context()

            return browser, context, p
        except Exception:
            await p.stop()
            raise

    async def execute_job(self, job_id: int, session: AsyncSession) -> Dict:
        """
        执行单个任务

        Args:
            job_id: 任务 ID
            session: 数据库 session

        Returns:
            执行结果字典
        """
        start_time = datetime.now()  # Will be used in future tasks for execution timing
        browser = None
        context = None
        playwright = None
        page = None
        job = None  # Initialize to prevent NameError in exception handler

        try:
            # 1. 查询任务和配置
            stmt = select(JobQueue).where(JobQueue.id == job_id)
            result = await session.execute(stmt)
            job = result.scalar_one_or_none()

            if not job:
                raise ValueError(f"任务不存在: {job_id}")

            stmt = select(CrawlerConfig).where(CrawlerConfig.id == job.config_id)
            result = await session.execute(stmt)
            config = result.scalar_one_or_none()

            if not config:
                raise ValueError(f"配置不存在: {job.config_id}")

            self.logger.info(f"开始执行任务 {job_id}，配置: {config.config_name}")

            # 2. 更新状态为 processing
            job.status = JobStatus.PROCESSING
            await session.commit()

            # 3. 启动浏览器
            browser, context, playwright = await self._launch_browser(config)
            page = await context.new_page()

            self.logger.info(f"浏览器启动成功（登录态: {config.auth_profile if config.need_login else '无'}）")

            # 4. 访问目标 URL
            await page.goto(config.target_url, timeout=TIMEOUTS['page_load'])
            self.logger.info(f"访问目标 URL: {config.target_url}")

            # TODO: 表单填充、数据提取等后续步骤

            return {
                "job_id": job_id,
                "status": "success",
                "message": "浏览器启动成功"
            }

        except Exception as e:
            self.logger.error(f"任务 {job_id} 执行失败: {e}", exc_info=True)

            if job:
                job.status = JobStatus.FAILED
                job.error_msg = str(e)
                job.retry_count += 1
                await session.commit()

            return {
                "job_id": job_id,
                "status": "failed",
                "error": str(e)
            }

        finally:
            # Cleanup in reverse order of creation to prevent resource leaks
            if page:
                await page.close()
            if context:
                await context.close()
            if browser:
                await browser.close()
            if playwright:
                await playwright.stop()
