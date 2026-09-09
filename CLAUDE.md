# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

这是一个配置驱动的浏览器自动化数据采集平台（RPA），基于 FastAPI + Playwright 构建。系统支持登录态管理、任务调度、WebSocket 实时通信和前端监控看板。

**核心特性**：
- 通过数据库配置驱动采集任务（无需修改代码）
- 支持多站点登录态隔离和持久化
- 失败任务自动补跑（APScheduler 每 30 分钟扫描）
- WebSocket 实时推送任务状态和日志

## 技术栈

- **后端**: FastAPI 0.115.0 + Uvicorn 0.30.6
- **浏览器自动化**: Playwright 1.47.0（async API）
- **数据库**: SQLAlchemy 2.0.35 + PyMySQL/aiomysql + Alembic
- **任务调度**: APScheduler 3.10.4（AsyncIOScheduler）
- **前端**: 原生 HTML/CSS/JavaScript + WebSocket
- **Python**: 3.10+

## 常用命令

### 环境初始化
```bash
# 安装依赖
pip install -r requirements.txt

# 安装 Playwright 浏览器驱动
playwright install chromium

# 配置环境变量（首次运行）
cp .env.example .env
```

### 启动服务
```bash
# 开发模式（推荐）
uvicorn app.main:app --reload

# 或直接运行
python -m app.main
```

### 数据库迁移
```bash
# 创建迁移脚本
alembic revision --autogenerate -m "描述"

# 执行迁移
alembic upgrade head

# 回滚
alembic downgrade -1
```

### 测试
```bash
# 运行所有测试
pytest tests/

# 运行单个测试文件
pytest tests/test_executor_websocket.py

# 带详细输出
pytest tests/ -v -s

# 测试登录态管理功能
bash test_auth.sh  # Linux/Mac
.\test_auth.ps1    # Windows PowerShell
```

### 访问服务
- API 文档: http://127.0.0.1:8000/docs
- 监控看板: http://127.0.0.1:8000/static/index.html
- 健康检查: http://127.0.0.1:8000/health
- WebSocket: ws://127.0.0.1:8000/ws

## 架构设计

### 核心流程

1. **配置驱动**: `crawler_configs` 表定义采集规则（URL、选择器、字段映射）
2. **任务队列**: `job_queue` 表存储待执行任务和查询参数
3. **执行器**: `services/executor.py` 读取配置 → 启动 Playwright → 填充表单 → 提取数据 → 分页抓取
4. **调度器**: `services/scheduler.py` 每 30 分钟扫描失败任务（retry_count < 3）并重试
5. **实时推送**: `api/websocket.py` 通过 WebSocket 推送任务状态、日志、统计数据

### 关键模块说明

#### 1. 登录态管理 (`services/auth_manager.py`)
- 拉起有头浏览器让用户手动登录
- 保存 cookies/localStorage 到 `auth_files/{profile}.json`
- 多站点通过 `auth_profile` 字段隔离

#### 2. 执行器 (`services/executor.py`)
- **关键方法**: `execute_job(job_id)` - 串行执行单个任务
- 支持多输入框配置（`input_configs` JSON 字段）
- 自动处理分页（`pagination_selector` + `max_pages`）
- 失败时记录 `error_msg` 并递增 `retry_count`

#### 3. 调度器 (`services/scheduler.py`)
- **启动时机**: `app.main:lifespan` 生命周期钩子
- **重试逻辑**: 
  - 查询 `status='failed' AND retry_count < 3` 的任务
  - 首次运行延迟 1 分钟，后续每 30 分钟执行
  - 通过 `coalesce=True` 避免堆积

#### 4. WebSocket 管理器 (`api/websocket.py`)
- **广播方法**: 
  - `broadcast_status(data)` - 推送任务状态
  - `broadcast_log(message, level)` - 推送日志
  - `broadcast_stats(stats)` - 推送统计数据
- **断线重连**: 前端自动重连，interval 从 1s 递增到 30s

#### 5. 数据库模型 (`models/`)
- `CrawlerConfig`: 采集配置（包含选择器规则、登录态、分页配置）
- `JobQueue`: 任务队列（状态：pending/processing/success/failed）
- `CrawlerResult`: 采集结果（JSON 存储提取数据）

### 数据流示例

```python
# 1. 数据库插入任务
job = JobQueue(
    config_id=1,
    query_params={"keyword": "手机", "price_range": "1000-2000"}
)

# 2. 执行器读取配置并执行
config = await session.get(CrawlerConfig, job.config_id)
# 启动浏览器 → 加载登录态 → 填充表单 → 等待结果 → 提取数据 → 翻页

# 3. WebSocket 推送进度
await ws_manager.broadcast_status({
    "job_id": job.id,
    "status": "processing",
    "progress": "第 2/5 页"
})

# 4. 保存结果
result = CrawlerResult(
    job_id=job.id,
    extracted_data=[{"title": "...", "price": "..."}],
    page_count=5
)
```

## 平台特殊性

### Windows 兼容性
```python
# main.py 已包含此设置
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
```

### Playwright 配置
- **有头模式**: `HEADLESS_MODE=False` 用于登录态管理
- **无头模式**: 生产环境任务执行使用 `HEADLESS_MODE=True`
- **浏览器路径**: Playwright 自动管理，无需手动配置

## 开发注意事项

1. **数据库连接**: 使用 `app.core.database.get_session()` 获取异步 session
2. **日志规范**: 使用 `logging.getLogger(__name__)` 而非 print
3. **WebSocket 推送**: 执行器中的关键步骤需调用 `ws_manager.broadcast_*()` 方法
4. **任务状态更新**: 修改 `job.status` 后必须 `await session.commit()`
5. **选择器命名**: 遵循 CSS Selector 或 XPath 语法（存储在数据库 JSON 字段）
6. **登录态加载**: 在 `page.goto()` 之前调用 `context.add_cookies()` 和 `context.add_init_script()`

## 文档参考

- `docs/01_prd.md` - 产品需求文档
- `docs/02_tech_design.md` - 技术设计方案
- `docs/03_auth_usage.md` - 登录态管理使用指南
- `docs/executor_usage.md` - 执行器使用说明
- `docs/scheduler_usage.md` - 调度器使用说明
- `docs/database_usage.md` - 数据库操作指南
- `docs/websocket_usage.md` - WebSocket 集成说明

## 配置文件位置

- `.env` - 环境变量配置（数据库连接、端口等）
- `alembic.ini` - Alembic 数据库迁移配置
- `auth_files/*.json` - 登录态文件存储目录
- `app/core/config.py` - 应用配置类

## 当前分支

- 主分支: `main`
- 当前分支: `master`（注意：通常需要合并到 `main`）
