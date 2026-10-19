# 自动重新执行已完成任务配置指南

## 🎯 功能说明

**全局自动重新执行机制**：所有状态为 `success` 的任务，完成后过了指定时间，会自动创建新任务重新执行。

**适用场景**：
- ✅ 定期更新数据（每天/每小时采集一次）
- ✅ 监控数据变化（定期检查是否有更新）
- ✅ 批量任务定期重跑

---

## ⚙️ 配置方式

只需在 `.env` 文件中配置两个参数：

```bash
# 是否启用自动重新执行（true/false）
AUTO_RECREATE_SUCCESS_JOBS=true

# 任务完成后多久重新执行（分钟）
AUTO_RECREATE_INTERVAL_MINUTES=1440
```

---

## 📝 配置示例

### 示例 1：每天自动重新执行

```bash
# 启用自动重新执行，每24小时（1440分钟）重新执行一次
AUTO_RECREATE_SUCCESS_JOBS=true
AUTO_RECREATE_INTERVAL_MINUTES=1440
```

### 示例 2：每小时自动重新执行

```bash
# 启用自动重新执行，每小时（60分钟）重新执行一次
AUTO_RECREATE_SUCCESS_JOBS=true
AUTO_RECREATE_INTERVAL_MINUTES=60
```

### 示例 3：每6小时自动重新执行

```bash
# 启用自动重新执行，每6小时（360分钟）重新执行一次
AUTO_RECREATE_SUCCESS_JOBS=true
AUTO_RECREATE_INTERVAL_MINUTES=360
```

### 示例 4：禁用自动重新执行

```bash
# 不自动重新执行
AUTO_RECREATE_SUCCESS_JOBS=false
```

---

## ⏰ 常用时间间隔

| 频率 | AUTO_RECREATE_INTERVAL_MINUTES |
|------|-------------------------------|
| 每30分钟 | 30 |
| 每小时 | 60 |
| 每2小时 | 120 |
| 每6小时 | 360 |
| 每12小时 | 720 |
| 每天 | 1440 |
| 每3天 | 4320 |
| 每周 | 10080 |

---

## 🔄 工作原理

```
任务执行完成（status=success）
  ↓
记录完成时间（updated_at）
  ↓
等待指定时间（AUTO_RECREATE_INTERVAL_MINUTES）
  ↓
调度器扫描（每5分钟检查一次）
  ↓
发现任务完成时间 > 指定间隔
  ↓
自动创建新任务（复用相同的 config_id 和 query_params）
  ↓
新任务进入队列等待执行
  ↓
循环重复
```

### 详细说明

1. **自动识别**：系统自动扫描所有 `status='success'` 的任务
2. **时间判断**：检查任务完成时间是否超过指定间隔
3. **自动创建**：为满足条件的任务创建新任务（完全相同的配置和参数）
4. **无限循环**：新任务完成后，再次等待间隔时间，继续创建

---

## 📋 完整的 .env 配置示例

```bash
# ===========================================
# 数据库配置
# ===========================================
DATABASE_URL=mssql+aioodbc://sa:YourPassword@localhost:1433/bap?driver=ODBC+Driver+17+for+SQL+Server

# ===========================================
# 应用配置
# ===========================================
APP_HOST=0.0.0.0
APP_PORT=8000
DEBUG=False
HEADLESS_MODE=True

# ===========================================
# 进程池配置
# ===========================================
MAX_WORKERS=3
WORKER_MEMORY_LIMIT_MB=512

# ===========================================
# 任务调度配置
# ===========================================
DISPATCH_INTERVAL_MINUTES=1
RETRY_INTERVAL_MINUTES=30
MAX_RETRY_COUNT=3
RETRY_MIN_WAIT_MINUTES=60
RETRY_SKIP_IF_PENDING_OVER=100

# ===========================================
# 自动重新执行配置（全局）
# ===========================================
SCHEDULE_CHECK_INTERVAL_MINUTES=5
SCHEDULE_FIRST_RUN_DELAY_MINUTES=2

# 是否启用自动重新执行（true=启用，false=禁用）
AUTO_RECREATE_SUCCESS_JOBS=true

# 任务完成后多久重新执行（分钟，1440=24小时）
AUTO_RECREATE_INTERVAL_MINUTES=1440

# ===========================================
# 请求级限流配置
# ===========================================
REQUEST_RATE_LIMIT_ENABLED=False
REQUEST_RATE_LIMIT_INTERVAL_SECONDS=5.0
```

---

## 🚀 使用步骤

### 步骤 1：编辑 .env 文件

打开项目根目录的 `.env` 文件

### 步骤 2：添加配置

```bash
# 启用自动重新执行，每天一次
AUTO_RECREATE_SUCCESS_JOBS=true
AUTO_RECREATE_INTERVAL_MINUTES=1440
```

### 步骤 3：重启服务

```bash
python -m app.main
```

### 步骤 4：观察日志

```log
INFO - 开始扫描已完成任务（间隔: 1440 分钟）...
INFO - 发现 5 个任务需要重新执行 (完成时间超过 1440 分钟)
INFO - 为任务 #123 (config_id=44) 创建新任务 (原任务完成于 2026-10-18 10:00:00)
INFO - 成功创建 5 个新任务
```

---

## ✅ 验证功能

### 方法 1：查看日志

启动服务后，观察日志输出：

```log
INFO - 任务调度器启动成功
# 等待 2 分钟后
INFO - 开始扫描已完成任务（间隔: 1440 分钟）...
```

### 方法 2：查询数据库

```sql
-- 查看所有 success 任务
SELECT 
    id,
    config_id,
    status,
    updated_at,
    DATEDIFF(MINUTE, updated_at, GETDATE()) as minutes_ago
FROM job_queue
WHERE status = 'success'
ORDER BY updated_at DESC;

-- 查看哪些任务会被重新执行（超过间隔时间）
SELECT 
    id,
    config_id,
    status,
    updated_at,
    DATEDIFF(MINUTE, updated_at, GETDATE()) as minutes_ago
FROM job_queue
WHERE status = 'success'
  AND updated_at < DATEADD(MINUTE, -1440, GETDATE())
ORDER BY updated_at ASC;
```

### 方法 3：测试验证

```bash
# 设置短间隔用于测试（10分钟）
AUTO_RECREATE_SUCCESS_JOBS=true
AUTO_RECREATE_INTERVAL_MINUTES=10

# 重启服务，等待10分钟后查看是否创建新任务
```

---

## 💡 实际场景

### 场景 1：每天定时采集

```bash
# 所有采集任务每天自动重新执行一次
AUTO_RECREATE_SUCCESS_JOBS=true
AUTO_RECREATE_INTERVAL_MINUTES=1440
```

**效果**：
- 今天 10:00 完成任务 A
- 明天 10:00 自动创建新任务 A
- 自动进入队列执行

### 场景 2：每小时监控

```bash
# 所有监控任务每小时自动重新执行一次
AUTO_RECREATE_SUCCESS_JOBS=true
AUTO_RECREATE_INTERVAL_MINUTES=60
```

**效果**：
- 每个任务完成后，1小时后自动创建新任务
- 实现持续监控

### 场景 3：定期批量更新

```bash
# 所有任务每6小时自动重新执行一次
AUTO_RECREATE_SUCCESS_JOBS=true
AUTO_RECREATE_INTERVAL_MINUTES=360
```

---

## 🔍 工作示例

假设有以下任务：

| 任务ID | 配置ID | 参数 | 完成时间 |
|--------|--------|------|----------|
| 101 | 44 | {"registration_no": "A001"} | 2026-10-18 10:00 |
| 102 | 44 | {"registration_no": "A002"} | 2026-10-18 11:00 |
| 103 | 50 | {"keyword": "医疗"} | 2026-10-18 12:00 |

**配置**：
```bash
AUTO_RECREATE_SUCCESS_JOBS=true
AUTO_RECREATE_INTERVAL_MINUTES=1440  # 24小时
```

**2026-10-19 10:05（第二天）**：
- 调度器扫描发现任务 101 完成时间超过 24 小时
- 自动创建新任务：`config_id=44, query_params={"registration_no": "A001"}`
- 新任务进入队列等待执行

**2026-10-19 11:05**：
- 扫描发现任务 102 完成时间超过 24 小时
- 自动创建新任务：`config_id=44, query_params={"registration_no": "A002"}`

---

## 🐛 常见问题

### Q1: 如何只对特定任务生效？

**当前设计**：全局配置，所有 success 任务都会重新执行

**如果只想特定任务重新执行**：
- 方式1：手动删除不需要重新执行的 success 任务
- 方式2：将任务标记为其他状态（非 success）

### Q2: 任务会无限重复执行吗？

**是的**，这就是设计目的：
- 任务完成 → 等待间隔 → 创建新任务 → 执行 → 完成 → 循环

**如果不想无限重复**：
- 设置 `AUTO_RECREATE_SUCCESS_JOBS=false` 禁用

### Q3: 如何停止某个任务的重复执行？

**方法1**：删除该任务
```sql
DELETE FROM job_queue WHERE id = 123;
```

**方法2**：将任务状态改为非 success
```sql
UPDATE job_queue SET status = 'cancelled' WHERE id = 123;
```

**方法3**：禁用全局功能
```bash
AUTO_RECREATE_SUCCESS_JOBS=false
```

### Q4: 修改间隔时间后，已有任务会受影响吗？

**会**，修改 `AUTO_RECREATE_INTERVAL_MINUTES` 后：
- 重启服务生效
- 所有 success 任务都按新间隔重新计算

### Q5: 如何查看哪些任务即将被重新执行？

```sql
-- 查看即将重新执行的任务（距离间隔时间不到1小时）
SELECT 
    id,
    config_id,
    query_params,
    updated_at,
    DATEDIFF(MINUTE, updated_at, GETDATE()) as completed_minutes_ago,
    1440 - DATEDIFF(MINUTE, updated_at, GETDATE()) as minutes_until_recreate
FROM job_queue
WHERE status = 'success'
  AND DATEDIFF(MINUTE, updated_at, GETDATE()) BETWEEN 1380 AND 1440
ORDER BY updated_at ASC;
```

---

## 📊 监控建议

### 定期检查任务数量

```sql
-- 统计各状态任务数量
SELECT 
    status,
    COUNT(*) as count
FROM job_queue
GROUP BY status;
```

### 监控重复执行情况

```sql
-- 查看最近自动创建的任务
SELECT TOP 10
    id,
    config_id,
    status,
    created_at,
    query_params
FROM job_queue
ORDER BY created_at DESC;
```

---

## ✨ 优势

| 特性 | 说明 |
|------|------|
| **全局生效** | 一次配置，所有任务都自动重复 |
| **简单配置** | 只需两个参数 |
| **灵活间隔** | 可以设置任意分钟间隔 |
| **自动管理** | 无需手动创建任务 |
| **参数复用** | 自动复用原任务的配置和参数 |

---

## 📝 总结

**启用自动重新执行**：

```bash
# .env 配置
AUTO_RECREATE_SUCCESS_JOBS=true
AUTO_RECREATE_INTERVAL_MINUTES=1440
```

**效果**：
- ✅ 所有完成的任务（success）会在指定时间后自动重新执行
- ✅ 无需手动创建任务
- ✅ 无限循环执行
- ✅ 适用于定期数据更新、监控等场景

就这么简单！
