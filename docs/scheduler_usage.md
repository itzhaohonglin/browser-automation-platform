# 调度器使用文档

## 功能概述

APScheduler 定时调度器集成到浏览器自动化平台，提供失败任务的自动补跑机制。系统会定期扫描失败的任务，并将符合条件的任务重新加入执行队列，实现任务的自动重试和故障恢复。

## 核心特性

- **自动补跑**：每 30 分钟自动扫描失败任务并重试
- **重试限制**：单个任务最多重试 3 次，避免无限重试
- **智能筛选**：只补跑未达到重试上限的失败任务
- **优雅启停**：与 FastAPI 生命周期集成，支持优雅关闭
- **异步执行**：基于 AsyncIOScheduler，与 FastAPI 异步架构兼容
- **实时通知**：通过 WebSocket 向前端广播补跑状态

## 调度规则

### 补跑条件

调度器会筛选满足以下条件的任务进行补跑：

```sql
SELECT * FROM job_queue 
WHERE status = 'failed' 
  AND retry_count < 3
ORDER BY updated_at ASC
```

**条件说明**：
- `status = 'failed'`：任务状态为失败
- `retry_count < 3`：重试次数小于 3 次
- `ORDER BY updated_at ASC`：优先补跑最早失败的任务

### 执行流程

```
1. 定时触发（每 30 分钟）
   ↓
2. 扫描数据库（查询失败任务）
   ↓
3. 筛选任务（retry_count < 3）
   ↓
4. 重置状态（failed → pending）
   ↓
5. 清空错误信息（保留 retry_count）
   ↓
6. 广播通知（WebSocket 消息）
   ↓
7. 任务执行器自动处理（串行执行）
```

**重要原则**：
- 补跑任务只负责将失败任务重置为 `pending` 状态
- 重置后的任务进入正常的任务队列
- 由现有的任务执行器按照串行方式处理
- 不会并发执行多个补跑任务（`max_instances=1`）

### 重试次数管理

```
初始状态：retry_count = 0
         ↓
第1次执行失败：retry_count = 1 → 自动补跑
         ↓
第2次执行失败：retry_count = 2 → 自动补跑
         ↓
第3次执行失败：retry_count = 3 → 不再补跑（达到上限）
```

**计数规则**：
- 初始创建任务时 `retry_count = 0`
- 每次执行失败后 `retry_count += 1`（由任务执行器负责递增）
- 补跑时**不修改** `retry_count`（只重置状态）
- 达到 3 次后任务将永久保持 `failed` 状态

## 配置说明

### 调度器配置

调度器在 `app/services/scheduler.py` 中配置：

```python
class TaskScheduler:
    def __init__(self, ws_manager=None):
        self.scheduler = AsyncIOScheduler(
            timezone='Asia/Shanghai',          # 时区设置
            job_defaults={
                'coalesce': True,              # 合并错过的执行
                'max_instances': 1             # 同时只运行一个补跑任务
            }
        )
```

**配置项说明**：
- `timezone`：时区，默认 `Asia/Shanghai`
- `coalesce`：如果错过了多次执行，只运行一次
- `max_instances`：最大同时运行实例数，避免并发冲突

### 定时任务配置

```python
self.scheduler.add_job(
    self.retry_failed_jobs,                # 执行函数
    trigger='interval',                    # 触发器类型：间隔触发
    minutes=30,                            # 间隔时间：30 分钟
    next_run_time=datetime.now() + timedelta(minutes=1)  # 首次执行：启动后 1 分钟
)
```

**可调整参数**：
- `minutes`：调度间隔（默认 30 分钟）
- `next_run_time`：首次执行延迟（默认启动后 1 分钟）

### 最大重试次数配置

最大重试次数硬编码为 3 次。如需修改，可在以下位置调整：

1. **调度器查询条件**（`app/services/scheduler.py`）：
   ```python
   .filter(JobQueue.retry_count < 3)  # 修改此处
   ```

2. **前端显示逻辑**（可选，如有）：
   ```javascript
   if (job.retry_count >= 3) {
       // 不显示重试按钮
   }
   ```

### 首次执行延迟配置

为避免应用启动时立即执行补跑任务（此时可能数据库连接尚未稳定），默认延迟 1 分钟：

```python
next_run_time=datetime.now() + timedelta(minutes=1)
```

可根据实际需要调整延迟时间：
- 开发环境：建议 10-30 秒
- 生产环境：建议 1-3 分钟

## 监控

### 查看日志

调度器会记录详细的执行日志，包括：

**启动日志**：
```
[INFO] Scheduler started
[INFO] Next retry job scheduled at: 2026-08-31 14:33:00
```

**执行日志**：
```
[INFO] [Scheduler] Starting retry job scan
[INFO] [Scheduler] Found 5 failed jobs to retry
[INFO] [Scheduler] Reset job #123 from failed to pending
[INFO] [Scheduler] Reset job #124 from failed to pending
[INFO] [Scheduler] Retry job completed: 5 jobs reset
```

**错误日志**：
```
[ERROR] [Scheduler] Failed to reset job #123: Database connection lost
[ERROR] [Scheduler] Retry job failed: Connection timeout
```

**停止日志**：
```
[INFO] Scheduler stopped gracefully
```

### 前端看板

访问 `http://127.0.0.1:8000/static/index.html` 查看实时监控看板：

#### 统计卡片
- **总任务数**：所有任务总数
- **成功数**：`status = 'success'` 的任务数
- **失败数**：`status = 'failed'` 的任务数
- **成功率**：`(成功数 / 总数) * 100%`

#### 实时日志
- 显示最近 100 条日志
- 颜色区分：
  - 蓝色：INFO 级别
  - 橙色：WARNING 级别
  - 红色：ERROR 级别
- 自动滚动到最新日志
- 包含时间戳：`[HH:MM:SS]`

#### 当前任务进度
- 显示正在执行的任务 ID
- 实时进度条（基于 current/total）
- 无任务时显示"空闲中"

## 手动触发补跑

如需立即执行补跑任务（不等待定时触发），可以通过以下方式：

### 方式 1：重启应用

调度器会在应用启动后 1 分钟执行首次补跑：

```bash
# 停止应用（Ctrl+C）
# 重新启动
uvicorn app.main:app --reload
```

### 方式 2：直接操作数据库

手动将失败任务重置为 `pending` 状态：

```sql
UPDATE job_queue 
SET status = 'pending', 
    error_msg = NULL,
    updated_at = NOW()
WHERE status = 'failed' 
  AND retry_count < 3;
```

**注意**：此方式不会触发 WebSocket 通知，前端统计数据可能延迟更新。

### 方式 3：添加 API 接口（未实现）

可扩展实现手动触发 API：

```python
@app.post("/scheduler/trigger-retry")
async def trigger_retry():
    """手动触发补跑任务"""
    await scheduler.retry_failed_jobs()
    return {"message": "Retry job triggered"}
```

## 故障排查

### 问题 1：调度器未启动

**症状**：日志中无 "Scheduler started" 信息

**排查步骤**：
1. 检查 `app/main.py` 中 `lifespan` 是否正确配置
2. 检查是否有异常日志阻止了启动
3. 验证 APScheduler 是否正确安装：`pip show apscheduler`

**解决方案**：
```bash
pip install --upgrade apscheduler
```

### 问题 2：失败任务未补跑

**症状**：数据库中有 `failed` 任务，但状态未重置

**排查步骤**：
1. 检查 `retry_count` 是否已达到 3 次：
   ```sql
   SELECT id, status, retry_count FROM job_queue WHERE status = 'failed';
   ```
2. 查看调度器日志，确认是否执行了补跑任务
3. 检查数据库连接是否正常

**解决方案**：
- 如果 `retry_count >= 3`，手动重置为 0：
  ```sql
  UPDATE job_queue SET retry_count = 0 WHERE id = 123;
  ```
- 如果数据库连接异常，检查数据库服务状态

### 问题 3：补跑任务执行频率异常

**症状**：补跑任务执行过于频繁或不执行

**排查步骤**：
1. 检查调度器配置中的 `minutes` 参数
2. 查看 `next_run_time` 是否设置正确
3. 检查系统时间和时区设置

**解决方案**：
```python
# 修改 app/services/scheduler.py
self.scheduler.add_job(
    self.retry_failed_jobs,
    trigger='interval',
    minutes=30,  # 调整此处
    next_run_time=datetime.now() + timedelta(minutes=1)
)
```

### 问题 4：应用关闭时卡住

**症状**：`Ctrl+C` 后应用未立即退出

**原因**：调度器正在执行任务，等待任务完成

**解决方案**：
- 正常情况：等待最多 30 秒（超时时间）
- 强制退出：再次按 `Ctrl+C`

## 性能优化

### 数据库查询优化

调度器使用索引查询，确保以下索引存在：

```sql
CREATE INDEX idx_config_status ON job_queue(config_id, status);
CREATE INDEX idx_updated_at ON job_queue(updated_at);
```

### 限制扫描数量

如果失败任务数量过多，可以限制每次补跑的任务数：

```python
# 在 app/services/scheduler.py 中修改查询
failed_jobs = result.scalars().limit(100).all()  # 每次最多补跑 100 个任务
```

### 调整调度间隔

根据实际需求调整补跑频率：

- **高频场景**（任务较多，失败率高）：缩短间隔至 10-15 分钟
- **低频场景**（任务较少，失败率低）：延长间隔至 60 分钟
- **生产环境推荐**：保持 30 分钟

```python
self.scheduler.add_job(
    self.retry_failed_jobs,
    trigger='interval',
    minutes=10,  # 调整为 10 分钟
    next_run_time=datetime.now() + timedelta(minutes=1)
)
```

## 相关文档

- [技术设计文档](../docs/superpowers/specs/2026-08-31-scheduler-and-dashboard-design.md)
- [WebSocket 使用文档](../docs/websocket_usage.md)
- [任务执行器文档](../docs/executor_usage.md)
- [PRD 文档](../docs/01_prd.md)

## 常见问题

**Q: 为什么首次执行延迟 1 分钟？**  
A: 避免应用启动时数据库连接尚未稳定，导致补跑失败。

**Q: 可以手动触发补跑吗？**  
A: 目前可以通过重启应用或直接操作数据库实现，未来可添加手动触发 API。

**Q: 补跑任务会影响正在执行的任务吗？**  
A: 不会。补跑只负责重置状态，任务执行器会串行处理所有 `pending` 任务。

**Q: 达到 3 次重试上限的任务怎么处理？**  
A: 任务将永久保持 `failed` 状态，需要人工介入排查原因后手动重置 `retry_count`。

**Q: 调度器支持 cron 表达式吗？**  
A: 当前版本使用固定间隔触发，未来可扩展支持 cron 表达式。
