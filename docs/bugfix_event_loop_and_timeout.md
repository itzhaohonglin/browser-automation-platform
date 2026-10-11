# Bug 修复报告：Event Loop 和页面元素超时问题

**修复日期**: 2026-10-10  
**问题严重程度**: 高

## 问题描述

### 1. Event Loop 关闭错误
**症状**: 任务在第二次重试时失败，错误信息为 `RuntimeError: Event loop is closed`

**根本原因**: 
- 在 `app/services/process_pool.py` 的 `_execute_job_in_process` 函数中使用了 `asyncio.run()`
- `asyncio.run()` 会在任务完成后自动关闭 event loop
- 当进程池重用同一进程执行第二个任务时，尝试在已关闭的 event loop 上执行操作导致错误

### 2. 页面元素超时错误
**症状**: 任务在填充表单输入框时超时（10秒），错误信息为 `TimeoutError: 元素 input[name='zczbh'] 等待超时`

**根本原因**:
- 在 iframe 内的元素可能需要额外的加载时间
- 代码直接尝试填充元素，没有先等待元素变为可见和可交互状态
- 缺少对 iframe 内元素加载完成的确认

## 修复方案

### 修复 1: Event Loop 管理（app/services/process_pool.py）

**修改前**:
```python
def _execute_job_in_process(job_id: int) -> dict:
    import asyncio
    from app.services.executor import PlaywrightExecutor
    from app.core.database import get_session

    async def run_job():
        async with get_session() as session:
            executor = PlaywrightExecutor()
            result = await executor.execute_job(job_id, session)
            return result

    # 问题：asyncio.run() 会关闭 event loop
    result = asyncio.run(run_job())
    return result
```

**修改后**:
```python
def _execute_job_in_process(job_id: int) -> dict:
    import asyncio
    import sys
    from app.services.executor import PlaywrightExecutor
    from app.core.database import get_session

    # Windows 平台设置事件循环策略
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    async def run_job():
        async with get_session() as session:
            executor = PlaywrightExecutor()
            result = await executor.execute_job(job_id, session)
            return result

    # 手动管理 event loop 生命周期
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        result = loop.run_until_complete(run_job())
        return result
    finally:
        # 正确清理所有待处理的任务
        try:
            pending = asyncio.all_tasks(loop)
            for task in pending:
                task.cancel()
            if pending:
                loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
        except Exception:
            pass
        finally:
            loop.close()
```

**改进点**:
1. 使用 `asyncio.new_event_loop()` 创建新的 event loop
2. 使用 `loop.run_until_complete()` 而不是 `asyncio.run()`
3. 在 finally 块中正确清理所有待处理任务
4. 手动关闭 loop，确保资源释放

### 修复 2: 表单元素等待（app/services/executor.py）

**修改前**:
```python
self.logger.info(f"填充字段: {selector} = {value} (类型: {input_type})")

try:
    if input_type == 'text' or input_type == 'fill':
        await page.fill(selector, value, timeout=timeouts['click'])
    # ... 其他类型
except PlaywrightTimeoutError:
    raise TimeoutError(f"元素 {selector} 等待超时")
```

**修改后**:
```python
self.logger.info(f"填充字段: {selector} = {value} (类型: {input_type})")

try:
    # 先等待元素可见和可交互
    await page.wait_for_selector(selector, state='visible', timeout=timeouts['wait_selector'])
    self.logger.debug(f"元素 {selector} 已可见")

    # 再等待一小段时间确保元素完全加载（iframe 内的元素可能需要额外时间）
    await asyncio.sleep(0.5)

    if input_type == 'text' or input_type == 'fill':
        await page.fill(selector, value, timeout=timeouts['click'])
    # ... 其他类型
except PlaywrightTimeoutError:
    raise TimeoutError(f"元素 {selector} 等待超时")
```

**改进点**:
1. 在填充前显式等待元素变为可见状态（使用 `wait_for_selector`）
2. 添加 0.5 秒的额外等待，确保 iframe 内的元素完全加载
3. 使用更长的超时时间（`wait_selector` 默认 15秒，而不是 `click` 的 10秒）

## 测试验证

### 验证步骤
1. 重启服务，使用修复后的代码
2. 手动创建新的测试任务
3. 观察任务执行日志
4. 验证任务能够成功填充表单并完成采集
5. 验证失败任务重试时不再出现 event loop 错误

### 预期结果
- ✅ 任务能够成功等待并填充 iframe 内的表单元素
- ✅ 任务重试时不会出现 "Event loop is closed" 错误
- ✅ 进程池能够正确重用进程执行多个任务

## 附加说明

### 为什么不使用 asyncio.run()
`asyncio.run()` 是 Python 3.7+ 引入的便捷函数，但它有以下限制：
- 每次调用都会创建新的 event loop 并在结束时关闭
- 不适合在需要重用进程的场景中使用
- 在进程池中会导致 event loop 生命周期管理问题

### Windows 特定处理
在 Windows 上，需要设置 `WindowsProactorEventLoopPolicy` 以支持子进程和异步 I/O 操作。

## 清理工作

已执行以下清理操作：
- 重置了卡住的任务（任务 5、6、7）状态为 FAILED
- 将 retry_count 设置为 3，防止这些问题任务被自动重试
- 添加了错误说明信息

## 后续建议

1. 监控任务执行成功率
2. 如果仍有超时问题，可以考虑：
   - 增加 `wait_selector` 超时时间
   - 增加 iframe 加载后的等待时间
   - 添加更详细的调试日志
3. 考虑添加任务执行的健康检查和监控告警
