# 限流配置指南

## 功能概述

限流功能用于控制任务执行速率，防止对目标网站造成过大压力，避免被封禁或触发反爬机制。

## 核心概念

### 1. 时间窗口（Time Window）
- 定义：统计任务数量的时间范围
- 示例：60 分钟的时间窗口，表示统计最近 60 分钟内执行的任务数

### 2. 最大任务数（Max Tasks）
- 定义：在时间窗口内允许执行的最大任务数
- 示例：100 个任务，表示在时间窗口内最多执行 100 个任务

### 3. 限流模式

#### 全局限流（RATE_LIMIT_PER_CONFIG=False）
- 所有任务共享一个限流配额
- 适用场景：所有任务访问同一个网站或共享同一 IP

#### 按配置限流（RATE_LIMIT_PER_CONFIG=True）
- 每个配置（config_id）独立计算限流配额
- 适用场景：不同配置访问不同网站或使用不同账号

## 环境变量配置

在 `.env` 文件中添加：

```bash
# 是否启用限流
RATE_LIMIT_ENABLED=true

# 时间窗口（分钟）
RATE_LIMIT_WINDOW_MINUTES=60

# 时间窗口内最多执行的任务数
RATE_LIMIT_MAX_TASKS=100

# 是否按配置ID分别限流
RATE_LIMIT_PER_CONFIG=false
```

## 配置示例

### 场景1：严格限流（防止被封）
适用于目标网站有严格的访问频率限制

```bash
RATE_LIMIT_ENABLED=true
RATE_LIMIT_WINDOW_MINUTES=60
RATE_LIMIT_MAX_TASKS=50
RATE_LIMIT_PER_CONFIG=false
```

**含义**：全局限流，每小时最多执行 50 个任务

### 场景2：中等限流（平衡速度与安全）
适用于一般的数据采集需求

```bash
RATE_LIMIT_ENABLED=true
RATE_LIMIT_WINDOW_MINUTES=60
RATE_LIMIT_MAX_TASKS=100
RATE_LIMIT_PER_CONFIG=false
```

**含义**：全局限流，每小时最多执行 100 个任务

### 场景3：宽松限流（高速采集）
适用于目标网站没有严格限制或测试环境

```bash
RATE_LIMIT_ENABLED=true
RATE_LIMIT_WINDOW_MINUTES=60
RATE_LIMIT_MAX_TASKS=300
RATE_LIMIT_PER_CONFIG=false
```

**含义**：全局限流，每小时最多执行 300 个任务

### 场景4：多站点独立限流
适用于同时采集多个网站，每个网站有不同的限流要求

```bash
RATE_LIMIT_ENABLED=true
RATE_LIMIT_WINDOW_MINUTES=60
RATE_LIMIT_MAX_TASKS=100
RATE_LIMIT_PER_CONFIG=true
```

**含义**：按配置ID分别限流，每个配置每小时最多执行 100 个任务

### 场景5：短时间窗口限流
适用于需要精细控制短期内访问频率的场景

```bash
RATE_LIMIT_ENABLED=true
RATE_LIMIT_WINDOW_MINUTES=10
RATE_LIMIT_MAX_TASKS=20
RATE_LIMIT_PER_CONFIG=false
```

**含义**：全局限流，每 10 分钟最多执行 20 个任务（相当于每小时 120 个）

### 场景6：不启用限流
适用于开发测试或目标网站无限制

```bash
RATE_LIMIT_ENABLED=false
```

**含义**：不启用限流，任务尽快执行

## 工作原理

### 1. 任务分发时检查
```
调度器扫描 pending 任务
  ↓
检查限流：can_execute(config_id)?
  ↓
YES → 标记 processing → 提交到进程池 → 记录执行时间
NO  → 跳过该任务 → 记录等待时间
```

### 2. 时间窗口滑动
```
时间窗口：[now - 60分钟, now]
任务执行时间戳：[t1, t2, t3, ..., tn]

检查时：
- 移除超出时间窗口的旧时间戳
- 统计窗口内的任务数
- 判断是否达到上限
```

### 3. 等待时间计算
```
如果达到限流上限：
wait_time = (最早的时间戳 + 窗口时长) - 当前时间

示例：
- 最早时间戳：14:00
- 窗口时长：60 分钟
- 当前时间：14:30
- wait_time = (14:00 + 60) - 14:30 = 30 分钟
```

## API 接口

### 1. 查询限流状态
```bash
GET /api/rate-limit/status

# 查询全局状态
curl http://localhost:8000/api/rate-limit/status

# 查询特定配置的状态
curl http://localhost:8000/api/rate-limit/status?config_id=44
```

**响应示例**：
```json
{
  "success": true,
  "data": {
    "enabled": true,
    "window_minutes": 60,
    "max_tasks": 100,
    "current_count": 45,
    "remaining": 55,
    "utilization": "45/100 (45.0%)"
  }
}
```

### 2. 查询等待时间
```bash
GET /api/rate-limit/wait-time

# 查询全局等待时间
curl http://localhost:8000/api/rate-limit/wait-time

# 查询特定配置的等待时间
curl http://localhost:8000/api/rate-limit/wait-time?config_id=44
```

**响应示例**：
```json
{
  "success": true,
  "data": {
    "wait_seconds": 1800,
    "wait_minutes": 30.0,
    "can_execute_now": false
  }
}
```

### 3. 重置限流计数器
```bash
POST /api/rate-limit/reset

# 重置所有
curl -X POST http://localhost:8000/api/rate-limit/reset

# 重置特定配置
curl -X POST http://localhost:8000/api/rate-limit/reset?config_id=44
```

### 4. 查询限流配置
```bash
GET /api/rate-limit/config

curl http://localhost:8000/api/rate-limit/config
```

**响应示例**：
```json
{
  "success": true,
  "data": {
    "enabled": true,
    "window_minutes": 60,
    "max_tasks": 100,
    "per_config": false,
    "description": {
      "enabled": "是否启用限流",
      "window_minutes": "时间窗口（分钟）",
      "max_tasks": "在 60 分钟内最多执行 100 个任务",
      "per_config": "是否按配置ID分别限流"
    }
  }
}
```

## 监控和调优

### 1. 监控限流使用率
定期查询限流状态，观察 `utilization` 字段：

- **< 50%**：限流宽松，可以考虑增加任务数或缩短窗口
- **50-80%**：合理范围
- **> 80%**：接近限流上限，任务可能被延迟执行
- **100%**：达到限流上限，新任务会被跳过

### 2. 调整策略

#### 如果任务被频繁跳过
```bash
# 方案1：增加时间窗口内的任务数
RATE_LIMIT_MAX_TASKS=150  # 从100增到150

# 方案2：缩短时间窗口（但保持总速率）
RATE_LIMIT_WINDOW_MINUTES=30
RATE_LIMIT_MAX_TASKS=50  # 相当于每小时100个

# 方案3：启用按配置限流
RATE_LIMIT_PER_CONFIG=true
```

#### 如果目标网站返回限流错误
```bash
# 方案1：降低任务数
RATE_LIMIT_MAX_TASKS=50  # 从100降到50

# 方案2：延长时间窗口
RATE_LIMIT_WINDOW_MINUTES=120  # 从60分钟延长到120分钟

# 方案3：降低并发数（配合限流）
MAX_WORKERS=2  # 从3降到2
RATE_LIMIT_MAX_TASKS=50
```

### 3. 日志监控

启动应用后，查看日志中的限流信息：

```
INFO - 限流管理器初始化: enabled=True, window=60分钟, max_tasks=100, per_config=False
INFO - 任务 #123 (config_id=44) 因限流跳过，需等待 1800 秒
WARNING - 达到全局限流上限: 100/100 任务在 60 分钟内
```

## 常见问题

### Q1: 限流会影响正在执行的任务吗？
A: 不会。限流只影响任务的分发，已经在执行的任务不受影响。

### Q2: 如何临时突破限流限制？
A: 调用重置 API：`POST /api/rate-limit/reset`，清空计数器后重新计算。

### Q3: 按配置限流时，不同配置的任务数可以不同吗？
A: 当前版本所有配置共享相同的 `max_tasks` 配置。如需不同配置有不同限流，需要在数据库配置中添加限流字段（待扩展）。

### Q4: 限流和 MAX_WORKERS 的关系？
A: 
- `MAX_WORKERS`：控制同时执行的任务数（并发数）
- `RATE_LIMIT_MAX_TASKS`：控制一段时间内执行的总任务数（速率）
- 两者独立工作，都需要满足才能执行任务

### Q5: 如何选择合适的限流参数？
A: 
1. 先观察目标网站的响应（是否返回 429 错误）
2. 从保守值开始（如 60分钟/50任务）
3. 逐步增加任务数，直到出现限流错误
4. 回退到安全值（出现错误前的 70-80%）

## 扩展功能（未来）

### 1. 数据库级别的配置限流
在 `crawler_configs` 表添加字段：
```sql
ALTER TABLE crawler_configs ADD COLUMN rate_limit_max_tasks INT;
ALTER TABLE crawler_configs ADD COLUMN rate_limit_window_minutes INT;
```

### 2. 动态调整限流
根据目标网站的响应自动调整限流参数：
- 收到 429 错误 → 降低限流
- 长期正常 → 逐步提高限流

### 3. 时间段限流
不同时间段使用不同的限流策略：
- 工作时间（9:00-18:00）：严格限流
- 非工作时间：宽松限流

## 最佳实践

1. **先测试再上线**：在测试环境中验证限流参数是否合适
2. **监控日志**：定期检查是否有任务因限流被跳过
3. **灵活调整**：根据业务需求和目标网站的反馈调整参数
4. **分散任务**：避免在短时间内提交大量任务
5. **合理配置窗口**：通常 30-60 分钟的窗口比较合理
