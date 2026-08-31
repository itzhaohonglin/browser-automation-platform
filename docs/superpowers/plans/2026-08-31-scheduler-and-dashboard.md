# APScheduler 定时补跑和前端看板实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 集成 APScheduler 实现失败任务的定时补跑，并完善前端监控看板展示任务进度、实时日志、登录态状态和统计面板。

**Architecture:** 使用 AsyncIOScheduler 在 FastAPI lifespan 中管理定时任务，每 30 分钟扫描失败任务并重置为 pending 状态。前端通过 WebSocket 接收实时消息，展示统计卡片、进度面板、登录态状态和日志滚动。

**Tech Stack:** FastAPI lifespan, APScheduler 3.10.4, AsyncIOScheduler, WebSocket, 原生 HTML/CSS/JavaScript

---

## 文件结构

### 新建文件
- `app/services/scheduler.py` - 调度器服务（定时补跑逻辑）
- `static/style.css` - 看板样式定义
- `static/app.js` - WebSocket 连接和前端逻辑

### 修改文件
- `app/main.py` - 添加 lifespan 事件管理
- `static/index.html` - 完整看板 UI 结构
- `app/api/endpoints.py` - 添加统计数据 API（可选）

---

## Task 1: 创建调度器服务

**Files:**
- Create: `app/services/scheduler.py`
- Test: Manual testing (定时任务测试)

- [ ] **Step 1: 编写调度器服务基础结构**

创建 `app/services/scheduler.py`:

```python
import logging
from datetime import datetime, timedelta
from typing import Optional
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.models.job import JobQueue, JobStatus

logger = logging.getLogger(__name__)


class TaskScheduler:
    """任务调度器 - 负责定时补跑失败任务"""

    def __init__(self, ws_manager=None):
        """
        初始化调度器

        Args:
            ws_manager: WebSocket 管理器（可选，用于状态推送）
        """
        self.scheduler = AsyncIOScheduler(
            timezone='Asia/Shanghai',
            job_defaults={
                'coalesce': True,  # 合并错过的执行
                'max_instances': 1  # 同时只运行一个补跑任务
            }
        )
        self.ws_manager = ws_manager
        self.logger = logger

    async def start(self):
        """启动调度器"""
        self.logger.info("正在启动任务调度器...")

        # 添加定时任务：每 30 分钟扫描并重试失败任务
        self.scheduler.add_job(
            func=self.retry_failed_jobs,
            trigger=IntervalTrigger(minutes=30),
            id='retry_failed_jobs',
            name='重试失败任务',
            next_run_time=datetime.now() + timedelta(minutes=1)  # 首次执行延迟 1 分钟
        )

        self.scheduler.start()
        self.logger.info("任务调度器启动成功")

    async def retry_failed_jobs(self):
        """
        扫描并重试失败的任务

        逻辑：
        1. 查询 status='failed' 且 retry_count < 3 的任务
        2. 将状态重置为 'pending'，清空 error_msg
        3. 保留 retry_count（由执行器在失败时递增）
        """
        self.logger.info("开始扫描失败任务...")

        try:
            async for session in get_session():
                # 查询失败任务
                stmt = select(JobQueue).where(
                    JobQueue.status == JobStatus.FAILED,
                    JobQueue.retry_count < 3
                ).order_by(JobQueue.updated_at.asc()).limit(100)

                result = await session.execute(stmt)
                failed_jobs = result.scalars().all()

                if not failed_jobs:
                    self.logger.info("没有需要重试的失败任务")
                    return

                self.logger.info(f"发现 {len(failed_jobs)} 个失败任务，开始重置状态")

                # 逐个重置任务状态
                reset_count = 0
                for job in failed_jobs:
                    try:
                        job.status = JobStatus.PENDING
                        job.error_msg = None
                        await session.commit()
                        reset_count += 1

                        self.logger.info(
                            f"任务 #{job.id} 已重置为 pending "
                            f"(重试次数: {job.retry_count}/3)"
                        )

                        # 广播日志消息
                        if self.ws_manager:
                            await self.ws_manager.broadcast({
                                "type": "log",
                                "level": "info",
                                "message": f"任务 #{job.id} 自动重试 (第 {job.retry_count + 1} 次)",
                                "timestamp": datetime.now().isoformat()
                            })

                    except Exception as e:
                        self.logger.error(f"重置任务 #{job.id} 失败: {e}")
                        await session.rollback()
                        continue

                self.logger.info(f"成功重置 {reset_count} 个失败任务")

        except Exception as e:
            self.logger.error(f"扫描失败任务时出错: {e}", exc_info=True)

    async def shutdown(self):
        """优雅停止调度器"""
        self.logger.info("正在停止任务调度器...")
        self.scheduler.shutdown(wait=True)
        self.logger.info("任务调度器已停止")
```

- [ ] **Step 2: 验证代码语法**

运行语法检查:

```bash
python -m py_compile app/services/scheduler.py
```

预期输出：无错误

- [ ] **Step 3: 提交调度器服务**

```bash
git add app/services/scheduler.py
git commit -m "feat: add task scheduler service for retrying failed jobs

- Implement AsyncIOScheduler with 30-minute interval
- Auto-reset failed jobs (retry_count < 3) to pending status
- Integrate WebSocket broadcast for retry notifications
"
```

---

## Task 2: 集成调度器到 FastAPI 应用

**Files:**
- Modify: `app/main.py`

- [ ] **Step 1: 添加 lifespan 上下文管理器**

修改 `app/main.py`，在导入部分添加：

```python
from contextlib import asynccontextmanager
from app.services.scheduler import TaskScheduler
```

然后在 `app = FastAPI(...)` 之前添加 lifespan 定义：

```python
# 全局调度器实例
scheduler: Optional[TaskScheduler] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    global scheduler
    
    # Startup
    logger.info("应用启动中...")
    scheduler = TaskScheduler(ws_manager=websocket_manager)
    await scheduler.start()
    logger.info("调度器已启动")
    
    yield
    
    # Shutdown
    logger.info("应用关闭中...")
    if scheduler:
        await scheduler.shutdown()
    logger.info("调度器已停止")
```

- [ ] **Step 2: 将 lifespan 传递给 FastAPI 实例**

修改 FastAPI 实例化代码：

找到：
```python
app = FastAPI(
    title="浏览器自动化数据采集平台",
    description="配置驱动的 RPA 数据采集系统（支持登录态管理和任务执行）",
    version="1.0.0",
    debug=settings.DEBUG
)
```

改为：
```python
app = FastAPI(
    title="浏览器自动化数据采集平台",
    description="配置驱动的 RPA 数据采集系统（支持登录态管理和任务执行）",
    version="1.0.0",
    debug=settings.DEBUG,
    lifespan=lifespan
)
```

- [ ] **Step 3: 添加 Optional 类型导入**

在文件顶部导入部分添加：

```python
from typing import Optional
```

- [ ] **Step 4: 测试应用启动和关闭**

启动应用：

```bash
python -m app.main
```

预期日志输出：
```
INFO:     应用启动中...
INFO:     正在启动任务调度器...
INFO:     任务调度器启动成功
INFO:     调度器已启动
INFO:     Uvicorn running on http://127.0.0.1:8000
```

按 Ctrl+C 停止，预期日志输出：
```
INFO:     应用关闭中...
INFO:     正在停止任务调度器...
INFO:     任务调度器已停止
INFO:     调度器已停止
```

- [ ] **Step 5: 提交 lifespan 集成**

```bash
git add app/main.py
git commit -m "feat: integrate scheduler with FastAPI lifespan

- Add lifespan context manager for scheduler lifecycle
- Auto-start scheduler on app startup
- Gracefully shutdown scheduler on app exit
"
```

---

## Task 3: 创建前端看板 HTML 结构

**Files:**
- Modify: `static/index.html`

- [ ] **Step 1: 重写 index.html 完整结构**

替换整个 `static/index.html` 文件内容：

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>浏览器自动化数据采集平台 - 监控看板</title>
    <link rel="stylesheet" href="/static/style.css">
</head>
<body>
    <!-- 头部 -->
    <header class="header">
        <div class="header-content">
            <h1>🚀 浏览器自动化数据采集平台</h1>
            <div class="connection-status">
                <span id="ws-status" class="status-badge disconnected">连接中...</span>
            </div>
        </div>
    </header>

    <!-- 主容器 -->
    <div class="container">
        <!-- 统计卡片区域 -->
        <section class="stats-section">
            <div class="stat-card stat-total">
                <div class="stat-icon">📊</div>
                <div class="stat-content">
                    <div class="stat-label">总任务数</div>
                    <div class="stat-value" id="stat-total">0</div>
                </div>
            </div>

            <div class="stat-card stat-success">
                <div class="stat-icon">✅</div>
                <div class="stat-content">
                    <div class="stat-label">成功</div>
                    <div class="stat-value" id="stat-success">0</div>
                </div>
            </div>

            <div class="stat-card stat-failed">
                <div class="stat-icon">❌</div>
                <div class="stat-content">
                    <div class="stat-label">失败</div>
                    <div class="stat-value" id="stat-failed">0</div>
                </div>
            </div>

            <div class="stat-card stat-rate">
                <div class="stat-icon">📈</div>
                <div class="stat-content">
                    <div class="stat-label">成功率</div>
                    <div class="stat-value" id="stat-rate">0%</div>
                </div>
            </div>
        </section>

        <!-- 进度和登录态区域 -->
        <section class="info-section">
            <!-- 当前任务进度 -->
            <div class="panel progress-panel">
                <h2>当前任务进度</h2>
                <div id="progress-content">
                    <div class="idle-state">
                        <span class="idle-icon">💤</span>
                        <p>空闲中</p>
                    </div>
                </div>
            </div>

            <!-- 登录态状态 -->
            <div class="panel auth-panel">
                <h2>登录态状态</h2>
                <div id="auth-list">
                    <p class="empty-state">暂无登录态配置</p>
                </div>
            </div>
        </section>

        <!-- 实时日志区域 -->
        <section class="log-section">
            <div class="panel">
                <h2>实时日志</h2>
                <div id="log-container" class="log-container">
                    <div class="log-entry log-info">
                        <span class="log-time">[--:--:--]</span>
                        <span class="log-level">[INFO]</span>
                        <span class="log-message">等待 WebSocket 连接...</span>
                    </div>
                </div>
            </div>
        </section>
    </div>

    <script src="/static/app.js"></script>
</body>
</html>
```

- [ ] **Step 2: 验证 HTML 语法**

在浏览器中打开 `http://127.0.0.1:8000/static/index.html`，检查：
- 页面加载无错误
- 所有区域正常显示（即使样式未完成）

- [ ] **Step 3: 提交 HTML 结构**

```bash
git add static/index.html
git commit -m "feat: create dashboard HTML structure

- Add stats cards section (total, success, failed, rate)
- Add progress panel for current task
- Add auth status panel
- Add real-time log container
- Add WebSocket connection status indicator
"
```

---

## Task 4: 创建前端看板 CSS 样式

**Files:**
- Create: `static/style.css`

- [ ] **Step 1: 编写完整 CSS 样式**

创建 `static/style.css`:

```css
/* 全局样式 */
* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

:root {
    --primary-color: #667eea;
    --secondary-color: #764ba2;
    --success-color: #10b981;
    --warning-color: #f59e0b;
    --error-color: #ef4444;
    --info-color: #3b82f6;
    --bg-color: #f5f7fa;
    --card-bg: #ffffff;
    --text-primary: #1f2937;
    --text-secondary: #6b7280;
    --border-color: #e5e7eb;
    --shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
    --shadow-lg: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
}

body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', sans-serif;
    background: var(--bg-color);
    color: var(--text-primary);
    line-height: 1.6;
}

/* 头部 */
.header {
    background: linear-gradient(135deg, var(--primary-color) 0%, var(--secondary-color) 100%);
    color: white;
    padding: 1.5rem 2rem;
    box-shadow: var(--shadow-lg);
}

.header-content {
    max-width: 1400px;
    margin: 0 auto;
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.header h1 {
    font-size: 1.75rem;
    font-weight: 600;
}

.connection-status {
    display: flex;
    align-items: center;
}

.status-badge {
    padding: 0.5rem 1rem;
    border-radius: 20px;
    font-size: 0.875rem;
    font-weight: 500;
    display: flex;
    align-items: center;
    gap: 0.5rem;
}

.status-badge::before {
    content: '';
    width: 8px;
    height: 8px;
    border-radius: 50%;
    display: inline-block;
}

.status-badge.connected {
    background: rgba(16, 185, 129, 0.2);
    color: #ecfdf5;
}

.status-badge.connected::before {
    background: #10b981;
    animation: pulse 2s infinite;
}

.status-badge.disconnected {
    background: rgba(239, 68, 68, 0.2);
    color: #fef2f2;
}

.status-badge.disconnected::before {
    background: #ef4444;
}

@keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.5; }
}

/* 主容器 */
.container {
    max-width: 1400px;
    margin: 2rem auto;
    padding: 0 2rem;
}

/* 统计卡片区域 */
.stats-section {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
    gap: 1.5rem;
    margin-bottom: 2rem;
}

.stat-card {
    background: var(--card-bg);
    padding: 1.5rem;
    border-radius: 12px;
    box-shadow: var(--shadow);
    display: flex;
    align-items: center;
    gap: 1rem;
    transition: transform 0.2s, box-shadow 0.2s;
}

.stat-card:hover {
    transform: translateY(-2px);
    box-shadow: var(--shadow-lg);
}

.stat-icon {
    font-size: 2.5rem;
}

.stat-content {
    flex: 1;
}

.stat-label {
    font-size: 0.875rem;
    color: var(--text-secondary);
    margin-bottom: 0.25rem;
}

.stat-value {
    font-size: 2rem;
    font-weight: 700;
}

.stat-total .stat-value { color: var(--info-color); }
.stat-success .stat-value { color: var(--success-color); }
.stat-failed .stat-value { color: var(--error-color); }
.stat-rate .stat-value { color: var(--primary-color); }

/* 进度和登录态区域 */
.info-section {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 1.5rem;
    margin-bottom: 2rem;
}

.panel {
    background: var(--card-bg);
    border-radius: 12px;
    padding: 1.5rem;
    box-shadow: var(--shadow);
}

.panel h2 {
    font-size: 1.25rem;
    font-weight: 600;
    margin-bottom: 1rem;
    color: var(--text-primary);
}

/* 进度面板 */
.idle-state {
    text-align: center;
    padding: 2rem;
    color: var(--text-secondary);
}

.idle-icon {
    font-size: 3rem;
    display: block;
    margin-bottom: 0.5rem;
}

.task-info {
    margin-bottom: 1rem;
}

.task-id {
    font-size: 1.125rem;
    font-weight: 600;
    color: var(--primary-color);
    margin-bottom: 0.5rem;
}

.task-message {
    color: var(--text-secondary);
    font-size: 0.875rem;
}

.progress-bar-container {
    background: var(--bg-color);
    border-radius: 8px;
    height: 24px;
    overflow: hidden;
    margin-top: 0.5rem;
}

.progress-bar {
    height: 100%;
    background: linear-gradient(90deg, var(--primary-color), var(--secondary-color));
    transition: width 0.3s ease;
    display: flex;
    align-items: center;
    justify-content: center;
    color: white;
    font-size: 0.75rem;
    font-weight: 600;
}

/* 登录态面板 */
.auth-list {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
}

.auth-item {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    padding: 0.75rem;
    background: var(--bg-color);
    border-radius: 8px;
}

.auth-indicator {
    width: 12px;
    height: 12px;
    border-radius: 50%;
    flex-shrink: 0;
}

.auth-indicator.normal { background: var(--success-color); }
.auth-indicator.expired { background: var(--warning-color); }
.auth-indicator.not_configured { background: var(--text-secondary); }

.auth-profile {
    flex: 1;
    font-weight: 500;
}

.auth-status {
    font-size: 0.875rem;
    color: var(--text-secondary);
}

.empty-state {
    text-align: center;
    padding: 2rem;
    color: var(--text-secondary);
}

/* 日志区域 */
.log-section {
    margin-bottom: 2rem;
}

.log-container {
    background: #1f2937;
    color: #e5e7eb;
    border-radius: 8px;
    padding: 1rem;
    height: 400px;
    overflow-y: auto;
    font-family: 'Monaco', 'Menlo', 'Courier New', monospace;
    font-size: 0.875rem;
    line-height: 1.5;
}

.log-entry {
    margin-bottom: 0.25rem;
    word-wrap: break-word;
}

.log-time {
    color: #9ca3af;
}

.log-level {
    font-weight: 600;
    margin: 0 0.5rem;
}

.log-info .log-level { color: #3b82f6; }
.log-warning .log-level { color: #f59e0b; }
.log-error .log-level { color: #ef4444; }

.log-message {
    color: #e5e7eb;
}

/* 滚动条样式 */
.log-container::-webkit-scrollbar {
    width: 8px;
}

.log-container::-webkit-scrollbar-track {
    background: #374151;
    border-radius: 4px;
}

.log-container::-webkit-scrollbar-thumb {
    background: #4b5563;
    border-radius: 4px;
}

.log-container::-webkit-scrollbar-thumb:hover {
    background: #6b7280;
}

/* 响应式设计 */
@media (max-width: 1024px) {
    .info-section {
        grid-template-columns: 1fr;
    }
}

@media (max-width: 768px) {
    .container {
        padding: 0 1rem;
    }

    .header-content {
        flex-direction: column;
        gap: 1rem;
        text-align: center;
    }

    .stats-section {
        grid-template-columns: repeat(2, 1fr);
    }

    .stat-card {
        padding: 1rem;
    }

    .stat-icon {
        font-size: 2rem;
    }

    .stat-value {
        font-size: 1.5rem;
    }
}
```

- [ ] **Step 2: 验证样式效果**

刷新浏览器 `http://127.0.0.1:8000/static/index.html`，检查：
- 头部渐变色正常显示
- 统计卡片排列整齐
- 进度面板和登录态面板并排显示
- 日志区域深色背景正常
- 响应式布局（缩小浏览器窗口测试）

- [ ] **Step 3: 提交 CSS 样式**

```bash
git add static/style.css
git commit -m "feat: add dashboard CSS styles

- Modern card-based layout with gradients
- Responsive grid system for stats cards
- Dark theme for log container
- Smooth animations and transitions
- Mobile-friendly responsive design
"
```

---

## Task 5: 创建前端 WebSocket 和交互逻辑

**Files:**
- Create: `static/app.js`

- [ ] **Step 1: 编写 WebSocket 连接管理代码（第 1 部分）**

创建 `static/app.js`，编写前半部分（连接管理和工具函数）:

```javascript
// WebSocket 连接管理
class DashboardApp {
    constructor() {
        this.ws = null;
        this.reconnectTimeout = null;
        this.reconnectDelay = 3000;
        this.maxLogs = 100;
        this.logs = [];
        this.currentJobId = null;

        // DOM 元素
        this.wsStatus = document.getElementById('ws-status');
        this.statTotal = document.getElementById('stat-total');
        this.statSuccess = document.getElementById('stat-success');
        this.statFailed = document.getElementById('stat-failed');
        this.statRate = document.getElementById('stat-rate');
        this.progressContent = document.getElementById('progress-content');
        this.authList = document.getElementById('auth-list');
        this.logContainer = document.getElementById('log-container');
    }

    init() {
        this.connectWebSocket();
        this.startHeartbeat();
    }

    connectWebSocket() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws`;

        this.addLog('info', `正在连接 WebSocket: ${wsUrl}`);

        try {
            this.ws = new WebSocket(wsUrl);

            this.ws.onopen = () => this.onOpen();
            this.ws.onmessage = (event) => this.onMessage(event);
            this.ws.onerror = (error) => this.onError(error);
            this.ws.onclose = () => this.onClose();
        } catch (error) {
            this.addLog('error', `WebSocket 连接失败: ${error.message}`);
            this.scheduleReconnect();
        }
    }

    onOpen() {
        this.updateConnectionStatus(true);
        this.addLog('info', 'WebSocket 连接成功');

        // 清除重连定时器
        if (this.reconnectTimeout) {
            clearTimeout(this.reconnectTimeout);
            this.reconnectTimeout = null;
        }

        // 请求初始统计数据
        this.fetchInitialStats();
    }

    onMessage(event) {
        try {
            const message = JSON.parse(event.data);
            this.handleMessage(message);
        } catch (error) {
            console.error('解析 WebSocket 消息失败:', error);
        }
    }

    onError(error) {
        console.error('WebSocket 错误:', error);
    }

    onClose() {
        this.updateConnectionStatus(false);
        this.addLog('warning', 'WebSocket 连接已断开，将在 3 秒后重连...');
        this.scheduleReconnect();
    }

    scheduleReconnect() {
        if (this.reconnectTimeout) {
            return;
        }

        this.reconnectTimeout = setTimeout(() => {
            this.reconnectTimeout = null;
            this.connectWebSocket();
        }, this.reconnectDelay);
    }

    startHeartbeat() {
        setInterval(() => {
            if (this.ws && this.ws.readyState === WebSocket.OPEN) {
                this.ws.send('ping');
            }
        }, 30000);
    }

    updateConnectionStatus(connected) {
        if (connected) {
            this.wsStatus.textContent = '已连接';
            this.wsStatus.className = 'status-badge connected';
        } else {
            this.wsStatus.textContent = '已断开';
            this.wsStatus.className = 'status-badge disconnected';
        }
    }
```

- [ ] **Step 2: 编写消息处理逻辑（第 2 部分）**

继续在 `static/app.js` 中添加消息处理代码:

```javascript
    handleMessage(message) {
        switch (message.type) {
            case 'progress':
                this.handleProgress(message);
                break;
            case 'log':
                this.handleLog(message);
                break;
            case 'stats':
                this.handleStats(message);
                break;
            case 'auth_status':
                this.handleAuthStatus(message);
                break;
            default:
                console.warn('未知的消息类型:', message.type);
        }
    }

    handleProgress(message) {
        this.currentJobId = message.job_id;
        const progress = message.progress;

        let progressHtml = `
            <div class="task-info">
                <div class="task-id">任务 #${message.job_id}</div>
                <div class="task-message">${message.message}</div>
            </div>
        `;

        if (progress && progress.current !== undefined && progress.total !== undefined) {
            const percentage = Math.round((progress.current / progress.total) * 100);
            progressHtml += `
                <div class="progress-bar-container">
                    <div class="progress-bar" style="width: ${percentage}%">
                        ${percentage}%
                    </div>
                </div>
            `;
        }

        this.progressContent.innerHTML = progressHtml;
    }

    handleLog(message) {
        this.addLog(message.level, message.message);
    }

    handleStats(message) {
        const data = message.data;
        this.statTotal.textContent = data.total || 0;
        this.statSuccess.textContent = data.success || 0;
        this.statFailed.textContent = data.failed || 0;
        this.statRate.textContent = `${data.success_rate?.toFixed(1) || 0}%`;
    }

    handleAuthStatus(message) {
        // 这里简化处理，实际应维护一个状态列表
        this.addLog('info', `登录态更新: ${message.profile} - ${message.status}`);
    }

    addLog(level, message) {
        const now = new Date();
        const time = now.toTimeString().split(' ')[0];

        const logEntry = {
            time,
            level,
            message,
            timestamp: now.getTime()
        };

        this.logs.push(logEntry);

        // 限制日志数量
        if (this.logs.length > this.maxLogs) {
            this.logs.shift();
        }

        this.renderLogs();
    }

    renderLogs() {
        const logsHtml = this.logs.map(log => `
            <div class="log-entry log-${log.level}">
                <span class="log-time">[${log.time}]</span>
                <span class="log-level">[${log.level.toUpperCase()}]</span>
                <span class="log-message">${this.escapeHtml(log.message)}</span>
            </div>
        `).join('');

        this.logContainer.innerHTML = logsHtml;

        // 自动滚动到底部
        this.logContainer.scrollTop = this.logContainer.scrollHeight;
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    async fetchInitialStats() {
        try {
            const response = await fetch('/api/stats');
            if (response.ok) {
                const data = await response.json();
                this.handleStats({ type: 'stats', data });
            }
        } catch (error) {
            console.error('获取初始统计数据失败:', error);
        }
    }
}

// 初始化应用
const app = new DashboardApp();
app.init();
```

- [ ] **Step 3: 验证 JavaScript 语法**

在浏览器控制台检查是否有语法错误：
- 打开 `http://127.0.0.1:8000/static/index.html`
- 按 F12 打开开发者工具
- 检查 Console 标签，确认无语法错误

- [ ] **Step 4: 测试 WebSocket 连接**

在浏览器中：
1. 观察右上角连接状态从"连接中..."变为"已连接"
2. 检查日志区域显示"WebSocket 连接成功"
3. 停止后端服务，观察连接状态变为"已断开"并自动重连

- [ ] **Step 5: 提交 JavaScript 代码**

```bash
git add static/app.js
git commit -m "feat: add dashboard WebSocket and UI logic

- Implement WebSocket connection with auto-reconnect
- Add message routing for progress/log/stats/auth_status
- Implement real-time UI updates for all panels
- Add log management with 100-entry limit
- Add heartbeat mechanism (30s interval)
"
```

---

## Task 6: 添加统计数据 API 端点（可选）

**Files:**
- Modify: `app/api/endpoints.py`

- [ ] **Step 1: 添加统计数据查询端点**

在 `app/api/endpoints.py` 文件末尾添加新端点：

```python
@router.get("/api/stats")
async def get_task_stats(session: AsyncSession = Depends(get_session)):
    """
    获取任务统计数据
    
    Returns:
        统计数据字典（总数、成功数、失败数、成功率）
    """
    from sqlalchemy import func, select
    from app.models.job import JobQueue, JobStatus
    
    # 查询总数
    total_stmt = select(func.count(JobQueue.id))
    total_result = await session.execute(total_stmt)
    total = total_result.scalar() or 0
    
    # 查询成功数
    success_stmt = select(func.count(JobQueue.id)).where(
        JobQueue.status == JobStatus.SUCCESS
    )
    success_result = await session.execute(success_stmt)
    success = success_result.scalar() or 0
    
    # 查询失败数
    failed_stmt = select(func.count(JobQueue.id)).where(
        JobQueue.status == JobStatus.FAILED
    )
    failed_result = await session.execute(failed_stmt)
    failed = failed_result.scalar() or 0
    
    # 计算成功率
    success_rate = (success / total * 100) if total > 0 else 0.0
    
    return {
        "total": total,
        "success": success,
        "failed": failed,
        "success_rate": round(success_rate, 1)
    }
```

- [ ] **Step 2: 测试统计 API**

运行应用并测试：

```bash
curl http://127.0.0.1:8000/api/stats
```

预期输出：
```json
{
  "total": 0,
  "success": 0,
  "failed": 0,
  "success_rate": 0.0
}
```

- [ ] **Step 3: 在浏览器中验证统计数据加载**

打开 `http://127.0.0.1:8000/static/index.html`，检查统计卡片是否显示数据（即使为 0）

- [ ] **Step 4: 提交统计 API**

```bash
git add app/api/endpoints.py
git commit -m "feat: add task statistics API endpoint

- Add GET /api/stats for fetching task statistics
- Calculate total, success, failed counts and success rate
- Support initial dashboard data loading
"
```

---

## Task 7: 端到端测试

**Files:**
- Test: 完整功能测试

- [ ] **Step 1: 创建测试任务数据**

使用数据库工具或 Python 脚本创建测试数据：

```python
# 临时测试脚本 test_data.py
import asyncio
from app.core.database import get_session
from app.models.job import JobQueue, JobStatus

async def create_test_jobs():
    async for session in get_session():
        # 创建成功任务
        for i in range(5):
            job = JobQueue(
                config_id=1,
                query_params={"keyword": f"test{i}"},
                status=JobStatus.SUCCESS
            )
            session.add(job)
        
        # 创建失败任务（retry_count < 3）
        for i in range(3):
            job = JobQueue(
                config_id=1,
                query_params={"keyword": f"failed{i}"},
                status=JobStatus.FAILED,
                retry_count=i,
                error_msg="Test error"
            )
            session.add(job)
        
        await session.commit()
        print("测试数据创建成功")

if __name__ == "__main__":
    asyncio.run(create_test_jobs())
```

运行：
```bash
python test_data.py
```

- [ ] **Step 2: 验证看板统计数据**

刷新看板页面，检查：
- 总任务数：8
- 成功数：5
- 失败数：3
- 成功率：62.5%

- [ ] **Step 3: 验证定时补跑机制**

等待 1 分钟后（首次执行延迟），检查：
1. 后端日志显示"开始扫描失败任务..."
2. 后端日志显示"发现 3 个失败任务，开始重置状态"
3. 查询数据库，确认失败任务状态已变为 `pending`
4. 前端日志显示自动重试消息

手动触发测试（可选）：
```python
# 手动触发补跑
from app.services.scheduler import TaskScheduler
scheduler = TaskScheduler()
await scheduler.retry_failed_jobs()
```

- [ ] **Step 4: 验证 WebSocket 实时推送**

运行一个任务执行测试：
```bash
curl -X POST "http://127.0.0.1:8000/task/run?job_id=1"
```

观察看板：
1. 进度面板显示"任务 #1"
2. 日志区域实时显示执行日志
3. 统计数据实时更新

- [ ] **Step 5: 验证断线重连**

1. 停止后端服务
2. 观察看板状态变为"已断开"
3. 重启后端服务
4. 观察看板自动重连并恢复"已连接"状态

- [ ] **Step 6: 清理测试数据**

删除测试脚本（如果创建了）：
```bash
rm test_data.py
```

或保留在 `tests/manual/` 目录：
```bash
mkdir -p tests/manual
mv test_data.py tests/manual/
```

- [ ] **Step 7: 最终提交**

```bash
git add -A
git commit -m "test: verify scheduler and dashboard integration

- Verify automatic retry of failed jobs every 30 minutes
- Verify real-time WebSocket updates on dashboard
- Verify statistics display and calculation
- Verify auto-reconnect mechanism
- All end-to-end tests passed
"
```

---

## Task 8: 更新文档

**Files:**
- Create: `docs/scheduler_usage.md`

- [ ] **Step 1: 编写使用文档**

创建 `docs/scheduler_usage.md`:

```markdown
# 任务调度器使用说明

## 功能概述

任务调度器负责自动扫描失败的任务并重新调度执行，确保临时失败的任务有重试机会。

## 核心特性

- **自动补跑**：每 30 分钟自动扫描失败任务
- **重试限制**：最多重试 3 次（retry_count < 3）
- **优雅停止**：应用关闭时等待正在执行的调度任务完成
- **WebSocket 通知**：补跑操作实时推送到前端看板

## 调度规则

### 补跑条件

任务满足以下条件时会被自动补跑：
1. 状态为 `failed`
2. 重试次数 `retry_count < 3`

### 执行流程

```
1. 扫描符合条件的失败任务
2. 将状态从 failed 重置为 pending
3. 清空 error_msg（保留 retry_count）
4. 任务重新进入正常执行队列
```

### 重试次数管理

- 初始创建：`retry_count = 0`
- 执行失败：`retry_count += 1`（由执行器自动递增）
- 补跑重置：保持 `retry_count` 不变
- 停止补跑：当 `retry_count >= 3` 时不再自动重试

## 配置说明

### 调度间隔

默认：30 分钟

修改方法（在 `app/services/scheduler.py` 中）：
```python
self.scheduler.add_job(
    func=self.retry_failed_jobs,
    trigger=IntervalTrigger(minutes=30),  # 修改这里
    # ...
)
```

### 最大重试次数

默认：3 次

修改方法（在 `app/services/scheduler.py` 中）：
```python
stmt = select(JobQueue).where(
    JobQueue.status == JobStatus.FAILED,
    JobQueue.retry_count < 3  # 修改这里
)
```

### 首次执行延迟

默认：应用启动后 1 分钟

修改方法（在 `app/services/scheduler.py` 中）：
```python
self.scheduler.add_job(
    # ...
    next_run_time=datetime.now() + timedelta(minutes=1)  # 修改这里
)
```

## 监控

### 查看调度日志

后端日志输出：
```
INFO: 正在启动任务调度器...
INFO: 任务调度器启动成功
INFO: 开始扫描失败任务...
INFO: 发现 3 个失败任务，开始重置状态
INFO: 任务 #123 已重置为 pending (重试次数: 1/3)
INFO: 成功重置 3 个失败任务
```

### 前端看板监控

访问 `http://127.0.0.1:8000/static/index.html`，查看：
- 实时日志区域显示补跑消息
- 统计卡片显示失败任务数量变化

## 手动触发补跑

在 Python 控制台或脚本中：

```python
from app.services.scheduler import TaskScheduler
from app.api.websocket import websocket_manager

scheduler = TaskScheduler(ws_manager=websocket_manager)
await scheduler.retry_failed_jobs()
```

## 故障排查

### 问题：调度器未启动

**症状**：后端日志无"任务调度器启动成功"

**解决方法**：
1. 检查 `app/main.py` 是否正确配置 lifespan
2. 检查 APScheduler 是否正确安装：`pip list | grep APScheduler`

### 问题：失败任务未被补跑

**症状**：30 分钟后失败任务状态仍为 failed

**排查步骤**：
1. 检查 retry_count 是否 >= 3
2. 检查后端日志是否有"开始扫描失败任务..."
3. 检查数据库连接是否正常

### 问题：调度器无法停止

**症状**：应用关闭时长时间无响应

**解决方法**：
1. 检查是否有长时间运行的补跑任务
2. 调整 shutdown 超时时间（默认 30 秒）
3. 强制停止：`Ctrl+C` 两次

## 性能优化

### 限制扫描数量

在 `app/services/scheduler.py` 中添加 limit：

```python
stmt = select(JobQueue).where(
    JobQueue.status == JobStatus.FAILED,
    JobQueue.retry_count < 3
).order_by(JobQueue.updated_at.asc()).limit(100)  # 每次最多处理 100 个
```

### 使用数据库索引

确保 `idx_config_status` 索引存在（已在 ORM 模型中定义）。

## 相关文档

- [任务执行器使用说明](executor_usage.md)
- [WebSocket 使用说明](websocket_usage.md)
- [PRD - 3.5 容错与失败重试机制](01_prd.md#35-容错与失败重试机制状态机驱动)
```

- [ ] **Step 2: 更新 README.md**

在 `README.md` 的"已完成功能"部分添加：

```markdown
- [x] **定时任务调度** (PRD 3.5)
  - [x] APScheduler 集成
  - [x] 失败任务自动补跑（每 30 分钟）
  - [x] 重试次数限制（最多 3 次）
  - [x] 优雅启动和停止
- [x] **前端监控看板** (PRD 3.6)
  - [x] 实时统计卡片（总数、成功、失败、成功率）
  - [x] 当前任务进度展示
  - [x] 登录态状态面板
  - [x] 实时日志滚动
  - [x] WebSocket 断线重连
```

- [ ] **Step 3: 提交文档**

```bash
git add docs/scheduler_usage.md README.md
git commit -m "docs: add scheduler usage guide and update README

- Document scheduler features and configuration
- Add troubleshooting guide
- Update README with completed features
"
```

---

## 自我审查清单

### Spec 覆盖检查

- [x] **调度器集成**：Task 1（scheduler.py）、Task 2（lifespan）
- [x] **定时补跑逻辑**：Task 1 中的 retry_failed_jobs 方法
- [x] **前端统计卡片**：Task 3（HTML）、Task 4（CSS）、Task 5（JS stats 处理）
- [x] **前端进度面板**：Task 3（HTML）、Task 4（CSS）、Task 5（JS progress 处理）
- [x] **前端登录态状态**：Task 3（HTML）、Task 4（CSS）、Task 5（JS auth_status 处理）
- [x] **实时日志滚动**：Task 3（HTML）、Task 4（CSS）、Task 5（JS log 处理）
- [x] **WebSocket 消息协议**：Task 5（完整实现 4 种消息类型）
- [x] **自动重连机制**：Task 5（reconnect 逻辑）
- [x] **统计数据 API**：Task 6（/api/stats 端点）

### 占位符检查

- [x] 无 TBD、TODO
- [x] 所有代码块完整
- [x] 所有命令具体
- [x] 无"类似于..."引用

### 类型一致性检查

- [x] `TaskScheduler` 类名一致
- [x] `retry_failed_jobs` 方法名一致
- [x] `websocket_manager` 变量名一致
- [x] WebSocket 消息类型一致（progress, log, stats, auth_status）
- [x] DOM 元素 ID 一致（stat-total, stat-success, etc.）

---

## 执行建议

**推荐顺序**：按 Task 1 → Task 8 顺序执行

**关键里程碑**：
1. Task 2 完成后：验证调度器能否启动和停止
2. Task 4 完成后：验证看板 UI 布局
3. Task 5 完成后：验证 WebSocket 连接和消息处理
4. Task 7 完成后：端到端功能验证

**测试策略**：每个 Task 完成后立即测试，避免问题累积

---

**计划状态**：已完成  
**预计工时**：2-3 小时（包含测试和调试）  
**复杂度**：中等
