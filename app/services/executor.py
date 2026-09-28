import asyncio
import logging
import os
import time
from typing import Optional, Dict, List, Tuple, Literal, Union
from datetime import datetime

from playwright.async_api import async_playwright, Browser, Page, Frame, TimeoutError as PlaywrightTimeoutError

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.job import JobQueue, JobStatus
from app.models.config import CrawlerConfig
from app.models.result import CrawlerResult
from app.services.metrics_collector import metrics_collector

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

    async def _broadcast_progress(self, job_id: int, data: Dict):
        """
        推送进度消息（遵循 PRD V2.0 格式）

        Args:
            job_id: 任务 ID
            data: 进度数据字典
        """
        if not self.ws_manager:
            return

        payload = {
            "type": "progress",
            "data": data
        }

        try:
            await self.ws_manager.broadcast(payload)
        except Exception as e:
            self.logger.error(f"Failed to broadcast progress: {e}")

    async def _broadcast_log(self, level: Literal["info", "success", "error", "warning"], msg: str):
        """
        推送日志消息（遵循 PRD V2.0 格式）

        Args:
            level: 日志级别（info/success/error/warning）
            msg: 日志内容
        """
        if not self.ws_manager:
            return

        payload = {
            "type": "log",
            "level": level,
            "msg": msg
        }

        try:
            await self.ws_manager.broadcast(payload)
        except Exception as e:
            self.logger.error(f"Failed to broadcast log: {e}")

    async def _fill_form(
        self,
        page: Union[Page, Frame],
        input_configs: List[Dict],
        query_params: Dict
    ):
        """
        填充表单

        Args:
            page: 页面对象或 Frame 对象
            input_configs: 输入配置列表
            query_params: 查询参数（用于占位符替换）
        """
        self.logger.info(f"开始填充表单，参数: {query_params}")

        for input_cfg in input_configs:
            selector = input_cfg['selector']
            param_key = input_cfg.get('param_key')
            input_type = input_cfg.get('input_type', 'text')

            # 从 query_params 中获取值
            if param_key:
                value = query_params.get(param_key, '')
            else:
                # 向后兼容：如果有 value 字段，使用占位符替换
                value_template = input_cfg.get('value', '')
                try:
                    value = value_template.format(**query_params) if value_template else ''
                except KeyError as e:
                    raise ValueError(f"占位符替换失败，缺少参数: {e}")

            self.logger.info(f"填充字段: {selector} = {value} (类型: {input_type})")

            try:
                if input_type == 'text' or input_type == 'fill':
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

    async def _extract_page_data(self, page: Union[Page, Frame], fields_mapping: Dict) -> List[Dict]:
        """
        提取当前页面的数据（在浏览器端一次性完成，性能优化）

        Args:
            page: 页面对象或 Frame 对象
            fields_mapping: 字段映射规则
                新格式: {"list_selector": "...", "fields": [{"name": "...", "selector": "...", "attr": "..."}]}
                旧格式: {"title": ".product-title text", "link": ".detail-link @href"}

        Returns:
            提取的数据列表
        """
        self.logger.info("开始提取当前页数据")

        # 诊断：检查 page 对象是否有效
        try:
            page_url = page.url if hasattr(page, 'url') else 'N/A'
            self.logger.info(f"提取数据的 page/frame URL: {page_url}")
        except Exception as e:
            self.logger.warning(f"无法获取 page URL: {e}")

        # 适配新旧格式
        if 'list_selector' in fields_mapping and 'fields' in fields_mapping:
            # 新格式
            container_selector = fields_mapping['list_selector']
            fields = fields_mapping['fields']

            self.logger.info(f"使用容器选择器（新格式）: {container_selector}")
            self.logger.info(f"字段数量: {len(fields)}")
            self.logger.info(f"字段列表: {[f['name'] for f in fields]}")

            # 在浏览器端一次性提取所有数据
            self.logger.info("开始执行 JavaScript 提取...")
            page_data = await page.evaluate("""
                (config) => {
                    const { containerSelector, fields } = config;
                    const result = [];

                    // 查找所有容器元素
                    let containers = document.querySelectorAll(containerSelector);
                    console.log('[提取] 容器选择器:', containerSelector);
                    console.log('[提取] 初始找到容器数量:', containers.length);

                    // 如果容器数量少于预期，等待一下（可能是异步渲染）
                    // 注意：这是同步代码中的简单重试，不是真正的异步等待
                    if (containers.length < 4) {
                        console.log('[提取] 容器数量少于4，可能数据未完全加载');
                    }

                    containers.forEach((container, containerIndex) => {
                        // 跳过 jqGrid 占位行
                        if (container.classList.contains('jqgfirstrow')) {
                            console.log(`[提取] 跳过占位行 ${containerIndex}`);
                            return;
                        }

                        const row = {};
                        let hasNonEmptyField = false;

                        fields.forEach((field, fieldIndex) => {
                            let value = '';
                            const { name, selector, attr } = field;

                            try {
                                // 在容器内查找元素
                                const element = container.querySelector(selector);

                                if (element) {
                                    if (attr === 'text') {
                                        value = element.innerText || element.textContent || '';
                                    } else if (attr === 'href' || attr === 'src') {
                                        value = element.getAttribute(attr) || '';
                                    } else {
                                        value = element.getAttribute(attr) || '';
                                    }
                                }
                            } catch (e) {
                                console.error(`提取字段 ${name} 失败:`, e);
                            }

                            const trimmedValue = value.trim();
                            row[name] = trimmedValue;

                            if (trimmedValue.length > 0) {
                                hasNonEmptyField = true;
                            }
                        });

                        // 调试：打印前5行的详细信息
                        if (containerIndex < 5) {
                            const values = Object.values(row);
                            console.log(`[提取] 行${containerIndex}: classList=${Array.from(container.classList).join(',')}, hasNonEmpty=${hasNonEmptyField}, 第1字段="${values[0]?.substring(0, 20)}", 第2字段="${values[1]?.substring(0, 30)}"`);
                        }

                        // 只添加至少有一个非空字段的行
                        if (hasNonEmptyField) {
                            result.push(row);
                        }
                    });

                    return result;
                }
            """, {"containerSelector": container_selector, "fields": fields})

            self.logger.info(f"JavaScript 执行完成，原始数据量: {len(page_data)}")

            # 输出浏览器控制台日志
            if hasattr(self, 'console_logs') and self.console_logs:
                self.logger.info(f"浏览器控制台日志 ({len(self.console_logs)} 条):")
                for log in self.console_logs[:20]:  # 最多显示前20条
                    try:
                        self.logger.info(f"  [JS] {log}")
                    except:
                        pass
                # 清空日志避免累积
                self.console_logs = []

            # Python 端智能过滤：移除无效数据行
            self.logger.info("开始 Python 端过滤...")
            filtered_data = []
            for idx, row in enumerate(page_data):
                # 获取第二个字段（通常是编码字段）
                values = list(row.values())
                self.logger.info(f"  行 {idx}: 字段数={len(values)}")
                if len(values) < 2:
                    self.logger.info(f"  行 {idx}: 字段数不足，跳过")
                    continue

                second_field = values[1].strip()
                self.logger.info(f"  行 {idx}: 第二字段='{second_field[:50]}'")

                # 检查是否为有效编码（以字母或数字开头，长度 > 5）
                import re
                if re.match(r'^[A-Z0-9][A-Z0-9]{5,}', second_field):
                    filtered_data.append(row)
                    self.logger.info(f"  行 {idx}: ✓ 保留")
                else:
                    self.logger.info(f"  行 {idx}: ✗ 过滤")

            self.logger.info(f"过滤后数据量: {len(filtered_data)}")
            page_data = filtered_data

        else:
            # 旧格式：保持原有逻辑
            first_field = list(fields_mapping.keys())[0]
            first_rule = fields_mapping[first_field]
            parts = first_rule.split()
            container_selector = parts[0]

            self.logger.info(f"使用容器选择器（旧格式）: {container_selector}")

            # 在浏览器端一次性提取所有数据
            page_data = await page.evaluate("""
                (config) => {
                    const { containerSelector, fieldsMapping } = config;
                    const result = [];

                    // 查找所有容器元素
                    const containers = document.querySelectorAll(containerSelector);

                    containers.forEach(container => {
                        const row = {};

                        for (const [fieldName, selectorRule] of Object.entries(fieldsMapping)) {
                            let value = '';

                            try {
                                // 解析选择器规则（格式：".selector text" 或 ".selector @attr"）
                                const parts = selectorRule.trim().split(/\\s+/);
                                const selector = parts[0];
                                const extractType = parts.length > 1 ? parts[1] : 'text';

                                // 在容器内查找元素
                                const element = container.querySelector(selector);

                                if (element) {
                                    if (extractType === 'text') {
                                        // 提取文本内容
                                        value = element.innerText || element.textContent || '';
                                    } else if (extractType.startsWith('@')) {
                                        // 提取属性（如 @href, @src）
                                        const attrName = extractType.substring(1);
                                        value = element.getAttribute(attrName) || '';
                                    } else {
                                        // 默认提取文本
                                        value = element.innerText || element.textContent || '';
                                    }

                                    // 去除首尾空白
                                    value = value.trim();
                                }
                            } catch (error) {
                                // 忽略错误，返回空字符串
                                console.warn(`提取字段 ${fieldName} 失败:`, error);
                            }

                            row[fieldName] = value;
                        }

                        result.push(row);
                    });

                    return result;
                }
            """, {
                "containerSelector": container_selector,
                "fieldsMapping": fields_mapping
            })

        self.logger.info(f"提取到 {len(page_data)} 条数据")

        # 打印前5条数据用于调试
        for i, item in enumerate(page_data[:5]):
            # 打印每条数据的第一个字段
            if item:
                first_key = list(item.keys())[0] if item.keys() else None
                first_value = item.get(first_key, '') if first_key else ''
                self.logger.info(f"数据行 {i+1} - {first_key}: '{first_value[:50]}'")

        if len(page_data) == 0:
            self.logger.warning("未找到任何数据项")

        return page_data

    async def _extract_with_pagination(
        self,
        page: Union[Page, Frame],
        fields_mapping: Dict,
        pagination_selector: str,
        wait_selector: str,
        max_pages: int,
        job_id: int = None
    ) -> Tuple[List[Dict], int]:
        """
        翻页提取数据

        Args:
            page: 页面对象或 Frame 对象
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
                data={
                    "current_page": current_page,
                    "total_pages": max_pages,
                    "status": "processing"
                }
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
                await self._broadcast_log("info", f"点击下一页按钮（第 {current_page + 1} 页）")

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
        start_time = None  # Initialize to None to prevent NameError in finally
        success = False
        browser = None
        context = None
        playwright = None
        page = None
        job = None  # Initialize to prevent NameError in exception handler

        try:
            start_time = time.time()

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
            await self._broadcast_progress(
                job_id=job_id,
                data={
                    "job_id": job_id,
                    "status": "running",
                    "current_page": 0,
                    "total_pages": config.max_pages
                }
            )

            # 3. 启动浏览器
            browser, context, playwright = await self._launch_browser(config)
            page = await context.new_page()

            # 监听浏览器控制台（用于调试）
            self.console_logs = []
            def handle_console(msg):
                self.console_logs.append(msg.text)
            page.on("console", handle_console)

            self.logger.info(f"浏览器启动成功（登录态: {config.auth_profile if config.need_login else '无'}）")

            # 节点 2: 浏览器启动完成
            await self._broadcast_log(
                "info",
                f"浏览器启动成功（登录态: {config.auth_profile if config.need_login else '无'}）"
            )

            # 4. 访问目标 URL
            await page.goto(config.target_url, timeout=TIMEOUTS['page_load'], wait_until='networkidle')
            self.logger.info(f"访问目标 URL: {config.target_url}")

            # 等待页面完全加载（iframe 内容可能需要额外时间渲染）
            await asyncio.sleep(10)
            await self._broadcast_log("info", "页面加载完成，检测 iframe...")

            # 5. 检测 iframe 并选择正确的操作上下文
            target_frame = page

            # 检查是否配置了多层iframe
            iframe_levels = 0
            if isinstance(config.fields_mapping, dict):
                iframe_levels = config.fields_mapping.get('iframe_levels', 0)

            if iframe_levels >= 2:
                # 处理多层嵌套iframe（医保局等复杂页面）
                self.logger.info(f"检测到多层iframe配置，层数: {iframe_levels}")
                await self._broadcast_log("info", f"处理{iframe_levels}层嵌套iframe...")

                try:
                    # 获取第1层iframe选择器
                    iframe1_selector = config.fields_mapping.get('iframe1_selector')
                    if iframe1_selector:
                        self.logger.info(f"等待第1层iframe: {iframe1_selector}")
                        iframe1_element = await page.wait_for_selector(iframe1_selector, timeout=10000)
                        iframe1 = await iframe1_element.content_frame()

                        if not iframe1:
                            raise Exception("无法获取第1层iframe")

                        self.logger.info("成功进入第1层iframe")
                        await self._broadcast_log("info", "进入第1层iframe")

                        # 等待第1层iframe加载
                        await iframe1.wait_for_load_state("networkidle", timeout=10000)
                        await asyncio.sleep(2)

                        # 获取第2层iframe选择器
                        iframe2_selector = config.fields_mapping.get('iframe2_selector')
                        if iframe2_selector:
                            self.logger.info(f"等待第2层iframe: {iframe2_selector}")
                            iframe2_element = await iframe1.wait_for_selector(iframe2_selector, timeout=10000)
                            iframe2 = await iframe2_element.content_frame()

                            if not iframe2:
                                raise Exception("无法获取第2层iframe")

                            self.logger.info("成功进入第2层iframe")
                            await self._broadcast_log("info", "进入第2层iframe")

                            # 等待第2层iframe加载
                            await iframe2.wait_for_load_state("networkidle", timeout=10000)
                            await asyncio.sleep(2)

                            target_frame = iframe2
                            # 在 Frame 上注册控制台监听
                            target_frame.on("console", handle_console)
                            await self._broadcast_log("success", "成功定位到目标iframe")
                        else:
                            target_frame = iframe1
                    else:
                        self.logger.warning("未配置iframe1_selector，将使用自动检测")

                except Exception as e:
                    self.logger.error(f"多层iframe处理失败: {e}")
                    await self._broadcast_log("error", f"iframe处理失败: {e}")
                    raise

            # 如果没有配置多层iframe，使用原有的自动检测逻辑
            elif target_frame == page:
                frames = page.frames
                self.logger.info(f"检测到 {len(frames)} 个 frame")
                await self._broadcast_log("info", f"检测到 {len(frames)} 个 frame")

                if len(frames) > 1:
                    # 尝试在每个 frame 中查找可见的输入框
                    for idx, frame in enumerate(frames):
                        try:
                            self.logger.info(f"检查 Frame {idx}: {frame.url}")
                            # 检查是否有可见输入框
                            inputs = await frame.query_selector_all('input')
                            self.logger.info(f"Frame {idx} 找到 {len(inputs)} 个输入框")

                            visible_inputs = []
                            for inp in inputs:
                                try:
                                    if await inp.is_visible():
                                        visible_inputs.append(inp)
                                except:
                                    pass

                            self.logger.info(f"Frame {idx} 有 {len(visible_inputs)} 个可见输入框")

                            if len(visible_inputs) > 0:
                                self.logger.info(f"选择 Frame {idx} ({frame.url})")
                                target_frame = frame
                                # 在 Frame 上也注册控制台监听
                                target_frame.on("console", handle_console)
                                await self._broadcast_log("info", f"使用 Frame {idx}: {frame.url}")
                                break
                        except Exception as e:
                            self.logger.warning(f"Frame {idx} 检查失败: {e}")
                            continue

            if target_frame == page:
                self.logger.info("使用主页面（未找到合适的 iframe）")
                await self._broadcast_log("info", "使用主页面")

            # 6. 填充表单
            if config.input_configs:
                # 提取 inputs 列表（兼容新旧格式）
                inputs = config.input_configs.get('inputs', config.input_configs) if isinstance(config.input_configs, dict) else config.input_configs
                await self._fill_form(target_frame, inputs, job.query_params)
                # 节点 3: 表单填充完成
                await self._broadcast_log("info", "表单填充完成")

            # 7. 点击提交按钮
            self.logger.info(f"点击提交按钮: {config.submit_selector}")
            await target_frame.click(config.submit_selector, timeout=TIMEOUTS['click'])

            # 节点 4: 提交按钮点击
            await self._broadcast_log("info", "点击提交按钮")

            # 8. 等待结果加载
            self.logger.info(f"等待结果加载: {config.wait_selector}")
            await target_frame.wait_for_selector(
                config.wait_selector,
                state="visible",
                timeout=TIMEOUTS['wait_selector']
            )

            # 额外等待确保数据完全加载（特别是动态渲染的内容）
            await asyncio.sleep(3)

            # 尝试等待真实的数据行（包含编码的单元格）
            # 这比等待空表格更可靠
            try:
                # 等待至少有 3 个 tbody tr（1个占位行 + 至少2个数据/分页行）
                await target_frame.wait_for_function("""
                    () => {
                        const rows = document.querySelectorAll('table tbody tr');
                        return rows.length >= 3;
                    }
                """, timeout=10000)
                self.logger.info("表格行数已达到最小值")

                # 再等待出现包含编码的单元格
                await target_frame.wait_for_function("""
                    () => {
                        const cells = document.querySelectorAll('table tbody tr td');
                        for (const cell of cells) {
                            const text = cell.innerText || cell.textContent || '';
                            // 查找包含编码的单元格（通常以 C 开头，长度 > 10）
                            if (text.trim().length > 10 && /^[A-Z0-9]/.test(text.trim())) {
                                return true;
                            }
                        }
                        return false;
                    }
                """, timeout=10000)
                self.logger.info("数据行已完全加载")

                #关键：额外等待确保 DOM 完全稳定并且所有行都已渲染
                # jqGrid 可能在数据加载后还会重新渲染 DOM
                await asyncio.sleep(2)
                self.logger.info("额外等待 2 秒确保 DOM 稳定")
            except Exception as e:
                self.logger.warning(f"等待数据行加载超时，继续执行: {e}")

            self.logger.info("结果页面加载完成")

            # 节点 5: 结果页面加载完成
            await self._broadcast_log("info", "结果页面加载完成")

            # 9. 数据提取（含翻页）
            self.logger.info(f"准备提取数据，target_frame 类型: {type(target_frame).__name__}")
            if hasattr(target_frame, 'url'):
                self.logger.info(f"target_frame URL: {target_frame.url}")

            # 数据提取重试机制（针对异步加载的数据）
            max_retries = 2
            retry_delay = 3  # 秒

            extracted_data = []
            page_count = 1

            for attempt in range(max_retries):
                self.logger.info(f"=== 第 {attempt + 1} 次提取尝试 ===")
                if config.pagination_selector and config.max_pages > 1:
                    self.logger.info("使用分页提取")
                    extracted_data, page_count = await self._extract_with_pagination(
                        target_frame,
                        config.fields_mapping,
                        config.pagination_selector,
                        config.wait_selector,
                        config.max_pages,
                        job_id
                    )
                else:
                    self.logger.info("使用单页提取")
                    extracted_data = await self._extract_page_data(target_frame, config.fields_mapping)
                    page_count = 1

                self.logger.info(f"提取方法返回，数据量: {len(extracted_data)}")

                # 如果提取到数据，直接返回
                if len(extracted_data) > 0:
                    self.logger.info(f"第 {attempt + 1} 次尝试成功，提取到 {len(extracted_data)} 条数据")
                    break

                # 如果是最后一次尝试，不再重试
                if attempt < max_retries - 1:
                    self.logger.warning(f"第 {attempt + 1} 次尝试未提取到数据，{retry_delay}秒后重试...")
                    await asyncio.sleep(retry_delay)
                else:
                    self.logger.warning(f"已尝试 {max_retries} 次，仍未提取到数据")

            self.logger.info(f"数据提取完成，共 {page_count} 页，{len(extracted_data)} 条数据")

            # 打印前3条数据用于调试
            for i, item in enumerate(extracted_data[:3]):
                self.logger.info(f"数据 {i+1}: {item}")

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

            success = True
            execution_time = time.time() - start_time
            self.logger.info(f"任务 {job_id} 执行成功，耗时 {execution_time:.2f} 秒")

            # 节点 8: 任务成功完成
            await self._broadcast_progress(
                job_id=job_id,
                data={
                    "job_id": job_id,
                    "status": "completed",
                    "extracted_count": len(extracted_data),
                    "pages_crawled": page_count,
                    "execution_time": execution_time
                }
            )
            await self._broadcast_log(
                "success",
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
            await self._broadcast_log("error", f"任务 {job_id} 执行失败: {str(e)}")
            await self._broadcast_progress(
                job_id=job_id,
                data={
                    "job_id": job_id,
                    "status": "failed",
                    "error": str(e)
                }
            )

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
            # 记录指标（不能影响资源清理）
            try:
                if start_time is not None:  # 确保 start_time 已初始化
                    execution_time = time.time() - start_time

                    await metrics_collector.record(
                        metric_name="job_execution_time",
                        value=execution_time,
                        labels={"job_id": str(job_id)}
                    )

                    # 记录成功/失败率
                    if success:
                        await metrics_collector.record(
                            metric_name="job_success_rate",
                            value=1.0,
                            labels={"status": "success"}
                        )
                    else:
                        await metrics_collector.record(
                            metric_name="job_failure_rate",
                            value=1.0,
                            labels={"status": "failed"}
                        )

                    self.logger.info(
                        f"任务 {job_id} 执行完成 - "
                        f"状态: {'成功' if success else '失败'}, "
                        f"耗时: {execution_time:.2f}s"
                    )
            except Exception as e:
                self.logger.error(f"指标记录失败: {e}", exc_info=True)

            # 资源清理（必须执行）
            # Cleanup in reverse order of creation to prevent resource leaks
            if page:
                await page.close()
            if context:
                await context.close()
            if browser:
                await browser.close()
            if playwright:
                await playwright.stop()
