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

    async def _fill_form(
        self,
        page: Page,
        input_configs: List[Dict],
        query_params: Dict
    ):
        """
        填充表单

        Args:
            page: 页面对象
            input_configs: 输入配置列表
            query_params: 查询参数（用于占位符替换）
        """
        self.logger.info(f"开始填充表单，参数: {query_params}")

        for input_cfg in input_configs:
            selector = input_cfg['selector']
            value_template = input_cfg['value']
            input_type = input_cfg.get('type', 'fill')

            # 占位符替换
            try:
                value = value_template.format(**query_params)
            except KeyError as e:
                raise ValueError(f"占位符替换失败，缺少参数: {e}")

            self.logger.info(f"填充字段: {selector} = {value} (类型: {input_type})")

            try:
                if input_type == 'fill':
                    await page.fill(selector, value, timeout=TIMEOUTS['click'])
                elif input_type == 'select':
                    await page.select_option(selector, value, timeout=TIMEOUTS['click'])
                elif input_type == 'check':
                    await page.check(selector, timeout=TIMEOUTS['click'])
                else:
                    self.logger.warning(f"未知的输入类型: {input_type}，使用 fill")
                    await page.fill(selector, value, timeout=TIMEOUTS['click'])
            except PlaywrightTimeoutError:
                raise TimeoutError(f"元素 {selector} 等待超时")
            except Exception as e:
                raise Exception(f"填充字段 {selector} 失败: {e}")

        self.logger.info("表单填充完成")

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

            # 5. 填充表单
            if config.input_configs:
                await self._fill_form(page, config.input_configs, job.query_params)

            # 6. 点击提交按钮
            self.logger.info(f"点击提交按钮: {config.submit_selector}")
            await page.click(config.submit_selector, timeout=TIMEOUTS['click'])

            # 7. 等待结果加载
            self.logger.info(f"等待结果加载: {config.wait_selector}")
            await page.wait_for_selector(
                config.wait_selector,
                state="visible",
                timeout=TIMEOUTS['wait_selector']
            )
            await asyncio.sleep(1)  # 额外等待确保数据加载完成

            self.logger.info("结果页面加载完成")

            # TODO: 数据提取和保存

            return {
                "job_id": job_id,
                "status": "success",
                "message": "表单填充和提交成功"
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
