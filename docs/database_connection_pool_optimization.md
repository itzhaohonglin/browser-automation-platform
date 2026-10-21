# 数据库连接池优化说明

## 问题描述

在长期运行过程中，系统出现数据库连接关闭错误：

```
sqlalchemy\pool\base.py", line 374, in _close_connection
sqlalchemy\engine\default.py", line 705, in do_terminate
sqlalchemy\connectors\aioodbc.py", line 87, in close
```

## 根本原因分析

### 原因 1: 连接池配置不适合长期运行

**旧配置问题：**
```python
pool_size=5                    # 连接池太小，无法满足并发需求
max_overflow=10                # 溢出连接过多，不受池管理
pool_recycle=3600              # 1小时回收，但 SQL Server 30分钟空闲超时
```

**影响：**
- 3 个工作进程 + 调度器 + API 请求 = 需要 10+ 连接
- 频繁创建/销毁溢出连接，增加错误概率
- 连接在 SQL Server 超时后才被回收，导致关闭失败

### 原因 2: SQL Server 空闲连接超时

SQL Server 默认行为：
- 空闲连接 30 分钟后自动关闭
- `pool_recycle=3600`（1小时）尝试关闭已被服务器关闭的连接
- 触发 `do_terminate` 错误

### 原因 3: 进程池任务取消时的会话泄漏

当任务被取消时，`async with get_session()` 可能无法完成 `__aexit__`，导致：
- 连接未归还到连接池
- 事务未回滚
- 连接资源泄漏

## 解决方案

### 1. 优化连接池配置

**新配置（app/core/database.py）：**
```python
async_engine = create_async_engine(
    DATABASE_URL,
    echo=settings.DEBUG,
    pool_pre_ping=True,                   # 使用前检测连接有效性
    pool_size=10,                         # 增加到 10（支持并发）
    max_overflow=5,                       # 减少到 5（提高池管理效率）
    pool_recycle=1200,                    # 20分钟回收（避免 SQL Server 30分钟超时）
    pool_timeout=30,                      # 获取连接超时
    pool_reset_on_return='rollback',      # 归还时自动回滚
    connect_args={
        "timeout": 30,
        "autocommit": False
    },
    echo_pool=settings.DEBUG              # 调试模式显示连接池日志
)
```

**优化点：**
- ✅ `pool_size=10`：满足并发需求（3 工作进程 + 3 调度器 + 4 预留）
- ✅ `max_overflow=5`：减少溢出，总容量 15 连接
- ✅ `pool_recycle=1200`：20 分钟回收，避免 SQL Server 30 分钟超时
- ✅ `pool_timeout=30`：防止无限等待
- ✅ `pool_reset_on_return='rollback'`：自动清理未提交事务

### 2. 添加连接池事件监听

**功能：**
- 记录连接创建/关闭/签入/签出事件
- 捕获并忽略关闭时的错误
- 调试模式下输出详细日志

**代码（app/core/database.py）：**
```python
@event.listens_for(Pool, "close")
def receive_pool_close(dbapi_conn, connection_record):
    """连接池关闭连接时的回调（捕获并记录错误）"""
    try:
        logger.debug(f"连接池正在关闭连接: {id(dbapi_conn)}")
    except Exception as e:
        # 忽略关闭时的错误，防止影响应用运行
        logger.warning(f"关闭连接时出现错误（已忽略）: {e}")
```

### 3. 增强进程池会话管理

**优化：**
- 任务取消时显式回滚和关闭会话
- 添加错误处理和日志
- 延迟事件循环关闭，确保资源释放

**代码（app/services/process_pool.py）：**
```python
async def run_job():
    session = None
    try:
        async with get_session() as session:
            executor = PlaywrightExecutor()
            result = await executor.execute_job(job_id, session)
            return result
    except asyncio.CancelledError:
        # 任务被取消时，确保会话正确关闭
        logger.warning(f"任务 {job_id} 被取消，正在清理会话")
        if session:
            try:
                await session.rollback()
                await session.close()
            except Exception as e:
                logger.error(f"取消任务时关闭会话失败: {e}")
        raise
```

## 使用监控工具

### 实时监控连接池状态

```bash
python scripts/monitor_connection_pool.py
```

**输出示例：**
```
[2026-10-20 14:30:15]
  连接池大小: 10
  最大溢出: 5
  当前连接数: 7
  空闲连接: 3
  使用中连接: 4
  溢出连接: 0
  利用率: 46.7%
```

**告警规则：**
- ⚠️ 使用溢出连接：超出 pool_size
- ⚠️ 连接池利用率过高：> 80%
- ⚠️ 无空闲连接：可能即将阻塞

### 诊断连接泄漏

1. 启动监控工具
2. 观察"使用中连接"是否持续增长
3. 检查"空闲连接"是否归零
4. 确认任务完成后连接是否归还

## 验证修复

### 1. 检查配置

```bash
python -c "from app.core.database import async_engine; print(f'pool_size={async_engine.pool._pool.maxsize}, max_overflow={async_engine.pool._max_overflow}, pool_recycle={async_engine.pool._recycle}')"
```

**预期输出：**
```
pool_size=10, max_overflow=5, pool_recycle=1200
```

### 2. 长期运行测试

运行系统 24 小时，观察：
- 不再出现 `do_terminate` 错误
- 连接池状态稳定
- 无连接泄漏

### 3. 压力测试

批量导入任务，观察：
- 连接池利用率
- 溢出连接数
- 任务完成后连接归还

## 配置建议

根据不同场景调整参数：

### 高并发场景（大量短任务）
```python
pool_size=15                   # 更大的连接池
max_overflow=5                 # 适度溢出
pool_recycle=600               # 10分钟回收（更激进）
```

### 低并发场景（少量长任务）
```python
pool_size=5                    # 较小的连接池
max_overflow=3                 # 最小溢出
pool_recycle=1800              # 30分钟回收（更保守）
```

### SQL Server 特定优化
```python
pool_recycle=1200              # 必须 < 30分钟（SQL Server 空闲超时）
pool_pre_ping=True             # 必须启用（检测断开连接）
pool_reset_on_return='rollback'  # 推荐（自动清理事务）
```

## 监控和维护

### 日常检查

1. **查看日志**：检查是否有连接关闭错误
2. **监控连接数**：确保不超过 pool_size + max_overflow
3. **检查空闲连接**：确保任务完成后连接归还

### 调试模式

在 `.env` 中启用调试：
```bash
DEBUG=true
```

将输出详细的连接池事件日志。

### 性能调优

如果遇到性能问题：
1. 增加 `pool_size`（但不要超过 SQL Server 最大连接数）
2. 减少 `max_overflow`（避免频繁创建/销毁连接）
3. 调整 `pool_recycle`（根据 SQL Server 超时设置）

## 相关文档

- SQLAlchemy 连接池文档：https://docs.sqlalchemy.org/en/20/core/pooling.html
- SQL Server 连接超时设置：查询 `sp_configure 'remote query timeout'`
- aioodbc 文档：https://aioodbc.readthedocs.io/

## 故障排查

### 问题：仍然出现连接关闭错误

**排查步骤：**
1. 检查 `pool_recycle` 是否小于 SQL Server 超时
2. 确认 `pool_pre_ping=True` 已启用
3. 查看连接池监控工具，确认无连接泄漏

### 问题：连接池耗尽

**排查步骤：**
1. 使用监控工具查看连接状态
2. 检查是否有长时间运行的查询
3. 确认所有 `get_session()` 都使用了 `async with`

### 问题：性能下降

**排查步骤：**
1. 检查连接池利用率（是否过高）
2. 增加 `pool_size`（如果利用率 > 80%）
3. 检查是否频繁使用溢出连接

## 总结

此次优化通过以下措施解决了长期运行时的连接问题：

1. ✅ 增大连接池，减少溢出连接
2. ✅ 调整回收时间，避免 SQL Server 超时
3. ✅ 增强会话管理，防止资源泄漏
4. ✅ 添加监控工具，便于诊断问题

**关键参数：**
- `pool_size=10`（原 5）
- `max_overflow=5`（原 10）
- `pool_recycle=1200`（原 3600）

**预期效果：**
- 不再出现连接关闭错误
- 连接池状态稳定
- 长期运行无资源泄漏
