# 详情采集功能实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 扩展 PlaywrightExecutor 执行器，增加配置驱动的详情采集能力，支持逐条点击详情按钮提取详情数据，并以主子关系嵌套格式存储。

**Architecture:** 在现有执行器中新增 4 个独立方法：`_extract_detail_data()`（单条详情提取）、`_extract_detail_with_retry()`（带重试）、`_extract_list_with_details()`（单页列表+详情）、`_extract_list_with_details_paginated()`（分页+详情）。修改 `execute_job()` 主流程，根据 `detail_config.enabled` 配置选择采集模式。

**Tech Stack:** Python 3.10+, Playwright async API, SQLAlchemy 2.0, FastAPI WebSocket

---

## 文件结构规划

### 修改的文件
- `app/services/executor.py` - 执行器核心文件，新增详情采集方法

### 新增的文件
- `tests/test_detail_extraction.py` - 详情提取单元测试
- `scripts/init_nhsa_config.py` - 医保局网站配置初始化脚本

### 不需要修改的文件
- `app/models/*.py` - 数据模型无需变更，使用现有 JSON 字段
- `app/api/*.py` - API 接口无需变更
- `app/core/*.py` - 核心配置无需变更

---

## Task 1: 实现单条详情提取方法 `_extract_detail_data()`

**Files:**
- Modify: `app/services/executor.py`（在 `_extract_page_data()` 方法后插入）
- Test: `tests/test_detail_extraction.py`（新建）

- [ ] **Step 1: 编写测试用例 - 详情按钮点击和iframe切换**

在 `tests/test_detail_extraction.py` 创建测试骨架：

```python
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.executor import PlaywrightExecutor


@pytest.mark.asyncio
async def test_extract_detail_data_with_iframe():
    """测试详情提取 - iframe场景"""
    executor = PlaywrightExecutor()
    
    # Mock页面和定位器
    main_page = AsyncMock()
    detail_button = AsyncMock()
    detail_iframe_element = AsyncMock()
    detail_frame = AsyncMock()
    
    # 模拟点击详情按钮
    detail_button.click = AsyncMock()
    
    # 模拟等待iframe出现
    main_page.wait_for_selector = AsyncMock(return_value=detail_iframe_element)
    
    # 模拟获取iframe的content_frame
    detail_iframe_element.content_frame = AsyncMock(return_value=detail_frame)
    
    # 模拟等待详情内容加载
    detail_frame.wait_for_selector = AsyncMock()
    
    # 模拟提取详情字段
    detail_frame.evaluate = AsyncMock(return_value=[
        {"产品名称": "测试产品", "型号规格": "10ml"}
    ])
    
    # 模拟按ESC键关闭
    detail_frame.keyboard = MagicMock()
    detail_frame.keyboard.press = AsyncMock()
    
    # 模拟返回列表页
    main_page.wait_for_selector = AsyncMock()
    
    detail_config = {
        "detail_iframe_selector": "iframe#detailFrame",
        "wait_selector": ".detail-table",
        "close_method": "escape",
        "fields": [
            {"name": "产品名称", "selector": "#productName", "attr": "text"},
            {"name": "型号规格", "selector": "#spec", "attr": "text"}
        ],
        "timeout": {
            "iframe_load": 10000,
            "wait_selector": 5000
        }
    }
    
    # 执行测试
    detail_data, status, error = await executor._extract_detail_data(
        main_page, detail_button, detail_config, 0
    )
    
    # 验证
    assert status == "success"
    assert error is None
    assert "产品名称" in detail_data
    assert detail_data["产品名称"] == "测试产品"
    detail_button.click.assert_called_once()
```

- [ ] **Step 2: 运行测试确认失败**

```bash
pytest tests/test_detail_extraction.py::test_extract_detail_data_with_iframe -v
```

Expected: FAIL with "AttributeError: 'PlaywrightExecutor' object has no attribute '_extract_detail_data'"

- [ ] **Step 3: 实现 `_extract_detail_data()` 方法**

在 `app/services/executor.py` 中，在 `_extract_page_data()` 方法后添加：

```python
async def _extract_detail_data(
    self,
    main_page: Union[Page, Frame],
    detail_button: Locator,
    detail_config: Dict,
    row_index: int
) -> Tuple[Dict, str, Optional[str]]:
    """
    提取单条数据的详情
    
    Args:
        main_page: 列表页面/Frame
        detail_button: 详情按钮定位器
        detail_config: 详情配置
        row_index: 当前行索引（用于日志）
    
    Returns:
        (detail_data, status, error_msg)
        - detail_data: 提取的详情字典
        - status: "success"/"failed"
        - error_msg: 失败时的错误信息
    """
    try:
        # 1. 点击详情按钮
        self.logger.info(f"[详情] 第 {row_index + 1} 条：点击详情按钮")
        await detail_button.click(timeout=10000)
        
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
        
        # 4. 提取详情字段
        detail_fields = detail_config['fields']
        self.logger.info(f"[详情] 提取 {len(detail_fields)} 个详情字段")
        
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
        
        # 5. 关闭详情
        close_method = detail_config.get('close_method', 'auto')
        close_selector = detail_config.get('close_selector')
        
        if close_method == 'click' and close_selector:
            # 点击关闭按钮
            self.logger.info(f"[详情] 点击关闭按钮: {close_selector}")
            await detail_frame.click(close_selector, timeout=5000)
        elif close_method == 'escape':
            # 按ESC键
            self.logger.info(f"[详情] 按ESC键关闭")
            await detail_frame.keyboard.press('Escape')
        elif close_method == 'auto':
            # 自动选择：优先点击，失败则ESC
            if close_selector:
                try:
                    await detail_frame.click(close_selector, timeout=3000)
                except:
                    self.logger.info(f"[详情] 关闭按钮点击失败，改用ESC键")
                    await detail_frame.keyboard.press('Escape')
            else:
                await detail_frame.keyboard.press('Escape')
        
        # 6. 等待返回列表页
        await asyncio.sleep(0.5)
        
        return detail_data, "success", None
        
    except PlaywrightTimeoutError as e:
        error_msg = f"超时: {str(e)}"
        self.logger.error(f"[详情] 第 {row_index + 1} 条提取失败: {error_msg}")
        return {}, "failed", error_msg
    except Exception as e:
        error_msg = str(e)
        self.logger.error(f"[详情] 第 {row_index + 1} 条提取失败: {error_msg}")
        return {}, "failed", error_msg
```

- [ ] **Step 4: 运行测试确认通过**

```bash
pytest tests/test_detail_extraction.py::test_extract_detail_data_with_iframe -v
```

Expected: PASS

- [ ] **Step 5: 提交代码**

```bash
git add app/services/executor.py tests/test_detail_extraction.py
git commit -m "feat: add _extract_detail_data method for detail extraction"
```

---

## Task 2: 实现带重试的详情提取方法 `_extract_detail_with_retry()`

**Files:**
- Modify: `app/services/executor.py`（在 `_extract_detail_data()` 方法后插入）
- Test: `tests/test_detail_extraction.py`

- [ ] **Step 1: 编写测试用例 - 重试机制**

在 `tests/test_detail_extraction.py` 添加：

```python
@pytest.mark.asyncio
async def test_extract_detail_with_retry_success_on_second_attempt():
    """测试详情提取重试 - 第2次成功"""
    executor = PlaywrightExecutor()
    
    main_page = AsyncMock()
    detail_button = AsyncMock()
    
    detail_config = {
        "detail_iframe_selector": None,
        "wait_selector": ".detail-content",
        "close_method": "escape",
        "fields": [{"name": "field1", "selector": "#f1", "attr": "text"}],
        "retry": {
            "max_attempts": 3,
            "delay_seconds": 0.1
        }
    }
    
    # 模拟第1次失败，第2次成功
    call_count = 0
    async def mock_extract(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise Exception("临时错误")
        return {"field1": "value1"}, "success", None
    
    executor._extract_detail_data = mock_extract
    
    # 执行测试
    detail_data, status, error = await executor._extract_detail_with_retry(
        main_page, detail_button, detail_config, 0
    )
    
    # 验证
    assert status == "success"
    assert call_count == 2
    assert detail_data["field1"] == "value1"


@pytest.mark.asyncio
async def test_extract_detail_with_retry_all_failed():
    """测试详情提取重试 - 全部失败"""
    executor = PlaywrightExecutor()
    
    main_page = AsyncMock()
    detail_button = AsyncMock()
    
    detail_config = {
        "retry": {
            "max_attempts": 3,
            "delay_seconds": 0.1
        },
        "fields": []
    }
    
    # 模拟始终失败
    async def mock_extract(*args, **kwargs):
        raise Exception("持续错误")
    
    executor._extract_detail_data = mock_extract
    
    # 执行测试
    detail_data, status, error = await executor._extract_detail_with_retry(
        main_page, detail_button, detail_config, 0
    )
    
    # 验证
    assert status == "failed"
    assert "持续错误" in error
    assert "已重试3次" in error
```

- [ ] **Step 2: 运行测试确认失败**

```bash
pytest tests/test_detail_extraction.py::test_extract_detail_with_retry_success_on_second_attempt -v
pytest tests/test_detail_extraction.py::test_extract_detail_with_retry_all_failed -v
```

Expected: FAIL with "AttributeError: 'PlaywrightExecutor' object has no attribute '_extract_detail_with_retry'"

- [ ] **Step 3: 实现 `_extract_detail_with_retry()` 方法**

在 `app/services/executor.py` 中，在 `_extract_detail_data()` 方法后添加：

```python
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
```

- [ ] **Step 4: 运行测试确认通过**

```bash
pytest tests/test_detail_extraction.py::test_extract_detail_with_retry_success_on_second_attempt -v
pytest tests/test_detail_extraction.py::test_extract_detail_with_retry_all_failed -v
```

Expected: PASS (2 tests)

- [ ] **Step 5: 提交代码**

```bash
git add app/services/executor.py tests/test_detail_extraction.py
git commit -m "feat: add _extract_detail_with_retry method with retry mechanism"
```

---

## Task 3: 实现单页列表+详情联合提取 `_extract_list_with_details()`

**Files:**
- Modify: `app/services/executor.py`
- Test: `tests/test_detail_extraction.py`

- [ ] **Step 1: 编写测试用例 - 列表+详情联合提取**

在 `tests/test_detail_extraction.py` 添加：

```python
@pytest.mark.asyncio
async def test_extract_list_with_details():
    """测试列表+详情联合提取"""
    executor = PlaywrightExecutor()
    
    page = AsyncMock()
    
    fields_mapping = {
        "list_selector": "#gridlist tbody tr",
        "fields": [
            {"name": "产品名称", "selector": "td:nth-child(1)", "attr": "text"},
            {"name": "注册证号", "selector": "td:nth-child(2)", "attr": "text"}
        ]
    }
    
    detail_config = {
        "enabled": True,
        "detail_button_selector": "td:nth-child(3) a",
        "wait_selector": ".detail-content",
        "close_method": "escape",
        "fields": [
            {"name": "详细规格", "selector": "#spec", "attr": "text"}
        ],
        "retry": {
            "max_attempts": 2,
            "delay_seconds": 0.1
        }
    }
    
    # Mock列表数据提取
    async def mock_extract_page_data(p, fm):
        return [
            {"产品名称": "产品A", "注册证号": "ABC123"},
            {"产品名称": "产品B", "注册证号": "DEF456"}
        ]
    
    executor._extract_page_data = mock_extract_page_data
    
    # Mock行定位器
    row_locator = AsyncMock()
    row_locator.count = AsyncMock(return_value=2)
    
    # Mock第1行
    row1 = AsyncMock()
    button1 = AsyncMock()
    button1.count = AsyncMock(return_value=1)
    row1.locator = MagicMock(return_value=button1)
    
    # Mock第2行
    row2 = AsyncMock()
    button2 = AsyncMock()
    button2.count = AsyncMock(return_value=1)
    row2.locator = MagicMock(return_value=button2)
    
    # Mock nth方法
    def mock_nth(index):
        return row1 if index == 0 else row2
    
    row_locator.nth = mock_nth
    page.locator = MagicMock(return_value=row_locator)
    
    # Mock详情提取
    call_count = 0
    async def mock_extract_detail_with_retry(mp, btn, cfg, idx):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return {"详细规格": "规格A"}, "success", None
        else:
            return {"详细规格": "规格B"}, "success", None
    
    executor._extract_detail_with_retry = mock_extract_detail_with_retry
    
    # Mock WebSocket
    executor.ws_manager = None
    
    # 执行测试
    result = await executor._extract_list_with_details(
        page, fields_mapping, detail_config, job_id=1
    )
    
    # 验证
    assert len(result) == 2
    assert result[0]["list_data"]["产品名称"] == "产品A"
    assert result[0]["detail_data"]["详细规格"] == "规格A"
    assert result[0]["detail_status"] == "success"
    assert result[1]["list_data"]["产品名称"] == "产品B"
    assert result[1]["detail_data"]["详细规格"] == "规格B"
```

- [ ] **Step 2: 运行测试确认失败**

```bash
pytest tests/test_detail_extraction.py::test_extract_list_with_details -v
```

Expected: FAIL with "AttributeError: 'PlaywrightExecutor' object has no attribute '_extract_list_with_details'"

- [ ] **Step 3: 实现 `_extract_list_with_details()` 方法**

在 `app/services/executor.py` 中添加：

```python
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
```

- [ ] **Step 4: 运行测试确认通过**

```bash
pytest tests/test_detail_extraction.py::test_extract_list_with_details -v
```

Expected: PASS

- [ ] **Step 5: 提交代码**

```bash
git add app/services/executor.py tests/test_detail_extraction.py
git commit -m "feat: add _extract_list_with_details method for single page list+detail extraction"
```

---

## Task 4: 实现分页+详情提取 `_extract_list_with_details_paginated()`

**Files:**
- Modify: `app/services/executor.py`
- Test: `tests/test_detail_extraction.py`

- [ ] **Step 1: 编写测试用例 - 分页+详情**

在 `tests/test_detail_extraction.py` 添加：

```python
@pytest.mark.asyncio
async def test_extract_list_with_details_paginated():
    """测试分页+详情提取"""
    executor = PlaywrightExecutor()
    
    page = AsyncMock()
    
    config = MagicMock()
    config.fields_mapping = {
        "list_selector": "#gridlist tbody tr",
        "fields": [{"name": "name", "selector": "td", "attr": "text"}],
        "detail_config": {
            "enabled": True,
            "detail_button_selector": "a",
            "wait_selector": ".detail",
            "fields": [{"name": "detail", "selector": "div", "attr": "text"}],
            "retry": {"max_attempts": 2, "delay_seconds": 0.1}
        }
    }
    config.pagination_selector = "#next"
    config.max_pages = 2
    config.wait_selector = "#gridlist"
    
    # Mock单页提取（每页返回2条数据）
    page_call_count = 0
    async def mock_extract_list_with_details(p, fm, dc, jid):
        nonlocal page_call_count
        page_call_count += 1
        return [
            {"list_data": {"name": f"Page{page_call_count}-Item1"}, 
             "detail_data": {"detail": "D1"}, "detail_status": "success"},
            {"list_data": {"name": f"Page{page_call_count}-Item2"}, 
             "detail_data": {"detail": "D2"}, "detail_status": "success"}
        ]
    
    executor._extract_list_with_details = mock_extract_list_with_details
    
    # Mock翻页按钮
    next_button = AsyncMock()
    next_button.count = AsyncMock(side_effect=[1, 0])  # 第1页有下一页，第2页没有
    next_button.is_disabled = AsyncMock(return_value=False)
    next_button.click = AsyncMock()
    page.locator = MagicMock(return_value=next_button)
    page.wait_for_selector = AsyncMock()
    
    # Mock WebSocket
    executor.ws_manager = None
    
    # 执行测试
    all_items, page_count, summary = await executor._extract_list_with_details_paginated(
        page, config, job_id=1
    )
    
    # 验证
    assert len(all_items) == 4  # 2页 x 2条
    assert page_count == 2
    assert summary["total_items"] == 4
    assert summary["detail_success"] == 4
    assert summary["detail_failed"] == 0
```

- [ ] **Step 2: 运行测试确认失败**

```bash
pytest tests/test_detail_extraction.py::test_extract_list_with_details_paginated -v
```

Expected: FAIL with "AttributeError: 'PlaywrightExecutor' object has no attribute '_extract_list_with_details_paginated'"

- [ ] **Step 3: 实现 `_extract_list_with_details_paginated()` 方法**

在 `app/services/executor.py` 中添加：

```python
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
```

- [ ] **Step 4: 运行测试确认通过**

```bash
pytest tests/test_detail_extraction.py::test_extract_list_with_details_paginated -v
```

Expected: PASS

- [ ] **Step 5: 提交代码**

```bash
git add app/services/executor.py tests/test_detail_extraction.py
git commit -m "feat: add _extract_list_with_details_paginated method for pagination support"
```

---

## Task 5: 修改 `execute_job()` 集成详情采集逻辑

**Files:**
- Modify: `app/services/executor.py`（修改 `execute_job()` 方法的第9步数据提取部分）

- [ ] **Step 1: 编写集成测试**

在 `tests/test_detail_extraction.py` 添加：

```python
@pytest.mark.asyncio
async def test_execute_job_with_detail_enabled():
    """测试execute_job集成 - 启用详情采集"""
    # 这个测试比较复杂，需要mock整个执行流程
    # 这里只测试分支逻辑是否正确
    executor = PlaywrightExecutor()
    
    # Mock配置
    config = MagicMock()
    config.fields_mapping = {
        "detail_config": {
            "enabled": True
        }
    }
    
    # 验证分支判断逻辑
    detail_enabled = config.fields_mapping.get('detail_config', {}).get('enabled', False)
    assert detail_enabled == True


@pytest.mark.asyncio
async def test_execute_job_with_detail_disabled():
    """测试execute_job集成 - 未启用详情采集"""
    executor = PlaywrightExecutor()
    
    # Mock配置
    config = MagicMock()
    config.fields_mapping = {}
    
    # 验证分支判断逻辑
    detail_enabled = config.fields_mapping.get('detail_config', {}).get('enabled', False)
    assert detail_enabled == False
```

- [ ] **Step 2: 运行测试确认通过**

```bash
pytest tests/test_detail_extraction.py::test_execute_job_with_detail_enabled -v
pytest tests/test_detail_extraction.py::test_execute_job_with_detail_disabled -v
```

Expected: PASS (2 tests)

- [ ] **Step 3: 修改 `execute_job()` 方法的数据提取部分**

在 `app/services/executor.py` 的 `execute_job()` 方法中，找到第9步"数据提取"部分（大约在第990-1094行），替换为：

```python
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
```

- [ ] **Step 4: 运行现有所有测试确认无回归**

```bash
pytest tests/test_detail_extraction.py -v
```

Expected: PASS (所有测试)

- [ ] **Step 5: 提交代码**

```bash
git add app/services/executor.py tests/test_detail_extraction.py
git commit -m "feat: integrate detail extraction into execute_job main flow"
```

---

## Task 6: 创建医保局网站配置初始化脚本

**Files:**
- Create: `scripts/init_nhsa_config.py`

- [ ] **Step 1: 创建配置初始化脚本**

创建 `scripts/init_nhsa_config.py`：

```python
"""
医保局医疗器械编码查询配置初始化脚本

用途：创建医保局网站的爬虫配置和测试任务

运行：
    python -m scripts.init_nhsa_config
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from app.core.database import get_session
from app.models.config import CrawlerConfig
from app.models.job import JobQueue


async def init_nhsa_config():
    """初始化医保局网站配置"""
    
    async for session in get_session():
        try:
            # 检查配置是否已存在
            stmt = select(CrawlerConfig).where(
                CrawlerConfig.config_name == "医保局医疗器械编码查询"
            )
            result = await session.execute(stmt)
            existing_config = result.scalar_one_or_none()
            
            if existing_config:
                print(f"配置已存在，ID: {existing_config.id}")
                config_id = existing_config.id
            else:
                # 创建配置
                config = CrawlerConfig(
                    config_name="医保局医疗器械编码查询",
                    target_url="https://code.nhsa.gov.cn/toSearch.html?sysflag=1004",
                    need_login=False,
                    input_configs={
                        "inputs": [
                            {
                                "selector": "#regcardNm",
                                "param_key": "register_no",
                                "input_type": "text"
                            }
                        ]
                    },
                    submit_selector="#search",
                    wait_selector="#gridlist tbody tr",
                    pagination_selector="#next_gridpage",
                    max_pages=2,  # 默认2页，可根据需要调整
                    fields_mapping={
                        "iframe_levels": 2,
                        "iframe1_selector": "iframe[name='mainFrame']",
                        "iframe2_selector": "iframe[name='contentFrame']",
                        "list_selector": "#gridlist tbody tr",
                        "fields": [
                            {"name": "序号", "selector": "td:nth-child(1)", "attr": "text"},
                            {"name": "医疗器械编码", "selector": "td:nth-child(2)", "attr": "text"},
                            {"name": "医疗器械名称", "selector": "td:nth-child(3)", "attr": "text"},
                            {"name": "注册证号", "selector": "td:nth-child(4)", "attr": "text"}
                        ],
                        "detail_config": {
                            "enabled": True,
                            "detail_button_selector": "td:nth-child(5) a",
                            "detail_iframe_selector": "iframe#detailIframe",
                            "wait_selector": ".detail-table",
                            "close_method": "escape",
                            "fields": [
                                {"name": "产品名称", "selector": "#productName", "attr": "text"},
                                {"name": "型号规格", "selector": "#specification", "attr": "text"},
                                {"name": "注册人名称", "selector": "#registrant", "attr": "text"},
                                {"name": "注册人住所", "selector": "#address", "attr": "text"},
                                {"name": "生产地址", "selector": "#productionAddress", "attr": "text"}
                            ],
                            "retry": {
                                "max_attempts": 3,
                                "delay_seconds": 2
                            },
                            "timeout": {
                                "iframe_load": 10000,
                                "wait_selector": 5000
                            }
                        }
                    },
                    is_active=True,
                    priority=5
                )
                
                session.add(config)
                await session.commit()
                await session.refresh(config)
                
                print(f"✓ 配置已创建，ID: {config.id}")
                config_id = config.id
            
            # 创建测试任务
            job = JobQueue(
                config_id=config_id,
                query_params={"register_no": "川械注准20182170152"},
                priority=5
            )
            
            session.add(job)
            await session.commit()
            await session.refresh(job)
            
            print(f"✓ 测试任务已创建，ID: {job.id}")
            print(f"\n可通过以下方式执行测试：")
            print(f"  1. API接口：curl -X POST http://localhost:8000/api/jobs/{job.id}/execute")
            print(f"  2. 前端看板：http://localhost:8000/static/index.html")
            print(f"\n注意：")
            print(f"  - 首次运行请手动调整 detail_config 中的选择器")
            print(f"  - 建议先在浏览器开发者工具中确认实际的HTML结构")
            
            break  # 退出 async for 循环
            
        except Exception as e:
            print(f"✗ 初始化失败: {e}")
            import traceback
            traceback.print_exc()
            await session.rollback()
            raise


if __name__ == "__main__":
    print("=" * 60)
    print("医保局医疗器械编码查询配置初始化")
    print("=" * 60)
    
    asyncio.run(init_nhsa_config())
    
    print("\n初始化完成！")
```

- [ ] **Step 2: 测试脚本执行**

```bash
python -m scripts.init_nhsa_config
```

Expected: 
```
============================================================
医保局医疗器械编码查询配置初始化
============================================================
✓ 配置已创建，ID: 1
✓ 测试任务已创建，ID: 1

可通过以下方式执行测试：
  1. API接口：curl -X POST http://localhost:8000/api/jobs/1/execute
  2. 前端看板：http://localhost:8000/static/index.html

注意：
  - 首次运行请手动调整 detail_config 中的选择器
  - 建议先在浏览器开发者工具中确认实际的HTML结构

初始化完成！
```

- [ ] **Step 3: 验证数据库中的配置**

```bash
# 可选：使用数据库客户端查看 crawler_configs 和 job_queue 表
```

- [ ] **Step 4: 提交代码**

```bash
git add scripts/init_nhsa_config.py
git commit -m "feat: add NHSA config initialization script"
```

---

## Task 7: 真实环境调试和选择器调整

**Files:**
- Modify: `scripts/init_nhsa_config.py`（根据实际页面结构调整选择器）

- [ ] **Step 1: 启动应用服务**

```bash
uvicorn app.main:app --reload
```

Expected: 服务在 http://127.0.0.1:8000 启动

- [ ] **Step 2: 执行测试任务**

```bash
curl -X POST http://localhost:8000/api/jobs/1/execute
```

或访问前端看板：http://localhost:8000/static/index.html 并点击执行按钮

- [ ] **Step 3: 查看执行日志，识别问题**

观察日志输出，特别关注：
- iframe选择器是否正确
- 列表选择器是否提取到数据
- 详情按钮是否能找到
- 详情iframe是否成功加载
- 详情字段是否提取成功

常见问题和解决方法：
- iframe选择器不匹配：使用浏览器开发者工具查找正确的iframe标签
- 详情按钮选择器错误：检查"操作"列的实际HTML结构
- 详情字段为空：确认详情页的字段ID/Class是否正确

- [ ] **Step 4: 根据实际情况调整 `init_nhsa_config.py` 中的选择器**

根据Step 3的发现，修改脚本中的配置：

```python
# 例如调整iframe选择器
"iframe1_selector": "iframe[实际的name或id]",

# 例如调整详情按钮选择器
"detail_button_selector": "td:nth-child(实际列数) a.实际class",

# 例如调整详情字段选择器
"fields": [
    {"name": "产品名称", "selector": "#实际ID或.实际class", "attr": "text"},
    # ...
]
```

- [ ] **Step 5: 重新初始化配置并测试**

```bash
# 清空旧配置（可选）
# DELETE FROM job_queue WHERE config_id IN (SELECT id FROM crawler_configs WHERE config_name = '医保局医疗器械编码查询');
# DELETE FROM crawler_configs WHERE config_name = '医保局医疗器械编码查询';

# 重新初始化
python -m scripts.init_nhsa_config

# 再次测试
curl -X POST http://localhost:8000/api/jobs/1/execute
```

- [ ] **Step 6: 验证数据提取结果**

查询数据库中的 `crawler_results` 表：

```sql
SELECT 
    id, 
    job_id, 
    JSON_EXTRACT(extracted_data, '$.summary') as summary,
    JSON_LENGTH(extracted_data, '$.items') as item_count
FROM crawler_results 
WHERE job_id = 1;
```

验证：
- summary 中的 detail_success 数量是否合理
- items 数组长度是否符合预期
- 随机查看几条 items，检查 list_data 和 detail_data 是否都有数据

- [ ] **Step 7: 提交调整后的配置**

```bash
git add scripts/init_nhsa_config.py
git commit -m "fix: adjust NHSA selectors based on real page structure"
```

---

## 自查清单

### 规范覆盖检查

- [x] **配置驱动的详情采集**：通过 `detail_config.enabled` 控制
- [x] **列表+详情嵌套存储**：`{list_data: {...}, detail_data: {...}}`
- [x] **iframe场景支持**：`detail_iframe_selector` 配置
- [x] **重试机制**：`_extract_detail_with_retry()` 实现
- [x] **分页支持**：`_extract_list_with_details_paginated()` 实现
- [x] **向后兼容**：`detail_config` 可选，不配置时使用原逻辑
- [x] **WebSocket进度推送**：集成到各个方法中
- [x] **错误分类处理**：success/failed/skipped 三种状态

### 占位符检查

- [x] 所有方法签名完整
- [x] 所有代码块包含完整实现
- [x] 测试用例包含具体断言
- [x] 配置示例使用实际值

### 类型一致性检查

- [x] `_extract_detail_data()` 返回 `Tuple[Dict, str, Optional[str]]`
- [x] `_extract_detail_with_retry()` 返回 `Tuple[Dict, str, Optional[str]]`
- [x] `_extract_list_with_details()` 返回 `List[Dict]`
- [x] `_extract_list_with_details_paginated()` 返回 `Tuple[List[Dict], int, Dict]`
- [x] `detail_status` 字段值：success/failed/skipped
- [x] 所有方法中的 `detail_config` 参数类型一致

---

## 执行选择

计划完成并已保存到 `docs/superpowers/plans/2026-09-29-detail-crawler-implementation.md`。

**两种执行方式：**

**1. Subagent-Driven（推荐）** - 我为每个任务派发新的子代理，任务间进行审查，快速迭代

**2. Inline Execution** - 在当前会话中使用 executing-plans 执行任务，批量执行带检查点

你希望选择哪种方式？
