# 失败重试配置最佳实践

## 当前配置分析

```bash
# 失败任务重试间隔（分钟）
RETRY_INTERVAL_MINUTES=30

# 最大重试次数
MAX_RETRY_COUNT=3

# 每批重试的任务数量
RETRY_BATCH_SIZE=100

# 失败后至少等待多久才重试（分钟）
RETRY_MIN_WAIT_MINUTES=60

# 如果 pending 任务超过此数量，跳过失败任务重试
RETRY_SKIP_IF_PENDING_OVER=100
```

## 配置原则

### 1. 重试时机的选择

**问题**: `RETRY_INTERVAL_MINUTES=30` 但 `RETRY_MIN_WAIT_MINUTES=60`，会发生什么？

**答案**: 
- 重试任务每 30 分钟执行一次
- 但只会处理失败时间超过 60 分钟的任务
- **结果**: 前两次检查（0分钟、30分钟）都会跳过，第三次检查（60分钟）才开始重试

**建议关系**:
```
RETRY_INTERVAL_MINUTES ≈ RETRY_MIN_WAIT_MINUTES / 2
```

**理由**: 
- 在最小等待时间到达后，能及时发现并重试
- 避免频繁检查浪费资源
- 给失败任务一个合理的缓冲期

---

### 2. 重试次数的选择

**问题**: `MAX_RETRY_COUNT=3` 是否合理？

**分析**:
- 太少（1-2次）: 临时性问题（网络抖动）可能导致任务永久失败
- 太多（5+次）: 持续性问题（目标站点封禁）会浪费大量资源
- **推荐**: 3-5 次

**不同场景**:
- **网络不稳定**: 5 次
- **目标站点严格**: 3 次
- **内部系统**: 5-10 次

---

### 3. 批量处理大小

**问题**: `RETRY_BATCH_SIZE=100` 是否合理？

**分析**:
```
假设场景:
- 1000个任务，10%失败率 = 100个failed
- 每次重试100个，会一次性全部重试
- 如果这些任务再次失败，会瞬间增加100个failed任务
```

**建议**:
```
RETRY_BATCH_SIZE = 预期失败任务数 × 0.3 ~ 0.5
```

**理由**:
- 分批处理，降低风险
- 避免一次性冲击进程池
- 给系统和目标站点缓冲时间

**示例**:
- 小规模（<100任务）: `RETRY_BATCH_SIZE=20-30`
- 中等规模（100-1000任务）: `RETRY_BATCH_SIZE=50-100`
- 大规模（1000+任务）: `RETRY_BATCH_SIZE=100-200`

---

### 4. 智能避让阈值

**问题**: `RETRY_SKIP_IF_PENDING_OVER=100` 是否合理？

**分析**:
```
场景1: 批量导入1000个任务
- pending任务数一直>100
- 失败任务永远不会被重试
- 问题: 新任务处理完后，失败任务还在等待

场景2: 日常使用，pending<10
- 失败任务可以及时重试
- 问题: 如果突然批量导入，重试会暂停
```

**建议关系**:
```
RETRY_SKIP_IF_PENDING_OVER = MAX_WORKERS × RETRY_INTERVAL_MINUTES ÷ DISPATCH_INTERVAL_MINUTES

解释:
- MAX_WORKERS=3: 每分钟最多处理3个任务
- RETRY_INTERVAL_MINUTES=30: 重试间隔30分钟
- DISPATCH_INTERVAL_MINUTES=1: 分发间隔1分钟
- 计算: 3 × 30 ÷ 1 = 90

含义: 如果pending任务超过90个，说明至少需要30分钟才能处理完
```

**推荐值**:
- **保守策略**: `MAX_WORKERS × 20 ~ 30` (约20-30分钟的任务量)
- **激进策略**: `MAX_WORKERS × 10 ~ 15` (约10-15分钟的任务量)
- **平衡策略**: `MAX_WORKERS × 30 ~ 60` (约30-60分钟的任务量)

---

## 推荐配置方案

### 方案1: 快速重试（激进）

**适用场景**: 
- 网络不稳定
- 目标站点限流不严格
- 需要快速完成任务

```bash
# 15分钟检查一次，失败30分钟后重试
RETRY_INTERVAL_MINUTES=15
RETRY_MIN_WAIT_MINUTES=30

# 多给几次机会
MAX_RETRY_COUNT=5

# 小批量，降低风险
RETRY_BATCH_SIZE=30

# 激进避让：10分钟任务量
RETRY_SKIP_IF_PENDING_OVER=30  # 假设 MAX_WORKERS=3
```

**特点**:
- ✅ 快速响应失败任务
- ✅ 多次重试机会
- ⚠️ 可能增加目标站点压力
- ⚠️ 重试任务可能与新任务竞争

---

### 方案2: 平衡重试（推荐）⭐

**适用场景**:
- 大多数场景
- 目标站点限流适中
- 平衡速度和稳定性

```bash
# 30分钟检查一次，失败60分钟后重试
RETRY_INTERVAL_MINUTES=30
RETRY_MIN_WAIT_MINUTES=60

# 标准重试次数
MAX_RETRY_COUNT=3

# 中等批量
RETRY_BATCH_SIZE=50

# 平衡避让：30-60分钟任务量
RETRY_SKIP_IF_PENDING_OVER=90  # 假设 MAX_WORKERS=3
```

**特点**:
- ✅ 给失败任务足够的缓冲时间
- ✅ 不会过度消耗资源
- ✅ 新任务优先级合理
- ✅ 适合大多数场景

---

### 方案3: 保守重试（稳健）

**适用场景**:
- 目标站点限流严格（如政府网站）
- 任务不紧急
- 避免被封禁

```bash
# 60分钟检查一次，失败120分钟后重试
RETRY_INTERVAL_MINUTES=60
RETRY_MIN_WAIT_MINUTES=120

# 保守重试次数
MAX_RETRY_COUNT=3

# 小批量
RETRY_BATCH_SIZE=20

# 保守避让：60-90分钟任务量
RETRY_SKIP_IF_PENDING_OVER=180  # 假设 MAX_WORKERS=3
```

**特点**:
- ✅ 给目标站点充足的恢复时间
- ✅ 降低被封禁风险
- ✅ 新任务绝对优先
- ⚠️ 失败任务重试较慢

---

### 方案4: 大批量场景

**适用场景**:
- 一次性导入1000+任务
- 预期失败率5-10%
- 需要稳定处理

```bash
# 60分钟检查一次，失败120分钟后重试
RETRY_INTERVAL_MINUTES=60
RETRY_MIN_WAIT_MINUTES=120

# 标准重试次数
MAX_RETRY_COUNT=3

# 大批量
RETRY_BATCH_SIZE=150

# 高阈值避让：优先处理新任务
RETRY_SKIP_IF_PENDING_OVER=300  # 假设 MAX_WORKERS=3
```

**特点**:
- ✅ 优先完成所有新任务
- ✅ 失败任务集中处理
- ✅ 避免重试任务干扰新任务
- ⚠️ 失败任务等待时间长

---

## 配置关系公式

### 1. 重试间隔 vs 最小等待时间

```
RETRY_MIN_WAIT_MINUTES ≈ RETRY_INTERVAL_MINUTES × 2
```

**示例**:
- 检查间隔 30 分钟 → 最小等待 60 分钟
- 检查间隔 15 分钟 → 最小等待 30 分钟
- 检查间隔 60 分钟 → 最小等待 120 分钟

### 2. 批量大小 vs 预期失败数

```
RETRY_BATCH_SIZE = 总任务数 × 预期失败率 × 0.5
```

**示例**:
- 1000任务，10%失败率 → RETRY_BATCH_SIZE ≈ 50
- 500任务，5%失败率 → RETRY_BATCH_SIZE ≈ 12-15
- 100任务，20%失败率 → RETRY_BATCH_SIZE ≈ 10

### 3. 避让阈值 vs 处理能力

```
RETRY_SKIP_IF_PENDING_OVER = MAX_WORKERS × 目标处理时间(分钟) ÷ DISPATCH_INTERVAL_MINUTES
```

**示例**:
- 3工作进程，希望30分钟内处理完 → 3 × 30 ÷ 1 = 90
- 5工作进程，希望60分钟内处理完 → 5 × 60 ÷ 1 = 300
- 3工作进程，希望15分钟内处理完 → 3 × 15 ÷ 1 = 45

---

## 常见问题

### Q1: 为什么 RETRY_MIN_WAIT_MINUTES > RETRY_INTERVAL_MINUTES？

**答**: 这是正常的！

- `RETRY_INTERVAL_MINUTES`: 多久检查一次
- `RETRY_MIN_WAIT_MINUTES`: 失败后至少等待多久

**示例**:
```
0:00 - 任务失败
0:30 - 重试任务执行，检查发现失败时间才30分钟（<60），跳过
1:00 - 重试任务执行，检查发现失败时间60分钟（=60），开始重试
```

### Q2: 如何判断配置是否合理？

**监控指标**:
1. 失败任务重试成功率
2. pending 任务平均等待时间
3. 重试任务被跳过的次数

**查询SQL**:
```sql
-- 失败任务统计
SELECT 
    retry_count,
    COUNT(*) as count
FROM job_queue 
WHERE status = 'failed'
GROUP BY retry_count;

-- pending 任务数量
SELECT COUNT(*) FROM job_queue WHERE status = 'pending';

-- 超时失败的任务（被 check_timeout_jobs 标记的）
SELECT COUNT(*) FROM job_queue 
WHERE status = 'failed' 
  AND error_msg LIKE '%超时%';
```

### Q3: 配置冲突怎么办？

**场景**: `RETRY_SKIP_IF_PENDING_OVER=100` 但批量导入1000个任务

**解决方案**:
1. **临时调整**: 批量导入前，提高阈值
   ```bash
   RETRY_SKIP_IF_PENDING_OVER=500
   ```

2. **分批导入**: 每次导入200个，分5批
   ```bash
   # 每批导入后等待处理完成
   python scripts/batch_import.py --limit 200
   ```

3. **优先级调整**: 给重试任务更高优先级（代码修改）

---

## 实际案例

### 案例1: 国家医保局网站采集

**特点**:
- 政府网站，限流严格
- 任务不紧急
- 避免被封禁

**推荐配置**:
```bash
RETRY_INTERVAL_MINUTES=60
RETRY_MIN_WAIT_MINUTES=120
MAX_RETRY_COUNT=3
RETRY_BATCH_SIZE=20
RETRY_SKIP_IF_PENDING_OVER=180
```

### 案例2: 电商平台数据采集

**特点**:
- 限流适中
- 需要快速完成
- 网络波动

**推荐配置**:
```bash
RETRY_INTERVAL_MINUTES=30
RETRY_MIN_WAIT_MINUTES=60
MAX_RETRY_COUNT=5
RETRY_BATCH_SIZE=50
RETRY_SKIP_IF_PENDING_OVER=90
```

### 案例3: 内部系统采集

**特点**:
- 无限流
- 快速响应
- 偶尔故障

**推荐配置**:
```bash
RETRY_INTERVAL_MINUTES=15
RETRY_MIN_WAIT_MINUTES=30
MAX_RETRY_COUNT=10
RETRY_BATCH_SIZE=100
RETRY_SKIP_IF_PENDING_OVER=30
```

---

## 配置调优建议

### 初始配置（推荐）

从平衡方案开始：
```bash
RETRY_INTERVAL_MINUTES=30
RETRY_MIN_WAIT_MINUTES=60
MAX_RETRY_COUNT=3
RETRY_BATCH_SIZE=50
RETRY_SKIP_IF_PENDING_OVER=90
```

### 调优步骤

1. **观察1周**，收集数据：
   - 失败任务总数
   - 重试成功率
   - pending 任务峰值

2. **根据观察调整**：
   - 失败率高（>20%）→ 增加 `MAX_RETRY_COUNT`
   - 重试成功率低 → 增加 `RETRY_MIN_WAIT_MINUTES`
   - 重试经常被跳过 → 增加 `RETRY_SKIP_IF_PENDING_OVER`
   - pending 任务堆积 → 降低 `RETRY_SKIP_IF_PENDING_OVER`

3. **微调优化**：
   - 每次只调整一个参数
   - 观察变化后再调整下一个
   - 记录每次调整的效果

---

## 总结

**核心原则**:
1. ⏰ **时间关系**: `RETRY_MIN_WAIT_MINUTES ≈ RETRY_INTERVAL_MINUTES × 2`
2. 📦 **批量大小**: 根据预期失败数的30-50%设置
3. 🚦 **避让阈值**: 根据处理能力的30-60分钟任务量设置
4. 🔄 **重试次数**: 3-5次平衡稳定性和资源消耗

**记住**: 没有完美的配置，只有适合你场景的配置！
