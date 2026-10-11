# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

这是一个配置驱动的浏览器自动化数据采集平台（RPA），基于 FastAPI + Playwright 构建。系统支持登录态管理、任务调度、WebSocket 实时通信和前端监控看板。

**核心理念 - 配置驱动**：
- 一次配置（`crawler_configs`）→ 多次任务（`job_queue`）→ 动态参数（`query_params`）
- 新增采集目标只需插入数据库配置，无需修改代码
- 通过 JSON 字段存储复杂规则（输入框配置、字段映射、iframe 处理、详情采集）

**核心特性**：
- 通过数据库配置驱动采集任务（无需修改代码）
- 支持多站点登录态隔离和持久化
- 失败任务自动补跑（可配置重试间隔和次数）
- 进程池并发执行（可配置工作进程数）
- **请求级限流控制（可配置每个 HTTP 请求间隔，防止被封禁）**
- WebSocket 实时推送任务状态和日志
- 支持复杂页面（多层 iframe、详情弹窗、分页）

## 技术栈

- **后端**: FastAPI 0.115.0 + Uvicorn 0.30.6
- **浏览器自动化**: Playwright 1.47.0（async API）
- **数据库**: SQLAlchemy 2.0.35 + pyodbc/aioodbc + Alembic
- **数据库服务器**: SQL Server on Windows
- **任务调度**: APScheduler 3.10.4（AsyncIOScheduler）
- **前端**: 原生 HTML/CSS/JavaScript + WebSocket
- **Python**: 3.10+

## 常用命令

### 📦 打包版本（推荐 - 无需 Python 环境）

适用于 `dist/browser-automation-platform/` 目录，所有操作通过批处理文件完成：

```bash
# === 首次安装 ===
install.bat                # 配置环境变量和数据库连接
init_database.bat          # 创建数据库表结构
install_browser.bat        # 安装 Playwright Chromium 浏览器
init_config.bat            # 初始化 NHSA 采集配置

# === 批量导入任务 ===
# 1. 准备数据文件：import_data\jobs.txt（每行一个注册证号）
# 2. 运行导入脚本
batch_import.bat           # 交互式批量导入任务

# === 启动和监控 ===
startup.bat                # 启动 Web 服务
check_config.bat           # 检查配置文件是否正确

# === 手动执行命令（高级用户）===
browser-automation-platform.exe --init-config              # 初始化配置
browser-automation-platform.exe --import-jobs "file.txt"   # 导入任务
browser-automation-platform.exe --migrate                  # 执行数据库迁移
browser-automation-platform.exe --install-browser          # 安装浏览器驱动
browser-automation-platform.exe                            # 启动服务
```

**重要**: 打包版本的配置文件（`.env`）在首次运行 `install.bat` 时会从 `.env.template` 自动创建，包含所有配置项及详细说明。如需更新已部署版本的配置，参考 `docs/package_config_update.md`。

### 🔧 开发环境（需要 Python 环境）

#### 环境初始化
```bash
# 安装依赖
pip install -r requirements.txt

# 安装 Playwright 浏览器驱动
playwright install chromium

# 配置环境变量（首次运行）
cp .env.example .env

# 初始化数据库（SQL Server）
# 方式1: 使用 sqlcmd
sqlcmd -S localhost -U sa -P YourPassword -Q "CREATE DATABASE bap COLLATE Latin1_General_100_CI_AS_SC_UTF8;"

# 方式2: 使用 SQL Server Management Studio (SSMS)
# 手动创建数据库 bap，COLLATE 设置为 Latin1_General_100_CI_AS_SC_UTF8

# 执行数据库迁移
alembic upgrade head
```

#### 启动服务
```bash
# 开发模式（推荐）
uvicorn app.main:app --reload

# 生产模式
python -m app.main
```

#### 数据库操作
```bash
# 创建迁移脚本
alembic revision --autogenerate -m "描述"

# 执行迁移
alembic upgrade head

# 回滚一个版本
alembic downgrade -1

# 查看迁移历史
alembic history

# 验证迁移（运行验证脚本）
python scripts/verify_migration.py
```

#### 测试
```bash
# 运行所有测试
pytest

# 运行单个测试文件
pytest tests/test_executor_websocket.py

# 带详细输出和覆盖率
pytest -v -s --cov=app --cov-report=html

# 端到端测试
python scripts/final_e2e_test.py
```

#### 初始化配置和任务
```bash
# 初始化 NHSA 注册证号查询配置（示例）
python scripts/init_nhsa_registration_config.py

# 批量导入任务（从文件）
python scripts/batch_import_registration_jobs.py path/to/jobs.txt

# 批量导入任务（交互式）
python scripts/import_registration_numbers_from_txt.py

# 导出样本数据
python scripts/export_sample_data.py
```

### 代码质量检查
```bash
# 代码格式化
black app/ tests/
isort app/ tests/

# 代码检查
flake8 app/ tests/

# 安全扫描
bandit -r app/ -c pyproject.toml

# 运行所有 pre-commit 检查
pre-commit run --all-files
```

### 访问服务
- **API 文档**: http://127.0.0.1:8000/docs
- **监控看板**: http://127.0.0.1:8000/static/index.html
- **健康检查**: http://127.0.0.1:8000/health
- **WebSocket**: ws://127.0.0.1:8000/ws

## 架构设计

### 系统分层

```
前端监控看板 (static/index.html)
    ↓ HTTP + WebSocket
FastAPI 应用层 (app/main.py)
    ├─ API 端点 (api/endpoints.py, api/jobs.py, api/configs.py)
    ├─ WebSocket 管理器 (api/websocket.py)
    └─ 调度器启动 (lifespan)
    ↓
服务层 (services/)
    ├─ PlaywrightExecutor - 任务执行核心
    ├─ Scheduler - 失败任务补跑
    └─ AuthManager - 登录态管理
    ↓
数据访问层 (models/ + core/database.py)
    ├─ CrawlerConfig - 采集配置
    ├─ JobQueue - 任务队列
    └─ CrawlerResult - 采集结果
    ↓
SQL Server 数据库
```

### 核心执行流程

**配置驱动的数据采集流程**：

```
1. 配置阶段（一次性）
   ├─ 在 crawler_configs 表插入采集规则
   ├─ 定义：target_url, input_configs, fields_mapping
   └─ 可选：iframe_config, detail_config（详情采集）

2. 任务创建（批量/API）
   ├─ 在 job_queue 表插入任务
   ├─ 指定 config_id + query_params（动态参数）
   └─ 示例：{"registration_no": "滇械注准20192140008"}

3. 任务执行（Executor）
   ├─ 读取 config 和 job 数据
   ├─ 启动 Playwright 浏览器（有头/无头模式）
   ├─ 加载登录态（如需要，从 auth_files/{profile}.json）
   ├─ 访问 target_url
   ├─ 填充表单（遍历 input_configs，动态替换占位符）
   ├─ 点击提交按钮，等待结果加载
   ├─ 处理 iframe（支持多层嵌套）
   ├─ 提取列表数据（fields_mapping）
   ├─ 可选：点击详情按钮，提取详情数据
   ├─ 自动分页（pagination_selector）
   └─ 保存到 crawler_results 表

4. 状态推送（WebSocket）
   ├─ 实时推送任务状态变化
   ├─ 推送执行日志（info/success/error）
   └─ 推送统计数据（成功/失败数）

5. 失败重试（Scheduler）
   ├─ 每 30 分钟扫描 failed 任务
   ├─ 重置 status='pending'（retry_count < 3）
   └─ 自动重新进入执行队列
```

### 关键模块深入

#### 1. 执行器 (`services/executor.py`)

**核心类**: `PlaywrightExecutor`

**关键方法**：
- `execute_job(job_id)` - 主执行入口，处理完整任务生命周期
- `_handle_iframe(page, iframe_config)` - 处理多层 iframe 嵌套
- `_extract_list_data(frame, fields_mapping)` - 提取列表页数据
- `_extract_detail_data(frame, detail_config)` - 提取详情页数据
- `_handle_pagination(frame, pagination_selector)` - 自动翻页

**重要特性**：
- 支持复杂 iframe 结构（level 1 → level 2 → level N）
- 详情采集：点击详情按钮 → 进入详情 iframe → 提取字段 → 关闭弹窗
- 智能重试：提取失败自动重试（max_attempts 可配置）
- 超时控制：page_load、wait_selector、click 等分别配置超时时间
- 实时推送：每个关键步骤通过 WebSocket 推送进度

**配置示例**：
```python
config.fields_mapping = {
    "iframe_levels": 2,  # iframe 嵌套层数
    "iframe1_selector": "iframe#dataInfo",
    "iframe2_selector": "iframe.els-iframe.active",
    "list_selector": "tbody tr.jqgrow",
    "fields": [
        {"name": "序号", "selector": "td:nth-child(1)", "attr": "text"},
        {"name": "耗材名称", "selector": "td:nth-child(2)", "attr": "text"}
    ],
    "detail_config": {
        "enabled": True,
        "detail_button_selector": "a:has-text('详情')",
        "detail_iframe_selector": "iframe.artDialog-iframe",
        "fields": [
            {"name": "注册证号", "selector": "...", "attr": "text"}
        ]
    }
}
```

#### 2. 调度器 (`services/scheduler.py`)

**启动时机**: FastAPI 的 `lifespan` 上下文管理器（app/main.py）

**调度策略**：
- 使用 APScheduler 的 `AsyncIOScheduler`
- 首次运行延迟 1 分钟（避免启动时立即执行）
- 之后每 30 分钟执行一次
- `coalesce=True` 防止任务堆积
- `max_instances=1` 确保串行执行

**重试逻辑**：
```sql
SELECT * FROM job_queue 
WHERE status = 'failed' 
  AND retry_count < 3
ORDER BY created_at ASC
```

#### 3. 登录态管理 (`services/auth_manager.py`)

**多站点隔离**：
- 每个站点通过 `auth_profile` 标识（如：taobao, jd, nhsa）
- 登录态文件：`auth_files/auth_{profile}.json`
- 包含 cookies + localStorage 数据

**工作流程**：
1. 前端点击"更新登录态"
2. 后端启动有头浏览器（headless=False）
3. 跳转到 `login_url`
4. 用户手动完成登录（包括验证码）
5. 前端点击"确认保存"
6. 后端调用 `context.storage_state()` 保存登录态
7. 关闭浏览器

**加载登录态**：
```python
if config.need_login and config.auth_profile:
    auth_file = f"auth_files/auth_{config.auth_profile}.json"
    context = await browser.new_context(storage_state=auth_file)
else:
    context = await browser.new_context()  # 匿名模式
```

#### 4. WebSocket 管理器 (`api/websocket.py`)

**连接管理**：
```python
class ConnectionManager:
    active_connections: List[WebSocket] = []
    
    async def connect(websocket)
    async def disconnect(websocket)
    async def broadcast(message)  # 广播给所有连接
```

**消息类型**：
- `status` - 任务状态更新（job_id, status, progress）
- `log` - 日志消息（level: info/success/warning/error）
- `stats` - 统计数据（总任务数、成功数、失败数）

**前端自动重连**：
- 初始间隔 1s，最大 30s
- 指数退避策略
- 连接成功后重置间隔

#### 5. 数据库模型

**CrawlerConfig** - 采集配置（一次配置，多次使用）
- `input_configs`: JSON 数组，支持多个输入框
- `fields_mapping`: JSON 对象，定义数据提取规则
- `timeout_config`: JSON 对象，超时配置
- `extraction_config`: JSON 对象，提取重试配置
- `priority`: 优先级（1-10）

**JobQueue** - 任务队列（动态参数）
- `query_params`: JSON 对象，存储动态查询参数
- `status`: ENUM(pending, processing, success, failed)
- `retry_count`: 重试次数（最多 3 次）
- `error_msg`: 失败原因

**CrawlerResult** - 采集结果
- `extracted_data`: JSON 对象，嵌套结构：
  ```json
  {
    "items": [
      {
        "list_data": {...},
        "detail_data": {...},
        "detail_status": "success"
      }
    ],
    "summary": {
      "total_items": 10,
      "detail_success": 9,
      "detail_failed": 1
    }
  }
  ```

### 配置驱动示例

**场景**: 采集国家医保局注册证号查询结果

```python
# 1. 创建配置（一次性）
config = CrawlerConfig(
    config_name="国家医保局-注册证号查询",
    target_url="https://code.nhsa.gov.cn/toSearch.html?sysflag=1004",
    need_login=False,
    input_configs=[
        {
            "selector": "input[name='zczbh']",
            "param_name": "registration_no",  # 从 query_params 读取
            "input_method": "type"
        }
    ],
    submit_selector="button:has-text('查询')",
    wait_selector=".ui-jqgrid-btable",
    fields_mapping={
        "iframe_levels": 2,
        "iframe1_selector": "iframe#dataInfo",
        "iframe2_selector": "iframe.els-iframe.active",
        "list_selector": "tbody tr.jqgrow",
        "fields": [
            {"name": "耗材名称", "selector": "td:nth-child(2)", "attr": "text"}
        ]
    }
)
# config_id = 44

# 2. 批量创建任务（通过脚本或 API）
jobs = [
    JobQueue(config_id=44, query_params={"registration_no": "滇械注准20192140008"}),
    JobQueue(config_id=44, query_params={"registration_no": "京械注准20210001234"}),
    JobQueue(config_id=44, query_params={"registration_no": "沪械注准20200005678"}),
]

# 3. 执行任务
# - 前端看板手动触发
# - API 调用：POST /api/jobs/{job_id}/execute
# - 调度器自动执行（pending 状态任务）
```

## 平台特殊性与注意事项

### Windows 兼容性
```python
# main.py 已包含此设置（必须保留）
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
```

### Playwright 配置
- **有头模式**: `HEADLESS_MODE=False` 用于登录态管理（需要用户交互）
- **无头模式**: 生产环境任务执行使用 `HEADLESS_MODE=True`（节省资源）
- **浏览器路径**: Playwright 自动管理，无需手动配置

### 数据库 JSON 字段
配置的灵活性依赖于 JSON 字段的正确结构：

**input_configs** - 必须是数组，每个元素包含：
```json
[
  {
    "selector": "input[name='keyword']",
    "param_name": "keyword",  // 对应 query_params 中的键
    "input_method": "type",   // type | fill | select
    "clear_before": true      // 可选
  }
]
```

**fields_mapping** - 支持嵌套结构：
```json
{
  "iframe_levels": 2,  // 可选，处理 iframe
  "iframe1_selector": "iframe#first",
  "iframe2_selector": "iframe.second",
  "list_selector": "table tbody tr",
  "fields": [
    {"name": "字段名", "selector": "CSS选择器", "attr": "text|href|src"}
  ],
  "detail_config": {  // 可选，详情采集
    "enabled": true,
    "detail_button_selector": "a.detail",
    "detail_iframe_selector": "iframe.dialog",
    "fields": [...]
  }
}
```

### 开发规范

1. **数据库会话管理**
   ```python
   # 正确：使用 get_session() 上下文管理器
   from app.core.database import get_session
   
   async with get_session() as session:
       job = await session.get(JobQueue, job_id)
       job.status = "success"
       await session.commit()
   
   # 错误：手动创建 session（会导致连接泄漏）
   session = AsyncSessionLocal()  # ❌ 不推荐
   ```

2. **日志规范**
   ```python
   # 正确：使用模块级 logger
   import logging
   logger = logging.getLogger(__name__)
   logger.info("任务执行成功")
   
   # 错误：使用 print
   print("任务执行成功")  # ❌ 不符合生产规范
   ```

3. **WebSocket 推送时机**
   - 执行器的关键步骤需调用 `ws_manager.broadcast_*()` 方法
   - 任务状态变化（pending → processing → success/failed）
   - 重要操作（开始、分页、详情采集、完成）
   - 错误和异常信息

4. **任务状态更新**
   ```python
   # 必须先更新状态，再 commit
   job.status = JobStatus.SUCCESS
   job.completed_at = datetime.now()
   await session.commit()
   
   # WebSocket 推送在 commit 之后
   await ws_manager.broadcast_status({"job_id": job.id, "status": "success"})
   ```

5. **选择器命名**
   - 优先使用 CSS Selector（更简洁）
   - XPath 用于复杂定位
   - 避免绝对路径（如 `/html/body/div[3]/table`），使用相对定位或 class/id
   - 文本选择器：`:has-text("文本")` 或 `text=文本`

6. **登录态加载顺序**
   ```python
   # 正确顺序（重要！）
   browser = await playwright.chromium.launch()
   context = await browser.new_context(storage_state=auth_file)  # 先创建 context
   page = await context.new_page()  # 再创建 page
   await page.goto(url)  # 最后访问页面
   
   # 错误：在 goto 之后加载 cookies（不生效）
   await page.goto(url)
   await context.add_cookies(cookies)  # ❌ 太晚了
   ```

7. **iframe 处理**
   ```python
   # 处理多层 iframe 时必须逐层定位
   frame1 = page.frame_locator("iframe#first")
   frame2 = frame1.frame_locator("iframe.second")
   
   # 在最终 frame 中操作
   await frame2.locator("button").click()
   ```

8. **错误处理**
   - 捕获 Playwright 特定异常：`PlaywrightTimeoutError`
   - 任务失败时：更新 status、记录 error_msg、递增 retry_count
   - 继续处理下一个任务，不中断整个队列

### 配置文件结构

```
.env                          # 环境变量（必须配置）
├─ DATABASE_URL              # 数据库连接（必填）
├─ HEADLESS_MODE             # true/false
├─ LOG_LEVEL                 # INFO/DEBUG/WARNING
├─ DEBUG                     # true/false
├─ MAX_WORKERS               # 最大工作进程数（并发任务数，默认3）
├─ RETRY_INTERVAL_MINUTES    # 失败任务重试间隔（分钟，默认30）
├─ MAX_RETRY_COUNT           # 最大重试次数（默认3）
├─ RETRY_BATCH_SIZE          # 每批重试任务数量（默认100）
├─ RETRY_MIN_WAIT_MINUTES    # 失败后至少等待多久才重试（分钟，默认60）
└─ RETRY_SKIP_IF_PENDING_OVER # pending任务超过此数量则跳过重试（默认100）

alembic.ini                  # Alembic 配置（勿修改）
auth_files/                  # 登录态存储目录
├─ auth_taobao.json         # 淘宝登录态
├─ auth_jd.json             # 京东登录态
└─ auth_nhsa.json           # NHSA 登录态

app/core/config.py           # 应用配置类
```

### 环境变量配置详解

#### 并发控制配置
```bash
# 最大工作进程数（同时执行的任务数）
MAX_WORKERS=3
# 建议值：
# - 低配机器（4核8G）：2-3
# - 中配机器（8核16G）：3-5
# - 高配机器（16核32G）：5-10
# 注意：每个进程约消耗 200-500MB 内存

# 工作进程内存限制（MB）
WORKER_MEMORY_LIMIT_MB=512
```

#### 任务调度配置
```bash
# 失败任务重试间隔（分钟）
RETRY_INTERVAL_MINUTES=30
# 建议值：快速重试 5-10 分钟，正常 30 分钟，低频 60 分钟

# 最大重试次数
MAX_RETRY_COUNT=3
# 建议值：2-5 次

# 每批重试的任务数量
RETRY_BATCH_SIZE=100
# 建议值：任务量少 50，中等 100，大量 200-500
```

#### 智能重试配置（重要！）
```bash
# 失败后至少等待多久才重试（分钟）
RETRY_MIN_WAIT_MINUTES=60
# 建议值：根据任务总量计算
# 公式：预计全量任务耗时 × 0.8
# 示例：1000个任务需16小时 → 设置为 800 分钟

# 如果 pending 任务超过此数量，跳过重试
RETRY_SKIP_IF_PENDING_OVER=100
# 建议值：总任务数 × 0.1
# 作用：优先处理新任务，避免重试任务竞争
```

**智能重试机制**：
- ✅ 检查 pending 队列，如果过多则延迟重试
- ✅ 只重试失败时间超过最小等待时间的任务
- ✅ 优先保证新任务执行，避免队列竞争
- 📖 详细说明：`docs/smart_retry_optimization.md`

#### 请求级限流配置

**配置方式**：在 `extraction_config` JSON 字段中配置请求级限流，控制每个 HTTP 请求之间的间隔时间。

**数据库配置示例**：
```python
config.extraction_config = {
    "request_rate_limit": {
        "enabled": True,
        "interval_seconds": 5  # 每个 HTTP 请求间隔 5 秒
    }
}
```

**参数说明**：
- `enabled` (boolean): 是否启用请求级限流，默认 `false`
- `interval_seconds` (float): 每个 HTTP 请求之间的最小间隔时间（秒）

**限流作用点**：
- 访问页面 (`page.goto`)
- 点击查询按钮
- 点击详情按钮
- 翻页操作
- 详情内翻页

**使用场景**：
- 防止因请求频率过高被目标网站封禁
- 模拟人工操作速度
- 控制服务器负载
- 遵守目标网站的访问频率限制

**配置示例**：
```python
# 严格限流：每 10 秒一个请求
config.extraction_config = {
    "request_rate_limit": {
        "enabled": True,
        "interval_seconds": 10
    }
}

# 中等限流：每 5 秒一个请求
config.extraction_config = {
    "request_rate_limit": {
        "enabled": True,
        "interval_seconds": 5
    }
}

# 宽松限流：每 2 秒一个请求
config.extraction_config = {
    "request_rate_limit": {
        "enabled": True,
        "interval_seconds": 2
    }
}

# 禁用限流
config.extraction_config = {
    "request_rate_limit": {
        "enabled": False
    }
}
```

**重要提示**：
- 修改配置后立即生效，无需重启应用
- 限流在单个任务执行过程中生效
- 不同任务之间的限流互不影响


### 常见陷阱

1. **占位符替换**
   ```python
   # input_configs 中的 value 支持占位符
   "value": "{keyword}"  # 从 query_params["keyword"] 读取
   
   # 执行时替换
   for input_cfg in config.input_configs:
       value = input_cfg["value"].format(**query_params)
   ```

2. **异步/同步混用**
   ```python
   # 正确：全部使用 async/await
   async def execute_job(job_id):
       async with get_session() as session:
           job = await session.get(JobQueue, job_id)
   
   # 错误：混用同步代码
   def execute_job(job_id):  # ❌ 缺少 async
       session.query(JobQueue).get(job_id)  # ❌ 同步查询
   ```

3. **浏览器资源泄漏**
   ```python
   # 正确：使用 try-finally 确保关闭
   try:
       async with async_playwright() as p:
           browser = await p.chromium.launch()
           # ... 操作
   finally:
       await browser.close()  # 确保关闭
   
   # 或使用上下文管理器（推荐）
   async with async_playwright() as p:
       async with await p.chromium.launch() as browser:
           # ... 操作自动关闭
   ```

4. **JSON 字段更新**
   ```python
   # 错误：直接修改 JSON 字段（SQLAlchemy 不会检测到变化）
   config.fields_mapping["new_key"] = "value"  # ❌
   await session.commit()  # 不会保存
   
   # 正确：重新赋值整个对象
   mapping = config.fields_mapping.copy()
   mapping["new_key"] = "value"
   config.fields_mapping = mapping
   await session.commit()  # ✓ 会保存
   
   # 或使用 flag_modified
   from sqlalchemy.orm.attributes import flag_modified
   config.fields_mapping["new_key"] = "value"
   flag_modified(config, "fields_mapping")
   await session.commit()
   ```

## 文档参考

### 核心文档
- `docs/01_prd.md` - 产品需求文档（了解业务背景和功能需求）
- `docs/02_tech_design.md` - 技术设计方案（架构和技术选型）
- `docs/batch_import_guide.md` - 批量导入任务手册（实用操作指南）
- `README.md` - 项目说明和快速开始

### 功能文档
- `docs/03_auth_usage.md` - 登录态管理使用指南
- `docs/executor_usage.md` - 执行器使用说明
- `docs/scheduler_usage.md` - 调度器使用说明
- `docs/database_usage.md` - 数据库操作指南
- `docs/websocket_usage.md` - WebSocket 集成说明

### 配置指南
- `docs/nhsa_registration_config_guide.md` - NHSA 注册证号查询配置示例
- `docs/nhsa_registration_test_results.md` - 配置测试报告（参考数据结构）
- `docs/package_config_update.md` - 打包版本配置更新指南
- `docs/package_config_quick_ref.md` - 打包版本配置快速参考卡片
- `docs/env_config_update.md` - 环境变量配置更新说明
- `docs/smart_retry_optimization.md` - 智能重试优化说明

### 设计文档
- `docs/superpowers/specs/` - 功能设计规范
- `docs/superpowers/plans/` - 实现计划文档

## 项目结构关键点

```
app/
├── main.py                    # FastAPI 入口，包含 lifespan（调度器启动）
├── api/                       # API 路由层
│   ├── websocket.py          # WebSocket 连接管理器（ConnectionManager）
│   ├── endpoints.py          # 通用端点（健康检查、统计）
│   ├── jobs.py               # 任务管理 API
│   └── configs.py            # 配置管理 API
├── core/
│   ├── config.py             # Settings 配置类（读取 .env）
│   └── database.py           # get_session() 异步会话工厂
├── models/
│   ├── base.py               # SQLAlchemy Base
│   ├── config.py             # CrawlerConfig 模型
│   ├── job.py                # JobQueue 模型
│   └── result.py             # CrawlerResult 模型
├── services/
│   ├── executor.py           # PlaywrightExecutor（核心执行逻辑）
│   ├── scheduler.py          # Scheduler（失败任务补跑）
│   └── auth_manager.py       # AuthManager（登录态管理）
└── utils/
    └── logger.py             # 日志配置

scripts/                       # 工具脚本
├── init_nhsa_*.py            # 初始化配置脚本
├── batch_import_*.py         # 批量导入脚本
├── export_sample_data.py     # 导出样本数据
└── verify_*.py               # 验证脚本

alembic/                       # 数据库迁移
└── versions/                 # 迁移脚本（按时间排序）

static/                        # 前端资源
└── index.html                # 监控看板

auth_files/                    # 登录态存储（.gitignore）
tests/                         # 测试文件
```

## 重要文件说明

- **app/main.py** - 应用入口，包含调度器启动逻辑（lifespan），修改端口/CORS 在这里
- **app/services/executor.py** - 最复杂的文件，处理 iframe、详情、分页、数据提取
- **app/core/config.py** - 所有环境变量定义，新增配置项在这里添加
- **.env** - 实际配置值，**不提交到 Git**，每个环境独立配置
- **alembic/env.py** - 数据库迁移配置，修改 target_metadata 会影响迁移
