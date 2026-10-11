# 智能重试机制优化说明

## 问题场景

### 冲突场景描述

```
场景：大批量任务 + 严格限流 + 自动重试

1. 有 1000 个任务待执行（pending）
2. 限流设置：每 2 分钟 2 个任务
3. 理论耗时：1000 ÷ 2 × 2 = 1000 分钟（16.7 小时）
4. 重试间隔：30 分钟

问题：
- 30分钟后，重试补偿开始工作
- 但此时 pending 队列还有大量任务未执行
- 重试任务和 pending 任务竞争，导致：
  ✗ pending 任务执行更慢
  ✗ 重试任务也得不到及时处理
  ✗ 整体效率降低
```

## 解决方案：智能重试机制

### 核心思路

**优先处理新任务，智能延迟重试**

### 三重检查机制

#### 检查1：Pending 队列压力
```python
if pending_count > RETRY_SKIP_IF_PENDING_OVER:
    # 跳过重试，优先处理 pending 任务
    logger.warning(f"当前有 {pending_count} 个 pending 任务，跳过重试")
    return
```

#### 检查2：限流压力
```python
if rate_limit_utilization > 80%:
    # 限流使用率过高，跳过重试
    logger.warning(f"限流使用率 {utilization}%，跳过重试")
    return
```

#### 检查3：最小等待时间
```python
# 只重试失败时间超过最小等待时间的任务
WHERE updated_at < (now - RETRY_MIN_WAIT_MINUTES)
```

## 新增配置参数

### 环境变量配置

在 `.env` 文件中添加：

```bash
# ==================== 智能重试配置 ====================

# 失败后至少等待多久才重试（分钟）
RETRY_MIN_WAIT_MINUTES=60

# 如果 pending 任务超过此数量，跳过重试
RETRY_SKIP_IF_PENDING_OVER=100

# 重试时是否遵守限流
RETRY_RESPECT_RATE_LIMIT=true
```

### 参数说明

| 参数 | 默认值 | 说明 | 推荐值 |
|------|--------|------|--------|
| `RETRY_MIN_WAIT_MINUTES` | 60 | 失败后最少等待时间 | 60-180 分钟 |
| `RETRY_SKIP_IF_PENDING_OVER` | 100 | pending 任务阈值 | 50-200 |
| `RETRY_RESPECT_RATE_LIMIT` | true | 是否考虑限流压力 | true |

## 工作流程

### 传统重试流程（优化前）

```
每 30 分钟执行一次
  ↓
扫描所有 failed 任务
  ↓
重置为 pending
  ↓
立即与其他 pending 任务竞争
  ↓
问题：可能加重队列压力
```

### 智能重试流程（优化后）

```
每 30 分钟执行一次
  ↓
检查1: pending 数量 > 100？
  ├─ YES → 跳过重试（记录日志）
  └─ NO  → 继续
  ↓
检查2: 限流使用率 > 80%？
  ├─ YES → 跳过重试（记录日志）
  └─ NO  → 继续
  ↓
检查3: 扫描失败时间 > 60分钟的任务
  ↓
重置为 pending
  ↓
优势：避免在系统繁忙时加重压力
```

## 配置场景

### 场景1：大批量任务（推荐配置）

```bash
# 严格限流
RATE_LIMIT_ENABLED=true
RATE_LIMIT_WINDOW_MINUTES=2
RATE_LIMIT_MAX_TASKS=2

# 智能重试
RETRY_MIN_WAIT_MINUTES=120      # 失败后等待2小时再重试
RETRY_SKIP_IF_PENDING_OVER=50   # pending > 50 时跳过重试
RETRY_RESPECT_RATE_LIMIT=true   # 遵守限流

# 重试扫描间隔
RETRY_INTERVAL_MINUTES=60       # 每小时扫描一次
```

**效果**：
- 1000个任务慢慢执行（约16小时）
- 期间失败任务不会立即重试
- 等大部分任务执行完后才重试失败任务
- 避免重试和新任务竞争

### 场景2：正常任务量

```bash
# 中等限流
RATE_LIMIT_ENABLED=true
RATE_LIMIT_WINDOW_MINUTES=60
RATE_LIMIT_MAX_TASKS=100

# 标准重试
RETRY_MIN_WAIT_MINUTES=60       # 失败后等待1小时
RETRY_SKIP_IF_PENDING_OVER=100  # pending > 100 时跳过
RETRY_RESPECT_RATE_LIMIT=true

# 重试扫描间隔
RETRY_INTERVAL_MINUTES=30       # 每30分钟扫描一次
```

**效果**：
- 任务可以较快执行完（约1小时）
- 失败任务会在1小时后重试
- 队列压力不大

### 场景3：紧急模式（关闭智能重试）

```bash
# 不限流
RATE_LIMIT_ENABLED=false

# 激进重试
RETRY_MIN_WAIT_MINUTES=10       # 失败后10分钟就重试
RETRY_SKIP_IF_PENDING_OVER=1000 # 阈值设得很高
RETRY_RESPECT_RATE_LIMIT=false  # 不考虑限流

# 频繁扫描
RETRY_INTERVAL_MINUTES=10       # 每10分钟扫描一次
```

**效果**：
- 快速重试失败任务
- 不考虑队列压力
- 适用于紧急修复后的快速恢复

## 监控和日志

### 关键日志信息

#### 跳过重试（pending 过多）
```
WARNING - 当前有 150 个 pending 任务（超过阈值 100），
          跳过失败任务重试，优先处理现有任务
```

#### 跳过重试（限流压力大）
```
WARNING - 限流使用率过高 (85.0%)，
          跳过失败任务重试，避免加重限流压力
```

#### 正常重试
```
INFO - 发现 10 个失败任务（失败时间超过 60 分钟），开始重置状态
INFO - 任务 #123 已重置为 pending (重试次数: 1/3, 失败时间: 2026-10-11 14:00:00)
INFO - 成功重置 10 个失败任务
```

### 监控指标

创建监控脚本：

```python
# monitor_retry.py
import asyncio
from app.core.database import get_session
from app.models.job import JobQueue, JobStatus
from sqlalchemy import select, func

async def monitor():
    async with get_session() as session:
        # 统计各状态任务数
        stmt = select(
            JobQueue.status,
            func.count(JobQueue.id)
        ).group_by(JobQueue.status)
        
        result = await session.execute(stmt)
        stats = dict(result.all())
        
        pending = stats.get(JobStatus.PENDING, 0)
        processing = stats.get(JobStatus.PROCESSING, 0)
        failed = stats.get(JobStatus.FAILED, 0)
        success = stats.get(JobStatus.SUCCESS, 0)
        
        print(f"Pending: {pending}, Processing: {processing}, Failed: {failed}, Success: {success}")
        
        # 判断是否应该重试
        if pending > 100:
            print("⚠️ Pending 过多，重试会被跳过")
        else:
            print("✓ 可以正常重试")

if __name__ == "__main__":
    asyncio.run(monitor())
```

## 实际案例

### 案例1：1000个任务，严格限流

**配置**：
```bash
RATE_LIMIT_WINDOW_MINUTES=2
RATE_LIMIT_MAX_TASKS=2
RETRY_MIN_WAIT_MINUTES=120
RETRY_SKIP_IF_PENDING_OVER=50
```

**时间线**：
```
00:00 - 提交1000个任务
00:00 - 开始执行（每2分钟2个）
00:30 - 重试扫描：pending=970，跳过重试 ✓
01:00 - 重试扫描：pending=940，跳过重试 ✓
02:00 - 重试扫描：pending=880，跳过重试 ✓
...
15:00 - 重试扫描：pending=20，开始重试失败任务 ✓
16:00 - 所有任务完成
```

### 案例2：100个任务，正常限流

**配置**：
```bash
RATE_LIMIT_WINDOW_MINUTES=60
RATE_LIMIT_MAX_TASKS=100
RETRY_MIN_WAIT_MINUTES=60
RETRY_SKIP_IF_PENDING_OVER=100
```

**时间线**：
```
00:00 - 提交100个任务
00:00 - 开始执行（每小时100个）
00:30 - 重试扫描：pending=50，允许重试 ✓
01:00 - 所有任务完成
01:30 - 重试扫描：处理失败任务 ✓
```

## 调优建议

### 如何设置 RETRY_MIN_WAIT_MINUTES

**公式**：
```
RETRY_MIN_WAIT_MINUTES = 预计全量任务耗时 × 0.8

示例：
- 1000个任务，每2分钟2个 → 耗时1000分钟
- RETRY_MIN_WAIT_MINUTES = 1000 × 0.8 = 800 分钟（13小时）
```

### 如何设置 RETRY_SKIP_IF_PENDING_OVER

**公式**：
```
RETRY_SKIP_IF_PENDING_OVER = 总任务数 × 0.1

示例：
- 1000个任务 → RETRY_SKIP_IF_PENDING_OVER = 100
- 100个任务 → RETRY_SKIP_IF_PENDING_OVER = 10
```

### 动态调整策略

根据实际情况调整：

```python
# 如果经常看到 "跳过重试" 日志
→ 说明配置合理，保持现状

# 如果从不看到 "跳过重试" 日志
→ 阈值可能设得太高，可以降低：
  RETRY_SKIP_IF_PENDING_OVER=50  # 从100降到50

# 如果重试太频繁影响新任务
→ 增加最小等待时间：
  RETRY_MIN_WAIT_MINUTES=180  # 从60增加到180
```

## 对比总结

| 维度 | 优化前 | 优化后 |
|------|--------|--------|
| **重试时机** | 固定30分钟 | 考虑队列压力 |
| **队列竞争** | 严重 | 避免 |
| **限流压力** | 不考虑 | 智能检测 |
| **执行效率** | 低（相互竞争） | 高（优先新任务） |
| **可配置性** | 低 | 高（3个新参数） |
| **适用场景** | 小批量任务 | 大批量+严格限流 |

## 相关文档

- **限流配置指南**: `docs/rate_limit_guide.md`
- **环境变量配置**: `docs/env_config_examples.md`
- **项目文档**: `CLAUDE.md`
