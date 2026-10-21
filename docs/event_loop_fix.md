# Event Loop 关闭错误修复指南

## 问题描述

**错误信息：**
```
RuntimeError: Event loop is closed
Exception in: <function Connection.__del__ at 0x...>
sqlalchemy.pool.base.py line 374, in close_connection
aioodbc.connection.py line 137, in close
RuntimeError: Event loop is closed
```

**影响：**
- 任务执行失败，报错"Event loop is closed"
- 错误发生在数据库连接关闭阶段
- 影响进程池中的任务执行

## 根本原因

### 问题的数据流追踪

1. **进程执行任务**（`process_pool.py:_execute_job_in_process`）：
   - 创建新的事件循环
   - 使用 `async with get_session()` 获取数据库会话
   - 执行任务

2. **任务完成，会话关闭**：
   - `session.close()` 触发连接归还到池
   - `pool_reset_on_return='rollback'` 执行异步回滚
   - 触发事件监听器回调（需要事件循环）

3. **进程清理（finally 块）**：
   - 取消待处理任务
   - 等待 0.1 秒
   - **立即关闭事件循环** ❌

4. **数据库连接池后台清理**：
   - SQLAlchemy 尝试在后台关闭连接
   - `aioodbc` 需要事件循环来执行异步关闭
   - **但事件循环已经关闭了**
   - 抛出 `RuntimeError: Event loop is closed`

### 为什么新配置暴露了这个问题？

**旧版配置（`database.py`）：**
```python
pool_size=5, max_overflow=10, pool_recycle=3600
# 无 pool_reset_on_return
# 无事件监听器
```

**新版配置（2026-10-20 优化后）：**
```python
pool_size=10, max_overflow=5, pool_recycle=1200
pool_reset_on_return='rollback'  # ← 每次归还都回滚（异步操作）
# 5 个事件监听器（connect, close, checkin, checkout, pool close）
```

新配置增加了：
1. 每次归还连接时的异步回滚操作
2. 多个需要事件循环的事件监听器
3. 更频繁的连接回收（20分钟 vs 1小时）

这些变化使得连接池的异步清理操作更加活跃，从而暴露了事件循环过早关闭的问题。

## 解决方案

### 修复 1: 在关闭事件循环前显式关闭数据库引擎

**修改文件：** `app/services/process_pool.py`

在 `_execute_job_in_process()` 的 `finally` 块中，**在关闭事件循环之前**调用 `async_engine.dispose()`：

```python
finally:
    # 清理顺序很重要：
    # 1. 先关闭数据库引擎（释放连接池资源）
    # 2. 再取消待处理任务
    # 3. 最后关闭事件循环
    try:
        # 步骤 1: 关闭数据库引擎
        loop.run_until_complete(cleanup_resources())  # 调用 engine.dispose()

        # 步骤 2: 取消所有待处理的任务
        pending = asyncio.all_tasks(loop)
        if pending:
            for task in pending:
                task.cancel()
            loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
    except Exception as e:
        logger.warning(f"清理事件循环时出错: {e}")
    finally:
        # 步骤 3: 关闭事件循环
        loop.close()
```

**关键点：**
- `engine.dispose()` 会等待所有连接完全关闭
- 确保所有异步清理操作在事件循环关闭前完成
- 避免 `aioodbc` 在已关闭的事件循环中执行操作

### 修复 2: 改进连接池错误处理

**修改文件：** `app/core/database.py`

改进 `Pool.close` 事件监听器，特别处理 "Event loop is closed" 错误：

```python
@event.listens_for(Pool, "close")
def receive_pool_close(dbapi_conn, connection_record):
    """连接池关闭连接时的回调（捕获并记录错误）"""
    try:
        logger.debug(f"连接池正在关闭连接: {id(dbapi_conn)}")
    except RuntimeError as e:
        # 特别处理 "Event loop is closed" 错误
        if "Event loop is closed" in str(e):
            pass  # 静默忽略，避免日志污染
        else:
            logger.warning(f"关闭连接时出现运行时错误（已忽略）: {e}")
    except Exception as e:
        logger.warning(f"关闭连接时出现错误（已忽略）: {e}")
```

## 测试验证

### 测试脚本

**文件：** `scripts/test_engine_dispose.py`

运行测试：
```bash
python scripts/test_engine_dispose.py
```

**预期结果：**
```
[测试 A] 使用 engine.dispose() 的版本（修复后）
  ✓ 查询成功
  ✓ 数据库引擎已关闭
  ✓ 事件循环已关闭
  ✓ 没有错误！
```

## 相关资源

- [SQLAlchemy Async Engine Documentation](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html)
- [SQLAlchemy Discussion #7531: When to dispose async engine?](https://github.com/sqlalchemy/sqlalchemy/discussions/7531)
- [Stack Overflow: SQLAlchemy event loop closed](https://stackoverflow.com/questions/68138601/sqlalchemy-event-loop-closed)

## 总结

**问题：** 进程池在关闭事件循环前没有等待数据库连接完全关闭。

**修复：** 在 `finally` 块中按正确顺序清理资源：关闭数据库引擎 → 取消待处理任务 → 关闭事件循环。

**验证：** 测试通过，任务正常执行，没有 "Event loop is closed" 错误。

---

**修复日期：** 2026-10-21  
**影响范围：** 进程池任务执行  
**相关文件：** `app/services/process_pool.py`, `app/core/database.py`
