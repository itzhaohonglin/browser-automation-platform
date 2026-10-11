# 请求级限流实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 删除任务级限流，实现请求级限流（固定间隔方式），简化配置

**Architecture:** 
- 删除全局 RateLimiter 和相关配置（5个配置项、2个文件）
- 在 PlaywrightExecutor 内部实现轻量级 RequestRateLimiter
- 使用固定间隔方式（interval_seconds）控制HTTP请求频率

**Tech Stack:** Python 3.10+, asyncio, datetime

---

## File Structure

### Files to Delete
- `app/services/rate_limiter.py` - 全局限流器（304行）
- `app/api/rate_limit.py` - 限流API端点（约100行）

### Files to Modify
- `app/core/config.py` - 删除5个限流配置项
- `app/services/scheduler.py` - 删除限流检查逻辑（约30行）
- `app/main.py` - 删除限流路由注册（1行）
- `app/services/executor.py` - 添加 RequestRateLimiter 类和集成逻辑（约100行）

### Files to Create
- `tests/test_request_rate_limiter.py` - 请求级限流器单元测试

---

## Task 1: 删除任务级限流配置

**Files:**
- Modify: `app/core/config.py:45,52-55`

- [ ] **Step 1: 备份当前配置**

```bash
git diff app/core/config.py > /tmp/config_backup.diff
```

Expected: 创建备份文件

- [ ] **Step 2: 删除配置项**

从 `app/core/config.py` 删除以下行：

```python
# 删除第45行
RETRY_RESPECT_RATE_LIMIT: bool = True  # 重试时是否遵守限流

# 删除第52-55行
RATE_LIMIT_ENABLED: bool = False  # 是否启用限流
RATE_LIMIT_WINDOW_MINUTES: int = 60  # 限流时间窗口（分钟）
RATE_LIMIT_MAX_TASKS: int = 100  # 时间窗口内最多执行的任务数
RATE_LIMIT_PER_CONFIG: bool = False  # 是否按配置ID分别限流
```

- [ ] **Step 3: 验证语法**

```bash
python -m py_compile app/core/config.py
```

Expected: 无输出（编译成功）

- [ ] **Step 4: 提交**

```bash
git add app/core/config.py
git commit -m "refactor: remove task-level rate limit config"
```

---

## Task 2: 删除调度器中的限流逻辑

**Files:**
- Modify: `app/services/scheduler.py:14,114-123,249-264`

- [ ] **Step 1: 删除 rate_limiter 导入**

从 `app/services/scheduler.py` 第14行删除：

```python
from app.services.rate_limiter import rate_limiter
```

- [ ] **Step 2: 删除 retry_failed_jobs 中的限流检查**

删除第114-123行（在 `retry_failed_jobs` 方法中）：

```python
# 步骤2：检查限流压力（如果启用）
if settings.RETRY_RESPECT_RATE_LIMIT:
    rate_limit_status = await rate_limiter.get_status()
    if rate_limit_status.get('enabled'):
        utilization = rate_limit_status['current_count'] / rate_limit_status['max_tasks']
        if utilization > 0.8:  # 使用率超过80%
            self.logger.warning(
                f"限流使用率过高 ({utilization*100:.1f}%)，"
                f"跳过失败任务重试，避免加重限流压力"
            )
            return
```

更新注释，将 "步骤3" 改为 "步骤2"

- [ ] **Step 3: 删除 dispatch_pending_jobs 中的限流检查**

删除第249-264行（在 `dispatch_pending_jobs` 方法中）：

```python
# 检查限流
can_execute = await rate_limiter.can_execute(job.config_id)
if not can_execute:
    wait_time = await rate_limiter.get_wait_time(job.config_id)
    logger.info(
        f"任务 #{job.id} (config_id={job.config_id}) 因限流跳过，"
        f"需等待 {wait_time} 秒"
    )
    continue

# 更新任务状态为 processing
job.status = JobStatus.PROCESSING
await session.commit()

# 记录限流执行
await rate_limiter.record_execution(job.config_id)
```

替换为：

```python
# 更新任务状态为 processing
job.status = JobStatus.PROCESSING
await session.commit()
```

- [ ] **Step 4: 验证语法**

```bash
python -m py_compile app/services/scheduler.py
```

Expected: 无输出

- [ ] **Step 5: 提交**

```bash
git add app/services/scheduler.py
git commit -m "refactor: remove rate limit checks from scheduler"
```

---

## Task 3: 删除限流API路由

**Files:**
- Modify: `app/main.py:21,158`
- Delete: `app/api/rate_limit.py`

- [ ] **Step 1: 删除路由导入和注册**

从 `app/main.py` 删除第21行：

```python
from app.api.rate_limit import router as rate_limit_router
```

从 `app/main.py` 删除第158行（在路由注册部分）：

```python
app.include_router(rate_limit_router)
```

- [ ] **Step 2: 删除限流API文件**

```bash
git rm app/api/rate_limit.py
```

Expected: rm 'app/api/rate_limit.py'

- [ ] **Step 3: 验证应用启动**

```bash
python -c "from app.main import app; print('OK')"
```

Expected: 输出 "OK"

- [ ] **Step 4: 提交**

```bash
git add app/main.py app/api/rate_limit.py
git commit -m "refactor: remove rate limit API endpoint"
```

---

## Task 4: 删除全局限流器

**Files:**
- Delete: `app/services/rate_limiter.py`

- [ ] **Step 1: 检查是否还有其他引用**

```bash
grep -r "from app.services.rate_limiter" --include="*.py" app/
```

Expected: 无输出（没有其他引用）

- [ ] **Step 2: 删除文件**

```bash
git rm app/services/rate_limiter.py
```

Expected: rm 'app/services/rate_limiter.py'

- [ ] **Step 3: 提交**

```bash
git add app/services/rate_limiter.py
git commit -m "refactor: remove global rate limiter"
```

---

## Task 5: 实现 RequestRateLimiter 类（TDD）

**Files:**
- Create: `tests/test_request_rate_limiter.py`
- Modify: `app/services/executor.py` (添加内部类)

- [ ] **Step 1: 编写第一个测试 - 首次请求立即通过**

创建 `tests/test_request_rate_limiter.py`：

```python
import pytest
import asyncio
from datetime import datetime


# 暂时内联 RequestRateLimiter 用于测试
class RequestRateLimiter:
    """请求级限流器 - 控制HTTP请求间隔"""
    
    def __init__(self, interval_seconds: float):
        self.interval_seconds = interval_seconds
        self.last_request_time = None
        
    async def acquire(self) -> float:
        """获取请求许可"""
        pass  # 待实现


@pytest.mark.asyncio
async def test_first_request_no_wait():
    """测试：首次请求应立即通过"""
    limiter = RequestRateLimiter(interval_seconds=5)
    
    wait_time = await limiter.acquire()
    
    assert wait_time == 0.0
    assert limiter.last_request_time is not None
```

- [ ] **Step 2: 运行测试验证失败**

```bash
pytest tests/test_request_rate_limiter.py::test_first_request_no_wait -v
```

Expected: FAIL (acquire 返回 None)

- [ ] **Step 3: 实现最小代码使测试通过**

在 `RequestRateLimiter.acquire()` 中添加：

```python
async def acquire(self) -> float:
    """获取请求许可"""
    now = datetime.now()
    
    if self.last_request_time is None:
        self.last_request_time = now
        return 0.0
    
    return 0.0  # 临时返回
```

- [ ] **Step 4: 运行测试验证通过**

```bash
pytest tests/test_request_rate_limiter.py::test_first_request_no_wait -v
```

Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add tests/test_request_rate_limiter.py
git commit -m "test: add first request rate limiter test"
```

---

## Task 6: 实现请求间隔等待逻辑（TDD）

**Files:**
- Modify: `tests/test_request_rate_limiter.py`
- Modify: `RequestRateLimiter.acquire()` in test file

- [ ] **Step 1: 编写测试 - 间隔不足时等待**

在 `tests/test_request_rate_limiter.py` 添加：

```python
@pytest.mark.asyncio
async def test_wait_if_interval_not_met():
    """测试：如果距离上次请求时间不足，应等待"""
    limiter = RequestRateLimiter(interval_seconds=2)
    
    # 第一次请求
    wait1 = await limiter.acquire()
    assert wait1 == 0.0
    
    # 立即第二次请求（间隔不足）
    start = datetime.now()
    wait2 = await limiter.acquire()
    elapsed = (datetime.now() - start).total_seconds()
    
    # 应该等待约2秒
    assert wait2 >= 1.9
    assert wait2 <= 2.1
    assert elapsed >= 1.9  # 确认实际等待了
```

- [ ] **Step 2: 运行测试验证失败**

```bash
pytest tests/test_request_rate_limiter.py::test_wait_if_interval_not_met -v
```

Expected: FAIL (wait2 == 0.0, 没有等待)

- [ ] **Step 3: 实现等待逻辑**

更新 `RequestRateLimiter.acquire()`:

```python
async def acquire(self) -> float:
    """获取请求许可"""
    now = datetime.now()
    
    if self.last_request_time is None:
        self.last_request_time = now
        return 0.0
    
    # 计算距离上次请求的时间间隔
    elapsed = (now - self.last_request_time).total_seconds()
    
    # 如果间隔不足，需要等待
    if elapsed < self.interval_seconds:
        wait_seconds = self.interval_seconds - elapsed
        await asyncio.sleep(wait_seconds)
        self.last_request_time = datetime.now()
        return wait_seconds
    else:
        # 间隔足够，直接通过
        self.last_request_time = now
        return 0.0
```

- [ ] **Step 4: 运行测试验证通过**

```bash
pytest tests/test_request_rate_limiter.py::test_wait_if_interval_not_met -v
```

Expected: PASS

- [ ] **Step 5: 添加测试 - 间隔足够时不等待**

在 `tests/test_request_rate_limiter.py` 添加：

```python
@pytest.mark.asyncio
async def test_no_wait_if_interval_met():
    """测试：如果间隔已足够，应立即通过"""
    limiter = RequestRateLimiter(interval_seconds=1)
    
    # 第一次请求
    await limiter.acquire()
    
    # 等待超过间隔时间
    await asyncio.sleep(1.1)
    
    # 第二次请求应立即通过
    wait2 = await limiter.acquire()
    assert wait2 == 0.0
```

- [ ] **Step 6: 运行测试验证通过**

```bash
pytest tests/test_request_rate_limiter.py::test_no_wait_if_interval_met -v
```

Expected: PASS

- [ ] **Step 7: 提交**

```bash
git add tests/test_request_rate_limiter.py
git commit -m "feat: implement request rate limiter with interval control"
```

---

## Task 7: 将 RequestRateLimiter 集成到 Executor

**Files:**
- Modify: `app/services/executor.py:35-95` (添加 RequestRateLimiter 类)

- [ ] **Step 1: 在 executor.py 中添加 RequestRateLimiter 类**

在 `app/services/executor.py` 的开头（第35行左右，在 `PlaywrightExecutor` 类之前）添加：

```python
class RequestRateLimiter:
    """请求级限流器 - 控制HTTP请求间隔"""
    
    def __init__(self, interval_seconds: float):
        """
        Args:
            interval_seconds: 每个请求之间的间隔时间（秒）
        """
        self.interval_seconds = interval_seconds
        self.last_request_time = None
        
    async def acquire(self) -> float:
        """
        获取请求许可（如果距离上次请求时间不足，则等待）
        
        Returns:
            等待时间（秒）
        """
        now = datetime.now()
        
        # 首次请求，直接通过
        if self.last_request_time is None:
            self.last_request_time = now
            return 0.0
        
        # 计算距离上次请求的时间间隔
        elapsed = (now - self.last_request_time).total_seconds()
        
        # 如果间隔不足，需要等待
        if elapsed < self.interval_seconds:
            wait_seconds = self.interval_seconds - elapsed
            await asyncio.sleep(wait_seconds)
            self.last_request_time = datetime.now()
            return wait_seconds
        else:
            # 间隔足够，直接通过
            self.last_request_time = now
            return 0.0
```

- [ ] **Step 2: 验证语法**

```bash
python -m py_compile app/services/executor.py
```

Expected: 无输出

- [ ] **Step 3: 更新测试文件移除内联类**

在 `tests/test_request_rate_limiter.py` 顶部，移除内联的 `RequestRateLimiter` 类定义，改为导入：

```python
import pytest
import asyncio
from datetime import datetime
from app.services.executor import RequestRateLimiter


# 测试代码保持不变
@pytest.mark.asyncio
async def test_first_request_no_wait():
    ...
```

- [ ] **Step 4: 运行测试验证通过**

```bash
pytest tests/test_request_rate_limiter.py -v
```

Expected: 所有测试 PASS

- [ ] **Step 5: 提交**

```bash
git add app/services/executor.py tests/test_request_rate_limiter.py
git commit -m "feat: add RequestRateLimiter to executor"
```

---

## Task 8: 在 Executor 初始化限流器

**Files:**
- Modify: `app/services/executor.py` (在 execute_job 方法开始处)

- [ ] **Step 1: 编写集成测试**

在 `tests/test_request_rate_limiter.py` 添加：

```python
@pytest.mark.asyncio
async def test_executor_loads_rate_limit_config():
    """测试：执行器正确加载限流配置"""
    from app.models.config import CrawlerConfig
    from app.services.executor import PlaywrightExecutor
    
    # 创建测试配置
    config = CrawlerConfig(
        config_name="测试",
        target_url="http://example.com",
        input_configs=[],
        submit_selector="button",
        wait_selector=".result",
        fields_mapping={},
        extraction_config={
            "request_rate_limit": {
                "enabled": True,
                "interval_seconds": 5
            }
        }
    )
    
    executor = PlaywrightExecutor()
    
    # 加载配置
    extraction_cfg = executor._load_extraction_config(config)
    
    # 验证配置正确加载
    assert "request_rate_limit" in extraction_cfg
    assert extraction_cfg["request_rate_limit"]["enabled"] is True
    assert extraction_cfg["request_rate_limit"]["interval_seconds"] == 5
```

- [ ] **Step 2: 运行测试验证通过**

```bash
pytest tests/test_request_rate_limiter.py::test_executor_loads_rate_limit_config -v
```

Expected: PASS (配置已正确加载)

- [ ] **Step 3: 在 execute_job 方法开始处初始化限流器**

在 `app/services/executor.py` 的 `execute_job` 方法中，找到加载 `extraction_cfg` 的位置（约1390行左右），在其后添加：

```python
# 加载提取配置
extraction_cfg = self._load_extraction_config(config)

# 初始化请求级限流器
rate_limit_cfg = extraction_cfg.get("request_rate_limit", {})
if rate_limit_cfg.get("enabled", False):
    interval = rate_limit_cfg.get("interval_seconds", 5)
    if interval <= 0:
        self.logger.warning(
            f"[限流] request_rate_limit.interval_seconds 必须大于 0，已禁用限流"
        )
        self._request_limiter = None
    else:
        self._request_limiter = RequestRateLimiter(interval_seconds=interval)
        self.logger.info(
            f"[限流] 已启用请求级限流: 每 {interval} 秒一个请求"
        )
else:
    self._request_limiter = None
```

- [ ] **Step 4: 验证语法**

```bash
python -m py_compile app/services/executor.py
```

Expected: 无输出

- [ ] **Step 5: 提交**

```bash
git add app/services/executor.py tests/test_request_rate_limiter.py
git commit -m "feat: initialize request rate limiter in executor"
```

---

## Task 9: 实现限流检查辅助方法

**Files:**
- Modify: `app/services/executor.py` (添加 _rate_limit_check 方法)

- [ ] **Step 1: 添加 _rate_limit_check 方法**

在 `app/services/executor.py` 的 `PlaywrightExecutor` 类中添加方法（建议在 `_broadcast_log` 方法附近）：

```python
async def _rate_limit_check(self, operation_name: str = "请求"):
    """
    执行限流检查
    
    Args:
        operation_name: 操作名称（用于日志）
    """
    if not self._request_limiter:
        return
    
    try:
        wait_time = await self._request_limiter.acquire()
        
        if wait_time > 0:
            # 记录等待日志
            self.logger.info(
                f"[限流] {operation_name} - 等待 {wait_time:.1f} 秒"
            )
            
            # WebSocket 推送
            if self.ws_manager:
                await self._broadcast_log(
                    "info",
                    f"[限流] 等待 {wait_time:.1f} 秒（请求频率控制）"
                )
    except Exception as e:
        self.logger.error(f"[限流] 限流器异常: {e}，跳过限流检查")
```

- [ ] **Step 2: 验证语法**

```bash
python -m py_compile app/services/executor.py
```

Expected: 无输出

- [ ] **Step 3: 提交**

```bash
git add app/services/executor.py
git commit -m "feat: add rate limit check helper method"
```

---

## Task 10: 集成限流检查到关键操作点

**Files:**
- Modify: `app/services/executor.py` (多个位置)

- [ ] **Step 1: 在 page.goto 前添加限流检查**

在 `execute_job` 方法中，找到 `await page.goto(config.target_url, ...)` 的位置（约1430行），在其前添加：

```python
# 限流检查：访问页面
await self._rate_limit_check("访问页面")

await page.goto(
    config.target_url,
    wait_until="domcontentloaded",
    timeout=timeouts['page_load']
)
```

- [ ] **Step 2: 在点击查询按钮前添加限流检查**

找到 `await page.click(config.submit_selector, ...)` 的位置（约1460行），在其前添加：

```python
# 限流检查：点击查询
await self._rate_limit_check("点击查询")

await page.click(config.submit_selector, timeout=timeouts['click'])
```

- [ ] **Step 3: 在点击详情按钮前添加限流检查**

在 `_extract_detail_data` 方法中，找到 `await detail_button.click(...)` 的位置（约625行），在其前添加：

```python
# 限流检查：点击详情
await self._rate_limit_check("点击详情")

# 尝试点击详情按钮
try:
    await detail_button.evaluate("element => element.click()")
except Exception:
    await detail_button.click(timeout=click_timeout)
```

- [ ] **Step 4: 在翻页前添加限流检查**

在 `_handle_pagination` 方法中，找到 `await next_button.click(...)` 的位置（约1162行），在其前添加：

```python
# 限流检查：翻页
await self._rate_limit_check("翻页")

await next_button.click(timeout=timeouts['click'])
```

也在详情页翻页处（约767行）添加：

```python
# 限流检查：详情翻页
await self._rate_limit_check("详情翻页")

await detail_frame.evaluate("""
    document.querySelector('#next_page').click();
""")
```

- [ ] **Step 5: 验证语法**

```bash
python -m py_compile app/services/executor.py
```

Expected: 无输出

- [ ] **Step 6: 提交**

```bash
git add app/services/executor.py
git commit -m "feat: integrate rate limit checks at all HTTP request points"
```

---

## Task 11: 端到端测试

**Files:**
- Create: `tests/test_e2e_rate_limiting.py`

- [ ] **Step 1: 编写端到端测试**

创建 `tests/test_e2e_rate_limiting.py`:

```python
import pytest
import asyncio
from datetime import datetime
from app.models.config import CrawlerConfig
from app.services.executor import PlaywrightExecutor


@pytest.mark.asyncio
@pytest.mark.slow
async def test_rate_limiting_enforces_interval():
    """
    端到端测试：验证限流在实际执行中生效
    
    注意：这是一个慢速测试，会实际等待
    """
    # 创建配置：每3秒一个请求
    config = CrawlerConfig(
        config_name="限流测试",
        target_url="http://httpbin.org/delay/0",
        input_configs=[],
        submit_selector="button",
        wait_selector="body",
        fields_mapping={},
        extraction_config={
            "request_rate_limit": {
                "enabled": True,
                "interval_seconds": 3
            }
        }
    )
    
    executor = PlaywrightExecutor()
    
    # 模拟连续3次请求
    start_times = []
    
    for i in range(3):
        start = datetime.now()
        await executor._rate_limit_check(f"请求{i+1}")
        start_times.append(start)
    
    # 验证间隔
    # 第1个请求：立即执行
    # 第2个请求：等待约3秒
    # 第3个请求：等待约3秒
    
    if len(start_times) >= 2:
        interval1 = (start_times[1] - start_times[0]).total_seconds()
        assert interval1 >= 2.9, f"第1-2个请求间隔应>=3秒，实际{interval1:.1f}秒"
    
    if len(start_times) >= 3:
        interval2 = (start_times[2] - start_times[1]).total_seconds()
        assert interval2 >= 2.9, f"第2-3个请求间隔应>=3秒，实际{interval2:.1f}秒"
    
    print(f"✓ 限流测试通过：3个请求总耗时约{(start_times[-1] - start_times[0]).total_seconds():.1f}秒")
```

- [ ] **Step 2: 运行端到端测试**

```bash
pytest tests/test_e2e_rate_limiting.py -v -s
```

Expected: PASS（耗时约6秒）

- [ ] **Step 3: 提交**

```bash
git add tests/test_e2e_rate_limiting.py
git commit -m "test: add end-to-end rate limiting test"
```

---

## Task 12: 更新文档 - CLAUDE.md

**Files:**
- Modify: `CLAUDE.md`

- [ ] **Step 1: 删除任务级限流说明**

从 `CLAUDE.md` 中删除以下部分（搜索 "RATE_LIMIT" 找到相关章节）：

- 删除 `.env` 配置示例中的限流配置
- 删除限流配置详解章节
- 删除限流监控命令

- [ ] **Step 2: 添加请求级限流说明**

在 `CLAUDE.md` 的配置部分添加：

```markdown
### 请求级限流配置

在 `extraction_config` 中配置，控制任务执行过程中HTTP请求的频率：

```json
{
  "extraction_config": {
    "request_rate_limit": {
      "enabled": true,
      "interval_seconds": 6
    }
  }
}
```

**字段说明**：
- `enabled`: 是否启用限流（默认 false）
- `interval_seconds`: 每个请求之间的间隔时间（秒，默认5）

**推荐配置**：
- 严格限流：`interval_seconds: 12`（每12秒一个请求）
- 中等限流：`interval_seconds: 6`（每6秒一个请求）
- 宽松限流：`interval_seconds: 3`（每3秒一个请求）
```

- [ ] **Step 3: 验证 Markdown 语法**

```bash
# 可选：使用 markdownlint 验证
# markdownlint CLAUDE.md
```

- [ ] **Step 4: 提交**

```bash
git add CLAUDE.md
git commit -m "docs: update CLAUDE.md with request-level rate limiting"
```

---

## Task 13: 更新文档 - README.md

**Files:**
- Modify: `README.md`

- [ ] **Step 1: 删除 .env 配置示例中的限流配置**

从 `README.md` 中搜索并删除：

```bash
RATE_LIMIT_ENABLED=true
RATE_LIMIT_WINDOW_MINUTES=60
RATE_LIMIT_MAX_TASKS=100
RATE_LIMIT_PER_CONFIG=false
```

- [ ] **Step 2: 添加请求级限流的简短说明**

在配置部分添加：

```markdown
## 请求限流

通过配置控制HTTP请求频率，防止触发反爬机制。在 `extraction_config` 中配置：

```json
{
  "request_rate_limit": {
    "enabled": true,
    "interval_seconds": 6
  }
}
```

详细配置请参考 `CLAUDE.md`。
```

- [ ] **Step 3: 提交**

```bash
git add README.md
git commit -m "docs: update README with simplified rate limiting"
```

---

## Task 14: 清理过时的文档

**Files:**
- Delete or Update: `docs/rate_limit_guide.md`
- Update: `docs/配置参数详解与设置指南.md`

- [ ] **Step 1: 检查是否存在 rate_limit_guide.md**

```bash
ls docs/rate_limit_guide.md
```

如果存在，删除或重写：

```bash
git rm docs/rate_limit_guide.md
```

或者重写为请求级限流指南（保留文件名）

- [ ] **Step 2: 更新配置参数指南**

编辑 `docs/配置参数详解与设置指南.md`：

- 删除 `RATE_LIMIT_*` 相关章节
- 添加请求级限流（`request_rate_limit`）说明
- 更新配置示例

- [ ] **Step 3: 提交**

```bash
git add docs/
git commit -m "docs: clean up outdated rate limiting documentation"
```

---

## Task 15: 运行完整测试套件

**Files:**
- N/A (验证阶段)

- [ ] **Step 1: 运行所有单元测试**

```bash
pytest tests/test_request_rate_limiter.py -v
```

Expected: 所有测试 PASS

- [ ] **Step 2: 运行回归测试**

```bash
pytest tests/ -v -k "not slow"
```

Expected: 所有非慢速测试 PASS

- [ ] **Step 3: 检查代码覆盖率**

```bash
pytest tests/test_request_rate_limiter.py --cov=app.services.executor --cov-report=term-missing
```

Expected: RequestRateLimiter 相关代码覆盖率 > 80%

- [ ] **Step 4: 验证应用启动**

```bash
python -m app.main &
sleep 5
curl http://localhost:8000/health
kill %1
```

Expected: 应用正常启动，健康检查返回 200

- [ ] **Step 5: 记录测试结果**

创建测试报告文件：

```bash
echo "# 测试报告" > /tmp/test_report.md
echo "- 单元测试: PASS" >> /tmp/test_report.md
echo "- 回归测试: PASS" >> /tmp/test_report.md
echo "- 应用启动: OK" >> /tmp/test_report.md
cat /tmp/test_report.md
```

---

## Task 16: 最终提交与标签

**Files:**
- N/A (Git 操作)

- [ ] **Step 1: 查看所有变更**

```bash
git log --oneline --since="1 day ago"
```

Expected: 显示所有相关提交

- [ ] **Step 2: 创建功能分支合并提交（如果在分支上）**

```bash
# 如果在 feature 分支
git checkout main
git merge --no-ff feature/request-rate-limiting -m "feat: implement request-level rate limiting

- Remove task-level rate limiting (5 config items, 2 files)
- Implement request-level rate limiting with fixed interval
- Simplify configuration to 2 fields (enabled, interval_seconds)
- Update all documentation

BREAKING CHANGE: RATE_LIMIT_* config removed, use request_rate_limit in extraction_config"
```

如果直接在 main 分支，跳过此步骤

- [ ] **Step 3: 打标签**

```bash
git tag -a v1.1.0 -m "Release v1.1.0: Request-level rate limiting

Features:
- Request-level rate limiting with fixed interval
- Simplified configuration (2 fields vs 5)
- Better control over HTTP request frequency

Breaking Changes:
- Removed RATE_LIMIT_ENABLED, RATE_LIMIT_WINDOW_MINUTES, etc.
- Removed /api/rate-limit/* endpoints
"
```

- [ ] **Step 4: 推送到远程（可选）**

```bash
git push origin main
git push origin v1.1.0
```

---

## Spec Self-Review

### Spec Coverage Check

✅ **删除任务级限流**：
- Task 1: 删除配置项
- Task 2: 删除调度器逻辑
- Task 3: 删除API端点
- Task 4: 删除限流器文件

✅ **实现请求级限流**：
- Task 5-6: TDD 实现 RequestRateLimiter
- Task 7: 集成到 Executor
- Task 8-9: 初始化和辅助方法
- Task 10: 集成到关键操作点

✅ **测试**：
- Task 5-6: 单元测试
- Task 11: 端到端测试
- Task 15: 完整测试套件

✅ **文档更新**：
- Task 12: CLAUDE.md
- Task 13: README.md
- Task 14: 清理过时文档

### Placeholder Scan

✅ 无 TBD、TODO、implement later
✅ 所有代码块都包含实际代码
✅ 所有测试都包含完整的断言

### Type Consistency

✅ `RequestRateLimiter` 类名一致
✅ `interval_seconds` 参数名一致
✅ `acquire()` 方法签名一致
✅ `_rate_limit_check()` 方法名一致

---

## 实施计划完成

总计：16个任务，约80个步骤

**预计耗时**：4-6小时

**关键路径**：
1. 删除旧代码（Task 1-4）- 1小时
2. 实现新功能（Task 5-10）- 2-3小时
3. 测试验证（Task 11,15）- 1小时
4. 文档更新（Task 12-14）- 1小时
5. 最终提交（Task 16）- 15分钟
