# 进程池回调失败导致任务停止执行的问题修复

## 问题描述

**现象：**
- 任务51执行完成后，调度器不再分发新任务
- 日志显示"进程池已满（1/1）"，但数据库中没有 PROCESSING 状态的任务
- 导致1576个 pending 任务无法执行

**根本原因：**

进程池管理器使用内存中的 `_active_workers` 计数器来跟踪活跃工作进程数。当任务完成时，通过回调函数 `_decrement_active_workers()` 递减计数器。

但在某些情况下，回调函数会失败：

1. **事件循环引用错误**：回调中使用 `asyncio.get_event_loop()` 可能获取到错误的或已关闭的事件循环
2. **run_coroutine_threadsafe 调度失败**：跨线程调度协程时可能失败但没有异常记录
3. **回调异常被吞没**：ProcessPoolExecutor 的回调异常不会传播到主线程

当回调失败时：
- `_active_workers` 没有递减（停留在 1）
- 调度器认为进程池已满，拒绝分发新任务
- 但数据库中任务已完成（status = success）
- 导致**内存状态与数据库状态不同步**

## 修复方案

### 1. 修复回调机制（process_pool.py）

**修复前：**
```python
def on_complete(f):
    loop = asyncio.get_event_loop()  # 可能获取到错误的loop
    asyncio.run_coroutine_threadsafe(
        self._decrement_active_workers(job_id, f),
        loop
    )
```

**修复后：**
```python
# 保存事件循环引用
current_loop = loop

def on_complete(f):
    try:
        # 使用保存的事件循环引用
        asyncio.run_coroutine_threadsafe(
            self._decrement_active_workers(job_id, f),
            current_loop
        )
    except Exception as e:
        # 回调失败时强制递减计数器（保险措施）
        logger.error(f"任务 {job_id} 回调执行失败: {e}", exc_info=True)
        asyncio.run_coroutine_threadsafe(
            self._force_decrement_worker(job_id),
            current_loop
        )
```

**改进点：**
- ✅ 使用闭包保存事件循环引用，避免获取错误的loop
- ✅ 添加异常捕获和日志记录
- ✅ 回调失败时强制递减计数器

### 2. 添加强制递减方法（process_pool.py）

```python
async def _force_decrement_worker(self, job_id: int):
    """强制递减活跃工作进程计数（回调失败时的保险措施）"""
    async with self._lock:
        if self._active_workers > 0:
            self._active_workers -= 1
            logger.warning(
                f"任务 {job_id} 回调失败，强制递减计数器（活跃工作进程: {self._active_workers}/{self.max_workers}）"
            )
        else:
            logger.error(f"任务 {job_id} 回调失败，但计数器已经为0，无法递减")
```

### 3. 添加数据库同步机制（process_pool.py）

```python
async def sync_worker_count_from_db(self):
    """
    从数据库同步活跃工作进程计数（防止计数器漂移）
    
    通过查询数据库中 PROCESSING 状态的任务数来校正内存中的计数器。
    这是一个保险机制，用于修复回调失败导致的计数器不同步问题。
    """
    async with get_session() as session:
        # 查询数据库中 PROCESSING 状态的任务数
        stmt = select(func.count()).where(JobQueue.status == JobStatus.PROCESSING)
        result = await session.execute(stmt)
        db_processing_count = result.scalar() or 0

        async with self._lock:
            old_count = self._active_workers
            # 数据库中的 PROCESSING 任务数才是真实的活跃工作进程数
            self._active_workers = min(db_processing_count, self.max_workers)

            if old_count != self._active_workers:
                logger.warning(
                    f"进程池计数器已同步：{old_count} → {self._active_workers} "
                    f"（数据库 PROCESSING 任务数: {db_processing_count}）"
                )
```

**设计思路：**
- 数据库状态是真实的（Single Source of Truth）
- 内存计数器可能漂移，需要定期校正
- 在每次分发任务前同步，确保状态一致

### 4. 调度器集成（scheduler.py）

```python
async def dispatch_pending_jobs(self):
    """分发待处理任务到进程池"""
    try:
        # 关键修复：在分发前先同步计数器，防止计数器漂移
        await self.pool_manager.sync_worker_count_from_db()

        # 计算可用插槽数
        active_workers = self.pool_manager.get_active_workers()
        available_slots = self.pool_manager.max_workers - active_workers
        
        # ... 后续分发逻辑
```

## 技术要点

### 为什么回调会失败？

1. **事件循环生命周期**：
   - 任务在独立进程中执行，有自己的事件循环
   - 回调在主进程的线程池中执行
   - `get_event_loop()` 可能返回错误的循环引用

2. **跨线程协程调度**：
   - `run_coroutine_threadsafe()` 是跨线程调度协程的正确方式
   - 但如果目标事件循环已关闭或繁忙，调度可能失败
   - 失败时没有明显的异常抛出

3. **ProcessPoolExecutor 特性**：
   - 回调在内部线程池中执行
   - 回调异常不会传播到主线程
   - 需要显式捕获和记录

### 为什么用数据库同步？

1. **数据库是真实状态**：
   - 任务的 status 字段由 executor 更新
   - PROCESSING = 正在执行，SUCCESS/FAILED = 已完成
   - 数据库状态不会"漂移"

2. **内存计数器可能不准**：
   - 回调失败 → 计数器不递减
   - 进程崩溃 → 计数器不更新
   - 网络抖动 → 状态更新延迟

3. **同步成本低**：
   - 每分钟同步一次（分发任务时）
   - 简单的 COUNT 查询，性能影响忽略不计
   - 确保状态一致性

## 验证方法

### 1. 检查进程池状态

```bash
python scripts/diagnose_pool_state.py
```

**正常输出：**
```
pending     :  1576 个任务
processing  :     0 个任务  ← 应该为0或正在执行的任务数
success     :    50 个任务
failed      :     0 个任务
```

### 2. 检查日志

**正常日志模式（任务完成）：**
```
11:42:48 - 提交任务 51 到进程池（当前活跃: 1/1）
11:43:45 - 任务 51 执行成功，耗时 57.01 秒
11:43:45 - 任务 51 执行完成，状态: success（活跃工作进程: 0/1）  ← 必须有这条
```

**异常日志（回调失败但已修复）：**
```
11:42:48 - 提交任务 51 到进程池（当前活跃: 1/1）
11:43:45 - 任务 51 执行成功，耗时 57.01 秒
11:43:45 - ERROR - 任务 51 回调执行失败: ...
11:43:45 - WARNING - 任务 51 回调失败，强制递减计数器（活跃工作进程: 0/1）
```

**同步日志（计数器漂移已修复）：**
```
11:44:48 - WARNING - 进程池计数器已同步：1 → 0（数据库 PROCESSING 任务数: 0）
11:44:48 - INFO - 开始扫描待处理任务（可用插槽: 1）...
```

## 后续改进建议

### 短期改进
1. ✅ 添加回调异常捕获（已完成）
2. ✅ 添加数据库同步机制（已完成）
3. ⏳ 添加监控指标（Prometheus metrics）

### 长期改进
1. **使用数据库状态代替内存计数**：
   - 完全移除 `_active_workers` 变量
   - 每次查询数据库获取 PROCESSING 任务数
   - 优点：永远准确；缺点：增加数据库查询

2. **使用消息队列**：
   - 用 Redis/RabbitMQ 管理任务队列
   - 利用消息队列的 ACK 机制保证状态一致性
   - 优点：更可靠；缺点：增加依赖

3. **健康检查机制**：
   - 定期检查 PROCESSING 任务的运行时长
   - 超时任务自动标记为失败
   - 已在 `check_timeout_jobs()` 中实现

## 总结

**修复前的问题：**
- 进程池回调可能失败，导致计数器漂移
- 内存状态与数据库状态不一致
- 任务执行停滞，需要重启应用

**修复后的保障：**
1. 回调失败时强制递减计数器（异常捕获）
2. 定期从数据库同步计数器（状态校正）
3. 详细的日志记录（问题诊断）

**效果：**
- ✅ 即使回调失败，任务也能继续执行
- ✅ 计数器漂移会被自动修复
- ✅ 不再需要重启应用来恢复执行

## 相关文件

- `app/services/process_pool.py` - 进程池管理器（主要修复）
- `app/services/scheduler.py` - 调度器（集成同步机制）
- `scripts/diagnose_pool_state.py` - 诊断脚本

## 版本信息

- 修复日期：2026-10-22
- 影响版本：所有使用进程池的版本
- 修复版本：当前版本
