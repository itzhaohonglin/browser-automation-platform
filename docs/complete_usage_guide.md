# 完整使用演示：大批量任务 + 限流 + 智能重试

## 场景说明

**需求**：采集1000个医疗器械注册证号  
**限制**：目标网站限制每2分钟最多2个请求  
**目标**：在不被封禁的情况下，尽可能高效完成采集

---

## 第一步：配置 .env 文件

创建或编辑 `.env` 文件：

```bash
# ==================== 数据库配置 ====================
DATABASE_URL=mssql+aioodbc://sa:YourPassword@localhost:1433/bap?driver=ODBC+Driver+17+for+SQL+Server

# ==================== 应用配置 ====================
APP_HOST=0.0.0.0
APP_PORT=8000
DEBUG=False
HEADLESS_MODE=True
LOG_LEVEL=INFO

# ==================== 进程池配置 ====================
# 并发数要匹配限流速率（每2分钟2个，所以2个worker足够）
MAX_WORKERS=2
WORKER_MEMORY_LIMIT_MB=512

# ==================== 严格限流配置（关键！）====================
# 启用限流
RATE_LIMIT_ENABLED=true

# 时间窗口：2分钟
RATE_LIMIT_WINDOW_MINUTES=2

# 每2分钟最多2个任务
RATE_LIMIT_MAX_TASKS=2

# 全局限流（所有任务共享配额）
RATE_LIMIT_PER_CONFIG=false

# ==================== 智能重试配置（关键！）====================
# 失败后等待13小时才重试
# 计算：1000个任务 ÷ 2个/2分钟 = 1000分钟（16.7小时）
# 设置为：1000 × 0.8 = 800 分钟（13.3小时）
RETRY_MIN_WAIT_MINUTES=800

# 如果 pending 任务超过100个，跳过重试
# 计算：1000 × 0.1 = 100
RETRY_SKIP_IF_PENDING_OVER=100

# 遵守限流规则
RETRY_RESPECT_RATE_LIMIT=true

# ==================== 重试扫描配置 ====================
# 每小时扫描一次失败任务
RETRY_INTERVAL_MINUTES=60

# 最多重试5次
MAX_RETRY_COUNT=5

# 每批重置50个失败任务
RETRY_BATCH_SIZE=50

# ==================== 任务分发配置 ====================
# 每30分钟分发一次待处理任务
DISPATCH_INTERVAL_MINUTES=30
```

---

## 第二步：启动应用

```bash
# 方式1：开发模式（推荐，可以看到实时日志）
uvicorn app.main:app --reload

# 方式2：生产模式
python -m app.main

# 方式3：后台运行
nohup uvicorn app.main:app > app.log 2>&1 &
```

启动后，查看日志确认配置加载成功：

```
INFO - 限流管理器初始化: enabled=True, window=2分钟, max_tasks=2, per_config=False
INFO - 初始化进程池管理器: max_workers=2, memory_limit=512MB
INFO - 调度器与进程池已启动
```

---

## 第三步：验证配置

### 3.1 验证限流配置

```bash
# 查询限流配置
curl http://localhost:8000/api/rate-limit/config

# 预期响应：
{
  "success": true,
  "data": {
    "enabled": true,
    "window_minutes": 2,
    "max_tasks": 2,
    "per_config": false,
    "description": {
      "max_tasks": "在 2 分钟内最多执行 2 个任务"
    }
  }
}
```

### 3.2 查询限流状态

```bash
# 查询当前限流状态
curl http://localhost:8000/api/rate-limit/status

# 预期响应：
{
  "success": true,
  "data": {
    "enabled": true,
    "window_minutes": 2,
    "max_tasks": 2,
    "current_count": 0,      # 当前窗口内已执行0个
    "remaining": 2,          # 还可以执行2个
    "utilization": "0/2 (0.0%)"
  }
}
```

---

## 第四步：准备采集配置

假设你已经在数据库中创建了采集配置（config_id=44）：

```sql
-- 查看配置
SELECT id, name, target_url, need_login 
FROM crawler_configs 
WHERE id = 44;

-- 示例结果：
-- id: 44
-- name: NHSA注册证号查询
-- target_url: https://fuwu.nhsa.gov.cn/...
-- need_login: false
```

---

## 第五步：批量创建任务

### 方式1：通过脚本批量导入

创建 `scripts/create_batch_jobs.py`：

```python
import asyncio
from app.core.database import get_session
from app.models.job import JobQueue

async def create_jobs():
    """批量创建1000个采集任务"""
    
    # 读取注册证号列表
    registration_numbers = []
    with open('registration_numbers.txt', 'r', encoding='utf-8') as f:
        registration_numbers = [line.strip() for line in f if line.strip()]
    
    print(f"共读取 {len(registration_numbers)} 个注册证号")
    
    async with get_session() as session:
        created_count = 0
        
        for reg_num in registration_numbers:
            job = JobQueue(
                config_id=44,  # NHSA配置ID
                query_params={
                    "registration_number": reg_num
                },
                priority=5  # 默认优先级
            )
            session.add(job)
            created_count += 1
            
            # 每100个提交一次
            if created_count % 100 == 0:
                await session.commit()
                print(f"已创建 {created_count} 个任务")
        
        # 提交剩余任务
        await session.commit()
        print(f"✓ 成功创建 {created_count} 个任务")

if __name__ == "__main__":
    asyncio.run(create_jobs())
```

运行脚本：

```bash
python scripts/create_batch_jobs.py
```

### 方式2：通过API创建（小批量）

```bash
# 创建单个任务
curl -X POST http://localhost:8000/api/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "config_id": 44,
    "query_params": {
      "registration_number": "国械注准20173210000"
    }
  }'
```

---

## 第六步：监控执行过程

### 6.1 实时监控限流状态

创建监控脚本 `monitor.sh`：

```bash
#!/bin/bash
echo "开始监控限流状态（每30秒刷新一次）"
echo "按 Ctrl+C 停止监控"
echo ""

while true; do
    clear
    echo "==================== $(date '+%Y-%m-%d %H:%M:%S') ===================="
    
    # 查询限流状态
    curl -s http://localhost:8000/api/rate-limit/status | \
        python3 -c "
import sys, json
data = json.load(sys.stdin)['data']
print(f\"限流状态: {'已启用' if data['enabled'] else '未启用'}\")
print(f\"时间窗口: {data['window_minutes']} 分钟\")
print(f\"配额上限: {data['max_tasks']} 个任务\")
print(f\"已使用: {data['current_count']} 个任务\")
print(f\"剩余: {data['remaining']} 个任务\")
print(f\"使用率: {data['utilization']}\")
"
    
    echo ""
    echo "----------------------------------------"
    
    # 查询任务统计（需要数据库连接）
    # 这里仅作示例，实际需要Python脚本
    echo "任务统计:"
    echo "  Pending: (查询数据库)"
    echo "  Processing: (查询数据库)"
    echo "  Success: (查询数据库)"
    echo "  Failed: (查询数据库)"
    
    sleep 30
done
```

运行监控：

```bash
chmod +x monitor.sh
./monitor.sh
```

### 6.2 查看应用日志

```bash
# 实时查看日志
tail -f app.log | grep -E "(限流|pending|重试)"

# 或者查看完整日志
tail -f app.log
```

**关键日志示例**：

```
# 正常执行
INFO - 任务 #1 已分发到进程池（优先级: 5, 1/2）
INFO - 记录任务执行: config_id=44, 当前窗口内任务数=1

# 限流生效
INFO - 任务 #3 (config_id=44) 因限流跳过，需等待 118 秒

# 智能重试跳过
WARNING - 当前有 950 个 pending 任务（超过阈值 100），跳过失败任务重试，优先处理现有任务

# 智能重试开始
INFO - 当前 pending 任务数: 50，继续重试流程
INFO - 发现 30 个失败任务（失败时间超过 800 分钟），开始重置状态
```

---

## 第七步：执行时间线预测

基于配置，预测执行过程：

```
时间    | 事件                                       | Pending | Failed | 说明
--------|-------------------------------------------|---------|--------|---------------------------
00:00   | 创建1000个任务                             | 1000    | 0      | 任务入队
00:00   | 开始执行，每2分钟2个                        | 998     | 0      | 限流生效
00:30   | 调度器分发任务                             | 985     | 10     | 发现一些失败
01:00   | 重试扫描触发                               | 940     | 25     | ❌ 跳过（pending > 100）
02:00   | 重试扫描触发                               | 880     | 40     | ❌ 跳过（pending > 100）
...     | （持续执行，重试一直被跳过）                 | ...     | ...    | 
14:00   | 重试扫描触发                               | 160     | 78     | ❌ 跳过（pending > 100）
15:00   | 重试扫描触发                               | 100     | 79     | ❌ 跳过（pending = 100）
16:00   | 重试扫描触发                               | 40      | 80     | ✅ 开始重试！
        | → 重置80个失败任务                         | 120     | 0      | 
17:00   | 重试扫描触发                               | 60      | 5      | ✅ 继续重试
        | → 重置5个失败任务                          | 65      | 0      | 
18:00   | 所有任务完成                               | 0       | 0      | ✓ 完成！
```

**预计总耗时**：16-18小时

---

## 第八步：处理特殊情况

### 情况1：需要紧急处理失败任务

如果某些失败任务很重要，需要立即重试：

```bash
# 方式1：重置限流计数器（临时突破限流）
curl -X POST http://localhost:8000/api/rate-limit/reset

# 方式2：手动重置特定任务为pending
# 需要直接操作数据库或通过API
```

### 情况2：限流太严格，想加快速度

临时修改配置：

```bash
# 编辑 .env
RATE_LIMIT_MAX_TASKS=4  # 从2改为4（每2分钟4个）

# 重启应用
# 新速度：每2分钟4个，总耗时减半
```

### 情况3：查看为什么任务被跳过

查看日志：

```bash
grep "限流跳过\|跳过重试" app.log

# 输出示例：
# 任务 #123 (config_id=44) 因限流跳过，需等待 118 秒
# 当前有 950 个 pending 任务，跳过失败任务重试
```

---

## 第九步：验证最终结果

### 9.1 查询任务统计

```python
# scripts/check_results.py
import asyncio
from sqlalchemy import select, func
from app.core.database import get_session
from app.models.job import JobQueue, JobStatus

async def check_results():
    async with get_session() as session:
        # 统计各状态任务数
        stmt = select(
            JobQueue.status,
            func.count(JobQueue.id)
        ).where(
            JobQueue.config_id == 44
        ).group_by(JobQueue.status)
        
        result = await session.execute(stmt)
        stats = dict(result.all())
        
        print("=" * 60)
        print("任务执行结果统计")
        print("=" * 60)
        print(f"成功: {stats.get(JobStatus.SUCCESS, 0)}")
        print(f"失败: {stats.get(JobStatus.FAILED, 0)}")
        print(f"待处理: {stats.get(JobStatus.PENDING, 0)}")
        print(f"处理中: {stats.get(JobStatus.PROCESSING, 0)}")
        print("=" * 60)
        
        # 查询失败原因
        if stats.get(JobStatus.FAILED, 0) > 0:
            print("\n失败任务详情:")
            failed_stmt = select(JobQueue).where(
                JobQueue.config_id == 44,
                JobQueue.status == JobStatus.FAILED
            ).limit(10)
            
            failed_result = await session.execute(failed_stmt)
            failed_jobs = failed_result.scalars().all()
            
            for job in failed_jobs:
                print(f"  任务 #{job.id}: {job.error_msg[:100]}...")

if __name__ == "__main__":
    asyncio.run(check_results())
```

运行检查：

```bash
python scripts/check_results.py
```

### 9.2 导出成功结果

```python
# scripts/export_results.py
import asyncio
import json
from sqlalchemy import select
from app.core.database import get_session
from app.models.job import JobQueue, JobStatus
from app.models.result import CrawlerResult

async def export_results():
    async with get_session() as session:
        # 查询所有成功任务的结果
        stmt = select(CrawlerResult).join(JobQueue).where(
            JobQueue.config_id == 44,
            JobQueue.status == JobStatus.SUCCESS
        )
        
        result = await session.execute(stmt)
        results = result.scalars().all()
        
        # 导出为JSON
        output_data = []
        for r in results:
            output_data.append({
                "job_id": r.job_id,
                "extracted_data": r.extracted_data,
                "created_at": r.created_at.isoformat()
            })
        
        with open('results.json', 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)
        
        print(f"✓ 已导出 {len(output_data)} 条结果到 results.json")

if __name__ == "__main__":
    asyncio.run(export_results())
```

---

## 完整配置参数速查

| 参数 | 值 | 说明 |
|------|---|------|
| `MAX_WORKERS` | 2 | 并发执行2个任务 |
| `RATE_LIMIT_ENABLED` | true | 启用限流 |
| `RATE_LIMIT_WINDOW_MINUTES` | 2 | 2分钟时间窗口 |
| `RATE_LIMIT_MAX_TASKS` | 2 | 每2分钟2个任务 |
| `RETRY_MIN_WAIT_MINUTES` | 800 | 失败后等待13小时 |
| `RETRY_SKIP_IF_PENDING_OVER` | 100 | pending>100跳过重试 |
| `RETRY_RESPECT_RATE_LIMIT` | true | 遵守限流 |

**预计效果**：
- ✅ 1000个任务在16-18小时内完成
- ✅ 严格遵守限流，不会被封禁
- ✅ 智能重试避免队列竞争
- ✅ 失败任务自动重试（最多5次）

---

## 常见问题

### Q1: 为什么前15小时失败任务不重试？
A: 这是智能重试的设计，优先保证新任务执行完，避免竞争。

### Q2: 如果有紧急失败任务怎么办？
A: 手动重置限流计数器：`curl -X POST http://localhost:8000/api/rate-limit/reset`

### Q3: 如何加快执行速度？
A: 调整限流参数：`RATE_LIMIT_MAX_TASKS=4`（需重启）

### Q4: 如何知道当前进度？
A: 查询限流状态和数据库任务统计

---

## 总结

通过这套完整的配置系统：

✅ **限流保护**：严格控制访问频率，避免被封禁  
✅ **智能重试**：避免队列竞争，提高整体效率  
✅ **灵活配置**：所有参数可调，适应不同场景  
✅ **实时监控**：API查询状态，日志记录详细  

**最终效果**：在严格限流下，高效、安全地完成大批量数据采集！🎉
