import asyncio
import logging
import os
from typing import Optional, Dict, List, Tuple, Literal
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

    async def _broadcast_progress(self, job_id: int, message: str, current: int = None, total: int = None):
        """
        推送进度消息

        Args:
            job_id: 任务 ID
            message: 进度描述
            current: 当前进度（可选）
            total: 总进度（可选）
        """
        if not self.ws_manager:
            return

        payload = {
            "type": "progress",
            "job_id": job_id,
            "message": message,
            "timestamp": datetime.now().isoformat()
        }

        if current is not None and total is not None:
            payload["progress"] = {"current": current, "total": total}

        try:
            await self.ws_manager.broadcast(payload)
        except Exception as e:
            self.logger.error(f"Failed to broadcast progress: {e}")

    async def _broadcast_log(self, level: Literal["info", "warning", "error"], message: str, job_id: int = None):
        """
        推送日志消息

        Args:
            level: 日志级别（info/warning/error）
            message: 日志内容
            job_id: 任务 ID（可选）
        """
        if not self.ws_manager:
            return

        payload = {
            "type": "log",
            "level": level,
            "message": message,
            "timestamp": datetime.now().isoformat()
        }

        if job_id is not None:
            payload["job_id"] = job_id

        try:
            await self.ws_manager.broadcast(payload)
        except Exception as e:
            self.logger.error(f"Failed to broadcast log: {e}")

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

    async def _extract_page_data(self, page: Page, fields_mapping: Dict) -> List[Dict]:
        """
        提取当前页面的数据

        Args:
            page: 页面对象
            fields_mapping: 字段映射规则（如 {"title": ".product-title text", "link": ".detail-link @href"}）

        Returns:
            提取的数据列表
        """
        self.logger.info("开始提取当前页数据")

        # 首先尝试检测是否是列表结构
        # 简化实现：假设 fields_mapping 的第一个选择器可以定位多个元素（列表项）
        first_field = list(fields_mapping.keys())[0]
        first_rule = fields_mapping[first_field]

        # 解析选择器（去掉 text 或 @属性 部分）
        parts = first_rule.split()
        first_selector = parts[0]

        # 检查是否有多个匹配元素
        elements = page.locator(first_selector)
        count = await elements.count()

        self.logger.info(f"检测到 {count} 个数据项")

        if count == 0:
            self.logger.warning("未找到任何数据项")
            return []

        # 如果是列表结构（多个元素），逐项提取
        if count > 1:
            result = []
            for i in range(count):
                item_data = {}
                for field_name, selector_rule in fields_mapping.items():
                    try:
                        value = await self._extract_field(page, selector_rule, index=i)
                        item_data[field_name] = value
                    except Exception as e:
                        self.logger.warning(f"字段 {field_name} 提取失败（第 {i+1} 项）: {e}")
                        item_data[field_name] = None

                result.append(item_data)

            return result
        else:
            # 单条数据
            item_data = {}
            for field_name, selector_rule in fields_mapping.items():
                try:
                    value = await self._extract_field(page, selector_rule, index=0)
                    item_data[field_name] = value
                except Exception as e:
                    self.logger.warning(f"字段 {field_name} 提取失败: {e}")
                    item_data[field_name] = None

            return [item_data]

    async def _extract_field(self, page: Page, selector_rule: str, index: int = 0) -> Optional[str]:
        """
        提取单个字段的值

        Args:
            page: 页面对象
            selector_rule: 选择器规则（如 ".title text" 或 ".link @href"）
            index: 元素索引（用于列表）

        Returns:
            提取的值
        """
        parts = selector_rule.split()
        selector = parts[0]

        # 获取指定索引的元素
        element = page.locator(selector).nth(index)

        # 检查是否提取属性
        if len(parts) > 1 and parts[1].startswith('@'):
            attr_name = parts[1][1:]  # 去掉 @ 符号
            value = await element.get_attribute(attr_name)
        else:
            # 提取文本（默认行为）
            value = await element.inner_text()

        return value.strip() if value else None

    async def _extract_with_pagination(
        self,
        page: Page,
        fields_mapping: Dict,
        pagination_selector: str,
        wait_selector: str,
        max_pages: int,
        job_id: int = None
    ) -> Tuple[List[Dict], int]:
        """
        翻页提取数据

        Args:
            page: 页面对象
            fields_mapping: 字段映射规则
            pagination_selector: 下一页按钮选择器
            wait_selector: 等待加载完成的选择器
            max_pages: 最大翻页数
            job_id: 任务 ID（可选，用于进度广播）

        Returns:
            (所有数据列表, 实际页数)
        """
        all_data = []
        current_page = 1

        while current_page <= max_pages:
            self.logger.info(f"提取第 {current_page} 页数据")

            # 1. 提取当前页数据
            page_data = await self._extract_page_data(page, fields_mapping)
            all_data.extend(page_data)
            self.logger.info(f"第 {current_page} 页提取 {len(page_data)} 条数据")

            # 节点 6: 每页数据提取完成
            await self._broadcast_progress(
                job_id=job_id,
                message=f"正在处理第 {current_page} 页",
                current=current_page,
                total=max_pages
            )

            # 2. 检查是否需要翻页
            if current_page >= max_pages:
                self.logger.info(f"已达到最大页数 {max_pages}")
                break

            # 3. 检查下一页按钮是否存在
            next_button = page.locator(pagination_selector)
            count = await next_button.count()

            if count == 0:
                self.logger.info("下一页按钮不存在，停止翻页")
                break

            # 4. 检查按钮是否可用
            is_disabled = await next_button.is_disabled()
            if is_disabled:
                self.logger.info("下一页按钮已禁用，停止翻页")
                break

            # 5. 点击下一页
            self.logger.info("点击下一页按钮")
            await next_button.click(timeout=TIMEOUTS['click'])

            # 节点 7: 翻页动作
            if job_id:
                await self._broadcast_log("info", f"点击下一页按钮（第 {current_page + 1} 页）", job_id)

            # 6. 等待新页面加载
            await page.wait_for_selector(
                wait_selector,
                state="visible",
                timeout=TIMEOUTS['wait_selector']
            )
            await asyncio.sleep(1)  # 额外等待确保数据加载完成

            current_page += 1

        return all_data, current_page

    async def _save_result(
        self,
        session: AsyncSession,
        job_id: int,
        config_id: int,
        query_params: Dict,
        extracted_data: List[Dict],
        page_count: int
    ):
        """
        保存结果到数据库

        Args:
            session: 数据库 session
            job_id: 任务 ID
            config_id: 配置 ID
            query_params: 查询参数
            extracted_data: 提取的数据
            page_count: 实际页数
        """
        self.logger.info(f"保存结果到数据库：任务 {job_id}，共 {len(extracted_data)} 条数据")

        result = CrawlerResult(
            job_id=job_id,
            config_id=config_id,
            query_params=query_params,
            extracted_data={"items": extracted_data},  # 包装为标准格式
            page_count=page_count
        )

        session.add(result)
        await session.commit()
        self.logger.info("结果保存成功")

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

            # 节点 1: 任务开始
            await self._broadcast_progress(job_id, f"开始执行任务 {job_id}")

            # 3. 启动浏览器
            browser, context, playwright = await self._launch_browser(config)
            page = await context.new_page()

            self.logger.info(f"浏览器启动成功（登录态: {config.auth_profile if config.need_login else '无'}）")

            # 节点 2: 浏览器启动完成
            await self._broadcast_log(
                "info",
                f"浏览器启动成功（登录态: {config.auth_profile if config.need_login else '无'}）",
                job_id
            )

            # 4. 访问目标 URL
            await page.goto(config.target_url, timeout=TIMEOUTS['page_load'])
            self.logger.info(f"访问目标 URL: {config.target_url}")

            # 5. 填充表单
            if config.input_configs:
                await self._fill_form(page, config.input_configs, job.query_params)
                # 节点 3: 表单填充完成
                await self._broadcast_log("info", "表单填充完成", job_id)

            # 6. 点击提交按钮
            self.logger.info(f"点击提交按钮: {config.submit_selector}")
            await page.click(config.submit_selector, timeout=TIMEOUTS['click'])

            # 节点 4: 提交按钮点击
            await self._broadcast_log("info", "点击提交按钮", job_id)

            # 7. 等待结果加载
            self.logger.info(f"等待结果加载: {config.wait_selector}")
            await page.wait_for_selector(
                config.wait_selector,
                state="visible",
                timeout=TIMEOUTS['wait_selector']
            )
            await asyncio.sleep(1)  # 额外等待确保数据加载完成

            self.logger.info("结果页面加载完成")

            # 节点 5: 结果页面加载完成
            await self._broadcast_log("info", "结果页面加载完成", job_id)

            # 8. 数据提取（含翻页）
            if config.pagination_selector and config.max_pages > 1:
                extracted_data, page_count = await self._extract_with_pagination(
                    page,
                    config.fields_mapping,
                    config.pagination_selector,
                    config.wait_selector,
                    config.max_pages,
                    job_id
                )
            else:
                extracted_data = await self._extract_page_data(page, config.fields_mapping)
                page_count = 1

            self.logger.info(f"数据提取完成，共 {page_count} 页，{len(extracted_data)} 条数据")

            # 9. 保存结果
            await self._save_result(
                session,
                job_id,
                config.id,
                job.query_params,
                extracted_data,
                page_count
            )

            # 10. 更新状态为 success
            job.status = JobStatus.SUCCESS
            await session.commit()

            execution_time = (datetime.now() - start_time).total_seconds()
            self.logger.info(f"任务 {job_id} 执行成功，耗时 {execution_time:.2f} 秒")

            # 节点 8: 任务成功完成
            await self._broadcast_progress(
                job_id,
                f"任务 {job_id} 执行成功，提取 {len(extracted_data)} 条数据，耗时 {execution_time:.2f} 秒"
            )

            return {
                "job_id": job_id,
                "status": "success",
                "extracted_count": len(extracted_data),
                "pages_crawled": page_count,
                "execution_time": execution_time
            }

        except Exception as e:
            self.logger.error(f"任务 {job_id} 执行失败: {e}", exc_info=True)

            # 节点 9: 任务失败
            await self._broadcast_log("error", f"任务 {job_id} 执行失败: {str(e)}", job_id)

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
