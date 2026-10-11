import asyncio
import logging
import os
import sys
import time
from typing import Optional, Dict, List, Tuple, Literal, Union
from datetime import datetime

from playwright.async_api import async_playwright, Browser, Page, Frame, Locator, TimeoutError as PlaywrightTimeoutError

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.job import JobQueue, JobStatus
from app.models.config import CrawlerConfig
from app.models.result import CrawlerResult
from app.services.metrics_collector import metrics_collector

# Windows 平台设置事件循环策略（必须在使用 Playwright 之前设置）
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

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

    def _load_timeouts(self, config: CrawlerConfig) -> Dict:
        """
        加载超时配置

        Args:
            config: 配置对象

        Returns:
            超时配置字典（毫秒）
        """
        # 默认超时配置
        timeouts = {
            "page_load": 30000,
            "wait_selector": 15000,
            "navigation": 30000,
            "click": 10000,
        }

        # 如果配置中有自定义超时，则合并
        if config.timeout_config:
            timeouts.update(config.timeout_config)
            self.logger.info(f"使用自定义超时配置: {config.timeout_config}")

        return timeouts

    def _load_extraction_config(self, config: CrawlerConfig) -> Dict:
        """
        加载提取配置（过滤器、等待时间、重试等）

        Args:
            config: 配置对象

        Returns:
            提取配置字典
        """
        # 默认提取配置
        extraction_config = {
            "filters": [],
            "wait_times": {
                "before_extraction": 3000,
                "after_click": 1000,
                "between_pages": 2000
            },
            "retry": {
                "max_attempts": 2,
                "delay_seconds": 3
            }
        }

        # 如果配置中有自定义提取配置，深度合并
        if config.extraction_config:
            # 合并 filters
            if "filters" in config.extraction_config:
                extraction_config["filters"] = config.extraction_config["filters"]

            # 合并 wait_times
            if "wait_times" in config.extraction_config:
                extraction_config["wait_times"].update(config.extraction_config["wait_times"])

            # 合并 retry
            if "retry" in config.extraction_config:
                extraction_config["retry"].update(config.extraction_config["retry"])

            self.logger.info(f"使用自定义提取配置: {config.extraction_config}")

        return extraction_config

    def _apply_filters(self, data: List[Dict], filters: List[Dict]) -> List[Dict]:
        """
        应用过滤器到提取的数据

        Args:
            data: 原始数据列表
            filters: 过滤器配置列表
                格式: [
                    {
                        "field_index": 1,
                        "type": "regex",
                        "pattern": "^[A-Z0-9]{6,}",
                        "action": "keep"
                    },
                    {
                        "field_index": 2,
                        "type": "length",
                        "min": 2,
                        "max": 100,
                        "action": "drop"
                    }
                ]

        Returns:
            过滤后的数据列表
        """
        if not filters:
            return data

        import re

        filtered_data = []

        for row in data:
            # 转换为值列表
            values = list(row.values())

            # 默认保留该行
            should_keep = True

            for filter_rule in filters:
                # 获取字段索引
                field_index = filter_rule.get("field_index", 0)

                # 检查索引是否有效
                if field_index >= len(values):
                    self.logger.warning(f"field_index {field_index} 超出范围，跳过此过滤器")
                    continue

                # 获取字段值
                field_value = values[field_index]

                # 获取过滤类型和动作
                filter_type = filter_rule.get("type")
                action = filter_rule.get("action", "keep")

                # 判断是否匹配
                is_match = False

                if filter_type == "regex":
                    # 正则表达式过滤
                    pattern = filter_rule.get("pattern", "")
                    if pattern and re.match(pattern, str(field_value)):
                        is_match = True

                elif filter_type == "length":
                    # 长度过滤
                    min_length = filter_rule.get("min", 0)
                    max_length = filter_rule.get("max", float('inf'))
                    value_length = len(str(field_value))

                    if min_length <= value_length <= max_length:
                        is_match = True

                elif filter_type == "empty":
                    # 空值检测
                    is_empty = not field_value or str(field_value).strip() == ""
                    allow_empty = filter_rule.get("allow_empty", False)

                    # 如果允许空值且字段为空，或字段非空，则匹配
                    if (allow_empty and is_empty) or (not is_empty):
                        is_match = True

                # 根据 action 和 is_match 决定是否保留
                if action == "keep":
                    # keep 模式：匹配则保留，不匹配则丢弃
                    if not is_match:
                        should_keep = False
                        break
                elif action == "drop":
                    # drop 模式：匹配则丢弃，不匹配则保留
                    if is_match:
                        should_keep = False
                        break

            if should_keep:
                filtered_data.append(row)

        self.logger.info(f"过滤器应用完成: {len(data)} -> {len(filtered_data)} 条数据")
        return filtered_data

    async def _extract_with_retry(
        self,
        page: Union[Page, Frame],
        fields_mapping: Dict,
        retry_config: Dict
    ) -> List[Dict]:
        """
        带重试机制的数据提取

        Args:
            page: 页面对象或 Frame 对象
            fields_mapping: 字段映射规则
            retry_config: 重试配置
                格式: {"max_attempts": 2, "delay_seconds": 3}

        Returns:
            提取的数据列表
        """
        max_attempts = retry_config.get("max_attempts", 2)
        delay_seconds = retry_config.get("delay_seconds", 3)

        for attempt in range(max_attempts):
            self.logger.info(f"第 {attempt + 1}/{max_attempts} 次提取尝试")

            try:
                data = await self._extract_page_data(page, fields_mapping)

                if len(data) > 0:
                    self.logger.info(f"第 {attempt + 1} 次尝试成功，提取到 {len(data)} 条数据")
                    return data
                else:
                    self.logger.warning(f"第 {attempt + 1} 次尝试未提取到数据")

            except Exception as e:
                self.logger.error(f"第 {attempt + 1} 次提取失败: {e}")

            # 如果不是最后一次尝试，等待后重试
            if attempt < max_attempts - 1:
                self.logger.info(f"等待 {delay_seconds} 秒后重试...")
                await asyncio.sleep(delay_seconds)

        self.logger.warning(f"已尝试 {max_attempts} 次，仍未成功提取数据")
        return []

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
        query_params: Dict,
        timeouts: Dict = None
    ):
        """
        填充表单

        Args:
            page: 页面对象或 Frame 对象
            input_configs: 输入配置列表
            query_params: 查询参数（用于占位符替换）
            timeouts: 超时配置（可选）
        """
        if timeouts is None:
            timeouts = TIMEOUTS

        self.logger.info(f"开始填充表单，参数: {query_params}")

        for input_cfg in input_configs:
            selector = input_cfg['selector']
            # 兼容 param_key 和 param_name
            param_key = input_cfg.get('param_key') or input_cfg.get('param_name')
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
                # 先等待元素可见和可交互
                await page.wait_for_selector(selector, state='visible', timeout=timeouts['wait_selector'])
                self.logger.debug(f"元素 {selector} 已可见")

                # 再等待一小段时间确保元素完全加载（iframe 内的元素可能需要额外时间）
                await asyncio.sleep(0.5)

                if input_type == 'text' or input_type == 'fill':
                    await page.fill(selector, value, timeout=timeouts['click'])
                elif input_type == 'select':
                    await page.select_option(selector, value, timeout=timeouts['click'])
                elif input_type == 'check':
                    await page.check(selector, timeout=timeouts['click'])
                else:
                    self.logger.warning(f"未知的输入类型: {input_type}，使用 fill")
                    await page.fill(selector, value, timeout=timeouts['click'])
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

    async def _extract_detail_data(
        self,
        main_page: Union[Page, Frame],
        detail_button: Locator,
        detail_config: Dict,
        row_index: int
    ) -> Tuple[Union[Dict, List[Dict]], str, Optional[str]]:
        """
        提取单条数据的详情

        Args:
            main_page: 列表页面/Frame
            detail_button: 详情按钮定位器
            detail_config: 详情配置
            row_index: 当前行索引（用于日志）

        Returns:
            (detail_data, status, error_msg)
            - detail_data: 提取的详情字典或字典列表（如果是detail_list_mode）
            - status: "success"/"failed"
            - error_msg: 失败时的错误信息
        """
        try:
            # 1. 点击详情按钮
            self.logger.info(f"[详情] 第 {row_index + 1} 条：点击详情按钮")
            click_timeout = detail_config.get('timeout', {}).get('click', 10000)
            click_method = detail_config.get('click_method', 'default')

            if click_method == 'javascript':
                # 使用JavaScript点击，避免元素遮挡问题
                self.logger.info(f"[详情] 使用JavaScript点击方法")
                await detail_button.evaluate("element => element.click()")
            else:
                # 默认Playwright点击
                await detail_button.click(timeout=click_timeout)

            # 2. 等待并切换到详情iframe（如果配置了）
            detail_frame = main_page
            detail_iframe_selector = detail_config.get('detail_iframe_selector')

            if detail_iframe_selector:
                iframe_timeout = detail_config.get('timeout', {}).get('iframe_load', 10000)
                self.logger.info(f"[详情] 等待详情iframe: {detail_iframe_selector}")

                iframe_element = await main_page.wait_for_selector(
                    detail_iframe_selector,
                    timeout=iframe_timeout
                )
                detail_frame = await iframe_element.content_frame()

                if not detail_frame:
                    raise Exception(f"无法获取详情iframe: {detail_iframe_selector}")

                self.logger.info(f"[详情] 成功切换到详情iframe")

            # 3. 等待详情内容加载
            wait_selector = detail_config['wait_selector']
            wait_timeout = detail_config.get('timeout', {}).get('wait_selector', 5000)

            self.logger.info(f"[详情] 等待详情内容加载: {wait_selector}")
            await detail_frame.wait_for_selector(
                wait_selector,
                state="visible",
                timeout=wait_timeout
            )

            # 额外等待确保数据完全加载
            await asyncio.sleep(1)

            # 4. 检查是否为列表模式（详情中包含多条记录）
            detail_list_mode = detail_config.get('detail_list_mode', False)
            detail_data = None

            if detail_list_mode:
                # 列表模式：提取详情iframe中的所有行（支持分页）
                self.logger.info(f"[详情] 列表模式：提取详情列表数据")

                # 重要：重置jqGrid到第1页（避免保留之前的页码状态）
                try:
                    await detail_frame.evaluate("""
                        () => {
                            const grid = jQuery('table.ui-jqgrid-btable:first')[0];
                            if (grid && grid.id) {
                                const gridId = grid.id;
                                jQuery('#' + gridId).jqGrid('setGridParam', {page: 1}).trigger('reloadGrid');
                            }
                        }
                    """)
                    self.logger.info("[详情] 已重置jqGrid到第1页")
                    await asyncio.sleep(2)  # 等待重置完成
                except Exception as e:
                    self.logger.warning(f"[详情] 重置jqGrid失败: {e}")

                detail_list_selector = detail_config.get('detail_list_selector', 'tbody tr.jqgrow')
                detail_fields = detail_config['fields']
                detail_pagination_selector = detail_config.get('detail_pagination_selector')

                all_detail_items = []
                detail_page = 1
                max_detail_pages = detail_config.get('max_detail_pages', 10)

                # 循环提取每一页的详情数据
                while detail_page <= max_detail_pages:
                    # 等待当前页数据加载（智能等待：如果0行则重试）
                    detail_rows = detail_frame.locator(detail_list_selector)
                    row_count = 0

                    # 最多等待5次，每次2秒（总共10秒）
                    for wait_attempt in range(5):
                        await asyncio.sleep(2)
                        row_count = await detail_rows.count()

                        if row_count > 0:
                            self.logger.info(f"[详情] 第 {detail_page} 页，行数: {row_count}（等待 {(wait_attempt+1)*2}s 后加载完成）")
                            break
                        else:
                            self.logger.debug(f"[详情] 第 {detail_page} 页，等待 {(wait_attempt+1)*2}s 后仍为0行，继续等待...")

                    # 如果等待5次后仍然是0行，则停止
                    if row_count == 0:
                        self.logger.warning(f"[详情] 第 {detail_page} 页等待10秒后仍为空，停止翻页")
                        break

                    # 提取当前页所有行的数据
                    page_items = await detail_rows.evaluate_all("""
                        (rows, fields) => {
                            return rows.map(row => {
                                const result = {};
                                for (const field of fields) {
                                    const {name, selector, attr} = field;
                                    let value = '';
                                    try {
                                        const element = row.querySelector(selector);
                                        if (element) {
                                            if (attr === 'text') {
                                                value = element.innerText || element.textContent || '';
                                            } else {
                                                value = element.getAttribute(attr) || '';
                                            }
                                            value = value.trim();
                                        }
                                    } catch (e) {
                                        console.error(`提取字段 ${name} 失败:`, e);
                                    }
                                    result[name] = value;
                                }
                                return result;
                            });
                        }
                    """, detail_fields)

                    all_detail_items.extend(page_items)
                    self.logger.info(f"[详情] 第 {detail_page} 页提取 {len(page_items)} 条记录，累计 {len(all_detail_items)} 条")

                    # 检查是否有下一页（核心逻辑：只依赖按钮状态）
                    if not detail_pagination_selector:
                        self.logger.info("[详情] 未配置分页选择器，停止翻页")
                        break

                    # 检查"下一页"按钮状态
                    button_disabled = await detail_frame.evaluate(f"""
                        () => {{
                            const btn = document.querySelector('{detail_pagination_selector}');
                            if (!btn) return true;
                            return btn.classList.contains('ui-state-disabled');
                        }}
                    """)

                    if button_disabled:
                        self.logger.info("[详情] 下一页按钮已禁用，已到最后一页")
                        break

                    # 使用jqGrid API翻页
                    try:
                        self.logger.info("[详情] 点击下一页")
                        await detail_frame.evaluate("""
                            () => {
                                const grid = jQuery('table.ui-jqgrid-btable:first')[0];
                                if (grid && grid.id) {
                                    const currentPage = jQuery('#' + grid.id).jqGrid('getGridParam', 'page');
                                    jQuery('#' + grid.id).jqGrid('setGridParam', {page: currentPage + 1}).trigger('reloadGrid');
                                }
                            }
                        """)
                        await asyncio.sleep(3)  # 等待AJAX加载
                        detail_page += 1
                    except Exception as e:
                        self.logger.warning(f"[详情] 翻页失败: {e}")
                        break

                detail_data = all_detail_items
                self.logger.info(f"[详情] 第 {row_index + 1} 条：共提取了 {len(all_detail_items)} 条详情记录（{detail_page} 页）")

            else:
                # 单条模式：提取详情字段
                detail_fields = detail_config['fields']
                self.logger.info(f"[详情] 单条模式：提取 {len(detail_fields)} 个详情字段")

                # 使用浏览器端JavaScript一次性提取所有字段
                detail_data = await detail_frame.evaluate("""
                    (fields) => {
                        const result = {};

                        for (const field of fields) {
                            const {name, selector, attr} = field;
                            let value = '';

                            try {
                                const element = document.querySelector(selector);

                                if (element) {
                                    if (attr === 'text') {
                                        value = element.innerText || element.textContent || '';
                                    } else if (attr === 'href' || attr === 'src') {
                                        value = element.getAttribute(attr) || '';
                                    } else {
                                        value = element.getAttribute(attr) || '';
                                    }

                                    value = value.trim();
                                }
                            } catch (e) {
                                console.error(`提取字段 ${name} 失败:`, e);
                            }

                            result[name] = value;
                        }

                        return result;
                    }
                """, detail_fields)

                self.logger.info(f"[详情] 第 {row_index + 1} 条提取完成，字段数: {len(detail_data)}")

            # 5. 关闭详情（失败不影响数据返回）
            try:
                close_method = detail_config.get('close_method', 'auto')
                close_selector = detail_config.get('close_selector')
                close_timeout = detail_config.get('timeout', {}).get('close', 5000)

                if close_method == 'click' and close_selector:
                    # 点击关闭按钮（在主frame中查找）
                    self.logger.info(f"[详情] 点击关闭按钮: {close_selector}")
                    await main_page.click(close_selector, timeout=close_timeout)
                elif close_method == 'escape':
                    # 按ESC键（使用page对象）
                    self.logger.info(f"[详情] 按ESC键关闭")
                    await main_page.page.keyboard.press('Escape')
                elif close_method == 'auto':
                    # 自动选择：优先点击，失败则ESC
                    if close_selector:
                        try:
                            await main_page.click(close_selector, timeout=close_timeout)
                        except Exception as e:
                            self.logger.info(f"[详情] 关闭按钮点击失败 ({e})，改用ESC键")
                            await main_page.page.keyboard.press('Escape')
                    else:
                        await main_page.page.keyboard.press('Escape')

                # 6. 等待返回列表页并验证iframe完全消失（最多尝试5次）
                iframe_closed = False
                for close_attempt in range(5):
                    await asyncio.sleep(1)

                    try:
                        iframe_count = await main_page.locator('iframe.artDialog-iframe').count()

                        if iframe_count == 0:
                            self.logger.info(f"[详情] iframe已完全关闭（等待 {close_attempt+1}s）")
                            iframe_closed = True
                            break
                        else:
                            self.logger.warning(f"[详情] 等待 {close_attempt+1}s 后仍有 {iframe_count} 个iframe，继续等待...")

                            # 如果第3秒还在，再按一次ESC
                            if close_attempt == 2:
                                self.logger.info(f"[详情] 再次按ESC键强制关闭")
                                await main_page.page.keyboard.press('Escape')
                    except Exception as e:
                        self.logger.debug(f"[详情] 验证iframe关闭时出错: {e}")
                        break

                if not iframe_closed:
                    self.logger.error(f"[详情] 等待5秒后iframe仍未关闭，可能影响下一条详情提取")

                # 额外等待1秒确保DOM稳定
                await asyncio.sleep(1)

            except Exception as e:
                self.logger.warning(f"[详情] 关闭操作失败，但数据已提取: {e}")
                # 尝试强制ESC作为后备
                try:
                    await main_page.page.keyboard.press('Escape')
                    await asyncio.sleep(2)
                except:
                    pass

            return detail_data, "success", None

        except PlaywrightTimeoutError as e:
            error_msg = f"超时: {str(e)}"
            self.logger.error(f"[详情] 第 {row_index + 1} 条提取失败: {error_msg}")
            return {}, "failed", error_msg
        except Exception as e:
            error_msg = str(e)
            self.logger.error(f"[详情] 第 {row_index + 1} 条提取失败: {error_msg}")
            return {}, "failed", error_msg

    async def _extract_detail_with_retry(
        self,
        main_page: Union[Page, Frame],
        detail_button: Locator,
        detail_config: Dict,
        row_index: int
    ) -> Tuple[Dict, str, Optional[str]]:
        """
        带重试机制的详情提取

        Args:
            main_page: 列表页面/Frame
            detail_button: 详情按钮定位器
            detail_config: 详情配置
            row_index: 当前行索引

        Returns:
            (detail_data, status, error_msg)
        """
        max_attempts = detail_config.get('retry', {}).get('max_attempts', 3)
        delay = detail_config.get('retry', {}).get('delay_seconds', 2)

        for attempt in range(max_attempts):
            try:
                self.logger.info(
                    f"[详情] 第 {row_index + 1} 条详情提取尝试 {attempt + 1}/{max_attempts}"
                )

                detail_data, status, error = await self._extract_detail_data(
                    main_page, detail_button, detail_config, row_index
                )

                if status == "success":
                    if attempt > 0:
                        self.logger.info(
                            f"[详情] 第 {row_index + 1} 条在第 {attempt + 1} 次尝试成功"
                        )
                    return detail_data, status, error
                else:
                    # 如果返回failed状态，也算一次失败
                    raise Exception(error if error else "提取失败")

            except Exception as e:
                self.logger.warning(
                    f"[详情] 第 {row_index + 1} 条提取失败（尝试 {attempt + 1}/{max_attempts}）: {e}"
                )

                if attempt < max_attempts - 1:
                    self.logger.info(f"[详情] 等待 {delay} 秒后重试...")
                    await asyncio.sleep(delay)
                    continue
                else:
                    error_msg = f"{str(e)}，已重试{max_attempts}次"
                    self.logger.error(f"[详情] 第 {row_index + 1} 条提取最终失败: {error_msg}")
                    return {}, "failed", error_msg

        return {}, "failed", "未知错误"

    async def _extract_list_with_details(
        self,
        page: Union[Page, Frame],
        fields_mapping: Dict,
        detail_config: Dict,
        job_id: int
    ) -> List[Dict]:
        """
        提取列表数据并逐条采集详情（单页）

        Args:
            page: 页面或Frame对象
            fields_mapping: 列表字段映射配置
            detail_config: 详情配置
            job_id: 任务ID（用于进度推送）

        Returns:
            [
                {
                    "list_data": {...},
                    "detail_data": {...},
                    "detail_status": "success/failed/skipped",
                    "detail_error": "..." (可选)
                }
            ]
        """
        # 1. 先提取当前页所有列表数据
        self.logger.info("[详情] 开始提取列表数据")
        list_data = await self._extract_page_data(page, fields_mapping)
        total_items = len(list_data)

        self.logger.info(f"[详情] 列表数据提取完成，共 {total_items} 条")

        if total_items == 0:
            self.logger.warning("[详情] 列表数据为空，跳过详情提取")
            return []

        # 2. 获取所有列表行的定位器
        list_selector = fields_mapping.get('list_selector')
        if not list_selector:
            self.logger.error("[详情] 缺少 list_selector 配置")
            return [{"list_data": item, "detail_data": {}, "detail_status": "skipped"}
                    for item in list_data]

        rows_locator = page.locator(list_selector)
        rows_count = await rows_locator.count()

        self.logger.info(f"[详情] 找到 {rows_count} 个列表行")

        # 3. 遍历每一行，提取详情
        result = []
        detail_button_selector = detail_config.get('detail_button_selector')

        for i in range(total_items):
            self.logger.info(f"[详情] 处理第 {i + 1}/{total_items} 条数据")

            # 重新定位该行（避免DOM变化导致引用失效）
            row = rows_locator.nth(i)

            # 在该行内定位详情按钮
            detail_button = row.locator(detail_button_selector)
            button_count = await detail_button.count()

            if button_count == 0:
                # 详情按钮不存在
                self.logger.warning(f"[详情] 第 {i + 1} 条：详情按钮不存在，跳过")
                result.append({
                    "list_data": list_data[i],
                    "detail_data": {},
                    "detail_status": "skipped"
                })
                continue

            # 提取详情（带重试）
            detail_data, status, error = await self._extract_detail_with_retry(
                page, detail_button, detail_config, i
            )

            # 组装数据
            item = {
                "list_data": list_data[i],
                "detail_data": detail_data,
                "detail_status": status
            }

            if error:
                item["detail_error"] = error

            result.append(item)

            # 推送进度
            if self.ws_manager:
                await self._broadcast_log(
                    "info",
                    f"[详情] 第 {i + 1}/{total_items} 条详情提取{status}"
                )

        # 统计
        success_count = sum(1 for item in result if item["detail_status"] == "success")
        failed_count = sum(1 for item in result if item["detail_status"] == "failed")
        skipped_count = sum(1 for item in result if item["detail_status"] == "skipped")

        self.logger.info(
            f"[详情] 当前页详情采集完成：总数 {total_items}, "
            f"成功 {success_count}, 失败 {failed_count}, 跳过 {skipped_count}"
        )

        return result

    async def _extract_list_with_details_paginated(
        self,
        page: Union[Page, Frame],
        config: CrawlerConfig,
        job_id: int
    ) -> Tuple[List[Dict], int, Dict]:
        """
        分页提取列表+详情数据

        Args:
            page: 页面或Frame对象
            config: 爬虫配置对象
            job_id: 任务ID

        Returns:
            (all_items, page_count, summary)
            - all_items: 所有页的数据列表
            - page_count: 实际爬取的页数
            - summary: 统计信息字典
        """
        all_items = []
        current_page = 1
        detail_success = 0
        detail_failed = 0
        detail_skipped = 0

        fields_mapping = config.fields_mapping
        detail_config = fields_mapping.get('detail_config', {})
        timeouts = self._load_timeouts(config)

        while current_page <= config.max_pages:
            self.logger.info(f"[详情] 开始提取第 {current_page} 页（最大 {config.max_pages} 页）")

            # 1. 提取当前页列表+详情
            page_items = await self._extract_list_with_details(
                page, fields_mapping, detail_config, job_id
            )

            all_items.extend(page_items)

            # 2. 统计
            for item in page_items:
                if item["detail_status"] == "success":
                    detail_success += 1
                elif item["detail_status"] == "failed":
                    detail_failed += 1
                elif item["detail_status"] == "skipped":
                    detail_skipped += 1

            self.logger.info(
                f"[详情] 第 {current_page} 页完成，本页 {len(page_items)} 条"
            )

            # 3. 推送分页进度
            if self.ws_manager:
                await self._broadcast_progress(
                    job_id=job_id,
                    data={
                        "current_page": current_page,
                        "total_pages": config.max_pages,
                        "status": "processing",
                        "detail_progress": {
                            "total": len(all_items),
                            "success": detail_success,
                            "failed": detail_failed,
                            "skipped": detail_skipped
                        }
                    }
                )

            # 4. 检查是否需要翻页
            if current_page >= config.max_pages:
                self.logger.info(f"[详情] 已达到最大页数 {config.max_pages}")
                break

            # 5. 检查下一页按钮是否存在
            if not config.pagination_selector:
                self.logger.info("[详情] 未配置分页选择器，停止翻页")
                break

            next_button = page.locator(config.pagination_selector)
            count = await next_button.count()

            if count == 0:
                self.logger.info("[详情] 下一页按钮不存在，停止翻页")
                break

            # 6. 检查按钮是否可用
            is_disabled = await next_button.is_disabled()
            if is_disabled:
                self.logger.info("[详情] 下一页按钮已禁用，停止翻页")
                break

            # 7. 点击下一页
            self.logger.info("[详情] 点击下一页按钮")
            await next_button.click(timeout=timeouts['click'])

            if self.ws_manager:
                await self._broadcast_log("info", f"[详情] 翻页到第 {current_page + 1} 页")

            # 8. 等待新页面加载
            await page.wait_for_selector(
                config.wait_selector,
                state="visible",
                timeout=timeouts['wait_selector']
            )
            await asyncio.sleep(2)  # 额外等待确保数据加载完成

            current_page += 1

        # 9. 生成摘要
        summary = {
            "total_items": len(all_items),
            "detail_success": detail_success,
            "detail_failed": detail_failed,
            "detail_skipped": detail_skipped,
            "pages_crawled": current_page
        }

        self.logger.info(
            f"[详情] 全部采集完成：共 {current_page} 页，{len(all_items)} 条数据，"
            f"成功 {detail_success}，失败 {detail_failed}，跳过 {detail_skipped}"
        )

        return all_items, current_page, summary

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

            # 加载动态配置
            timeouts = self._load_timeouts(config)
            extraction_cfg = self._load_extraction_config(config)

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
            await page.goto(config.target_url, timeout=timeouts['page_load'], wait_until='networkidle')
            self.logger.info(f"访问目标 URL: {config.target_url}")

            # 等待页面完全加载
            await asyncio.sleep(3)
            await self._broadcast_log("info", "页面加载完成")

            # 5. 确定操作目标 frame（表单填充和提交）
            operation_frame = page

            # 检查是否配置了多层iframe
            iframe_levels = 0
            if isinstance(config.fields_mapping, dict):
                iframe_levels = config.fields_mapping.get('iframe_levels', 0)

            # 首先尝试在主页面查找输入框
            first_input_selector = None
            if config.input_configs:
                inputs = config.input_configs.get('inputs', config.input_configs) if isinstance(config.input_configs, dict) else config.input_configs
                if inputs and len(inputs) > 0:
                    first_input_selector = inputs[0].get('selector')

            # 智能检测：输入框在主页面还是iframe中
            input_in_main_page = False
            if first_input_selector:
                try:
                    # 尝试在主页面查找
                    main_input = await page.query_selector(first_input_selector)
                    if main_input and await main_input.is_visible():
                        input_in_main_page = True
                        self.logger.info(f"输入框在主页面")
                except:
                    pass

            if not input_in_main_page and iframe_levels >= 2:
                # 输入框在iframe中，需要先进入iframe
                self.logger.info(f"输入框可能在iframe中，先进入iframe")
                await self._broadcast_log("info", f"处理{iframe_levels}层嵌套iframe...")

                try:
                    # 获取第1层iframe选择器
                    iframe1_selector = config.fields_mapping.get('iframe1_selector')
                    if iframe1_selector:
                        self.logger.info(f"等待第1层iframe: {iframe1_selector}")
                        iframe1_element = await page.wait_for_selector(iframe1_selector, timeout=timeouts['wait_selector'])
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
                            iframe2_element = await iframe1.wait_for_selector(iframe2_selector, timeout=timeouts['wait_selector'])
                            iframe2 = await iframe2_element.content_frame()

                            if not iframe2:
                                raise Exception("无法获取第2层iframe")

                            self.logger.info("成功进入第2层iframe")
                            await self._broadcast_log("info", "进入第2层iframe")

                            # 等待第2层iframe加载
                            await iframe2.wait_for_load_state("networkidle", timeout=10000)
                            await asyncio.sleep(2)

                            operation_frame = iframe2
                            # 在 Frame 上注册控制台监听
                            operation_frame.on("console", handle_console)
                            await self._broadcast_log("success", "成功定位到目标iframe")
                        else:
                            operation_frame = iframe1
                    else:
                        self.logger.warning("未配置iframe1_selector")

                except Exception as e:
                    self.logger.error(f"多层iframe处理失败: {e}")
                    await self._broadcast_log("error", f"iframe处理失败: {e}")
                    raise

            # 6. 填充表单（在 operation_frame 中）
            if config.input_configs:
                inputs = config.input_configs.get('inputs', config.input_configs) if isinstance(config.input_configs, dict) else config.input_configs
                await self._fill_form(operation_frame, inputs, job.query_params, timeouts)
                await self._broadcast_log("info", "表单填充完成")

            # 7. 点击提交按钮（在 operation_frame 中）
            self.logger.info(f"点击提交按钮: {config.submit_selector}")
            await operation_frame.click(config.submit_selector, timeout=timeouts['click'])
            await self._broadcast_log("info", "点击提交按钮")

            # 8. 等待结果加载
            self.logger.info(f"等待结果加载: {config.wait_selector}")
            await asyncio.sleep(3)

            # 9. 确定数据提取目标 frame（如果已经进入iframe操作，则使用相同frame）
            target_frame = operation_frame

            # 如果操作在主页面进行（input_in_main_page=True），但数据在iframe中
            # 需要进入iframe进行数据提取
            if input_in_main_page and iframe_levels >= 2:
                self.logger.info("操作在主页面，但数据在iframe中，现在进入iframe提取数据")
                await self._broadcast_log("info", f"处理{iframe_levels}层嵌套iframe...")

                try:
                    # 获取第1层iframe选择器
                    iframe1_selector = config.fields_mapping.get('iframe1_selector')
                    if iframe1_selector:
                        self.logger.info(f"等待第1层iframe: {iframe1_selector}")
                        iframe1_element = await page.wait_for_selector(iframe1_selector, timeout=timeouts['wait_selector'])
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
                            iframe2_element = await iframe1.wait_for_selector(iframe2_selector, timeout=timeouts['wait_selector'])
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
                        self.logger.warning("未配置iframe1_selector")

                except Exception as e:
                    self.logger.error(f"多层iframe处理失败: {e}")
                    await self._broadcast_log("error", f"iframe处理失败: {e}")
                    raise

            # 如果没有配置多层iframe，使用原有的自动检测逻辑
            if target_frame == page and not input_in_main_page:
                frames = page.frames
                self.logger.info(f"检测到 {len(frames)} 个 frame")
                await self._broadcast_log("info", f"检测到 {len(frames)} 个 frame")

                if len(frames) > 1:
                    # 尝试在每个 frame 中查找数据表格
                    table_selector = config.fields_mapping.get('list_selector', 'table') if isinstance(config.fields_mapping, dict) else 'table'
                    for idx, frame in enumerate(frames):
                        try:
                            self.logger.info(f"检查 Frame {idx}: {frame.url}")
                            # 检查是否有数据表格
                            tables = await frame.query_selector_all(table_selector)
                            self.logger.info(f"Frame {idx} 找到 {len(tables)} 个表格")

                            if len(tables) > 0:
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

            # 9. 等待结果数据在 target_frame 中加载
            self.logger.info(f"等待结果数据: {config.wait_selector}")

            # 先等待表格元素存在于DOM中（不要求visible，因为可能一开始是hidden）
            await target_frame.wait_for_selector(
                config.wait_selector,
                state="attached",
                timeout=timeouts['wait_selector']
            )
            self.logger.info(f"表格元素已存在于DOM")

            # 额外等待确保数据完全加载（特别是动态渲染的内容）
            await asyncio.sleep(5)

            # 10. 提取数据

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

                # 再等待出现真正的数据行（带有jqgrow class）
                # 如果20秒内没有出现数据行，说明查询无结果，继续执行（会提取到0条）
                try:
                    # 添加轮询调试，每2秒检查一次
                    max_wait = 20
                    interval = 2
                    for i in range(max_wait // interval):
                        rows_info = await target_frame.evaluate("""
                            () => {
                                const allRows = document.querySelectorAll('table tbody tr');
                                const dataRows = document.querySelectorAll('tbody tr.jqgrow');
                                const info = {
                                    total: allRows.length,
                                    dataRows: dataRows.length,
                                    classes: []
                                };
                                for (let j = 0; j < Math.min(5, allRows.length); j++) {
                                    info.classes.push(allRows[j].className);
                                }
                                return info;
                            }
                        """)
                        self.logger.info(f"等待数据行 [{i*interval}s]: 总行数={rows_info['total']}, 数据行={rows_info['dataRows']}, classes={rows_info['classes']}")

                        if rows_info['dataRows'] > 0:
                            self.logger.info("数据行已完全加载（检测到jqgrow行）")
                            break

                        await asyncio.sleep(interval)
                    else:
                        self.logger.warning(f"等待{max_wait}秒后仍未检测到数据行")
                except Exception as e:
                    self.logger.warning(f"等待数据行时出错: {e}")
                    # 继续执行，让后续提取逻辑处理0条数据的情况

                #关键：额外等待确保 DOM 完全稳定并且所有行都已渲染
                # jqGrid 可能在数据加载后还会重新渲染 DOM
                await asyncio.sleep(2)
                self.logger.info("额外等待 2 秒确保 DOM 稳定")

                # 调试：检查实际的行结构
                debug_info = await target_frame.evaluate("""
                    () => {
                        const rows = document.querySelectorAll('table tbody tr');
                        const info = {
                            total_rows: rows.length,
                            row_classes: []
                        };
                        for (let i = 0; i < Math.min(5, rows.length); i++) {
                            info.row_classes.push({
                                index: i,
                                className: rows[i].className,
                                id: rows[i].id,
                                cellCount: rows[i].cells.length
                            });
                        }
                        return info;
                    }
                """)
                self.logger.info(f"调试信息 - 总行数: {debug_info['total_rows']}, 前5行: {debug_info['row_classes']}")
            except Exception as e:
                self.logger.warning(f"等待数据行加载超时，继续执行: {e}")

            self.logger.info("结果页面加载完成")

            # 节点 5: 结果页面加载完成
            await self._broadcast_log("info", "结果页面加载完成")

            # 9. 数据提取（含翻页）
            self.logger.info(f"准备提取数据，target_frame 类型: {type(target_frame).__name__}")
            if hasattr(target_frame, 'url'):
                self.logger.info(f"target_frame URL: {target_frame.url}")

            # 检查是否启用详情采集
            detail_enabled = config.fields_mapping.get('detail_config', {}).get('enabled', False)

            extracted_data = []
            page_count = 1

            if detail_enabled:
                self.logger.info("使用详情采集模式")

                # 使用详情采集模式
                if config.pagination_selector and config.max_pages > 1:
                    self.logger.info("详情采集 + 分页模式")
                    all_items, page_count, summary = await self._extract_list_with_details_paginated(
                        target_frame,
                        config,
                        job_id
                    )
                    extracted_data = {
                        "items": all_items,
                        "summary": summary
                    }
                else:
                    self.logger.info("详情采集 + 单页模式")
                    detail_config = config.fields_mapping.get('detail_config', {})

                    # 等待数据稳定
                    extraction_cfg = self._load_extraction_config(config)
                    await asyncio.sleep(extraction_cfg["wait_times"]["before_extraction"] / 1000)

                    # 提取列表+详情
                    items = await self._extract_list_with_details(
                        target_frame,
                        config.fields_mapping,
                        detail_config,
                        job_id
                    )

                    # 生成摘要
                    detail_success = sum(1 for item in items if item["detail_status"] == "success")
                    detail_failed = sum(1 for item in items if item["detail_status"] == "failed")
                    detail_skipped = sum(1 for item in items if item["detail_status"] == "skipped")

                    extracted_data = {
                        "items": items,
                        "summary": {
                            "total_items": len(items),
                            "detail_success": detail_success,
                            "detail_failed": detail_failed,
                            "detail_skipped": detail_skipped,
                            "pages_crawled": 1
                        }
                    }
                    page_count = 1
            else:
                self.logger.info("使用标准列表采集模式")

                # 使用原有逻辑（不采集详情）
                if config.pagination_selector and config.max_pages > 1:
                    self.logger.info("使用分页提取")

                    # 翻页提取逻辑
                    current_page = 1
                    page_results = []

                    while current_page <= config.max_pages:
                        self.logger.info(f"提取第 {current_page} 页数据")

                        # 等待数据稳定
                        extraction_cfg = self._load_extraction_config(config)
                        await asyncio.sleep(extraction_cfg["wait_times"]["before_extraction"] / 1000)

                        # 提取数据（带重试）
                        page_data = await self._extract_with_retry(
                            target_frame,
                            config.fields_mapping,
                            extraction_cfg["retry"]
                        )

                        # 应用过滤器
                        filtered = self._apply_filters(page_data, extraction_cfg["filters"])
                        page_results.extend(filtered)

                        self.logger.info(f"第 {current_page} 页提取 {len(filtered)} 条数据")

                        # 广播进度
                        await self._broadcast_progress(
                            job_id=job_id,
                            data={
                                "current_page": current_page,
                                "total_pages": config.max_pages,
                                "status": "processing"
                            }
                        )

                        # 检查是否需要翻页
                        if current_page >= config.max_pages:
                            self.logger.info(f"已达到最大页数 {config.max_pages}")
                            break

                        # 检查下一页按钮是否存在
                        next_button = target_frame.locator(config.pagination_selector)
                        count = await next_button.count()

                        if count == 0:
                            self.logger.info("下一页按钮不存在，停止翻页")
                            break

                        # 检查按钮是否可用
                        is_disabled = await next_button.is_disabled()
                        if is_disabled:
                            self.logger.info("下一页按钮已禁用，停止翻页")
                            break

                        # 点击下一页
                        self.logger.info("点击下一页按钮")
                        await next_button.click(timeout=timeouts['click'])

                        if job_id:
                            await self._broadcast_log("info", f"点击下一页按钮（第 {current_page + 1} 页）")

                        # 等待新页面加载
                        await target_frame.wait_for_selector(
                            config.wait_selector,
                            state="visible",
                            timeout=timeouts['wait_selector']
                        )

                        # 页面切换后等待
                        await asyncio.sleep(extraction_cfg["wait_times"]["after_click"] / 1000)

                        # 页面之间的等待
                        await asyncio.sleep(extraction_cfg["wait_times"]["between_pages"] / 1000)

                        current_page += 1

                    extracted_data = {"items": page_results}
                    page_count = current_page

                else:
                    self.logger.info("使用单页提取")

                    # 如果配置了 list_selector，明确等待该选择器
                    if 'list_selector' in config.fields_mapping:
                        list_selector = config.fields_mapping['list_selector']
                        self.logger.info(f"等待列表选择器: {list_selector}")

                        # 尝试等待，超时时间增加到30秒
                        list_appeared = False
                        try:
                            await target_frame.wait_for_selector(list_selector, state="attached", timeout=30000)
                            self.logger.info(f"列表选择器已出现")
                            list_appeared = True
                        except Exception as e:
                            self.logger.warning(f"等待列表选择器超时（30秒）: {e}")

                        # 如果第一次超时，再等待10秒并重试
                        if not list_appeared:
                            self.logger.info("额外等待10秒后重试...")
                            await asyncio.sleep(10)
                            try:
                                count = await target_frame.locator(list_selector).count()
                                if count > 0:
                                    self.logger.info(f"重试成功，找到 {count} 个元素")
                                    list_appeared = True
                                else:
                                    self.logger.warning("重试后仍未找到元素")
                            except Exception as e2:
                                self.logger.error(f"重试检查失败: {e2}")

                    # 等待数据稳定
                    extraction_cfg = self._load_extraction_config(config)
                    await asyncio.sleep(extraction_cfg["wait_times"]["before_extraction"] / 1000)

                    # 提取数据（带重试）
                    page_data = await self._extract_with_retry(
                        target_frame,
                        config.fields_mapping,
                        extraction_cfg["retry"]
                    )

                    # 应用过滤器
                    filtered_data = self._apply_filters(page_data, extraction_cfg["filters"])
                    extracted_data = {"items": filtered_data}
                    page_count = 1

            self.logger.info(f"数据提取完成，共 {page_count} 页")

            # 打印前3条数据用于调试
            if isinstance(extracted_data.get("items"), list):
                for i, item in enumerate(extracted_data["items"][:3]):
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
            items_count = len(extracted_data.get("items", [])) if isinstance(extracted_data, dict) else len(extracted_data)
            await self._broadcast_progress(
                job_id=job_id,
                data={
                    "job_id": job_id,
                    "status": "completed",
                    "extracted_count": items_count,
                    "pages_crawled": page_count,
                    "execution_time": execution_time
                }
            )
            await self._broadcast_log(
                "success",
                f"任务 {job_id} 执行成功，提取 {items_count} 条数据，耗时 {execution_time:.2f} 秒"
            )

            return {
                "job_id": job_id,
                "status": "success",
                "extracted_count": items_count,
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
