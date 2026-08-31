# 浏览器自动化数据采集平台 - 技术设计方案（TDD）

**文档版本**：1.0  
**对应PRD版本**：V2.0  
**拟定日期**：2026-08-22  

---

## 1. 技术栈选型

- **后端框架**：FastAPI（异步高性能，原生支持WebSocket）
- **浏览器驱动**：Playwright（官方Async API）
- **数据库**：MySQL 8.0 + SQLAlchemy（ORM） + Alembic（迁移）
- **定时调度**：APScheduler（AsyncIOScheduler）
- **前端**：原生HTML + CSS + JavaScript（轻量，直接放`/static`）
- **Python版本**：3.10+

---

## 2. 数据库设计（核心DDL）

```sql
-- 1. 采集配置表（核心规则）
CREATE TABLE `crawler_configs` (
  `id` INT PRIMARY KEY AUTO_INCREMENT,
  `config_name` VARCHAR(100) NOT NULL COMMENT '任务名称',
  `target_url` VARCHAR(500) NOT NULL COMMENT '目标页面URL',
  `need_login` TINYINT(1) DEFAULT 0 COMMENT '是否需要登录',
  `auth_profile` VARCHAR(50) DEFAULT NULL COMMENT '登录态标识(如taobao)',
  `login_url` VARCHAR(500) DEFAULT NULL COMMENT '登录页地址',
  `input_configs` JSON NOT NULL COMMENT '多输入框配置 [{"selector":"#kw","value":"{keyword}","type":"fill"}]',
  `submit_selector` VARCHAR(200) NOT NULL COMMENT '查询按钮选择器',
  `wait_selector` VARCHAR(200) NOT NULL COMMENT '等待加载完成的选择器',
  `fields_mapping` JSON NOT NULL COMMENT '数据提取规则 {"title":".title text"}',
  `pagination_selector` VARCHAR(200) DEFAULT NULL COMMENT '下一页按钮选择器',
  `max_pages` INT DEFAULT 1 COMMENT '最大翻页数',
  `is_active` TINYINT(1) DEFAULT 1 COMMENT '是否启用',
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
  INDEX `idx_auth_profile` (`auth_profile`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 2. 任务队列表（动态读取待查询参数）
CREATE TABLE `job_queue` (
  `id` INT PRIMARY KEY AUTO_INCREMENT,
  `config_id` INT NOT NULL COMMENT '关联crawler_configs.id',
  `query_params` JSON NOT NULL COMMENT '查询参数 {"keyword":"手机","date":"2026-08-22"}',
  `status` ENUM('pending','processing','success','failed') DEFAULT 'pending',
  `retry_count` INT DEFAULT 0,
  `error_msg` TEXT,
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX `idx_config_status` (`config_id`, `status`),
  FOREIGN KEY (`config_id`) REFERENCES `crawler_configs`(`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 3. 采集结果表（存储提取的业务数据）
CREATE TABLE `crawler_results` (
  `id` INT PRIMARY KEY AUTO_INCREMENT,
  `job_id` INT NOT NULL COMMENT '关联job_queue.id',
  `config_id` INT NOT NULL,
  `query_params` JSON NOT NULL COMMENT '本次查询参数快照',
  `extracted_data` JSON NOT NULL COMMENT '提取的结构化业务数据',
  `page_count` INT DEFAULT 1 COMMENT '实际抓取页数',
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
  INDEX `idx_job` (`job_id`),
  FOREIGN KEY (`job_id`) REFERENCES `job_queue`(`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

## 3. 项目目录结构

```text
browser-automation-platform/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI 入口
│   ├── api/
│   │   ├── __init__.py
│   │   ├── websocket.py        # WebSocket 连接管理 & 状态推送
│   │   └── endpoints.py        # RESTful接口（任务启停/登录态更新/统计数据）
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py           # 全局配置（数据库连接、路径常量）
│   │   └── database.py         # SQLAlchemy 引擎 & Session
│   ├── models/
│   │   ├── __init__.py
│   │   ├── config.py           # CrawlerConfig ORM
│   │   ├── job.py              # JobQueue ORM
│   │   └── result.py           # CrawlerResult ORM
│   ├── services/
│   │   ├── __init__.py
│   │   ├── executor.py         # 核心：Playwright 串行执行器
│   │   ├── scheduler.py        # 定时任务调度（失败补跑）
│   │   └── auth_manager.py     # 登录态 UI 驱动核心逻辑
│   └── utils/
│       ├── __init__.py
│       └── logger.py           # 日志封装
├── auth_files/                 # 存放 auth_*.json（登录态文件）
├── static/                     # 前端静态文件
│   ├── index.html              # 监控看板界面
│   ├── style.css
│   └── app.js
├── requirements.txt
└── .env                        # 环境变量（DB_URL等）
```

## 4. 核心代码骨架

### 4.1 执行器核心逻辑 (`app/services/executor.py`)

```python
import asyncio
from playwright.async_api import async_playwright
from app.core.database import AsyncSessionLocal
from app.models.job import JobQueue
from app.api.websocket import manager  # WebSocket连接管理器

class PlaywrightExecutor:
    def __init__(self, config_dict: dict, websocket_manager):
        self.config = config_dict
        self.ws_manager = websocket_manager
        self.browser = None
        self.context = None

    async def execute_job(self, job_id: int, query_params: dict):
        """执行单个任务（串行）"""
        async with async_playwright() as p:
            # 1. 初始化浏览器上下文（多站点登录态隔离）
            browser = await p.chromium.launch(headless=True)
            
            if self.config['need_login']:
                auth_file = f"auth_files/auth_{self.config['auth_profile']}.json"
                self.context = await browser.new_context(storage_state=auth_file)
            else:
                self.context = await browser.new_context()
            
            page = await self.context.new_page()
            
            # 2. 推送状态：开始处理
            await self.ws_manager.broadcast({
                "type": "progress",
                "job_id": job_id,
                "keyword": query_params.get("keyword"),
                "status": "processing"
            })

            try:
                # 3. 访问目标URL
                await page.goto(self.config['target_url'])
                
                # 4. 多输入框填充（动态）
                for input_cfg in self.config['input_configs']:
                    selector = input_cfg['selector']
                    value = input_cfg['value'].format(**query_params)  # 占位符替换
                    if input_cfg['type'] == 'fill':
                        await page.fill(selector, value)
                    elif input_cfg['type'] == 'select':
                        await page.select_option(selector, value)
                
                # 5. 点击查询
                await page.click(self.config['submit_selector'])
                await page.wait_for_selector(self.config['wait_selector'], timeout=15000)
                
                # 6. 分页循环 + 数据提取
                all_data = []
                current_page = 1
                while current_page <= self.config.get('max_pages', 1):
                    # 提取当前页数据（利用 fields_mapping 在浏览器端执行）
                    page_data = await page.evaluate(f"""
                        (mapping) => {{
                            // 动态提取逻辑（稍后封装为通用函数）
                            return []; 
                        }}
                    """, self.config['fields_mapping'])
                    all_data.extend(page_data)
                    
                    # 检查是否有下一页
                    if not self.config.get('pagination_selector'):
                        break
                    next_btn = page.locator(self.config['pagination_selector'])
                    if await next_btn.count() == 0 or await next_btn.is_disabled():
                        break
                    
                    await next_btn.click()
                    await page.wait_for_selector(self.config['wait_selector'], state="visible")
                    current_page += 1
                
                # 7. 保存结果
                async with AsyncSessionLocal() as session:
                    job = await session.get(JobQueue, job_id)
                    job.status = 'success'
                    # 存入 crawler_results 表...
                    await session.commit()
                
                await self.ws_manager.broadcast({"type": "log", "level": "success", "msg": f"完成 {query_params}"})
                
            except Exception as e:
                # 失败处理：标记failed，记录错误，跳过继续
                async with AsyncSessionLocal() as session:
                    job = await session.get(JobQueue, job_id)
                    job.status = 'failed'
                    job.error_msg = str(e)
                    job.retry_count += 1
                    await session.commit()
                
                await self.ws_manager.broadcast({"type": "log", "level": "error", "msg": f"失败: {str(e)}"})
            
            finally:
                await browser.close()
```

### 4.2 登录态UI更新接口 (`app/api/endpoints.py`)

```python
from fastapi import APIRouter, HTTPException
from playwright.async_api import async_playwright
import json

router = APIRouter()

# 存储临时登录状态（用于UI回调）
temp_login_context = {}

@router.post("/auth/start")
async def start_auth_update(profile: str):
    """看板点击"更新登录态"时调用，拉起有头浏览器"""
    # 从数据库读取对应 profile 的 login_url（需提供查询接口）
    login_url = "https://example.com/login"  # 从配置表获取
    
    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch(headless=False)
    context = await browser.new_context()
    page = await context.new_page()
    await page.goto(login_url)
    
    # 存储playwright对象供后续保存使用
    temp_login_context[profile] = {
        "browser": browser,
        "context": context,
        "playwright": playwright
    }
    return {"msg": "浏览器已打开，请手动完成登录"}

@router.post("/auth/save")
async def save_auth_state(profile: str):
    """管理员在UI点击"确认已登录"时调用，保存登录态"""
    if profile not in temp_login_context:
        raise HTTPException(status_code=404, detail="未找到活跃的登录会话")
    
    ctx = temp_login_context[profile]
    await ctx["context"].storage_state(path=f"auth_files/auth_{profile}.json")
    
    # 关闭浏览器
    await ctx["browser"].close()
    await ctx["playwright"].stop()
    del temp_login_context[profile]
    
    return {"msg": f"{profile} 登录态已保存成功"}
```

### 4.3 WebSocket状态推送结构

推送消息格式严格遵循PRD，不携带业务数据：

```python
{
  "type": "progress",
  "data": {
    "current_keyword": "手机",
    "processed": 45,
    "total": 100,
    "current_page": 3,
    "status": "running"
  }
}
{
  "type": "log",
  "data": {
    "level": "info",   // info | success | warning | error
    "msg": "正在抓取第 3 页",
    "timestamp": "14:32:05"
  }
}
{
  "type": "auth_status",
  "data": {
    "profiles": [
      {"name": "taobao", "status": "valid"},
      {"name": "jd", "status": "expired"}
    ]
  }
}
```

## 5. 启动与运行

1. 安装依赖：`pip install -r requirements.txt && playwright install`
2. 配置 `.env` 文件（数据库连接串）
3. 初始化数据库：`alembic upgrade head`
4. 启动服务：`uvicorn app.main:app --reload`
5. 访问看板：`http://localhost:8000/static/index.html`

## 6. 后续开发步骤建议

1. **第一优先级**：完成数据库建表和ORM模型映射。
2. **第二优先级**：完善 `executor.py` 中的 `page.evaluate` 数据提取通用函数（根据 `fields_mapping` 动态生成JS提取逻辑）。
3. **第三优先级**：集成APScheduler定时任务，每小时扫描 `failed` 任务重置为 `pending`。
4. **第四优先级**：前端看板完善UI布局（登录态管理面板、日志滚动区、进度卡片）。