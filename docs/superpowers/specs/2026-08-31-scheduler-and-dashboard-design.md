---
name: scheduler-and-dashboard-design
description: APScheduler 定时补跑集成和前端监控看板完善设计
type: design
---

# APScheduler 定时补跑和前端看板设计文档

## 1. 概述

### 1.1 目标

集成 APScheduler 实现失败任务的定时补跑机制，并完善前端监控看板，提供任务进度、实时日志、登录态状态和统计面板的完整展示。

### 1.2 背景

根据 PRD 3.5 节要求，系统需要：
- 自动扫描 `failed` 状态且 `retry_count < 3` 的任务
- 每 30 分钟执行一次补跑
- 前端看板实时展示任务执行状态、日志和统计信息

### 1.3 范围

**包含**：
- APScheduler 集成和配置
- 定时补跑任务逻辑
- FastAPI lifespan 生命周期管理
- 前端看板完整 UI 实现
- WebSocket 消息协议扩展
- 统计数据计算和广播

**不包含**：
- 登录态管理功能（已实现）
- 任务执行器逻辑（已实现）
- WebSocket 基础设施（已实现）

## 2. 技术架构

### 2.1 调度器架构

#### 组件设计

```
┌─────────────────────────────────────┐
│      FastAPI Application            │
│  ┌──────────────────────────────┐   │
│  │   Lifespan Context Manager   │   │
│  │  - startup: init scheduler   │   │
│  │  - shutdown: stop scheduler  │   │
│  └──────────────────────────────┘   │
│              │                       │
│              ▼                       │
│  ┌──────────────────────────────┐   │
│  │   TaskScheduler Service      │   │
│  │  - AsyncIOScheduler          │   │
│  │  - retry_failed_jobs (30m)   │   │
│  └──────────────────────────────┘   │
│              │                       │
│              ▼                       │
│  ┌──────────────────────────────┐   │
│  │   Database (job_queue)       │   │
│  │  - scan failed jobs          │   │
│  │  - reset to pending          │   │
│  └──────────────────────────────┘   │
└─────────────────────────────────────┘
```

#### 调度器配置

- **调度器类型**：`AsyncIOScheduler`（与 FastAPI 异步架构兼容）
- **时区**：`Asia/Shanghai`
- **任务执行策略**：`coalesce=True`（合并错过的执行）
- **最大实例数**：`max_instances=1`（同时只运行一个补跑任务）

#### 定时任务规则

- **触发器**：`IntervalTrigger`
- **间隔**：30 分钟
- **首次执行**：应用启动后 1 分钟（避免启动时立即执行）

### 2.2 补跑逻辑

#### 任务筛选条件

```sql
SELECT * FROM job_queue 
WHERE status = 'failed' 
  AND retry_count < 3
ORDER BY updated_at ASC
```

#### 执行流程

```
1. 扫描数据库 → 2. 筛选失败任务 → 3. 逐个重置状态 → 4. 记录日志
   (SQL查询)      (retry_count < 3)   (failed → pending)   (广播消息)
```

**串行处理原则**：
- 补跑任务将失败任务重置为 `pending` 状态
- 重置后的任务进入正常的任务队列
- 由现有的任务执行器按照串行方式处理
- 清空 `error_msg` 字段，但保留 `retry_count`

#### 重试次数管理

- 初始 `retry_count = 0`
- 每次执行失败后 `retry_count += 1`
- 补跑时不修改 `retry_count`
- 达到 3 次后不再自动补跑

### 2.3 生命周期管理

#### FastAPI Lifespan 集成

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    scheduler = TaskScheduler()
    await scheduler.start()
    yield
    # Shutdown
    await scheduler.shutdown()
```

#### 优雅停止机制

- 调用 `scheduler.shutdown(wait=True)`
- 等待正在执行的任务完成
- 超时时间：30 秒
- 记录停止日志

## 3. 前端看板设计

### 3.1 布局结构

```
┌─────────────────────────────────────────────────────┐
│  🚀 浏览器自动化数据采集平台    [WebSocket: 已连接]  │
├─────────────────────────────────────────────────────┤
│  ┌──────┐  ┌──────┐  ┌──────┐  ┌──────┐            │
│  │ 总数 │  │ 成功 │  │ 失败 │  │成功率│  统计卡片   │
│  │  45  │  │  38  │  │  7   │  │ 84% │            │
│  └──────┘  └──────┘  └──────┘  └──────┘            │
├─────────────────────────┬───────────────────────────┤
│  当前任务进度            │  登录态状态                │
│  ┌───────────────────┐  │  ┌─────────────────────┐ │
│  │ 任务 #123         │  │  │ ● taobao    正常    │ │
│  │ 正在处理第 2 页   │  │  │ ○ jd        未配置  │ │
│  │ ▓▓▓▓░░░░ 40%     │  │  │ ● baidu     正常    │ │
│  └───────────────────┘  │  └─────────────────────┘ │
├─────────────────────────┴───────────────────────────┤
│  实时日志                                            │
│  ┌───────────────────────────────────────────────┐  │
│  │ [14:32:15] [INFO] 任务 #123 开始执行          │  │
│  │ [14:32:16] [INFO] 浏览器启动成功              │  │
│  │ [14:32:18] [INFO] 表单填充完成                │  │
│  │ [14:32:20] [ERROR] 任务 #124 执行失败         │  │
│  │                                               │  │
│  └───────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────┘
```

### 3.2 UI 组件

#### 统计卡片
- **总任务数**：`SELECT COUNT(*) FROM job_queue`
- **成功数**：`WHERE status = 'success'`
- **失败数**：`WHERE status = 'failed'`
- **成功率**：`(成功数 / 总数) * 100%`
- **颜色方案**：蓝色(总数)、绿色(成功)、红色(失败)、渐变色(成功率)

#### 进度面板
- 显示当前正在执行的任务 ID
- 动态进度条（基于 current/total）
- 当前页数提示
- 无任务时显示"空闲中"

#### 登录态状态面板
- 站点名称（`auth_profile`）
- 状态指示器：
  - `●` 绿色：正常
  - `○` 灰色：未配置
  - `●` 黄色：已过期
- 列表形式展示所有配置的站点

#### 实时日志区域
- 自动滚动到最新日志
- 日志级别颜色：
  - `INFO`：蓝色
  - `WARNING`：橙色
  - `ERROR`：红色
- 时间戳格式：`[HH:MM:SS]`
- 最大显示：最近 100 条日志

### 3.3 WebSocket 消息协议

#### 消息类型定义

```typescript
// 进度消息
{
  "type": "progress",
  "job_id": 123,
  "message": "正在处理第 2 页",
  "progress": {
    "current": 2,
    "total": 5
  },
  "timestamp": "2026-08-31T14:32:15"
}

// 日志消息
{
  "type": "log",
  "level": "info" | "warning" | "error",
  "message": "任务 #123 执行成功",
  "job_id": 123,  // 可选
  "timestamp": "2026-08-31T14:32:15"
}

// 统计数据
{
  "type": "stats",
  "data": {
    "total": 45,
    "success": 38,
    "failed": 7,
    "success_rate": 84.4
  },
  "timestamp": "2026-08-31T14:32:15"
}

// 登录态状态
{
  "type": "auth_status",
  "profile": "taobao",
  "status": "normal" | "expired" | "not_configured",
  "timestamp": "2026-08-31T14:32:15"
}
```

### 3.4 前端技术栈

- **HTML5**：语义化标签
- **CSS3**：Flexbox 布局、Grid 布局、CSS 变量
- **原生 JavaScript**：WebSocket API、DOM 操作
- **无外部依赖**：纯静态文件，易于部署

### 3.5 响应式设计

- **桌面端**（>1024px）：双列布局
- **平板端**（768-1024px）：单列堆叠
- **移动端**（<768px）：紧凑布局，统计卡片 2x2 网格

## 4. 实现细节

### 4.1 调度器服务 (`app/services/scheduler.py`)

#### 类结构

```python
class TaskScheduler:
    def __init__(self, ws_manager=None):
        self.scheduler = AsyncIOScheduler(
            timezone='Asia/Shanghai',
            job_defaults={
                'coalesce': True,
                'max_instances': 1
            }
        )
        self.ws_manager = ws_manager
    
    async def start(self):
        """启动调度器"""
        # 添加定时任务
        self.scheduler.add_job(
            self.retry_failed_jobs,
            trigger='interval',
            minutes=30,
            next_run_time=datetime.now() + timedelta(minutes=1)
        )
        self.scheduler.start()
    
    async def retry_failed_jobs(self):
        """扫描并重试失败任务"""
        # 数据库查询和状态重置逻辑
    
    async def shutdown(self):
        """优雅停止调度器"""
        self.scheduler.shutdown(wait=True)
```

#### 数据库操作

- 使用 `AsyncSession` 异步查询
- 事务管理：每个任务重置为独立事务
- 错误处理：单个任务失败不影响其他任务

### 4.2 主应用集成 (`app/main.py`)

#### Lifespan 事件

```python
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    scheduler = TaskScheduler(ws_manager=websocket_manager)
    await scheduler.start()
    logger.info("Scheduler started")
    
    yield
    
    # Shutdown
    await scheduler.shutdown()
    logger.info("Scheduler stopped")

app = FastAPI(lifespan=lifespan)
```

### 4.3 前端实现

#### 文件结构

```
static/
├── index.html      # 主页面结构
├── style.css       # 样式定义
└── app.js          # WebSocket 逻辑和 DOM 操作
```

#### 关键功能

**WebSocket 连接管理**：
- 自动重连机制（连接断开后 3 秒重试）
- 连接状态指示器
- 心跳检测（每 30 秒发送 ping）

**消息处理**：
- 消息类型路由（switch/case）
- 数据更新和 DOM 渲染
- 日志队列管理（保持最近 100 条）

**UI 交互**：
- 平滑滚动动画
- 进度条动画（CSS transition）
- 响应式布局调整

## 5. 数据流图

```
┌──────────────┐
│  APScheduler │ (每30分钟触发)
└──────┬───────┘
       │
       ▼
┌──────────────────┐
│ retry_failed_jobs│ (扫描 failed 任务)
└──────┬───────────┘
       │
       ▼
┌──────────────────┐
│  Database Update │ (failed → pending)
└──────┬───────────┘
       │
       ▼
┌──────────────────┐
│ WebSocket Broadcast│ (通知前端)
└──────┬───────────┘
       │
       ▼
┌──────────────────┐
│  Frontend Update │ (更新统计和日志)
└──────────────────┘
```

## 6. 错误处理

### 6.1 调度器层面

- **数据库连接失败**：记录错误日志，跳过本次执行
- **任务执行超时**：设置 30 秒超时，超时后终止
- **并发冲突**：`max_instances=1` 避免重复执行

### 6.2 前端层面

- **WebSocket 断开**：显示"连接断开"状态，自动重连
- **消息格式错误**：记录控制台错误，跳过该消息
- **DOM 更新失败**：try-catch 包裹，避免脚本中断

## 7. 性能考虑

### 7.1 调度器

- 使用索引查询：`idx_config_status` 索引
- 批量查询但串行重置：避免长事务
- 限制扫描结果数量：每次最多处理 100 个任务

### 7.2 前端

- 日志限制：最多显示 100 条，超出后删除旧日志
- DOM 批量更新：使用 DocumentFragment
- 防抖处理：统计数据更新间隔至少 1 秒

## 8. 测试策略

### 8.1 单元测试

- 调度器启动和停止
- 失败任务筛选逻辑
- 状态重置逻辑
- WebSocket 消息广播

### 8.2 集成测试

- 定时任务触发和执行
- 数据库事务正确性
- 前端 WebSocket 连接和消息处理

### 8.3 手动测试

- 创建失败任务，验证补跑机制
- 观察前端统计数据更新
- 测试 WebSocket 断线重连
- 验证登录态状态显示

## 9. 部署注意事项

### 9.1 环境要求

- Python 3.10+
- APScheduler 3.10.4（已在 requirements.txt）
- 现代浏览器（支持 WebSocket）

### 9.2 配置项

- 调度间隔：可在 `scheduler.py` 中修改
- 最大重试次数：可调整为环境变量
- 时区设置：根据部署地区调整

### 9.3 监控

- 日志记录：调度器执行日志
- 任务统计：定期检查失败任务数量
- WebSocket 连接数：监控活跃连接

## 10. 未来扩展

### 10.1 调度器

- 支持多种调度策略（cron 表达式）
- 任务优先级队列
- 失败任务告警通知

### 10.2 前端

- 任务详情弹窗
- 历史数据图表（ECharts）
- 手动触发任务补跑
- 登录态管理界面集成

## 11. 验收标准

### 11.1 功能验收

- [x] 系统启动后自动启动调度器
- [x] 每 30 分钟扫描并重置失败任务
- [x] 前端显示统计卡片（总数、成功、失败、成功率）
- [x] 前端显示当前任务进度和进度条
- [x] 前端显示登录态状态列表
- [x] 前端显示实时日志滚动
- [x] WebSocket 连接断开后自动重连
- [x] 应用关闭时调度器优雅停止

### 11.2 性能验收

- [x] 补跑任务执行时间 < 5 秒（数据库操作）
- [x] 前端日志更新无明显延迟（< 100ms）
- [x] WebSocket 消息广播性能良好（100+ 连接）

### 11.3 用户体验验收

- [x] 浏览器打开 `http://127.0.0.1:8000/static/index.html` 显示完整看板
- [x] 统计数据实时更新，与后端数据一致
- [x] 日志颜色区分清晰，易于阅读
- [x] 进度条动画流畅，视觉反馈明确
- [x] 登录态状态一目了然

---

**文档版本**：V1.0  
**创建日期**：2026-08-31  
**最后更新**：2026-08-31  
**状态**：待审核
