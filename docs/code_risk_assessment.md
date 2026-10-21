# 代码隐患排查报告

**排查日期**: 2026-10-21  
**排查范围**: 异步资源管理、事件循环、并发控制、错误处理  
**排查结论**: 发现 3 个潜在风险点，建议修复

---

## 📋 排查摘要

| 类别 | 发现问题数 | 严重程度 | 状态 |
|------|-----------|---------|------|
| 资源清理 | 2 | 中等 | 待修复 |
| 错误处理 | 1 | 低 | 待修复 |
| 已修复问题 | 1 | 高 | ✅ 已修复 |

---

## ✅ 已修复的问题

### 1. 事件循环关闭导致的数据库连接错误 ✅

**状态**: 已在 commit `6829fba` 中修复

**问题描述**:
- 进程池工作进程退出时，事件循环在数据库连接池清理前关闭
- 导致 `RuntimeError: Event loop is closed` 错误

**修复方案**:
1. 在 `process_pool.py` 中添加 `cleanup_resources()` 函数
2. 清理顺序：引擎关闭 → 任务取消 → 事件循环关闭
3. 在 `database.py` 中添加错误捕获，静默忽略预期的关闭错误

**验证工具**:
- `scripts/test_engine_dispose.py`
- `scripts/monitor_connection_pool.py`

---

## ⚠️ 发现的潜在风险

### 风险 1: Playwright 资源清理缺少异常保护（中等严重性）

**位置**: `app/services/executor.py:2144-2153`

**问题代码**:
```python
finally:
    # 资源清理（必须执行）
    if page:
        await page.close()           # ❌ 如果失败会阻止后续清理
    if context:
        await context.close()        # ❌ 如果 page.close() 失败，不会执行
    if browser:
        await browser.close()        # ❌ 如果前面失败，不会执行
    if playwright:
        await playwright.stop()      # ❌ 如果前面失败，不会执行
```

**风险分析**:
- **严重程度**: 中等
- **影响范围**: 单个任务执行失败可能导致浏览器进程泄漏
- **触发条件**: 
  - 网络异常导致 page.close() 失败
  - 浏览器进程崩溃
  - 超时异常
- **后果**: 
  - Playwright 进程未释放（内存泄漏）
  - 浏览器进程残留（资源泄漏）
  - 长时间运行后系统资源耗尽

**推荐修复**:
```python
finally:
    # 资源清理（逐个保护，确保全部执行）
    if page:
        try:
            await page.close()
            logger.debug(f"任务 {job_id}: 页面已关闭")
        except Exception as e:
            logger.warning(f"任务 {job_id}: 关闭页面失败（已忽略）: {e}")
    
    if context:
        try:
            await context.close()
            logger.debug(f"任务 {job_id}: 浏览器上下文已关闭")
        except Exception as e:
            logger.warning(f"任务 {job_id}: 关闭上下文失败（已忽略）: {e}")
    
    if browser:
        try:
            await browser.close()
            logger.debug(f"任务 {job_id}: 浏览器已关闭")
        except Exception as e:
            logger.warning(f"任务 {job_id}: 关闭浏览器失败（已忽略）: {e}")
    
    if playwright:
        try:
            await playwright.stop()
            logger.debug(f"任务 {job_id}: Playwright 已停止")
        except Exception as e:
            logger.warning(f"任务 {job_id}: 停止 Playwright 失败（已忽略）: {e}")
```

**参考案例**:
`process_pool.py:82-107` 中的清理逻辑已经使用了这种保护模式。

---

### 风险 2: WebSocket 广播可能阻塞主流程（中等严重性）

**位置**: `app/services/executor.py` 多处调用 `await self._broadcast_*`

**问题代码**:
```python
# 多处调用示例
await self._broadcast_log("info", "页面加载完成")
await self._broadcast_progress(job_id=job_id, data={...})
```

**风险分析**:
- **严重程度**: 中等
- **影响范围**: 任务执行性能和稳定性
- **触发条件**:
  - WebSocket 连接断开但未清理
  - WebSocket 发送缓冲区满
  - 网络延迟导致发送超时
- **后果**:
  - 任务执行被阻塞（等待 WebSocket 发送完成）
  - 级联失败（一个慢连接拖累所有任务）
  - 用户体验下降

**当前保护措施** ✅:
`app/api/websocket.py:44-78` 已经实现了基本保护：
- 捕获 `WebSocketDisconnect` 异常
- 自动清理断开的连接
- 使用连接快照避免迭代冲突

**推荐增强**:
```python
# 在 websocket.py 的 broadcast 方法中添加超时保护
async def broadcast(self, message: dict, timeout: float = 1.0):
    """
    向所有活跃连接广播消息（带超时保护）
    
    Args:
        message: 要广播的消息字典
        timeout: 单个连接的发送超时时间（秒）
    """
    if not self.active_connections:
        return

    disconnected = set()
    connections_snapshot = self.active_connections.copy()

    for connection in connections_snapshot:
        try:
            # 添加超时保护
            await asyncio.wait_for(
                connection.send_json(message),
                timeout=timeout
            )
        except asyncio.TimeoutError:
            logger.warning(f"WebSocket 发送超时（{timeout}s），移除连接")
            disconnected.add(connection)
        except WebSocketDisconnect:
            logger.debug("WebSocket disconnected during broadcast")
            disconnected.add(connection)
        except Exception as e:
            logger.warning(f"Error sending message to WebSocket: {e}")
            disconnected.add(connection)

    # 清理断开的连接
    for connection in disconnected:
        self.active_connections.discard(connection)
```

---

### 风险 3: 调度器关闭时可能丢失任务状态（低严重性）

**位置**: `app/services/scheduler.py:340-344`

**问题代码**:
```python
async def shutdown(self):
    """优雅停止调度器"""
    self.logger.info("正在停止任务调度器...")
    self.scheduler.shutdown(wait=True)  # ❌ 如果任务正在执行可能被中断
    self.logger.info("任务调度器已停止")
```

**风险分析**:
- **严重程度**: 低
- **影响范围**: 应用关闭时正在执行的调度任务
- **触发条件**: 
  - 应用重启/关闭时正好有调度任务在执行
  - `retry_failed_jobs` 或 `dispatch_pending_jobs` 正在运行
- **后果**:
  - 任务状态可能不一致（例如：已更新为 processing 但未提交到进程池）
  - 数据库事务可能未提交
- **实际影响**: 较小（下次启动时会重新处理）

**推荐增强**:
```python
async def shutdown(self):
    """优雅停止调度器"""
    self.logger.info("正在停止任务调度器...")
    
    try:
        # 1. 暂停调度器（不再接受新任务）
        self.scheduler.pause()
        self.logger.info("调度器已暂停，等待运行中任务完成...")
        
        # 2. 等待运行中的任务完成（最多等待 30 秒）
        max_wait = 30
        for i in range(max_wait):
            running_jobs = self.scheduler.get_jobs()
            if not running_jobs:
                break
            if i % 5 == 0:  # 每 5 秒日志一次
                self.logger.info(f"等待 {len(running_jobs)} 个调度任务完成...")
            await asyncio.sleep(1)
        
        # 3. 关闭调度器
        self.scheduler.shutdown(wait=False)  # 使用 wait=False 避免阻塞
        self.logger.info("任务调度器已停止")
        
    except Exception as e:
        self.logger.error(f"停止调度器时出错: {e}", exc_info=True)
        # 强制关闭
        try:
            self.scheduler.shutdown(wait=False)
        except Exception:
            pass
```

---

## 🔍 其他检查项（未发现问题）

### ✅ 数据库连接管理
- **检查位置**: `app/core/database.py`
- **状态**: 健康
- **验证**:
  - 使用 `get_session()` 上下文管理器 ✅
  - 异常时自动 rollback ✅
  - finally 块中正确关闭 ✅
  - 连接池配置合理 ✅

### ✅ 进程池管理
- **检查位置**: `app/services/process_pool.py`
- **状态**: 健康
- **验证**:
  - 事件循环清理顺序正确 ✅
  - 使用 try-finally 保护 ✅
  - 取消任务后等待完成 ✅
  - 显式调用 `async_engine.dispose()` ✅

### ✅ WebSocket 连接管理
- **检查位置**: `app/api/websocket.py`
- **状态**: 基本健康（建议增强超时保护）
- **验证**:
  - 自动清理断开连接 ✅
  - 捕获发送异常 ✅
  - 使用集合快照避免迭代冲突 ✅
  - 建议：添加超时保护 ⚠️

### ✅ 应用生命周期管理
- **检查位置**: `app/main.py:86-138`
- **状态**: 健康
- **验证**:
  - 启动失败时清理部分初始化资源 ✅
  - 关闭时优雅停止调度器和进程池 ✅
  - 异常处理完善 ✅

---

## 📊 风险评估矩阵

| 风险项 | 发生概率 | 影响程度 | 风险等级 | 优先级 |
|-------|---------|---------|---------|-------|
| Playwright 资源泄漏 | 中 | 高 | **中** | P1 |
| WebSocket 阻塞任务 | 低 | 中 | **中** | P2 |
| 调度器状态丢失 | 低 | 低 | **低** | P3 |

---

## 🛠️ 修复建议

### 优先级 P1（推荐立即修复）

**风险 1: Playwright 资源清理**
- **修改文件**: `app/services/executor.py`
- **预计工作量**: 15 分钟
- **测试方法**: 
  1. 模拟网络异常
  2. 运行 100 个任务后检查进程残留
  3. 使用 `ps aux | grep chromium` 验证

### 优先级 P2（建议近期修复）

**风险 2: WebSocket 超时保护**
- **修改文件**: `app/api/websocket.py`
- **预计工作量**: 10 分钟
- **测试方法**:
  1. 模拟慢连接（使用网络限流工具）
  2. 验证任务不被阻塞
  3. 验证慢连接被自动清理

### 优先级 P3（可选优化）

**风险 3: 调度器优雅关闭**
- **修改文件**: `app/services/scheduler.py`
- **预计工作量**: 20 分钟
- **测试方法**:
  1. 启动应用并等待调度任务执行
  2. 在任务执行中途关闭应用
  3. 检查数据库状态是否一致

---

## 🔧 修复验证清单

修复完成后，执行以下验证：

### 1. 资源泄漏测试
```bash
# 运行 1000 个任务
python scripts/stress_test_executor.py --count 1000

# 检查进程残留
ps aux | grep chromium
ps aux | grep playwright

# 检查内存使用
free -h
```

### 2. WebSocket 性能测试
```bash
# 模拟 50 个并发连接
python scripts/test_websocket_broadcast.py --connections 50

# 监控任务执行时间
python scripts/monitor_task_execution_time.py
```

### 3. 优雅关闭测试
```bash
# 启动应用
python -m app.main &

# 等待 60 秒（让调度器开始执行）
sleep 60

# 发送 SIGTERM 信号
kill -TERM $PID

# 检查日志和数据库状态
tail -f logs/app.log
```

---

## 📚 参考文档

- [事件循环修复说明](event_loop_fix.md)
- [数据库连接池优化](database_connection_pool_optimization.md)
- [Playwright 最佳实践](https://playwright.dev/python/docs/library#browser-contexts)
- [FastAPI WebSocket 指南](https://fastapi.tiangolo.com/advanced/websockets/)

---

## 🔄 后续建议

### 1. 增加监控指标
```python
# 在 metrics_collector 中添加
- playwright_instances_count: 活跃的 Playwright 实例数
- websocket_connections_count: 活跃的 WebSocket 连接数
- resource_cleanup_failures: 资源清理失败次数
```

### 2. 增加健康检查端点
```python
@app.get("/health/resources")
async def resource_health():
    return {
        "playwright_instances": get_playwright_count(),
        "websocket_connections": len(websocket_manager.active_connections),
        "database_connections": async_engine.pool.size()
    }
```

### 3. 定期审计
- **频率**: 每月
- **检查项**:
  - 进程残留（`ps aux | grep chromium`）
  - 内存增长趋势（`free -h`）
  - 错误日志分析（`grep "WARNING\|ERROR" logs/app.log`）

---

**报告生成时间**: 2026-10-21  
**下次审计时间**: 2026-11-21
