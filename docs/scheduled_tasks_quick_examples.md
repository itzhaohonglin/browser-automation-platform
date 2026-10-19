# 周期性任务快速配置示例

## 场景 1：每日采集（最常用）

```sql
-- 配置每天执行一次
UPDATE crawler_configs
SET schedule_config = N'{
  "enabled": true,
  "type": "interval",
  "interval_minutes": 1440,
  "keep_history": true,
  "max_history": 30
}'
WHERE id = 44;

-- 创建第一个任务
INSERT INTO job_queue (config_id, query_params, status)
VALUES (44, N'{"registration_no": "滇械注准20192140008"}', 'pending');
```

## 场景 2：每小时采集

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
WHERE id = 50;
```

## 场景 3：每周采集

```sql
-- 配置每周执行一次
UPDATE crawler_configs
SET schedule_config = N'{
  "enabled": true,
  "type": "interval",
  "interval_minutes": 10080,
  "keep_history": true,
  "max_history": 10
}'
WHERE id = 55;
```

## 场景 4：每 6 小时采集

```sql
-- 配置每 6 小时执行一次
UPDATE crawler_configs
SET schedule_config = N'{
  "enabled": true,
  "type": "interval",
  "interval_minutes": 360,
  "keep_history": true,
  "max_history": 100
}'
WHERE id = 60;
```

## 停止周期性任务

```sql
-- 方法 1：禁用
UPDATE crawler_configs
SET schedule_config = JSON_MODIFY(schedule_config, '$.enabled', 0)
WHERE id = 44;

-- 方法 2：删除配置
UPDATE crawler_configs
SET schedule_config = NULL
WHERE id = 44;
```

## 修改执行间隔

```sql
-- 从每天改为每 12 小时
UPDATE crawler_configs
SET schedule_config = JSON_MODIFY(schedule_config, '$.interval_minutes', 720)
WHERE id = 44;
```

## 查看周期性任务状态

```sql
-- 查看所有周期性配置及其最新任务状态
SELECT 
    c.id,
    c.config_name,
    JSON_VALUE(c.schedule_config, '$.enabled') as enabled,
    JSON_VALUE(c.schedule_config, '$.interval_minutes') as interval_min,
    j.status as latest_status,
    j.completed_at,
    DATEDIFF(MINUTE, j.completed_at, GETDATE()) as minutes_ago
FROM crawler_configs c
LEFT JOIN (
    SELECT config_id, status, completed_at,
           ROW_NUMBER() OVER (PARTITION BY config_id ORDER BY created_at DESC) as rn
    FROM job_queue
) j ON c.id = j.config_id AND j.rn = 1
WHERE JSON_VALUE(c.schedule_config, '$.enabled') = 'true';
```

## 常用间隔时间参考

| 频率 | interval_minutes | 说明 |
|------|-----------------|------|
| 每 5 分钟 | 5 | 高频监控 |
| 每 15 分钟 | 15 | 常规监控 |
| 每 30 分钟 | 30 | 中频采集 |
| 每小时 | 60 | 标准采集 |
| 每 6 小时 | 360 | 定期更新 |
| 每 12 小时 | 720 | 半日更新 |
| 每天 | 1440 | 日常采集 |
| 每周 | 10080 | 周期采集 |

## Python 代码示例

```python
from app.models.config import CrawlerConfig
from app.core.database import get_session

async def setup_daily_schedule(config_id: int):
    """设置每日调度"""
    async with get_session() as session:
        config = await session.get(CrawlerConfig, config_id)
        config.schedule_config = {
            "enabled": True,
            "type": "interval",
            "interval_minutes": 1440,
            "keep_history": True,
            "max_history": 30
        }
        await session.commit()
```
