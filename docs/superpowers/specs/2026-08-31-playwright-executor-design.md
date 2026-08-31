# Playwright 执行器设计规格

**文档版本**: 1.0  
**创建日期**: 2026-08-31  
**对应需求**: PRD V2.0 第 3.3 节 - 自动化执行流程  
**实现目标**: 实现 PlaywrightExecutor 类，完成浏览器自动化采集的全链路

---

## 1. 概述

本规格定义了浏览器自动化执行器的实现方案，负责根据数据库配置和任务参数，完成"填表单 → 点击 → 翻页 → 提取数据 → 存结果"的完整流程。

### 1.1 核心目标

- 实现 `PlaywrightExecutor` 类，封装所有浏览器自动化逻辑
- 支持 `input_configs` 的遍历填充和占位符替换
- 支持 `fields_mapping` 动态数据提取（文本和属性）
- 支持翻页循环提取数据
- 完整的异常处理和状态管理
- 提供测试接口 `/task/run` 手动触发任务执行

### 1.2 验收标准

1. 在数据库 `job_queue` 插入测试数据
2. 调用 `/task/run` 接口
3. 终端日志显示完整的执行过程
4. `crawler_results` 表中新增了抓取的数据
5. 任务状态正确更新（success 或 failed）

---

## 2. 架构设计

### 2.1 整体架构

**方案选择**: 单一 PlaywrightExecutor 类（方案 A）

**理由**:
- PRD 明确是"配置驱动"，不需要针对每个网站写专门策略
- 当前需求是通用的"填表单 → 点击 → 翻页 → 提取"流程
- 单一类更容易实现和测试，符合 YAGNI 原则
- 如果后续需要扩展，可以再重构为分层设计

### 2.2 文件结构

```
app/services/
├── __init__.py
├── executor.py          # PlaywrightExecutor 类（新建）
└── auth_manager.py      # 现有文件

app/api/
├── __init__.py
└── endpoints.py         # 新增 /task/run 接口
```

### 2.3 核心职责

**PlaywrightExecutor 类：**
1. **接收任务** - 根据 job_id 从数据库加载任务和配置
2. **浏览器初始化** - 根据 need_login 加载登录态或匿名上下文
3. **表单填充** - 遍历 input_configs，支持占位符替换
4. **提交和等待** - 点击提交按钮，等待结果加载
5. **数据提取** - 根据 fields_mapping 提取数据（支持翻页）
6. **结果保存** - 存入 crawler_results 表，更新任务状态
7. **异常处理** - 捕获所有错误，标记 failed 状态

---

## 3. 数据流设计

### 3.1 执行流程

```
1. API 接收请求 (/task/run?config_id=1)
   ↓
2. 查询 job_queue 获取 pending 任务
   ↓
3. 创建 PlaywrightExecutor 实例
   ↓
4. 执行 execute_job(job_id)
   ├─ 更新状态为 processing
   ├─ 启动浏览器（根据 need_login 加载登录态）
   ├─ 访问 target_url
   ├─ 填充表单（遍历 input_configs，占位符替换）
   ├─ 点击提交按钮
   ├─ 等待结果出现（wait_selector）
   ├─ 翻页循环提取数据
   │   ├─ 当前页提取（fields_mapping）
   │   ├─ 检查是否有下一页
   │   ├─ 点击下一页（如果有）
   │   └─ 重复直到无下一页或达到 max_pages
   ├─ 保存到 crawler_results
   └─ 更新状态为 success
   ↓
5. 返回执行结果
```

### 3.2 占位符替换逻辑

**input_configs 示例：**
```json
[
  {
    "selector": "#search-input",
    "value": "{keyword}",
    "type": "fill"
  },
  {
    "selector": "#date-picker",
    "value": "{date}",
    "type": "fill"
  },
  {
    "selector": "#category",
    "value": "{category}",
    "type": "select"
  }
]
```

**query_params 示例：**
```json
{
  "keyword": "手机",
  "date": "2026-08-31",
  "category": "电子产品"
}
```

**替换逻辑：**
```python
for input_cfg in config['input_configs']:
    selector = input_cfg['selector']
    # 使用 format 进行占位符替换
    value = input_cfg['value'].format(**query_params)
    
    if input_cfg['type'] == 'fill':
        await page.fill(selector, value)
    elif input_cfg['type'] == 'select':
        await page.select_option(selector, value)
```

### 3.3 数据提取逻辑

**fields_mapping 格式：**
```json
{
  "title": ".product-title text",
  "price": ".price text",
  "link": ".detail-link @href",
  "image": "img.product @src"
}
```

**提取规则：**
- 如果值以 `text` 结尾（或不包含 `@`）→ 提取 innerText
- 如果值包含 `@属性名` → 提取指定属性值
- 示例：
  - `.product-title text` → 提取元素的文本内容
  - `.detail-link @href` → 提取元素的 href 属性
  - `img.product @src` → 提取 img 标签的 src 属性

**提取实现：**
```python
async def extract_page_data(page, fields_mapping):
    """提取当前页面的数据"""
    result = []
    
    # 获取所有数据行（假设数据是列表形式）
    # 这里需要根据实际情况调整选择器策略
    # 简单实现：遍历 fields_mapping，逐个提取
    
    extracted_item = {}
    for field_name, selector_rule in fields_mapping.items():
        parts = selector_rule.split()
        selector = parts[0]
        
        # 检查是否提取属性
        if len(parts) > 1 and parts[1].startswith('@'):
            attr_name = parts[1][1:]  # 去掉 @ 符号
            element = page.locator(selector).first
            value = await element.get_attribute(attr_name)
        else:
            # 提取文本
            element = page.locator(selector).first
            value = await element.inner_text()
        
        extracted_item[field_name] = value
    
    result.append(extracted_item)
    return result
```

**注意**: 实际实现时，需要根据页面结构智能判断是单条数据还是列表数据。

### 3.4 翻页逻辑

```python
all_data = []
current_page = 1

while current_page <= max_pages:
    # 1. 提取当前页数据
    page_data = await extract_page_data(page, fields_mapping)
    all_data.extend(page_data)
    
    # 2. 检查是否有下一页
    if not pagination_selector:
        break
    
    next_button = page.locator(pagination_selector)
    count = await next_button.count()
    
    if count == 0:
        # 下一页按钮不存在
        break
    
    is_disabled = await next_button.is_disabled()
    if is_disabled:
        # 下一页按钮已禁用
        break
    
    # 3. 点击下一页
    await next_button.click()
    
    # 4. 等待新页面加载
    await page.wait_for_selector(wait_selector, state="visible")
    await asyncio.sleep(1)  # 额外等待，确保数据加载
    
    current_page += 1

return all_data, current_page - 1  # 返回数据和实际页数
```

---

## 4. 错误处理和状态管理

### 4.1 异常处理策略

**捕获的异常类型：**

1. **TimeoutError** - 元素等待超时
   - 等待 wait_selector 超时
   - 点击下一页超时
   - 页面加载超时

2. **网络错误** - 页面加载失败
   - DNS 解析失败
   - 连接超时
   - 服务器返回错误

3. **元素不存在** - 选择器匹配失败
   - input_configs 中的元素不存在
   - submit_selector 不存在
   - fields_mapping 中的元素不存在

4. **登录态失效** - 检测到跳转到登录页
   - 访问目标页面后检测 URL 变化
   - 检测页面是否包含登录相关元素

5. **通用异常** - 其他未预期的错误

**处理方式：**

```python
try:
    # 1. 更新状态为 processing
    job.status = JobStatus.PROCESSING
    await session.commit()
    
    # 2. 执行爬虫逻辑
    browser = await launch_browser(config)
    page = await browser.new_page()
    
    # 访问、填表、提取...
    data = await crawl_data(page, config, query_params)
    
    # 3. 保存结果
    await save_result(job_id, data)
    
    # 4. 更新状态为 success
    job.status = JobStatus.SUCCESS
    await session.commit()
    
except TimeoutError as e:
    logger.error(f"任务 {job_id} 元素等待超时: {e}")
    job.status = JobStatus.FAILED
    job.error_msg = f"元素等待超时: {str(e)}"
    job.retry_count += 1
    await session.commit()
    
except Exception as e:
    logger.error(f"任务 {job_id} 执行失败: {e}", exc_info=True)
    job.status = JobStatus.FAILED
    job.error_msg = f"执行失败: {str(e)}"
    job.retry_count += 1
    await session.commit()
    
finally:
    # 5. 确保浏览器关闭
    if browser:
        await browser.close()
```

### 4.2 状态转换

```
pending → processing (execute_job 开始时)
processing → success (数据保存成功后)
processing → failed (发生异常时)
```

**重要原则：**
- 状态更新立即 commit，确保外部可以实时查看
- failed 状态记录详细错误信息到 error_msg
- retry_count 在失败时递增，但不在执行器内重试

### 4.3 日志级别

**INFO 级别：**
- 任务开始执行
- 浏览器启动成功
- 页面访问成功
- 表单填充完成
- 每页数据提取完成
- 任务执行成功

**WARNING 级别：**
- 登录态可能失效（URL 跳转检测）
- 元素定位缓慢
- 下一页按钮未找到（正常结束）

**ERROR 级别：**
- 任务执行失败
- 异常详情（带堆栈）
- 数据库操作失败

**DEBUG 级别（可选）：**
- 每个步骤的详细信息
- 提取的原始数据
- 浏览器操作细节

### 4.4 超时配置

```python
TIMEOUTS = {
    "page_load": 30000,      # 页面加载超时 30秒
    "wait_selector": 15000,  # 元素等待超时 15秒
    "navigation": 30000,     # 页面跳转超时 30秒
    "click": 10000,          # 点击操作超时 10秒
}
```

---

## 5. PlaywrightExecutor 类设计

### 5.1 类结构

```python
class PlaywrightExecutor:
    """Playwright 浏览器自动化执行器"""
    
    def __init__(self, ws_manager=None):
        """
        初始化执行器
        
        Args:
            ws_manager: WebSocket 管理器（可选，用于状态推送）
        """
        self.ws_manager = ws_manager
        self.logger = logging.getLogger(__name__)
    
    async def execute_job(self, job_id: int, session: AsyncSession) -> dict:
        """
        执行单个任务
        
        Args:
            job_id: 任务 ID
            session: 数据库 session
        
        Returns:
            执行结果字典
        """
        pass
    
    async def _launch_browser(self, config: dict) -> Browser:
        """启动浏览器（根据登录态配置）"""
        pass
    
    async def _fill_form(self, page: Page, input_configs: list, query_params: dict):
        """填充表单"""
        pass
    
    async def _extract_page_data(self, page: Page, fields_mapping: dict) -> list:
        """提取当前页面的数据"""
        pass
    
    async def _extract_with_pagination(
        self, 
        page: Page, 
        fields_mapping: dict,
        pagination_selector: str,
        wait_selector: str,
        max_pages: int
    ) -> tuple:
        """翻页提取数据"""
        pass
    
    async def _save_result(
        self, 
        session: AsyncSession,
        job_id: int,
        config_id: int,
        query_params: dict,
        extracted_data: list,
        page_count: int
    ):
        """保存结果到数据库"""
        pass
```

### 5.2 方法说明

#### execute_job()
**职责**: 任务执行的主入口

**流程**:
1. 查询任务和配置
2. 更新状态为 processing
3. 启动浏览器
4. 访问目标 URL
5. 填充表单
6. 点击提交
7. 等待结果加载
8. 提取数据（含翻页）
9. 保存结果
10. 更新状态为 success
11. 处理异常（failed）

#### _launch_browser()
**职责**: 根据配置启动浏览器

**逻辑**:
```python
if config['need_login']:
    auth_file = f"auth_files/auth_{config['auth_profile']}.json"
    if not os.path.exists(auth_file):
        raise FileNotFoundError(f"登录态文件不存在: {auth_file}")
    context = await browser.new_context(storage_state=auth_file)
else:
    context = await browser.new_context()
```

#### _fill_form()
**职责**: 遍历 input_configs 填充表单

**逻辑**:
```python
for input_cfg in input_configs:
    selector = input_cfg['selector']
    value = input_cfg['value'].format(**query_params)
    
    if input_cfg['type'] == 'fill':
        await page.fill(selector, value, timeout=TIMEOUTS['click'])
    elif input_cfg['type'] == 'select':
        await page.select_option(selector, value, timeout=TIMEOUTS['click'])
    elif input_cfg['type'] == 'check':
        await page.check(selector, timeout=TIMEOUTS['click'])
```

#### _extract_page_data()
**职责**: 提取当前页面的数据

**逻辑**:
- 解析 fields_mapping
- 区分文本提取和属性提取
- 返回提取的数据列表

#### _extract_with_pagination()
**职责**: 处理翻页逻辑并提取所有页的数据

**逻辑**:
- 循环提取当前页
- 检查下一页按钮
- 点击并等待加载
- 重复直到无下一页或达到 max_pages

#### _save_result()
**职责**: 保存提取的数据到 crawler_results 表

**逻辑**:
```python
result = CrawlerResult(
    job_id=job_id,
    config_id=config_id,
    query_params=query_params,
    extracted_data=extracted_data,
    page_count=page_count
)
session.add(result)
await session.commit()
```

---

## 6. API 接口设计

### 6.1 新增接口：`/task/run`

**端点**: `POST /task/run`

**路由**: `/task/run`

**参数**:
```python
config_id: int = Query(..., description="配置 ID")
limit: int = Query(1, description="执行任务数量", ge=1, le=10)
```

**功能**:
1. 根据 config_id 查询该配置下状态为 `pending` 的任务
2. 取前 limit 个任务
3. 串行执行每个任务（调用 PlaywrightExecutor）
4. 返回执行结果摘要

**实现逻辑**:
```python
@router.post("/task/run")
async def run_tasks(
    config_id: int = Query(..., description="配置 ID"),
    limit: int = Query(1, description="执行任务数量", ge=1, le=10),
    db: AsyncSession = Depends(get_db)
):
    """
    手动触发执行指定配置的待处理任务
    
    用于测试和手动触发任务执行。
    """
    # 1. 查询待处理任务
    stmt = select(JobQueue).where(
        JobQueue.config_id == config_id,
        JobQueue.status == JobStatus.PENDING
    ).limit(limit)
    
    result = await db.execute(stmt)
    jobs = result.scalars().all()
    
    if not jobs:
        raise HTTPException(404, "未找到待处理的任务")
    
    # 2. 创建执行器
    executor = PlaywrightExecutor()
    
    # 3. 串行执行任务
    results = []
    for job in jobs:
        try:
            result = await executor.execute_job(job.id, db)
            results.append(result)
        except Exception as e:
            logger.error(f"任务 {job.id} 执行异常: {e}")
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

**返回示例（成功）**:
```json
{
  "status": "completed",
  "config_id": 1,
  "total_jobs": 1,
  "success_count": 1,
  "failed_count": 0,
  "results": [
    {
      "job_id": 1,
      "status": "success",
      "extracted_count": 10,
      "pages_crawled": 2,
      "execution_time": 15.5
    }
  ]
}
```

**返回示例（失败）**:
```json
{
  "status": "completed",
  "config_id": 1,
  "total_jobs": 1,
  "success_count": 0,
  "failed_count": 1,
  "results": [
    {
      "job_id": 1,
      "status": "failed",
      "error": "元素等待超时: Timeout 15000ms exceeded"
    }
  ]
}
```

### 6.2 路由配置

在 `app/main.py` 中注册新的路由：

```python
from app.api import endpoints

# 现有路由
app.include_router(endpoints.router)

# 或者创建新的 task router
from app.api import task_endpoints
app.include_router(task_endpoints.router, prefix="/task", tags=["任务执行"])
```

---

## 7. 测试验收流程

### 7.1 准备测试数据

**Step 1: 插入测试配置**

```sql
INSERT INTO crawler_configs (
    config_name, 
    target_url, 
    need_login, 
    input_configs, 
    submit_selector, 
    wait_selector, 
    fields_mapping,
    max_pages
) VALUES (
    '百度搜索测试',
    'https://www.baidu.com',
    0,
    '[{"selector":"#kw","value":"{keyword}","type":"fill"}]',
    '#su',
    '#content_left',
    '{"title":".t text","link":".t @href"}',
    2
);
```

**Step 2: 插入测试任务**

```sql
INSERT INTO job_queue (
    config_id, 
    query_params, 
    status
) VALUES (
    1,  -- 上面插入的配置 ID
    '{"keyword":"Python"}',
    'pending'
);
```

### 7.2 执行测试

**方式 1: 通过 API**

```bash
curl -X POST "http://localhost:8000/task/run?config_id=1&limit=1"
```

**方式 2: 通过 FastAPI Docs**

访问 `http://localhost:8000/docs`，找到 `/task/run` 接口，输入参数执行。

### 7.3 验证结果

**1. 检查终端日志**

应该看到类似输出：
```
INFO: 开始执行任务 1
INFO: 浏览器启动成功（无登录态）
INFO: 访问目标 URL: https://www.baidu.com
INFO: 填充表单: #kw = Python
INFO: 点击提交按钮: #su
INFO: 等待结果加载: #content_left
INFO: 提取第 1 页数据，共 10 条
INFO: 点击下一页
INFO: 提取第 2 页数据，共 10 条
INFO: 数据提取完成，共 2 页 20 条
INFO: 保存结果到数据库
INFO: 任务 1 执行成功
```

**2. 检查数据库**

```sql
-- 检查任务状态
SELECT id, status, error_msg, retry_count 
FROM job_queue 
WHERE id = 1;

-- 应该显示 status='success'

-- 检查结果表
SELECT id, job_id, page_count, extracted_data 
FROM crawler_results 
WHERE job_id = 1;

-- 应该有一条记录，extracted_data 包含提取的数据
```

**3. 验证数据内容**

```sql
SELECT JSON_EXTRACT(extracted_data, '$') as data
FROM crawler_results
WHERE job_id = 1;

-- 应该是类似：
-- [{"title":"...", "link":"..."}, {"title":"...", "link":"..."}, ...]
```

### 7.4 测试异常情况

**测试 1: 元素不存在**

插入错误的配置（submit_selector 错误）：
```sql
INSERT INTO crawler_configs (..., submit_selector, ...) 
VALUES (..., '#wrong-selector', ...);
```

执行后应该：
- 任务状态为 failed
- error_msg 包含 "元素等待超时" 或 "元素不存在"
- retry_count 递增

**测试 2: 登录态缺失**

配置 need_login=1 但不提供登录态文件：
```sql
UPDATE crawler_configs 
SET need_login = 1, auth_profile = 'test' 
WHERE id = 1;
```

执行后应该：
- 任务状态为 failed
- error_msg 包含 "登录态文件不存在"

---

## 8. 实现注意事项

### 8.1 性能考虑

1. **浏览器复用** - 当前设计是每个任务启动新浏览器，后续可优化为浏览器池
2. **并发控制** - 当前是串行执行，避免资源竞争
3. **内存管理** - 确保浏览器正确关闭，避免内存泄漏
4. **数据库连接** - 使用 session 的 commit 确保及时释放

### 8.2 安全考虑

1. **SQL 注入** - 使用 SQLAlchemy 参数化查询
2. **XSS 防护** - 提取的数据存储为 JSON，不直接渲染
3. **路径遍历** - 登录态文件路径需要验证
4. **资源限制** - limit 参数限制最大值（如 10）

### 8.3 可维护性

1. **日志完整** - 每个关键步骤都有日志
2. **错误信息详细** - error_msg 记录足够的调试信息
3. **代码注释** - 复杂逻辑添加注释
4. **单元测试** - 关键方法可以编写单元测试（可选）

### 8.4 扩展性预留

1. **WebSocket 接口** - ws_manager 参数预留
2. **自定义提取策略** - _extract_page_data 可以后续增强
3. **多浏览器支持** - 当前只用 chromium，可扩展 firefox、webkit
4. **代理支持** - 可在 browser.new_context 中添加 proxy 参数

---

## 9. 依赖项

### 9.1 Python 包

```txt
playwright>=1.47.0
```

### 9.2 导入清单

```python
# 标准库
import asyncio
import logging
import os
from typing import Optional
from datetime import datetime

# Playwright
from playwright.async_api import async_playwright, Browser, Page, TimeoutError

# FastAPI
from fastapi import APIRouter, Depends, Query, HTTPException

# SQLAlchemy
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

# 项目模块
from app.core.database import get_db
from app.models.job import JobQueue, JobStatus
from app.models.config import CrawlerConfig
from app.models.result import CrawlerResult
```

---

## 10. 后续优化建议

### 10.1 短期优化（下个版本）

1. **智能列表提取** - 当前提取逻辑较简单，可以增强为自动识别列表结构
2. **WebSocket 集成** - 实现实时状态推送到前端看板
3. **重试机制** - 实现定时任务自动重试 failed 任务
4. **性能监控** - 记录每个任务的执行时间、页面加载时间等

### 10.2 中期优化

1. **浏览器池** - 复用浏览器实例，减少启动开销
2. **并发执行** - 支持多任务并发（需要资源管理）
3. **截图功能** - 失败时自动截图保存，便于调试
4. **数据验证** - 对提取的数据进行格式验证

### 10.3 长期优化

1. **分布式执行** - 支持多机部署，任务分发
2. **智能反爬** - 检测反爬机制，自动调整策略
3. **机器学习** - 智能识别页面结构，减少配置工作
4. **插件系统** - 支持自定义提取插件

---

## 11. 检查清单

实现前检查：
- [ ] 已阅读 PRD 第 3.3 节
- [ ] 已阅读 TDD 第 4.1 节
- [ ] 已了解现有的 ORM 模型结构
- [ ] 已了解 auth_manager 的登录态管理逻辑

实现后检查：
- [ ] PlaywrightExecutor 类已实现
- [ ] /task/run 接口已添加
- [ ] 支持占位符替换
- [ ] 支持文本和属性提取
- [ ] 支持翻页逻辑
- [ ] 异常处理完整
- [ ] 状态更新正确
- [ ] 日志输出完整
- [ ] 测试验收通过

---

## 12. 参考资料

- [PRD V2.0](../01_prd.md) - 第 3.3 节自动化执行流程
- [TDD](../02_tech_design.md) - 第 4.1 节执行器核心逻辑
- [Playwright 文档](https://playwright.dev/python/docs/intro)
- [SQLAlchemy 异步 ORM](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html)
- 现有 ORM 模型：`app/models/`
- 现有登录态管理：`app/services/auth_manager.py`
