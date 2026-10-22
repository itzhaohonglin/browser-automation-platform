# 更新日志 - 任务超时自动检测功能

## 版本信息
- **更新日期**: 2026-10-22
- **功能**: 任务超时自动检测和失败标记
- **影响范围**: 调度器、配置文件

## 问题背景

### 发现的问题
在生产环境中发现 4 个任务卡在 `processing` 状态超过 19 小时，导致：
- 进程池被占满（MAX_WORKERS=1）
- 新任务无法执行（1571 个任务在 pending 队列中等待）
- 系统看起来"卡死"，实际上是僵尸任务阻塞

### 根本原因
1. 工作进程崩溃或异常退出时，任务状态未能正确更新
2. 没有超时检测机制，无法自动恢复
3. 需要人工介入才能发现和解决问题

## 解决方案

### 新增功能：任务超时自动检测

调度器会定期扫描所有 `processing` 状态的任务：
- 如果任务运行时间超过阈值（默认 60 分钟）
- 自动标记为 `failed`，设置错误信息
- 递增重试次数，让重试机制接管
- 通过 WebSocket 实时推送告警

## 代码变更

### 1. 新增配置项 (`app/core/config.py`)

```python
# 任务超时检测配置
TASK_TIMEOUT_CHECK_ENABLED: bool = True  # 是否启用任务超时检测
TASK_TIMEOUT_MINUTES: int = 60  # 任务超时阈值（分钟）
TASK_TIMEOUT_CHECK_INTERVAL_MINUTES: int = 10  # 超时检测间隔（分钟）
```

### 2. 调度器新增超时检测任务 (`app/services/scheduler.py`)

**新增方法**:
- `check_timeout_jobs()`: 检测并处理超时任务

**启动时注册**:
```python
if settings.TASK_TIMEOUT_CHECK_ENABLED:
    self.scheduler.add_job(
        func=self.check_timeout_jobs,
        trigger=IntervalTrigger(minutes=settings.TASK_TIMEOUT_CHECK_INTERVAL_MINUTES),
        id='check_timeout_jobs',
        name='检测超时任务',
        next_run_time=datetime.now() + timedelta(minutes=2)
    )
```

### 3. 配置文件更新

已同步更新以下文件：
- ✅ `.env.example` (根目录)
- ✅ `dist/browser-automation-platform/.env.example` (打包版)
- ✅ `dist/browser-automation-platform/_internal/.env.example` (打包版内部)

新增配置项：
```bash
# 任务超时检测配置
TASK_TIMEOUT_CHECK_ENABLED=true
TASK_TIMEOUT_MINUTES=60
TASK_TIMEOUT_CHECK_INTERVAL_MINUTES=10
```

## 使用指南

### 默认配置（推荐）
```bash
TASK_TIMEOUT_CHECK_ENABLED=true
TASK_TIMEOUT_MINUTES=60
TASK_TIMEOUT_CHECK_INTERVAL_MINUTES=10
```

### 根据任务特点调整

**快速任务（1-5 分钟/任务）**
```bash
TASK_TIMEOUT_MINUTES=30
```

**慢速任务（15-30 分钟/任务）**
```bash
TASK_TIMEOUT_MINUTES=120
```

**禁用超时检测**
```bash
TASK_TIMEOUT_CHECK_ENABLED=false
```

## 工作流程

```
1. 任务执行中
   └─ status: processing

2. 进程崩溃/卡死
   └─ 任务状态未更新，卡在 processing

3. 超时检测触发（每 10 分钟）
   ├─ 发现运行时长超过阈值
   ├─ 标记为 failed
   ├─ 设置 error_msg
   └─ retry_count += 1

4. 重试机制触发（30 分钟后）
   ├─ 发现 failed 任务
   ├─ retry_count < MAX_RETRY_COUNT
   └─ 重置为 pending，重新执行

5. 任务重新执行
   └─ 正常完成或再次超时
```

## 测试验证

### 本次修复验证

**修复前**:
```
pending: 1571
processing: 4  ← 僵尸任务
success: 51
failed: 0
```

**修复后**:
```
pending: 1571
processing: 0  ← 已清理
success: 51
failed: 4      ← 转为失败，等待重试
```

### 功能验证

1. **配置加载验证**
```bash
python -c "from app.core.config import settings; print(settings.TASK_TIMEOUT_CHECK_ENABLED)"
# 输出: True
```

2. **配置同步验证**
```bash
python scripts/sync_env_config.py
# 应显示所有文件已包含配置
```

3. **手动检测超时任务**
```python
python -c "
import asyncio
from app.core.database import get_session
from app.models.job import JobQueue, JobStatus
from sqlalchemy import select
from datetime import datetime

async def check():
    async with get_session() as session:
        stmt = select(JobQueue).where(JobQueue.status == JobStatus.PROCESSING)
        result = await session.execute(stmt)
        jobs = result.scalars().all()
        
        for job in jobs:
            duration = (datetime.now() - job.updated_at).total_seconds() / 60
            print(f'任务 {job.id}: 运行 {duration:.1f} 分钟')

asyncio.run(check())
"
```

## 相关文档

- **详细说明**: `docs/task_timeout_detection.md`
- **配置参考**: `docs/package_config_quick_ref.md`
- **智能重试**: `docs/smart_retry_optimization.md`

## 注意事项

1. **阈值设置建议**
   - 设置为平均任务耗时的 2-3 倍
   - 避免误杀正常运行的慢任务

2. **与重试机制配合**
   - 超时任务会递增 retry_count
   - 确保 MAX_RETRY_COUNT 设置合理（默认 3）
   - 超时任务需等待 RETRY_MIN_WAIT_MINUTES 才会重试

3. **监控建议**
   - 关注日志中的超时警告信息
   - 通过 WebSocket 监控看板实时查看
   - 如果频繁超时，考虑增加阈值或排查任务问题

## 后续优化建议

1. **进程健康检查**
   - 添加进程心跳机制
   - 主动检测进程是否存活

2. **资源监控**
   - 监控内存使用
   - 监控浏览器进程

3. **告警增强**
   - 超时次数过多时发送邮件告警
   - 集成钉钉/企业微信通知

## 回滚方案

如需禁用此功能：

1. **临时禁用**
```bash
# 修改 .env 文件
TASK_TIMEOUT_CHECK_ENABLED=false
```

2. **完全回滚**
```bash
# 回滚代码到之前的提交
git revert <commit-hash>
```

## 相关脚本

- `scripts/sync_env_config.py`: 同步配置文件
- `scripts/verify_migration.py`: 验证数据库（如有需要）

## 测试建议

上线前建议测试：
1. 启动服务，确认超时检测任务已注册
2. 人工创建一个长时间运行的测试任务
3. 等待超时检测触发，验证任务被正确标记为 failed
4. 验证重试机制是否正常工作

---

**更新人**: Claude Code  
**审核人**: 待审核  
**部署状态**: 已部署到开发环境
