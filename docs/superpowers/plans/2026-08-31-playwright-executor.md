# Playwright 执行器实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现 PlaywrightExecutor 类和 /task/run 接口，完成浏览器自动化采集的全链路功能。

**Architecture:** 单一 PlaywrightExecutor 类封装所有浏览器操作逻辑，支持占位符替换、动态数据提取、翻页循环。通过 FastAPI 接口手动触发任务执行，使用日志记录关键步骤，预留 WebSocket 接口。

**Tech Stack:** Playwright (异步), FastAPI, SQLAlchemy (异步), Python logging

---

## 文件结构概览

**新建文件：**
- `app/services/executor.py` - PlaywrightExecutor 执行器类

**修改文件：**
- `app/api/endpoints.py` - 新增 /task/run 接口

---

## Task 1: 创建 PlaywrightExecutor 基础结构

**Files:**
- Create: `app/services/executor.py`

- [ ] **Step 1: 创建执行器类基础结构**

```python
# app/services/executor.py
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
    
    async def execute_job(self, job_id: int, session: AsyncSession) -> Dict:
        """
        执行单个任务
        
        Args:
            job_id: 任务 ID
            session: 数据库 session
        
        Returns:
            执行结果字典
        """
        start_time = datetime.now()
        browser = None
        
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
            
            # 占位符，后续任务会实现
            # TODO: 启动浏览器、执行爬取、保存结果
            
            return {
                "job_id": job_id,
                "status": "success",
                "message": "基础结构已创建"
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
            if browser:
                await browser.close()
```

- [ ] **Step 2: 验证导入**

```bash
python -c "from app.services.executor import PlaywrightExecutor; print('Executor imported successfully')"
```

预期输出: Executor imported successfully

- [ ] **Step 3: 提交更改**

```bash
git add app/services/executor.py
git commit -m "feat: add PlaywrightExecutor base structure"
```

---

## Task 2: 实现浏览器启动逻辑

**Files:**
- Modify: `app/services/executor.py`

- [ ] **Step 1: 添加浏览器启动方法**

在 `PlaywrightExecutor` 类中添加：

```python
async def _launch_browser(self, config: CrawlerConfig) -> Browser:
    """
    启动浏览器（根据登录态配置）
    
    Args:
        config: 配置对象
    
    Returns:
        Browser 实例
    """
    async with async_playwright() as p:
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
        
        return browser, context
```

- [ ] **Step 2: 更新 execute_job 方法使用浏览器启动**

修改 `execute_job` 方法中的 TODO 部分：

```python
# 在 execute_job 方法中，替换 TODO 注释为：

# 3. 启动浏览器
browser, context = await self._launch_browser(config)
page = await context.new_page()

self.logger.info(f"浏览器启动成功（登录态: {config.auth_profile if config.need_login else '无'}）")

# 4. 访问目标 URL
await page.goto(config.target_url, timeout=TIMEOUTS['page_load'])
self.logger.info(f"访问目标 URL: {config.target_url}")

# TODO: 表单填充、数据提取等后续步骤
```

注意：需要将 `browser = None` 改为在 try 块内初始化

- [ ] **Step 3: 测试浏览器启动**

创建临时测试脚本 `test_browser.py`:

```python
import asyncio
from app.core.database import AsyncSessionLocal
from app.services.executor import PlaywrightExecutor
from app.models.config import CrawlerConfig

async def test():
    executor = PlaywrightExecutor()
    config = CrawlerConfig(
        config_name="测试",
        target_url="https://www.baidu.com",
        need_login=False,
        input_configs=[],
        submit_selector="",
        wait_selector="",
        fields_mapping={}
    )
    
    try:
        browser, context = await executor._launch_browser(config)
        print("✓ 浏览器启动成功")
        await browser.close()
    except Exception as e:
        print(f"✗ 失败: {e}")

asyncio.run(test())
```

运行: `python test_browser.py`
预期输出: ✓ 浏览器启动成功

删除测试文件: `rm test_browser.py`

- [ ] **Step 4: 提交更改**

```bash
git add app/services/executor.py
git commit -m "feat: implement browser launch logic with auth support"
```

---

## Task 3: 实现表单填充逻辑

**Files:**
- Modify: `app/services/executor.py`

- [ ] **Step 1: 添加表单填充方法**

在 `PlaywrightExecutor` 类中添加：

```python
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
```

- [ ] **Step 2: 更新 execute_job 集成表单填充**

在 `execute_job` 方法中，替换最后的 TODO 为：

```python
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
```

- [ ] **Step 3: 提交更改**

```bash
git add app/services/executor.py
git commit -m "feat: implement form filling with placeholder replacement"
```

---

## Task 4: 实现数据提取逻辑

**Files:**
- Modify: `app/services/executor.py`

- [ ] **Step 1: 添加数据提取方法**

在 `PlaywrightExecutor` 类中添加：

```python
async def _extract_page_data(
    self, 
    page: Page, 
    fields_mapping: Dict[str, str]
) -> List[Dict]:
    """
    提取当前页面的数据
    
    Args:
        page: 页面对象
        fields_mapping: 字段映射配置
            格式: {"field_name": "selector text"} 或 {"field_name": "selector @attr"}
    
    Returns:
        提取的数据列表
    """
    self.logger.debug(f"提取数据，字段映射: {fields_mapping}")
    
    extracted_item = {}
    
    for field_name, selector_rule in fields_mapping.items():
        parts = selector_rule.strip().split()
        
        if len(parts) == 0:
            self.logger.warning(f"字段 {field_name} 的选择器为空，跳过")
            continue
        
        selector = parts[0]
        
        try:
            # 检查是否提取属性
            if len(parts) > 1 and parts[1].startswith('@'):
                # 提取属性值
                attr_name = parts[1][1:]  # 去掉 @ 符号
                element = page.locator(selector).first
                value = await element.get_attribute(attr_name, timeout=TIMEOUTS['wait_selector'])
                self.logger.debug(f"提取属性 {field_name}: {selector} @{attr_name} = {value}")
            else:
                # 提取文本内容
                element = page.locator(selector).first
                value = await element.inner_text(timeout=TIMEOUTS['wait_selector'])
                value = value.strip() if value else ""
                self.logger.debug(f"提取文本 {field_name}: {selector} text = {value}")
            
            extracted_item[field_name] = value
            
        except PlaywrightTimeoutError:
            self.logger.warning(f"字段 {field_name} 的选择器 {selector} 超时，设置为 null")
            extracted_item[field_name] = None
        except Exception as e:
            self.logger.warning(f"提取字段 {field_name} 失败: {e}，设置为 null")
            extracted_item[field_name] = None
    
    return [extracted_item]  # 返回列表，便于与翻页逻辑统一
```

- [ ] **Step 2: 添加翻页提取方法**

在 `PlaywrightExecutor` 类中添加：

```python
async def _extract_with_pagination(
    self,
    page: Page,
    fields_mapping: Dict[str, str],
    pagination_selector: Optional[str],
    wait_selector: str,
    max_pages: int
) -> Tuple[List[Dict], int]:
    """
    翻页提取数据
    
    Args:
        page: 页面对象
        fields_mapping: 字段映射配置
        pagination_selector: 下一页按钮选择器
        wait_selector: 等待元素选择器
        max_pages: 最大翻页数
    
    Returns:
        (所有页数据列表, 实际抓取页数)
    """
    all_data = []
    current_page = 1
    
    while current_page <= max_pages:
        self.logger.info(f"提取第 {current_page} 页数据")
        
        # 提取当前页数据
        page_data = await self._extract_page_data(page, fields_mapping)
        all_data.extend(page_data)
        
        self.logger.info(f"第 {current_page} 页提取完成，共 {len(page_data)} 条数据")
        
        # 检查是否需要翻页
        if not pagination_selector or current_page >= max_pages:
            break
        
        # 检查下一页按钮是否存在
        try:
            next_button = page.locator(pagination_selector)
            count = await next_button.count()
            
            if count == 0:
                self.logger.info("未找到下一页按钮，结束翻页")
                break
            
            # 检查按钮是否可点击
            is_disabled = await next_button.is_disabled()
            if is_disabled:
                self.logger.info("下一页按钮已禁用，结束翻页")
                break
            
            # 点击下一页
            self.logger.info(f"点击下一页: {pagination_selector}")
            await next_button.click(timeout=TIMEOUTS['click'])
            
            # 等待新页面加载
            await page.wait_for_selector(
                wait_selector,
                state="visible",
                timeout=TIMEOUTS['wait_selector']
            )
            await asyncio.sleep(1)  # 额外等待确保数据加载
            
            current_page += 1
            
        except PlaywrightTimeoutError:
            self.logger.warning("下一页加载超时，结束翻页")
            break
        except Exception as e:
            self.logger.warning(f"翻页失败: {e}，结束翻页")
            break
    
    self.logger.info(f"数据提取完成，共 {current_page} 页 {len(all_data)} 条数据")
    return all_data, current_page
```

- [ ] **Step 3: 提交更改**

```bash
git add app/services/executor.py
git commit -m "feat: implement data extraction with pagination support"
```

---

## Task 5: 实现结果保存逻辑

**Files:**
- Modify: `app/services/executor.py`

- [ ] **Step 1: 添加结果保存方法**

在 `PlaywrightExecutor` 类中添加：

```python
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
        page_count: 抓取页数
    """
    self.logger.info(f"保存结果到数据库，任务 ID: {job_id}")
    
    result = CrawlerResult(
        job_id=job_id,
        config_id=config_id,
        query_params=query_params,
        extracted_data=extracted_data,
        page_count=page_count
    )
    
    session.add(result)
    await session.commit()
    await session.refresh(result)
    
    self.logger.info(f"结果保存成功，结果 ID: {result.id}")
    return result.id
```

- [ ] **Step 2: 完整集成 execute_job 方法**

替换 `execute_job` 方法中最后的 TODO 为完整实现：

```python
# 8. 提取数据（含翻页）
extracted_data, page_count = await self._extract_with_pagination(
    page,
    config.fields_mapping,
    config.pagination_selector,
    config.wait_selector,
    config.max_pages
)

# 9. 保存结果
result_id = await self._save_result(
    session,
    job_id,
    config.id,
    job.query_params,
    extracted_data,
    page_count
)

# 10. 更新任务状态为成功
job.status = JobStatus.SUCCESS
await session.commit()

execution_time = (datetime.now() - start_time).total_seconds()
self.logger.info(f"任务 {job_id} 执行成功，耗时 {execution_time:.2f} 秒")

return {
    "job_id": job_id,
    "status": "success",
    "result_id": result_id,
    "extracted_count": len(extracted_data),
    "pages_crawled": page_count,
    "execution_time": execution_time
}
```

同时需要修改 except 块中的返回值，保持一致：

```python
except Exception as e:
    self.logger.error(f"任务 {job_id} 执行失败: {e}", exc_info=True)
    
    # 查询 job 对象（如果还没查询）
    if 'job' not in locals():
        stmt = select(JobQueue).where(JobQueue.id == job_id)
        result = await session.execute(stmt)
        job = result.scalar_one_or_none()
    
    if job:
        job.status = JobStatus.FAILED
        job.error_msg = str(e)
        job.retry_count += 1
        await session.commit()
    
    execution_time = (datetime.now() - start_time).total_seconds()
    
    return {
        "job_id": job_id,
        "status": "failed",
        "error": str(e),
        "execution_time": execution_time
    }
```

- [ ] **Step 3: 修复浏览器上下文管理**

需要调整浏览器启动逻辑，确保 async_playwright 上下文正确管理。修改 `_launch_browser` 方法签名为返回 playwright 实例：

```python
# 将 _launch_browser 改为：
async def _launch_browser(self, config: CrawlerConfig, playwright_instance):
    """启动浏览器"""
    browser = await playwright_instance.chromium.launch(
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
    
    return browser, context

# 然后在 execute_job 中修改调用：
# 3. 启动 Playwright 和浏览器
async with async_playwright() as p:
    browser, context = await self._launch_browser(config, p)
    page = await context.new_page()
    
    # ... 后续逻辑保持不变
    
    # 确保在 try 块结束前关闭浏览器
    await browser.close()
```

- [ ] **Step 4: 提交更改**

```bash
git add app/services/executor.py
git commit -m "feat: implement result saving and complete execute_job"
```

---

## Task 6: 添加 API 接口

**Files:**
- Modify: `app/api/endpoints.py`

- [ ] **Step 1: 添加 /task/run 接口**

在 `app/api/endpoints.py` 文件末尾添加新的路由：

```python
# 在文件末尾添加任务执行相关接口

from app.services.executor import PlaywrightExecutor


@router.post("/task/run", tags=["任务执行"])
async def run_tasks(
    config_id: int = Query(..., description="配置 ID"),
    limit: int = Query(1, description="执行任务数量", ge=1, le=10),
    db: AsyncSession = Depends(get_db)
):
    """
    手动触发执行指定配置的待处理任务
    
    用于测试和手动触发任务执行。
    
    Args:
        config_id: 配置 ID
        limit: 执行任务数量（1-10）
        db: 数据库 session
    
    Returns:
        执行结果摘要
    """
    # 1. 查询待处理任务
    stmt = select(JobQueue).where(
        JobQueue.config_id == config_id,
        JobQueue.status == JobStatus.PENDING
    ).limit(limit)
    
    result = await db.execute(stmt)
    jobs = result.scalars().all()
    
    if not jobs:
        raise HTTPException(
            status_code=404,
            detail=f"未找到配置 {config_id} 的待处理任务"
        )
    
    # 2. 创建执行器
    executor = PlaywrightExecutor()
    
    # 3. 串行执行任务
    results = []
    for job in jobs:
        try:
            result = await executor.execute_job(job.id, db)
            results.append(result)
        except Exception as e:
            import logging
            logging.error(f"任务 {job.id} 执行异常: {e}", exc_info=True)
            results.append({
                "job_id": job.id,
                "status": "error",
                "error": str(e)
            })
    
    # 4. 统计结果
    success_count = sum(1 for r in results if r.get("status") == "success")
    failed_count = len(results) - success_count
    
    return {
        "status": "completed",
        "config_id": config_id,
        "total_jobs": len(results),
        "success_count": success_count,
        "failed_count": failed_count,
        "results": results
    }
```

需要在文件顶部添加缺少的导入：

```python
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.models.job import JobQueue, JobStatus
```

- [ ] **Step 2: 验证接口可访问**

启动服务：
```bash
uvicorn app.main:app --reload
```

访问 API 文档：`http://localhost:8000/docs`

应该能看到新的 `/task/run` 接口

- [ ] **Step 3: 提交更改**

```bash
git add app/api/endpoints.py
git commit -m "feat: add /task/run API endpoint for manual task execution"
```

---

## Task 7: 端到端测试

**Files:**
- None (测试任务)

- [ ] **Step 1: 准备测试数据库**

确保 MySQL 已启动并且数据库已创建：

```bash
mysql -u root -p browser_automation -e "SELECT 1;"
```

预期输出: 返回 1

- [ ] **Step 2: 插入测试配置**

```sql
INSERT INTO crawler_configs (
    config_name,
    target_url,
    need_login,
    input_configs,
    submit_selector,
    wait_selector,
    fields_mapping,
    pagination_selector,
    max_pages,
    is_active
) VALUES (
    '百度搜索测试',
    'https://www.baidu.com',
    0,
    '[{"selector":"#kw","value":"{keyword}","type":"fill"}]',
    '#su',
    '#content_left',
    '{"title":".t text","link":".t @href"}',
    NULL,
    1,
    1
);
```

记录插入的配置 ID（假设为 1）

- [ ] **Step 3: 插入测试任务**

```sql
INSERT INTO job_queue (
    config_id,
    query_params,
    status,
    retry_count
) VALUES (
    1,
    '{"keyword":"Python"}',
    'pending',
    0
);
```

记录插入的任务 ID（假设为 1）

- [ ] **Step 4: 启动服务并查看日志**

```bash
uvicorn app.main:app --reload --log-level=info
```

- [ ] **Step 5: 调用接口执行任务**

在新终端执行：

```bash
curl -X POST "http://localhost:8000/task/run?config_id=1&limit=1"
```

或通过浏览器访问 `http://localhost:8000/docs` 使用 Swagger UI 执行

- [ ] **Step 6: 检查终端日志**

应该看到类似输出：
```
INFO: 开始执行任务 1，配置: 百度搜索测试
INFO: 使用匿名浏览器上下文
INFO: 浏览器启动成功（登录态: 无）
INFO: 访问目标 URL: https://www.baidu.com
INFO: 开始填充表单，参数: {'keyword': 'Python'}
INFO: 填充字段: #kw = Python (类型: fill)
INFO: 表单填充完成
INFO: 点击提交按钮: #su
INFO: 等待结果加载: #content_left
INFO: 结果页面加载完成
INFO: 提取第 1 页数据
INFO: 第 1 页提取完成，共 1 条数据
INFO: 数据提取完成，共 1 页 1 条数据
INFO: 保存结果到数据库，任务 ID: 1
INFO: 结果保存成功，结果 ID: 1
INFO: 任务 1 执行成功，耗时 X.XX 秒
```

- [ ] **Step 7: 验证数据库结果**

检查任务状态：
```sql
SELECT id, status, error_msg, retry_count
FROM job_queue
WHERE id = 1;
```

预期输出: status='success'

检查结果表：
```sql
SELECT id, job_id, config_id, page_count, JSON_LENGTH(extracted_data) as data_count
FROM crawler_results
WHERE job_id = 1;
```

预期输出: 应该有一条记录

查看提取的数据：
```sql
SELECT extracted_data
FROM crawler_results
WHERE job_id = 1;
```

应该看到 JSON 格式的数据数组

- [ ] **Step 8: 测试失败场景**

插入一个错误的配置（元素选择器错误）：

```sql
INSERT INTO crawler_configs (
    config_name,
    target_url,
    need_login,
    input_configs,
    submit_selector,
    wait_selector,
    fields_mapping,
    max_pages,
    is_active
) VALUES (
    '错误配置测试',
    'https://www.baidu.com',
    0,
    '[]',
    '#wrong-selector',
    '#content_left',
    '{}',
    1,
    1
);

INSERT INTO job_queue (config_id, query_params, status)
VALUES (2, '{}', 'pending');
```

执行任务：
```bash
curl -X POST "http://localhost:8000/task/run?config_id=2&limit=1"
```

检查任务状态应该为 failed，error_msg 应该包含错误信息

- [ ] **Step 9: 清理测试数据（可选）**

```sql
DELETE FROM crawler_results WHERE job_id IN (1, 2);
DELETE FROM job_queue WHERE config_id IN (1, 2);
DELETE FROM crawler_configs WHERE id IN (1, 2);
```

---

## Task 8: 文档更新

**Files:**
- Create: `docs/executor_usage.md`

- [ ] **Step 1: 创建使用文档**

```markdown
# Playwright 执行器使用指南

## 快速开始

### 1. 准备测试数据

插入配置：
\`\`\`sql
INSERT INTO crawler_configs (
    config_name, target_url, need_login,
    input_configs, submit_selector, wait_selector, fields_mapping,
    max_pages, is_active
) VALUES (
    '示例配置',
    'https://example.com',
    0,
    '[{"selector":"#search","value":"{keyword}","type":"fill"}]',
    '#submit',
    '.results',
    '{"title":".item-title text","link":".item-link @href"}',
    2,
    1
);
\`\`\`

插入任务：
\`\`\`sql
INSERT INTO job_queue (config_id, query_params, status)
VALUES (1, '{"keyword":"测试"}', 'pending');
\`\`\`

### 2. 执行任务

通过 API 接口：
\`\`\`bash
curl -X POST "http://localhost:8000/task/run?config_id=1&limit=1"
\`\`\`

或访问 Swagger UI：`http://localhost:8000/docs`

### 3. 查看结果

检查任务状态：
\`\`\`sql
SELECT * FROM job_queue WHERE id = 1;
\`\`\`

查看提取的数据：
\`\`\`sql
SELECT extracted_data FROM crawler_results WHERE job_id = 1;
\`\`\`

## 配置说明

### input_configs 格式

支持三种输入类型：

1. **填充文本** (fill)：
   \`\`\`json
   {"selector":"#search","value":"{keyword}","type":"fill"}
   \`\`\`

2. **下拉选择** (select)：
   \`\`\`json
   {"selector":"#category","value":"{category}","type":"select"}
   \`\`\`

3. **复选框** (check)：
   \`\`\`json
   {"selector":"#agree","value":"true","type":"check"}
   \`\`\`

### fields_mapping 格式

1. **提取文本**：
   \`\`\`json
   {"title": ".item-title text"}
   \`\`\`

2. **提取属性**：
   \`\`\`json
   {"link": ".item-link @href", "image": "img @src"}
   \`\`\`

### 占位符替换

在 `input_configs` 的 `value` 中使用 `{参数名}` 格式，会自动从 `query_params` 中替换：

- `query_params`: `{"keyword": "Python", "date": "2026-08-31"}`
- `value`: `"{keyword}"`
- 实际值: `"Python"`

## 翻页配置

设置 `pagination_selector` 和 `max_pages` 实现自动翻页：

\`\`\`json
{
  "pagination_selector": ".next-page",
  "max_pages": 5
}
\`\`\`

系统会自动：
1. 点击下一页按钮
2. 等待新页面加载
3. 提取数据
4. 重复直到无下一页或达到 max_pages

## 登录态配置

如果网站需要登录：

1. 设置 `need_login = 1`
2. 设置 `auth_profile`（如 "taobao"）
3. 通过 `/auth/start` 接口更新登录态
4. 登录态文件保存在 `auth_files/auth_{profile}.json`

## 错误处理

常见错误及解决方案：

1. **元素等待超时**
   - 检查选择器是否正确
   - 增加 wait_selector 等待时间（代码中配置）

2. **登录态文件不存在**
   - 先调用 `/auth/start` 更新登录态

3. **占位符替换失败**
   - 检查 query_params 是否包含所需参数

4. **数据提取为 null**
   - 检查 fields_mapping 选择器是否正确
   - 查看日志确认具体原因

## 日志查看

启动服务时查看详细日志：

\`\`\`bash
uvicorn app.main:app --reload --log-level=info
\`\`\`

## API 响应示例

成功：
\`\`\`json
{
  "status": "completed",
  "config_id": 1,
  "total_jobs": 1,
  "success_count": 1,
  "failed_count": 0,
  "results": [{
    "job_id": 1,
    "status": "success",
    "result_id": 1,
    "extracted_count": 10,
    "pages_crawled": 2,
    "execution_time": 15.5
  }]
}
\`\`\`

失败：
\`\`\`json
{
  "status": "completed",
  "config_id": 1,
  "total_jobs": 1,
  "success_count": 0,
  "failed_count": 1,
  "results": [{
    "job_id": 1,
    "status": "failed",
    "error": "元素等待超时: ...",
    "execution_time": 5.2
  }]
}
\`\`\`
\`\`\`

- [ ] **Step 2: 提交文档**

```bash
git add docs/executor_usage.md
git commit -m "docs: add Playwright executor usage guide"
```

---

## 完成标志

当所有任务的所有步骤都打勾完成后，实现计划执行完毕。此时应该：

1. ✅ PlaywrightExecutor 类已完整实现
2. ✅ /task/run 接口已添加
3. ✅ 支持占位符替换
4. ✅ 支持文本和属性提取
5. ✅ 支持翻页逻辑
6. ✅ 异常处理完整
7. ✅ 状态更新正确
8. ✅ 日志输出完整
9. ✅ 端到端测试通过
10. ✅ 使用文档已创建

可以通过以下命令验证最终状态：

```bash
# 检查文件存在性
ls app/services/executor.py app/api/endpoints.py docs/executor_usage.md

# 测试执行器导入
python -c "from app.services.executor import PlaywrightExecutor; print('OK')"

# 启动服务测试接口
uvicorn app.main:app --reload

# 检查提交历史
git log --oneline --graph -10
```

所有输出应与预期一致，表示实现计划成功完成。
