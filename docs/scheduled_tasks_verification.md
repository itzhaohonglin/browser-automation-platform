# 周期性任务功能验证清单

## ✅ 功能已实现

周期性任务执行功能已经完整实现，以下是验证清单：

### 1. 代码实现
- ✅ 数据库模型：`CrawlerConfig.schedule_config` 字段
- ✅ 数据库迁移：`alembic/versions/7c8d9e4f5a6b_add_schedule_config_to_crawler_configs.py`
- ✅ 调度逻辑：`scheduler.recreate_scheduled_jobs()` 方法
- ✅ 调度注册：每 5 分钟自动检查一次
- ✅ 配置项：`SCHEDULE_CHECK_INTERVAL_MINUTES` 和 `SCHEDULE_FIRST_RUN_DELAY_MINUTES`

### 2. 工作原理

```
启动服务
  ↓
调度器启动（延迟2分钟）
  ↓
每5分钟执行一次 recreate_scheduled_jobs()
  ↓
查询 schedule_config.enabled=true 的配置
  ↓
检查最新任务状态
  ├─ 状态 = success 且达到间隔时间 → 创建新任务
  ├─ 状态 = pending/processing → 跳过
  └─ 状态 = failed → 由 retry_failed_jobs 处理
  ↓
新任务进入队列
  ↓
dispatch_pending_jobs 分发到进程池执行
  ↓
任务完成（status=success）
  ↓
等待下一个间隔周期（重复）
```

---

## 🔧 快速验证步骤

### 步骤 1：执行数据库迁移

```bash
# 如果数据库可用，执行迁移
alembic upgrade head
```

### 步骤 2：配置周期性调度

```sql
-- 示例：配置每 10 分钟执行一次（用于测试）
UPDATE crawler_configs
SET schedule_config = N'{
  "enabled": true,
  "type": "interval",
  "interval_minutes": 10,
  "keep_history": true,
  "max_history": 100
}'
WHERE id = 44;  -- 替换为你的配置ID
```

### 步骤 3：创建第一个任务

```sql
INSERT INTO job_queue (config_id, query_params, status, priority)
VALUES (44, N'{"registration_no": "滇械注准20192140008"}', 'pending', 5);
```

### 步骤 4：启动服务

```bash
python -m app.main
```

### 步骤 5：观察日志

启动后应该看到以下日志：

```log
INFO - 应用启动中...
INFO - 数据库迁移检查完成
INFO - 正在启动任务调度器...
INFO - 任务调度器启动成功
INFO - 调度器与进程池已启动

# 2分钟后
INFO - 开始扫描周期性任务配置...
INFO - 发现 1 个配置了周期性调度的采集配置

# 如果需要创建新任务
INFO - 为配置 #44 (国家医保局-每日定时采集) 创建周期性任务
INFO - 成功创建 1 个周期性任务
```

### 步骤 6：运行验证脚本

```bash
python scripts/test_scheduled_tasks.py
```

---

## 🐛 故障排查

### 问题 1：任务不会自动创建

**可能原因**：
1. `schedule_config.enabled` 不是 `true`
2. 最新任务状态不是 `success`（可能是 `pending`、`processing` 或 `failed`）
3. 还没到执行间隔时间
4. 服务未启动或调度器未启动

**解决方法**：
```sql
-- 检查配置
SELECT 
    id, 
    config_name,
    schedule_config,
    is_active
FROM crawler_configs 
WHERE schedule_config IS NOT NULL;

-- 检查最新任务状态
SELECT TOP 1
    id,
    config_id,
    status,
    created_at,
    updated_at
FROM job_queue
WHERE config_id = 44
ORDER BY created_at DESC;
```

### 问题 2：任务一直是 pending 状态

**可能原因**：
- 进程池已满
- `dispatch_pending_jobs` 未运行
- MAX_WORKERS 设置过小

**解决方法**：
```bash
# 检查 .env 配置
MAX_WORKERS=3
DISPATCH_INTERVAL_MINUTES=30

# 查看进程池状态日志
grep "进程池" logs/*.log
```

### 问题 3：调度器没有运行

**可能原因**：
- 应用启动失败
- 配置文件缺失

**解决方法**：
```bash
# 查看启动日志
python -m app.main

# 确认 .env 文件存在
ls -la .env

# 检查配置
cat .env | grep SCHEDULE
```

---

## 📊 监控和调试

### 查看周期性配置和任务状态

```sql
SELECT 
    c.id AS config_id,
    c.config_name,
    JSON_VALUE(c.schedule_config, '$.enabled') AS enabled,
    JSON_VALUE(c.schedule_config, '$.interval_minutes') AS interval_min,
    j.id AS latest_job_id,
    j.status AS latest_status,
    j.created_at AS job_created_at,
    DATEDIFF(MINUTE, j.created_at, GETDATE()) AS minutes_since_created
FROM crawler_configs c
LEFT JOIN (
    SELECT 
        config_id, 
        id, 
        status, 
        created_at,
        ROW_NUMBER() OVER (PARTITION BY config_id ORDER BY created_at DESC) AS rn
    FROM job_queue
) j ON c.id = j.config_id AND j.rn = 1
WHERE JSON_VALUE(c.schedule_config, '$.enabled') = 'true'
ORDER BY c.id;
```

### 查看任务执行历史

```sql
-- 查看某个配置的执行历史（最近10次）
SELECT TOP 10
    id,
    status,
    created_at,
    updated_at,
    DATEDIFF(MINUTE, created_at, updated_at) AS duration_minutes,
    error_msg
FROM job_queue
WHERE config_id = 44
ORDER BY created_at DESC;
```

### 计算下次执行时间

```sql
-- 计算下次应该执行的时间
SELECT 
    c.id,
    c.config_name,
    JSON_VALUE(c.schedule_config, '$.interval_minutes') AS interval_min,
    j.updated_at AS last_completed,
    DATEADD(
        MINUTE, 
        CAST(JSON_VALUE(c.schedule_config, '$.interval_minutes') AS INT),
        j.updated_at
    ) AS next_run_time,
    CASE 
        WHEN DATEADD(
            MINUTE, 
            CAST(JSON_VALUE(c.schedule_config, '$.interval_minutes') AS INT),
            j.updated_at
        ) <= GETDATE() 
        THEN '✅ 应该创建新任务'
        ELSE '⏳ 未到执行时间'
    END AS status
FROM crawler_configs c
INNER JOIN (
    SELECT 
        config_id,
        updated_at,
        ROW_NUMBER() OVER (PARTITION BY config_id ORDER BY created_at DESC) AS rn
    FROM job_queue
    WHERE status = 'success'
) j ON c.id = j.config_id AND j.rn = 1
WHERE JSON_VALUE(c.schedule_config, '$.enabled') = 'true';
```

---

## 📝 完整配置示例

### .env 配置

```bash
# 数据库连接
DATABASE_URL=mssql+aioodbc://sa:YourPassword@localhost:1433/bap?driver=ODBC+Driver+17+for+SQL+Server

# 进程池配置
MAX_WORKERS=3
WORKER_MEMORY_LIMIT_MB=512

# 任务调度配置
DISPATCH_INTERVAL_MINUTES=1  # 快速分发任务（1分钟检查一次）
RETRY_INTERVAL_MINUTES=30
MAX_RETRY_COUNT=3

# 周期性任务配置
SCHEDULE_CHECK_INTERVAL_MINUTES=5  # 每5分钟检查一次
SCHEDULE_FIRST_RUN_DELAY_MINUTES=2  # 启动后2分钟开始首次检查
```

### 数据库配置

```sql
-- 配置每小时执行一次
UPDATE crawler_configs
SET schedule_config = N'{
  "enabled": true,
  "type": "interval",
  "interval_minutes": 60,
  "keep_history": true,
  "max_history": 48
}'
WHERE id = 44;

-- 创建第一个任务
INSERT INTO job_queue (config_id, query_params, status, priority)
VALUES (
    44, 
    N'{"registration_no": "滇械注准20192140008"}',
    'pending',
    5
);
```

---

## ✅ 功能确认

如果以上步骤都正确，你应该看到：

1. ✅ 服务启动时，调度器成功启动
2. ✅ 每 5 分钟，日志中出现"开始扫描周期性任务配置"
3. ✅ 任务完成后（status=success），等待间隔时间后自动创建新任务
4. ✅ 新任务自动进入队列并执行
5. ✅ 历史任务按配置保留或清理

---

## 📚 相关文档

- 详细使用指南：`docs/scheduled_tasks_guide.md`
- 快速配置示例：`docs/scheduled_tasks_quick_examples.md`
- 验证脚本：`scripts/test_scheduled_tasks.py`

---

## 🎯 总结

周期性任务功能已经完全实现，核心逻辑：

1. **配置驱动**：在 `schedule_config` 字段配置执行规则
2. **自动触发**：调度器每 5 分钟检查一次
3. **智能判断**：基于最新任务状态和完成时间决定是否创建新任务
4. **无限循环**：任务完成 → 等待间隔 → 创建新任务 → 执行 → 完成（重复）

如果有任何问题，请：
1. 运行验证脚本：`python scripts/test_scheduled_tasks.py`
2. 检查服务日志
3. 查询数据库状态
4. 参考故障排查部分
