# 限流功能实现总结

## 功能概述

为浏览器自动化平台添加了速率限流功能，支持控制 **X 分钟内最多执行 X 个任务**，防止对目标网站造成过大压力，避免被封禁。

## 实现内容

### 1. 新增文件

| 文件路径 | 说明 |
|---------|------|
| `app/services/rate_limiter.py` | 限流管理器核心实现 |
| `app/api/rate_limit.py` | 限流管理 API 接口 |
| `docs/rate_limit_guide.md` | 限流配置详细指南 |
| `docs/env_config_examples.md` | 环境变量配置示例 |
| `docs/rate_limit_implementation.md` | 本文档 |

### 2. 修改文件

| 文件路径 | 修改内容 |
|---------|----------|
| `app/core/config.py` | 新增 4 个限流相关环境变量 |
| `app/services/scheduler.py` | 集成限流检查逻辑 |
| `app/main.py` | 注册限流 API 路由 |
| `CLAUDE.md` | 更新核心特性和配置说明 |

## 核心功能

### 1. 限流管理器（RateLimiter）

**位置**：`app/services/rate_limiter.py`

**核心方法**：
- `can_execute(config_id)` - 检查是否可以执行任务
- `record_execution(config_id)` - 记录任务执行
- `get_wait_time(config_id)` - 获取需要等待的时间
- `get_status(config_id)` - 获取限流状态
- `reset(config_id)` - 重置限流计数器

**特性**：
- ✅ 滑动时间窗口算法
- ✅ 支持全局限流和按配置限流两种模式
- ✅ 异步实现，线程安全
- ✅ 自动清理过期时间戳

### 2. 环境变量配置

在 `app/core/config.py` 中新增：

```python
# 是否启用限流
RATE_LIMIT_ENABLED: bool = False

# 时间窗口（分钟）
RATE_LIMIT_WINDOW_MINUTES: int = 60

# 时间窗口内最多执行的任务数
RATE_LIMIT_MAX_TASKS: int = 100

# 是否按配置ID分别限流
RATE_LIMIT_PER_CONFIG: bool = False
```

### 3. 调度器集成

在 `app/services/scheduler.py` 的 `dispatch_pending_jobs()` 方法中：

```python
# 检查限流
can_execute = await rate_limiter.can_execute(job.config_id)
if not can_execute:
    wait_time = await rate_limiter.get_wait_time(job.config_id)
    logger.info(f"任务 #{job.id} 因限流跳过，需等待 {wait_time} 秒")
    continue

# 记录限流执行
await rate_limiter.record_execution(job.config_id)

# 提交任务到进程池
await self.pool_manager.submit_job(job.id)
```

### 4. API 接口

**基础路径**：`/api/rate-limit`

| 接口 | 方法 | 说明 |
|------|------|------|
| `/status` | GET | 查询限流状态 |
| `/wait-time` | GET | 查询需要等待的时间 |
| `/config` | GET | 查询限流配置 |
| `/reset` | POST | 重置限流计数器 |

**使用示例**：
```bash
# 查询限流状态
curl http://localhost:8000/api/rate-limit/status

# 查询特定配置的状态
curl http://localhost:8000/api/rate-limit/status?config_id=44

# 重置限流计数器
curl -X POST http://localhost:8000/api/rate-limit/reset
```

## 工作原理

### 滑动时间窗口算法

```
当前时间：15:30
时间窗口：60 分钟
窗口范围：[14:30, 15:30]

任务执行时间戳队列：
[14:25, 14:40, 14:55, 15:10, 15:20]
       ↓
清理过期（< 14:30）：
[14:40, 14:55, 15:10, 15:20]
       ↓
统计窗口内任务数：4
       ↓
判断：4 < 100（限流上限）
       ↓
结果：可以执行
```

### 执行流程

```
任务分发循环
  ↓
查询 pending 任务
  ↓
检查限流：can_execute(config_id)?
  ├─ YES → 记录执行 → 提交到进程池
  └─ NO  → 跳过任务 → 记录等待时间
  ↓
继续下一个任务
```

## 配置示例

### 示例1：严格限流（防止被封）
```bash
RATE_LIMIT_ENABLED=true
RATE_LIMIT_WINDOW_MINUTES=60
RATE_LIMIT_MAX_TASKS=50
RATE_LIMIT_PER_CONFIG=false
```
**含义**：全局限流，每小时最多执行 50 个任务

### 示例2：按配置独立限流
```bash
RATE_LIMIT_ENABLED=true
RATE_LIMIT_WINDOW_MINUTES=60
RATE_LIMIT_MAX_TASKS=100
RATE_LIMIT_PER_CONFIG=true
```
**含义**：每个配置独立计数，每个配置每小时最多执行 100 个任务

### 示例3：短时间窗口
```bash
RATE_LIMIT_ENABLED=true
RATE_LIMIT_WINDOW_MINUTES=10
RATE_LIMIT_MAX_TASKS=20
RATE_LIMIT_PER_CONFIG=false
```
**含义**：全局限流，每 10 分钟最多执行 20 个任务（相当于每小时 120 个）

## 技术亮点

### 1. 高性能
- 使用 `deque` 双端队列，O(1) 时间复杂度的插入和删除
- 自动清理过期时间戳，避免内存泄漏
- 异步实现，不阻塞主线程

### 2. 灵活性
- 支持全局限流和按配置限流两种模式
- 可动态调整时间窗口和任务数
- 支持运行时重置计数器

### 3. 可观测性
- 提供详细的限流状态查询接口
- 日志记录每次限流决策
- 计算等待时间，便于调度优化

### 4. 健壮性
- 使用 `asyncio.Lock` 确保并发安全
- 异常处理完善，不影响主流程
- 向后兼容，默认不启用限流

## 与其他配置的协同

### 限流 + 并发控制

```bash
# 并发控制
MAX_WORKERS=3  # 同时执行3个任务

# 限流控制
RATE_LIMIT_ENABLED=true
RATE_LIMIT_WINDOW_MINUTES=60
RATE_LIMIT_MAX_TASKS=100  # 每小时100个任务
```

**效果**：
- 短期：受并发数限制（3个同时执行）
- 长期：受限流限制（每小时100个）

**理论吞吐量**：
- 如果单任务耗时 1 分钟：3个/分钟 × 60分钟 = 180个/小时
- 限流限制：100个/小时
- **实际吞吐量**：min(180, 100) = 100个/小时

### 限流 + 重试机制

```bash
# 重试配置
RETRY_INTERVAL_MINUTES=30
MAX_RETRY_COUNT=3

# 限流配置
RATE_LIMIT_ENABLED=true
RATE_LIMIT_WINDOW_MINUTES=60
RATE_LIMIT_MAX_TASKS=100
```

**协同工作**：
1. 任务执行失败 → 标记为 failed
2. 30 分钟后重试 → 检查限流
3. 如果达到限流上限 → 跳过重试，下次再试
4. 如果未达到限流上限 → 执行重试

## 监控和调优

### 1. 查看限流状态
```bash
curl http://localhost:8000/api/rate-limit/status
```

**响应示例**：
```json
{
  "success": true,
  "data": {
    "enabled": true,
    "window_minutes": 60,
    "max_tasks": 100,
    "current_count": 75,
    "remaining": 25,
    "utilization": "75/100 (75.0%)"
  }
}
```

### 2. 调优建议

**利用率 < 50%**：
- 限流过于宽松，可以提高任务数或缩短窗口

**利用率 50-80%**：
- 合理范围，保持当前配置

**利用率 > 80%**：
- 接近限流上限，可能导致任务延迟
- 建议提高 `RATE_LIMIT_MAX_TASKS` 或延长 `RATE_LIMIT_WINDOW_MINUTES`

**利用率 = 100%**：
- 达到限流上限，新任务会被跳过
- 必须调整配置或等待窗口滑动

### 3. 日志监控

关键日志：
```
INFO - 限流管理器初始化: enabled=True, window=60分钟, max_tasks=100, per_config=False
INFO - 任务 #123 (config_id=44) 因限流跳过，需等待 1800 秒
WARNING - 达到全局限流上限: 100/100 任务在 60 分钟内
DEBUG - 记录任务执行: config_id=44, 当前窗口内任务数=76
```

## 测试验证

### 1. 功能测试
```python
# 创建 150 个任务
for i in range(150):
    job = JobQueue(config_id=44, query_params={"keyword": f"test{i}"})
    session.add(job)
session.commit()

# 观察：
# - 前100个任务正常执行
# - 后50个任务被限流跳过
# - 60分钟后，窗口滑动，后50个任务开始执行
```

### 2. API 测试
```bash
# 查询状态
curl http://localhost:8000/api/rate-limit/status

# 查询等待时间
curl http://localhost:8000/api/rate-limit/wait-time

# 重置计数器
curl -X POST http://localhost:8000/api/rate-limit/reset

# 再次查询状态（应该显示 current_count=0）
curl http://localhost:8000/api/rate-limit/status
```

### 3. 压力测试
```bash
# 设置严格限流
RATE_LIMIT_WINDOW_MINUTES=10
RATE_LIMIT_MAX_TASKS=20

# 提交100个任务，观察执行情况
# 预期结果：每10分钟执行20个任务
```

## 未来扩展

### 1. 数据库级别的配置限流
在 `crawler_configs` 表添加字段：
```sql
ALTER TABLE crawler_configs ADD COLUMN rate_limit_max_tasks INT;
ALTER TABLE crawler_configs ADD COLUMN rate_limit_window_minutes INT;
```

### 2. 动态限流
根据目标网站响应自动调整：
- 收到 429 错误 → 降低限流
- 长期正常 → 逐步提高限流

### 3. 智能限流
机器学习预测最优限流参数

### 4. 分布式限流
使用 Redis 实现跨实例的限流控制

## 相关文档

- **详细配置指南**：`docs/rate_limit_guide.md`
- **配置示例**：`docs/env_config_examples.md`
- **基础配置说明**：`docs/env_config_update.md`
- **配置迁移总结**：`docs/config_migration_summary.md`
- **项目文档**：`CLAUDE.md`

## 总结

✅ **核心功能**：支持 X 分钟内最多执行 X 个任务的限流控制  
✅ **配置灵活**：通过环境变量轻松调整限流参数  
✅ **模式多样**：支持全局限流和按配置限流  
✅ **监控完善**：提供 API 查询限流状态和等待时间  
✅ **性能优化**：滑动窗口算法，O(1) 时间复杂度  
✅ **向后兼容**：默认不启用，不影响现有功能  
✅ **文档齐全**：提供详细的配置指南和使用示例
