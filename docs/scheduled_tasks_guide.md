# 周期性任务执行功能使用指南

## 功能概述

周期性任务执行功能允许你配置采集任务定期自动执行，无需手动触发。适用于需要定期更新数据的场景，如每日数据采集、定时监控等。

**核心特性**：
- ✅ 配置驱动：在 `crawler_configs` 表的 `schedule_config` 字段配置
- ✅ 自动创建：任务完成后自动创建新任务
- ✅ 历史管理：可选保留历史任务记录
- ✅ 灵活调度：支持间隔调度（未来可扩展 cron 表达式）

---

## 工作原理

```
1. 配置周期性调度（schedule_config）
   ↓
2. 创建第一个任务（手动或通过 API）
   ↓
3. 任务执行完成（status=success）
   ↓
4. 调度器检查（每 5 分钟）
   ├─ 检查任务完成时间
   ├─ 计算是否到达下次执行时间
   └─ 如果到达 → 自动创建新任务（复用相同参数）
   ↓
5. 新任务自动进入队列执行
   ↓
6. 重复步骤 3-5（无限循环）
```

---

## 配置说明

### schedule_config 字段结构

在 `crawler_configs` 表的 `schedule_config` 字段（JSON 类型）中配置：

```json
{
  "enabled": true,              // 是否启用周期性执行（必填）
  "type": "interval",           // 调度类型（必填）：interval=间隔调度
  "interval_minutes": 1440,     // 间隔分钟数（type=interval 时必填）
  "auto_recreate": true,        // 任务完成后是否自动创建新任务（可选，默认 true）
  "keep_history": true,         // 是否保留历史任务记录（可选，默认 true）
  "max_history": 100            // 最多保留历史记录数（可选，默认 100）
}
```

### 参数详解

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `enabled` | boolean | ✅ | - | 是否启用周期性执行 |
| `type` | string | ✅ | - | 调度类型，目前仅支持 `interval` |
| `interval_minutes` | int | ✅ | - | 任务执行间隔（分钟），如：1440=每天，60=每小时 |
| `auto_recreate` | boolean | ❌ | true | 是否自动创建新任务 |
| `keep_history` | boolean | ❌ | true | 是否保留历史任务 |
| `max_history` | int | ❌ | 100 | 保留的最大历史任务数 |

---

## 使用示例

### 示例 1：每日定时采集

**场景**：每天采集一次国家医保局注册证号数据

```sql
-- 1. 更新配置，启用周期性调度
UPDATE crawler_configs
SET schedule_config = N'{
  "enabled": true,
  "type": "interval",
  "interval_minutes": 1440,
  "keep_history": true,
  "max_history": 30
}'
WHERE id = 44;

-- 2. 创建第一个任务
INSERT INTO job_queue (config_id, query_params, status, priority)
VALUES (44, N'{"registration_no": "滇械注准20192140008"}', 'pending', 5);

-- 3. 之后任务会自动每 24 小时执行一次
```

### 示例 2：每小时监控

**场景**：每小时监控特定数据是否有变化

```sql
UPDATE crawler_configs
SET schedule_config = N'{
  "enabled": true,
  "type": "interval",
  "interval_minutes": 60,
  "keep_history": true,
  "max_history": 48
}'
WHERE id = 50;
```

### 示例 3：每周执行

**场景**：每周执行一次数据更新

```sql
UPDATE crawler_configs
SET schedule_config = N'{
  "enabled": true,
  "type": "interval",
  "interval_minutes": 10080,
  "keep_history": true,
  "max_history": 10
}'
WHERE id = 55;
-- 10080 分钟 = 7 天 × 24 小时 × 60 分钟
```

### 示例 4：不保留历史

**场景**：只关心最新结果，不保留历史任务

```sql
UPDATE crawler_configs
SET schedule_config = N'{
  "enabled": true,
  "type": "interval",
  "interval_minutes": 1440,
  "keep_history": false
}'
WHERE id = 60;
-- 注意：keep_history=false 时，会定期清理旧任务
```

---

## Python API 示例

### 创建周期性采集配置

```python
from app.models.config import CrawlerConfig
from app.core.database import get_session

async def create_scheduled_config():
    """创建周期性采集配置"""
    config = CrawlerConfig(
        config_name="国家医保局-每日定时采集",
        target_url="https://code.nhsa.gov.cn/toSearch.html?sysflag=1004",
        need_login=False,
        input_configs=[
            {
                "selector": "input[name='zczbh']",
                "param_name": "registration_no",
                "input_method": "type"
            }
        ],
        submit_selector="button:has-text('查询')",
        wait_selector=".ui-jqgrid-btable",
        fields_mapping={
            "iframe_levels": 2,
            "iframe1_selector": "iframe#dataInfo",
            "iframe2_selector": "iframe.els-iframe.active",
            "list_selector": "tbody tr.jqgrow",
            "fields": [
                {"name": "耗材名称", "selector": "td:nth-child(2)", "attr": "text"}
            ]
        },
        priority=5,
        # 周期性调度配置
        schedule_config={
            "enabled": True,
            "type": "interval",
            "interval_minutes": 1440,  # 每天执行一次
            "keep_history": True,
            "max_history": 30  # 保留最近 30 次记录
        }
    )
    
    async with get_session() as session:
        session.add(config)
        await session.commit()
        await session.refresh(config)
        return config
```

### 创建第一个任务

```python
from app.models.job import JobQueue, JobStatus

async def create_first_scheduled_job(config_id: int, query_params: dict):
    """创建第一个周期性任务"""
    job = JobQueue(
        config_id=config_id,
        query_params=query_params,
        priority=5,
        status=JobStatus.PENDING
    )
    
    async with get_session() as session:
        session.add(job)
        await session.commit()
        await session.refresh(job)
        return job

# 使用示例
job = await create_first_scheduled_job(
    config_id=44,
    query_params={"registration_no": "滇械注准20192140008"}
)
```

### 启用/禁用周期性调度

```python
async def toggle_schedule(config_id: int, enabled: bool):
    """启用或禁用周期性调度"""
    async with get_session() as session:
        config = await session.get(CrawlerConfig, config_id)
        
        if config.schedule_config:
            schedule_cfg = config.schedule_config.copy()
            schedule_cfg['enabled'] = enabled
            config.schedule_config = schedule_cfg
        else:
            # 首次配置
            config.schedule_config = {
                "enabled": enabled,
                "type": "interval",
                "interval_minutes": 1440
            }
        
        await session.commit()
        return config

# 启用
await toggle_schedule(44, enabled=True)

# 禁用
await toggle_schedule(44, enabled=False)
```

---

## 调度器配置

### 环境变量配置

在 `.env` 文件中配置调度器参数：

```bash
# 周期性任务检查间隔（分钟）
SCHEDULE_CHECK_INTERVAL_MINUTES=5

# 首次检查延迟（分钟）
SCHEDULE_FIRST_RUN_DELAY_MINUTES=2
```

**配置说明**：
- `SCHEDULE_CHECK_INTERVAL_MINUTES`：调度器多久检查一次是否需要创建新任务（默认 5 分钟）
- `SCHEDULE_FIRST_RUN_DELAY_MINUTES`：应用启动后延迟多久开始首次检查（默认 2 分钟）

**注意**：检查间隔不影响任务执行间隔，只影响调度器的检查频率。

---

## 常见问题

### Q1: 如何停止周期性任务？

**方法 1：禁用配置**
```sql
UPDATE crawler_configs
SET schedule_config = JSON_MODIFY(schedule_config, '$.enabled', 0)
WHERE id = 44;
```

**方法 2：删除 schedule_config**
```sql
UPDATE crawler_configs
SET schedule_config = NULL
WHERE id = 44;
```

### Q2: 如何修改执行间隔？

```sql
UPDATE crawler_configs
SET schedule_config = JSON_MODIFY(schedule_config, '$.interval_minutes', 720)
WHERE id = 44;
-- 修改为每 12 小时执行一次
```

### Q3: 任务失败了怎么办？

周期性任务和失败重试机制配合工作：
- 任务失败后，会进入失败重试队列（retry_failed_jobs）
- 重试成功后，周期性调度器会在下一个间隔创建新任务
- 如果重试失败达到上限，需要手动处理或调整配置

### Q4: 如何查看周期性任务的执行历史？

```sql
-- 查询某个配置的所有任务（按时间倒序）
SELECT 
    id,
    status,
    created_at,
    completed_at,
    error_msg
FROM job_queue
WHERE config_id = 44
ORDER BY created_at DESC;

-- 查询最近 10 次执行
SELECT TOP 10
    id,
    status,
    created_at,
    DATEDIFF(MINUTE, created_at, completed_at) as duration_minutes
FROM job_queue
WHERE config_id = 44 AND status = 'success'
ORDER BY created_at DESC;
```

### Q5: 可以为同一个配置创建多个周期性任务吗？

不建议。周期性调度基于配置的最新任务状态，如果手动创建多个任务，可能导致调度逻辑混乱。

**推荐做法**：
- 一个配置对应一条周期性任务链
- 如需不同参数的任务，创建多个配置

### Q6: 如何实现"每天凌晨 2 点执行"？

当前版本仅支持 `interval` 类型（固定间隔），不支持指定具体时间。

**临时解决方案**：
1. 在期望的时间（如凌晨 2 点）手动创建第一个任务
2. 设置 `interval_minutes: 1440`（24 小时）
3. 之后会在每天相同时间自动执行

**未来版本**：将支持 `cron` 类型，可以配置如 `"cron": "0 2 * * *"`。

---

## 最佳实践

### 1. 合理设置间隔时间

```python
# ✅ 推荐
interval_minutes = 1440  # 每天
interval_minutes = 60    # 每小时
interval_minutes = 10080 # 每周

# ❌ 不推荐
interval_minutes = 1     # 每分钟（频率过高）
interval_minutes = 43200 # 30 天（间隔过长，建议分为多次）
```

### 2. 控制历史记录数量

```python
# 根据执行频率设置 max_history
{
    "interval_minutes": 60,     # 每小时
    "max_history": 48           # 保留 2 天
}

{
    "interval_minutes": 1440,   # 每天
    "max_history": 30           # 保留 1 个月
}
```

### 3. 监控任务执行状态

```sql
-- 检查周期性任务是否正常运行
SELECT 
    c.id,
    c.config_name,
    JSON_VALUE(c.schedule_config, '$.enabled') as schedule_enabled,
    JSON_VALUE(c.schedule_config, '$.interval_minutes') as interval_minutes,
    j.status as latest_status,
    j.completed_at as last_completed_at,
    DATEDIFF(MINUTE, j.completed_at, GETDATE()) as minutes_since_last_run
FROM crawler_configs c
LEFT JOIN (
    SELECT config_id, status, completed_at,
           ROW_NUMBER() OVER (PARTITION BY config_id ORDER BY created_at DESC) as rn
    FROM job_queue
) j ON c.id = j.config_id AND j.rn = 1
WHERE JSON_VALUE(c.schedule_config, '$.enabled') = 'true';
```

### 4. 优雅地禁用调度

```python
# 禁用前检查是否有正在执行的任务
async def disable_schedule_safely(config_id: int):
    async with get_session() as session:
        # 检查是否有 processing 状态的任务
        stmt = select(JobQueue).where(
            JobQueue.config_id == config_id,
            JobQueue.status == JobStatus.PROCESSING
        )
        result = await session.execute(stmt)
        processing_jobs = result.scalars().all()
        
        if processing_jobs:
            raise ValueError(f"配置 #{config_id} 还有 {len(processing_jobs)} 个任务正在执行，请稍后再试")
        
        # 禁用调度
        config = await session.get(CrawlerConfig, config_id)
        schedule_cfg = config.schedule_config.copy()
        schedule_cfg['enabled'] = False
        config.schedule_config = schedule_cfg
        await session.commit()
```

---

## 日志和调试

### 查看调度器日志

调度器会输出详细的日志信息：

```log
2026-10-19 16:00:00 INFO - 开始扫描周期性任务配置...
2026-10-19 16:00:00 INFO - 发现 3 个配置了周期性调度的采集配置
2026-10-19 16:00:00 DEBUG - 任务 #123 已完成 1441.5 分钟，达到间隔 1440 分钟，需要创建新任务
2026-10-19 16:00:00 INFO - 为配置 #44 (国家医保局-每日定时采集) 创建周期性任务
2026-10-19 16:00:00 INFO - 配置 #44: 清理了 5 个历史任务
2026-10-19 16:00:00 INFO - 成功创建 1 个周期性任务
```

### 调试技巧

```python
# 手动触发调度器检查（用于测试）
from app.services.scheduler import scheduler

# 在 Python 环境中
await scheduler.recreate_scheduled_jobs()
```

---

## 数据库迁移

如果你是从旧版本升级，需要执行数据库迁移：

```bash
# 执行迁移
alembic upgrade head
```

迁移脚本会自动添加 `schedule_config` 字段到 `crawler_configs` 表。

---

## 总结

周期性任务执行功能让你可以轻松配置定时采集任务，无需手动触发。关键点：

1. ✅ 在 `schedule_config` 字段配置调度规则
2. ✅ 创建第一个任务后，系统会自动创建后续任务
3. ✅ 通过 `enabled: false` 可随时停止调度
4. ✅ 支持历史任务管理和清理

如有问题，请查看日志或提交 Issue。
