# 任务调度配置详解

## 概述

系统中有 **4 个独立的定时任务**，每个任务都有自己的触发条件和执行逻辑。这三组配置分别控制不同的任务调度机制。

## 调度器中的 4 个定时任务

### 1. 任务分发 (dispatch_pending_jobs)
**触发配置**: `DISPATCH_INTERVAL_MINUTES`

```bash
# 待处理任务分发间隔（分钟）
DISPATCH_INTERVAL_MINUTES=1
```

**执行逻辑**：
- 每隔 N 分钟扫描一次数据库
- 查询所有 `status='pending'` 的任务
- 按优先级和创建时间排序
- 提交到进程池执行（不超过可用插槽数）
- 更新任务状态为 `processing`

**何时触发**：
- 首次启动后 5 秒执行
- 之后每隔 `DISPATCH_INTERVAL_MINUTES` 分钟执行一次

**作用**：
- 这是任务执行的核心机制
- **如果不配置，pending 任务永远不会被执行**
- 设置为 1 分钟可以快速响应新任务

---

### 2. 失败任务重试 (retry_failed_jobs)
**触发配置**: `RETRY_INTERVAL_MINUTES`

```bash
# 失败任务重试间隔（分钟）
RETRY_INTERVAL_MINUTES=30

# 最大重试次数
MAX_RETRY_COUNT=3

# 每批重试的任务数量
RETRY_BATCH_SIZE=100
```

**执行逻辑**：
1. 检查 pending 任务数量，如果超过 `RETRY_SKIP_IF_PENDING_OVER`，则跳过
2. 查询 `status='failed'` 且 `retry_count < MAX_RETRY_COUNT` 的任务
3. 筛选失败时间超过 `RETRY_MIN_WAIT_MINUTES` 的任务
4. 将状态重置为 `pending`，等待下次分发
5. 最多处理 `RETRY_BATCH_SIZE` 个任务

**何时触发**：
- 首次启动后 1 分钟执行
- 之后每隔 `RETRY_INTERVAL_MINUTES` 分钟执行一次

**作用**：
- 自动重试失败的任务
- 避免手动重新创建任务
- 智能避让：优先处理新任务

---

### 3. 智能重试控制
**相关配置**: `RETRY_MIN_WAIT_MINUTES`, `RETRY_SKIP_IF_PENDING_OVER`

```bash
# 失败后至少等待多久才重试（分钟）
RETRY_MIN_WAIT_MINUTES=60

# 如果 pending 任务超过此数量，跳过失败任务重试
RETRY_SKIP_IF_PENDING_OVER=100
```

**执行逻辑**：
- 这两个配置**不是独立的定时任务**
- 它们是 `retry_failed_jobs` 任务的控制参数

**作用**：
- `RETRY_MIN_WAIT_MINUTES`: 防止失败任务立即重试（给系统缓冲时间）
- `RETRY_SKIP_IF_PENDING_OVER`: 当有大量新任务时，暂停重试，优先处理新任务

**示例场景**：
```
场景：批量导入 1000 个任务

1. 分发任务（每 1 分钟）
   - 0:00 - 分发 3 个任务到进程池
   - 0:01 - 分发 3 个任务
   - ... 持续分发

2. 失败任务重试（每 30 分钟）
   - 0:30 - 检查 pending 任务数 = 950（超过 100）
          → 跳过重试，优先处理新任务
   - 1:00 - 检查 pending 任务数 = 50（未超过 100）
          → 开始重试失败任务（失败时间超过 60 分钟的）
```

---

### 4. 超时任务检测 (check_timeout_jobs)
**触发配置**: `TASK_TIMEOUT_CHECK_ENABLED`, `TASK_TIMEOUT_MINUTES`, `TASK_TIMEOUT_CHECK_INTERVAL_MINUTES`

```bash
# 是否启用任务超时检测
TASK_TIMEOUT_CHECK_ENABLED=true

# 任务超时阈值（分钟）
TASK_TIMEOUT_MINUTES=30

# 超时检测间隔（分钟）
TASK_TIMEOUT_CHECK_INTERVAL_MINUTES=10
```

**执行逻辑**：
1. 查询所有 `status='processing'` 的任务
2. 检查 `updated_at` 是否超过 `TASK_TIMEOUT_MINUTES` 分钟
3. 将超时任务标记为 `failed`，设置错误信息
4. 递增 `retry_count`
5. 这些任务会被下次 `retry_failed_jobs` 重新执行

**何时触发**：
- 首次启动后 2 分钟执行
- 之后每隔 `TASK_TIMEOUT_CHECK_INTERVAL_MINUTES` 分钟执行一次
- 如果 `TASK_TIMEOUT_CHECK_ENABLED=false`，则不启动此任务

**作用**：
- 检测卡死的任务（如浏览器崩溃、网络断开）
- 自动标记为失败，触发重试机制
- 防止任务长时间占用进程池

---

## 三组配置的关系

### 配置组 1: 任务调度配置
```bash
DISPATCH_INTERVAL_MINUTES=1      # 控制任务分发频率
RETRY_INTERVAL_MINUTES=30        # 控制失败任务重试频率
MAX_RETRY_COUNT=3                # 失败任务最多重试 3 次
RETRY_BATCH_SIZE=100             # 每次重试最多处理 100 个任务
```

**控制的任务**：
- ✅ `dispatch_pending_jobs` - 分发待处理任务
- ✅ `retry_failed_jobs` - 重试失败任务

---

### 配置组 2: 智能重试配置
```bash
RETRY_MIN_WAIT_MINUTES=60        # 失败后至少等待 60 分钟才重试
RETRY_SKIP_IF_PENDING_OVER=100   # pending 任务超过 100 则跳过重试
```

**控制的任务**：
- ✅ `retry_failed_jobs` - 作为其执行条件

**注意**：这不是独立的定时任务，而是 `retry_failed_jobs` 的控制参数。

---

### 配置组 3: 任务超时检测配置
```bash
TASK_TIMEOUT_CHECK_ENABLED=true  # 是否启用超时检测
TASK_TIMEOUT_MINUTES=30          # 超时阈值
TASK_TIMEOUT_CHECK_INTERVAL_MINUTES=10  # 检测间隔
```

**控制的任务**：
- ✅ `check_timeout_jobs` - 检测并处理超时任务

---

## 完整的任务生命周期

```
1. 创建任务
   ↓
2. status = 'pending'
   ↓
3. dispatch_pending_jobs (每 1 分钟)
   - 将任务提交到进程池
   - status = 'processing'
   ↓
4a. 正常完成
    - status = 'success'
    ↓
    结束

4b. 执行失败
    - status = 'failed'
    - retry_count += 1
    ↓
5. retry_failed_jobs (每 30 分钟)
   - 检查：失败时间超过 60 分钟？
   - 检查：pending 任务数 < 100？
   - 检查：retry_count < 3？
   - 如果都满足：status = 'pending'
   ↓
   回到步骤 3

4c. 执行超时（卡死）
    - status 仍为 'processing'
    ↓
6. check_timeout_jobs (每 10 分钟)
   - 检查：updated_at 超过 30 分钟？
   - 如果是：status = 'failed', retry_count += 1
   ↓
   回到步骤 5
```

---

## 配置是否都生效？

### ✅ 都生效，但作用不同

| 配置组 | 独立定时任务 | 作用 |
|--------|-------------|------|
| **任务调度配置** | ✅ 是 | 控制 2 个定时任务的触发频率 |
| **智能重试配置** | ❌ 否 | 作为 `retry_failed_jobs` 的执行条件 |
| **超时检测配置** | ✅ 是 | 控制 1 个定时任务的触发频率和检测阈值 |

---

## 推荐配置

### 快速响应场景（推荐）
```bash
# 任务调度：快速分发和重试
DISPATCH_INTERVAL_MINUTES=1      # 1分钟分发一次
RETRY_INTERVAL_MINUTES=30        # 30分钟重试一次
MAX_RETRY_COUNT=3
RETRY_BATCH_SIZE=100

# 智能重试：适中的等待时间
RETRY_MIN_WAIT_MINUTES=60        # 失败后等待1小时再重试
RETRY_SKIP_IF_PENDING_OVER=100   # pending超过100则跳过重试

# 超时检测：30分钟超时
TASK_TIMEOUT_CHECK_ENABLED=true
TASK_TIMEOUT_MINUTES=30          # 30分钟超时
TASK_TIMEOUT_CHECK_INTERVAL_MINUTES=10  # 10分钟检测一次
```

### 批量处理场景
```bash
# 任务调度：降低检查频率
DISPATCH_INTERVAL_MINUTES=5      # 5分钟分发一次
RETRY_INTERVAL_MINUTES=60        # 1小时重试一次
MAX_RETRY_COUNT=3
RETRY_BATCH_SIZE=200

# 智能重试：更长的等待时间
RETRY_MIN_WAIT_MINUTES=120       # 失败后等待2小时再重试
RETRY_SKIP_IF_PENDING_OVER=500   # pending超过500则跳过重试

# 超时检测：60分钟超时
TASK_TIMEOUT_CHECK_ENABLED=true
TASK_TIMEOUT_MINUTES=60          # 60分钟超时
TASK_TIMEOUT_CHECK_INTERVAL_MINUTES=15  # 15分钟检测一次
```

### 高频场景
```bash
# 任务调度：高频分发
DISPATCH_INTERVAL_MINUTES=1      # 1分钟分发一次
RETRY_INTERVAL_MINUTES=15        # 15分钟重试一次
MAX_RETRY_COUNT=5                # 最多重试5次
RETRY_BATCH_SIZE=50

# 智能重试：短等待时间
RETRY_MIN_WAIT_MINUTES=30        # 失败后等待30分钟再重试
RETRY_SKIP_IF_PENDING_OVER=50    # pending超过50则跳过重试

# 超时检测：20分钟超时
TASK_TIMEOUT_CHECK_ENABLED=true
TASK_TIMEOUT_MINUTES=20          # 20分钟超时
TASK_TIMEOUT_CHECK_INTERVAL_MINUTES=5   # 5分钟检测一次
```

---

## 常见问题

### Q1: 为什么任务一直是 pending 状态？

**原因**：`dispatch_pending_jobs` 没有运行或进程池已满。

**检查**：
1. 确认 `DISPATCH_INTERVAL_MINUTES` 配置正确
2. 检查日志：`开始扫描待处理任务`
3. 检查进程池状态：`进程池已满`

### Q2: 失败任务为什么不重试？

**可能原因**：
1. `retry_count >= MAX_RETRY_COUNT`（重试次数用完）
2. 失败时间未超过 `RETRY_MIN_WAIT_MINUTES`（还没到重试时间）
3. pending 任务数超过 `RETRY_SKIP_IF_PENDING_OVER`（优先处理新任务）

### Q3: 任务超时后会怎样？

**流程**：
1. `check_timeout_jobs` 将任务标记为 `failed`
2. 递增 `retry_count`
3. `retry_failed_jobs` 会在下次检查时重新执行（如果满足条件）

### Q4: 如何禁用超时检测？

```bash
TASK_TIMEOUT_CHECK_ENABLED=false
```

### Q5: 三组配置可以独立修改吗？

✅ 可以！它们互不干扰：
- 修改 `DISPATCH_INTERVAL_MINUTES` 只影响任务分发频率
- 修改 `RETRY_INTERVAL_MINUTES` 只影响失败任务重试频率
- 修改 `TASK_TIMEOUT_MINUTES` 只影响超时判定阈值

---

## 监控建议

查看调度器日志：
```bash
# 任务分发
grep "开始扫描待处理任务" logs/app.log

# 失败任务重试
grep "开始扫描失败任务" logs/app.log

# 超时检测
grep "开始检测超时任务" logs/app.log
```

查看任务状态分布：
```sql
SELECT status, COUNT(*) as count 
FROM job_queue 
GROUP BY status;
```
