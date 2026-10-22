# 调度器停止问题 - 根本原因和彻底解决方案

## 问题根源确认

通过深入分析日志和代码，确认了真正的问题：

### 问题表现
- 任务执行到51后停止（第一次）
- 重启后执行到101又停止（第二次）
- 每次停止后，调度器继续运行但不再分发新任务
- 数据库中有大量pending任务等待

### 根本原因

**进程池回调未执行，导致内存计数器没有递减！**

具体流程：
1. 任务101在子进程中执行完成，返回`{"status": "success"}`
2. 子进程的finally块执行日志记录（但这部分日志可能没有输出到主日志文件）
3. **关键：进程池的回调函数（`on_complete`）应该被触发**
4. **但回调没有执行！**导致`_active_workers`计数器没有从1递减到0
5. 调度器认为进程池已满（`available_slots = max_workers - active_workers = 1 - 1 = 0`）
6. 所以不再分发新任务

### 为什么回调会失败？

查看`process_pool.py`第169-184行的回调代码：

```python
def on_complete(f):
    try:
        asyncio.run_coroutine_threadsafe(
            self._decrement_active_workers(job_id, f),
            current_loop
        )
    except Exception as e:
        logger.error(f"任务 {job_id} 回调执行失败: {e}", exc_info=True)
        asyncio.run_coroutine_threadsafe(
            self._force_decrement_worker(job_id),
            current_loop
        )
```

可能的原因：
1. **事件循环关闭**：如果主进程的事件循环在回调触发前关闭
2. **线程问题**：`run_coroutine_threadsafe`在某些情况下会失败
3. **超时**：回调等待太久导致超时
4. **异常被静默吞噬**：即使有try-except，异常可能在其他地方被吞噬

### 证据

1. **任务51**：
   - 11:43:45 执行成功
   - 12:33:46 被取消（你重启了服务）
   - **没有回调日志**

2. **任务101**：
   - 13:52:51 执行成功
   - 之后调度器一直运行但不分发任务
   - **没有回调日志**

3. **对比任务100**：
   - 13:51:51 执行成功
   - 13:51:51 **有回调日志**："任务 100 执行完成，状态: success（活跃工作进程: 0/1）"

## 彻底解决方案

### 方案1：数据库状态驱动（推荐）

**不依赖内存计数器，直接从数据库查询PROCESSING任务数！**

修改`scheduler.py`的`dispatch_pending_jobs()`：

```python
async def dispatch_pending_jobs(self):
    """分发待处理任务到进程池"""
    if self.pool_manager is None:
        return

    try:
        # ===关键修复：直接从数据库查询活跃任务数===
        async with get_session() as session:
            stmt = select(func.count()).where(JobQueue.status == JobStatus.PROCESSING)
            result = await session.execute(stmt)
            db_processing_count = result.scalar() or 0

        # 使用数据库的真实值，而不是内存计数器
        available_slots = self.pool_manager.max_workers - db_processing_count

        if available_slots <= 0:
            self.logger.info(
                f"进程池已满（数据库PROCESSING: {db_processing_count}/{self.pool_manager.max_workers}），"
                f"跳过任务分发"
            )
            return

        self.logger.info(
            f"开始扫描待处理任务（数据库PROCESSING: {db_processing_count}, "
            f"可用插槽: {available_slots}）..."
        )

        # 查询pending任务并分发
        async with get_session() as session:
            stmt = select(JobQueue).where(
                JobQueue.status == JobStatus.PENDING
            ).order_by(
                JobQueue.priority.desc(),
                JobQueue.created_at.asc()
            ).limit(available_slots)

            result = await session.execute(stmt)
            pending_jobs = result.scalars().all()

            if not pending_jobs:
                self.logger.info(f"没有待处理任务")
                return

            # ... 剩余代码不变 ...
```

### 方案2：增强回调可靠性

在`process_pool.py`中增加保险机制：

```python
future.add_done_callback(on_complete)

# 新增：设置超时检测
async def check_callback():
    """超时检测：如果5秒后回调还没执行，强制递减"""
    await asyncio.sleep(5)
    async with self._lock:
        if self._active_workers > 0:
            # 检查任务是否真的还在运行
            async with get_session() as session:
                stmt = select(JobQueue).where(
                    JobQueue.id == job_id,
                    JobQueue.status == JobStatus.PROCESSING
                )
                result = await session.execute(stmt)
                job = result.scalar_one_or_none()
                
                if not job:
                    # 任务已完成但回调没执行，强制递减
                    self._active_workers -= 1
                    logger.warning(
                        f"任务 {job_id} 回调超时，强制递减计数器"
                        f"（活跃: {self._active_workers}/{self.max_workers}）"
                    )

asyncio.create_task(check_callback())
```

### 方案3：定期同步机制（已有，需增强）

当前代码在`scheduler.py`第199行有`sync_worker_count_from_db()`，但调用后如果发现计数器正确就不记录日志。

**问题**：如果计数器不正确，同步后会修正，但**已经错过了一轮分发**！

增强方案：
```python
async def dispatch_pending_jobs(self):
    # 每次分发前强制同步
    await self.pool_manager.sync_worker_count_from_db()
    
    # 再次检查可用插槽
    active_workers = self.pool_manager.get_active_workers()
    available_slots = self.pool_manager.max_workers - active_workers
    
    # 记录同步结果（改为INFO级别）
    self.logger.info(
        f"进程池状态同步完成: active={active_workers}, max={self.pool_manager.max_workers}, "
        f"available={available_slots}"
    )
    
    # ... 继续分发逻辑 ...
```

## 立即修复步骤

1. **运行诊断脚本**：
   ```bash
   python scripts/fix_stuck_pool.py
   ```
   检查是否有卡住的PROCESSING任务，如果有，重置为PENDING

2. **应用代码修复**：
   采用**方案1（数据库驱动）**，这是最可靠的方案

3. **重启服务**：
   ```bash
   cd dist/browser-automation-platform
   startup.bat
   ```

4. **观察日志**：
   确认新的日志格式：
   ```
   开始扫描待处理任务（数据库PROCESSING: 0, 可用插槽: 1）...
   发现 1 个待处理任务，开始分发
   ```

## 为什么方案1最好？

1. **不依赖回调**：回调失败也不影响
2. **真实状态**：数据库是唯一真相来源
3. **自动恢复**：即使出问题，下一轮扫描会自动修正
4. **简单可靠**：逻辑清晰，不会出现计数器漂移

## 后续监控

添加告警指标：
- 如果数据库PROCESSING > 0 但进程池计数器=0 → 计数器漂移告警
- 如果连续10次扫描都没有发现任务，但数据库有pending → 查询问题告警
