# 请求级限流设计文档

## 文档信息
- **日期**: 2026-10-11
- **版本**: 1.0
- **状态**: 设计完成，待实施

---

## 1. 背景与目标

### 1.1 问题陈述

当前系统的限流机制（`RATE_LIMIT_*` 配置）仅在**任务级别**生效，控制的是每个时间窗口内执行的任务数量。但对于单个任务内部的多次HTTP请求（如点击查询、点击详情、翻页等），没有细粒度的频率控制。

**实际场景**：
```
任务执行流程：
1. 访问页面 (HTTP请求)
2. 点击查询 (HTTP请求)
3. 提取列表数据
4. 点击详情 (HTTP请求)
5. 提取详情数据
6. 关闭详情
7. 翻页 (HTTP请求)
8. 重复 3-7

问题：虽然任务级限流控制了任务数量，但单个任务内的多次请求仍可能触发网站反爬机制
```

### 1.2 目标

实现**请求级限流**，对任务执行过程中的每个HTTP请求进行频率控制，避免触发目标网站的反爬机制。

**需求**：
- 统一限流所有HTTP请求（访问页面、点击、翻页等）
- 配置在 `extraction_config` 中，每个爬虫配置可独立设置
- 基于时间窗口的动态限流（如"每分钟最多10次请求"）
- 与现有 `wait_times` 机制配合使用

---

## 2. 设计概览

### 2.1 架构方案

**选择方案**：执行器内部限流器

在 `PlaywrightExecutor` 中创建轻量级的请求限流器，每个任务执行时初始化一个独立的限流器实例。

**核心组件**：
1. **RequestRateLimiter** 类：维护请求时间戳队列，控制请求频率
2. **PlaywrightExecutor** 增强：在所有HTTP请求操作前调用限流检查

### 2.2 工作流程

```
任务开始
  ↓
读取 extraction_config.request_rate_limit
  ↓
初始化 RequestRateLimiter(window_minutes, max_requests)
  ↓
执行操作前调用 await limiter.acquire()
  ├─ 检查当前窗口内请求数
  ├─ 如果未超限 → 立即返回，记录时间戳
  └─ 如果超限 → 计算等待时间 → sleep → 返回
  ↓
执行实际操作（page.goto, click, etc.）
  ↓
继续下一个操作...
```

### 2.3 与现有机制的关系

**操作执行时序**：
```
1. 限流检查（request_rate_limit）  ← 新增
2. 固定等待（wait_times）          ← 现有
3. 执行操作（click/goto）
4. 等待元素（wait_for_selector）  ← 现有
```

**示例**：
```python
# 限流等待（动态）
await limiter.acquire()  # 可能等待 0-60 秒

# 固定等待
await asyncio.sleep(wait_times["after_click"] / 1000)  # 1 秒

# 执行操作
await page.click(submit_selector)
```

---

## 3. 数据结构与配置

### 3.1 配置格式

在 `extraction_config` 中添加 `request_rate_limit` 字段：

```json
{
  "extraction_config": {
    "wait_times": {
      "before_extraction": 3000,
      "after_click": 1000,
      "between_pages": 2000
    },
    "request_rate_limit": {
      "enabled": true,
      "window_minutes": 1,
      "max_requests": 10,
      "log_wait": true
    },
    "retry": {
      "max_attempts": 2,
      "delay_seconds": 3
    }
  }
}
```

**字段说明**：

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `enabled` | boolean | 否 | false | 是否启用请求级限流 |
| `window_minutes` | int | 否 | 1 | 时间窗口（分钟） |
| `max_requests` | int | 否 | 10 | 窗口内最大请求数 |
| `log_wait` | boolean | 否 | true | 是否记录等待日志 |

**配置示例**：

```python
# 严格限流（每分钟5次请求）
{
  "request_rate_limit": {
    "enabled": true,
    "window_minutes": 1,
    "max_requests": 5
  }
}

# 宽松限流（每5分钟50次请求）
{
  "request_rate_limit": {
    "enabled": true,
    "window_minutes": 5,
    "max_requests": 50
  }
}

# 不启用（默认）
{
  "request_rate_limit": {
    "enabled": false
  }
}
```

### 3.2 RequestRateLimiter 类设计

**类定义**：
```python
class RequestRateLimiter:
    """请求级限流器 - 控制任务执行过程中的HTTP请求频率"""
    
    def __init__(self, window_minutes: int, max_requests: int, log_wait: bool = True):
        """
        初始化限流器
        
        Args:
            window_minutes: 时间窗口（分钟）
            max_requests: 窗口内最大请求数
            log_wait: 是否记录等待日志
        """
        self.window_minutes = window_minutes
        self.max_requests = max_requests
        self.log_wait = log_wait
        self.timestamps = deque()  # 存储请求时间戳
        
    async def acquire(self) -> float:
        """
        获取请求许可（如果超限则自动等待）
        
        Returns:
            等待时间（秒），0 表示无需等待
        """
```

**内部状态**：
- `timestamps`: `deque[datetime]` - 存储窗口内的请求时间戳
- 自动清理过期时间戳（超出时间窗口）

---

## 4. 核心实现逻辑

### 4.1 RequestRateLimiter.acquire() 算法

**滑动窗口实现**：

```python
async def acquire(self) -> float:
    """
    获取请求许可
    
    逻辑：
    1. 清理过期的时间戳（超出时间窗口）
    2. 检查当前窗口内请求数是否达到上限
    3. 如果达到上限，计算需要等待的时间并 sleep
    4. 记录当前请求时间戳
    5. 返回实际等待时间
    """
    now = datetime.now()
    window_start = now - timedelta(minutes=self.window_minutes)
    
    # 步骤1: 清理过期的时间戳
    while self.timestamps and self.timestamps[0] < window_start:
        self.timestamps.popleft()
    
    # 步骤2: 检查是否超限
    if len(self.timestamps) >= self.max_requests:
        # 计算需要等待的时间（直到最早的请求过期）
        oldest = self.timestamps[0]
        wait_until = oldest + timedelta(minutes=self.window_minutes)
        wait_seconds = (wait_until - now).total_seconds()
        
        if wait_seconds > 0:
            # 等待到窗口滑动
            await asyncio.sleep(wait_seconds)
            
            # 等待后重新清理过期时间戳
            now = datetime.now()
            window_start = now - timedelta(minutes=self.window_minutes)
            while self.timestamps and self.timestamps[0] < window_start:
                self.timestamps.popleft()
            
            # 返回等待时间
            wait_time = wait_seconds
        else:
            wait_time = 0
    else:
        wait_time = 0
    
    # 步骤3: 记录当前请求时间戳
    self.timestamps.append(now)
    
    return wait_time
```

**时间复杂度**：O(n)，其中 n 为窗口内请求数（通常很小，如 10-100）

### 4.2 执行器集成

**初始化**（在 `execute_job` 方法开始）：

```python
# 加载提取配置
extraction_cfg = self._load_extraction_config(config)

# 初始化请求级限流器
rate_limit_cfg = extraction_cfg.get("request_rate_limit", {})
if rate_limit_cfg.get("enabled", False):
    # 验证配置
    max_requests = rate_limit_cfg.get("max_requests", 10)
    window_minutes = rate_limit_cfg.get("window_minutes", 1)
    
    if max_requests <= 0:
        self.logger.warning("request_rate_limit.max_requests 必须大于 0，已禁用限流")
        self._request_limiter = None
    elif window_minutes <= 0:
        self.logger.warning("request_rate_limit.window_minutes 必须大于 0，已禁用限流")
        self._request_limiter = None
    else:
        self._request_limiter = RequestRateLimiter(
            window_minutes=window_minutes,
            max_requests=max_requests,
            log_wait=rate_limit_cfg.get("log_wait", True)
        )
        self.logger.info(
            f"[限流] 已启用请求级限流: {max_requests} 请求/{window_minutes} 分钟"
        )
else:
    self._request_limiter = None
```

**使用方式**（在每个HTTP操作前）：

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
        
        if wait_time > 0 and self._request_limiter.log_wait:
            # 记录等待日志
            self.logger.info(
                f"[限流] {operation_name} - 等待 {wait_time:.1f} 秒"
                f"（窗口内请求已达 {self._request_limiter.max_requests} 次上限）"
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

### 4.3 需要限流的操作点

在以下操作前调用 `await self._rate_limit_check(operation_name)`：

| 操作 | 位置 | 操作名称 |
|------|------|----------|
| 访问目标页面 | `page.goto(target_url)` | "访问页面" |
| 点击查询按钮 | `page.click(submit_selector)` | "点击查询" |
| 点击详情按钮 | `detail_button.click()` | "点击详情" |
| 翻页操作 | `next_button.click()` | "翻页" |
| 详情页翻页 | `detail_frame` 内的翻页 | "详情翻页" |

**示例**：

```python
# 1. 访问页面
await self._rate_limit_check("访问页面")
await page.goto(config.target_url, timeout=timeouts['page_load'])

# 2. 点击查询
await self._rate_limit_check("点击查询")
await page.click(config.submit_selector, timeout=timeouts['click'])

# 3. 点击详情
await self._rate_limit_check("点击详情")
await detail_button.click(timeout=click_timeout)

# 4. 翻页
await self._rate_limit_check("翻页")
await next_button.click(timeout=timeouts['click'])
```

---

## 5. 日志与监控

### 5.1 日志输出

**启用时**：
```
[INFO] [限流] 已启用请求级限流: 10 请求/1 分钟
```

**限流触发时**：
```
[INFO] [限流] 点击查询 - 等待 45.3 秒（窗口内请求已达 10 次上限）
[INFO] [限流] 等待 45.3 秒（请求频率控制）  ← WebSocket
```

**Debug 级别**（可选）：
```
[DEBUG] [限流] 当前窗口: 7/10 请求，剩余配额: 3
```

### 5.2 WebSocket 推送

**限流等待事件**：
```json
{
  "type": "log",
  "level": "info",
  "msg": "[限流] 等待 45.3 秒（请求频率控制）"
}
```

**可选：限流状态推送**：
```json
{
  "type": "rate_limit_status",
  "current_count": 10,
  "max_requests": 10,
  "window_minutes": 1,
  "wait_seconds": 45.3
}
```

---

## 6. 错误处理与边界情况

### 6.1 配置错误处理

**无效配置**：
```python
# max_requests <= 0
if max_requests <= 0:
    self.logger.warning("request_rate_limit.max_requests 必须大于 0，已禁用限流")
    self._request_limiter = None

# window_minutes <= 0
if window_minutes <= 0:
    self.logger.warning("request_rate_limit.window_minutes 必须大于 0，已禁用限流")
    self._request_limiter = None
```

**配置未设置**：
- `request_rate_limit` 字段不存在 → 不启用限流
- `enabled: false` → 不启用限流
- `enabled: true` 但缺少必要字段 → 使用默认值

### 6.2 运行时异常处理

**限流器异常**：
```python
try:
    wait_time = await self._request_limiter.acquire()
except Exception as e:
    self.logger.error(f"[限流] 限流器异常: {e}，跳过限流检查")
    wait_time = 0
    # 不中断任务执行
```

### 6.3 边界情况

**1. 任务耗时超过时间窗口**
- **场景**：任务执行 5 分钟，但限流窗口只有 1 分钟
- **处理**：时间戳自动过期清理，不影响后续请求
- **结果**：限流窗口持续滑动，始终统计最近 N 分钟的请求

**2. 首次请求**
- **场景**：`timestamps` 队列为空
- **处理**：直接通过，不等待，记录时间戳
- **结果**：首个请求立即执行

**3. 配置未设置**
- **场景**：`extraction_config` 中没有 `request_rate_limit` 字段
- **处理**：`self._request_limiter = None`
- **结果**：所有限流检查跳过，行为与现有系统一致

**4. 与 wait_times 的交互**
- **场景**：同时配置 `request_rate_limit` 和 `wait_times`
- **处理**：两者叠加生效
- **示例**：
  ```python
  await self._rate_limit_check()  # 可能等待 10 秒（限流）
  await asyncio.sleep(wait_times["after_click"] / 1000)  # 等待 1 秒（固定）
  await page.click(...)
  # 总等待时间 = 10秒 + 1秒 = 11秒
  ```

**5. 窗口边界的精度**
- **场景**：请求时间戳为 `10:00:00`，窗口为 1 分钟，下一个请求在 `10:01:00`
- **处理**：使用 `timedelta` 精确计算，`10:01:00` 时 `10:00:00` 的时间戳被清理
- **结果**：精确的滑动窗口，无边界泄漏

**6. 多进程场景**
- **场景**：系统配置 `MAX_WORKERS=3`，3 个进程同时执行任务
- **处理**：每个进程独立计数（限流器随执行器实例创建）
- **结果**：
  - 每个任务有独立的限流配额（符合设计目标）
  - 全局请求数 = 单任务限流 × 进程数
  - 示例：每个任务 10 req/min，3 个进程 → 全局约 30 req/min

---

## 7. 兼容性与迁移

### 7.1 向后兼容

**现有配置完全不受影响**：
- 未设置 `request_rate_limit` 的配置 → 不启用限流
- 现有任务执行流程保持不变
- 不需要修改数据库表结构（JSON 字段扩展）

**迁移路径**：
```
阶段1: 部署新代码（不修改配置）
  → 所有任务正常执行，无变化

阶段2: 针对特定配置启用限流
  → 通过 API 或数据库更新 extraction_config
  → 只有更新的配置受影响

阶段3: 根据效果调整参数
  → 观察限流效果
  → 调整 window_minutes 和 max_requests
```

### 7.2 多进程场景

**当前架构**：
- 每个工作进程独立运行任务
- 进程间无共享状态

**限流行为**：
- 每个任务独立计数
- 进程 A 的任务不影响进程 B 的任务

**全局限流需求**：
- 如果需要全局共享限流（跨进程），需要使用方案 2（复用全局 RateLimiter）
- 当前方案专注于单任务内的请求频率控制

---

## 8. 测试策略

### 8.1 单元测试

**测试 RequestRateLimiter 类**：

```python
async def test_rate_limiter_basic():
    """测试基本限流功能"""
    limiter = RequestRateLimiter(window_minutes=1, max_requests=3)
    
    # 前3个请求应立即通过
    for i in range(3):
        wait_time = await limiter.acquire()
        assert wait_time == 0
    
    # 第4个请求应等待
    wait_time = await limiter.acquire()
    assert wait_time > 0

async def test_rate_limiter_window_expiry():
    """测试时间窗口过期"""
    limiter = RequestRateLimiter(window_minutes=0.01, max_requests=2)  # 0.6秒窗口
    
    # 前2个请求立即通过
    await limiter.acquire()
    await limiter.acquire()
    
    # 等待窗口过期
    await asyncio.sleep(1)
    
    # 第3个请求应立即通过（前2个已过期）
    wait_time = await limiter.acquire()
    assert wait_time == 0
```

### 8.2 集成测试

**测试配置加载**：
```python
async def test_executor_load_rate_limit_config():
    """测试执行器加载限流配置"""
    config = CrawlerConfig(
        extraction_config={
            "request_rate_limit": {
                "enabled": True,
                "window_minutes": 1,
                "max_requests": 5
            }
        }
    )
    
    executor = PlaywrightExecutor()
    # 验证限流器已初始化
    # 验证参数正确
```

**端到端测试**：
```python
async def test_e2e_rate_limiting():
    """端到端测试限流效果"""
    # 1. 创建配置（max_requests=3, window_minutes=1）
    # 2. 创建任务
    # 3. 执行任务
    # 4. 验证：
    #    - 前3个请求立即执行
    #    - 第4个请求等待约60秒
    #    - 日志中包含限流等待记录
```

### 8.3 性能测试

**测试指标**：
- 限流器 `acquire()` 方法的耗时（应 < 1ms）
- 时间戳队列的内存占用（应 < 1KB）
- 大量请求下的性能（1000次请求）

---

## 9. 配置示例

### 9.1 国家医保局注册证号查询

**场景**：政府网站，需要严格限流

```json
{
  "config_name": "国家医保局-注册证号查询",
  "target_url": "https://code.nhsa.gov.cn/toSearch.html?sysflag=1004",
  "extraction_config": {
    "wait_times": {
      "before_extraction": 3000,
      "after_click": 1000,
      "between_pages": 2000
    },
    "request_rate_limit": {
      "enabled": true,
      "window_minutes": 1,
      "max_requests": 5,
      "log_wait": true
    }
  }
}
```

**效果**：
- 每分钟最多 5 个HTTP请求
- 访问页面、查询、详情、翻页等操作共享配额
- 超限时自动等待，日志记录等待时间

### 9.2 电商商品采集

**场景**：反爬较严，但流量较大

```json
{
  "config_name": "电商平台-商品信息",
  "extraction_config": {
    "request_rate_limit": {
      "enabled": true,
      "window_minutes": 5,
      "max_requests": 50,
      "log_wait": false
    }
  }
}
```

**效果**：
- 每 5 分钟最多 50 个请求（平均每 6 秒一个）
- 不记录等待日志（减少日志量）

### 9.3 内部系统（不限流）

```json
{
  "config_name": "内部数据系统",
  "extraction_config": {
    "request_rate_limit": {
      "enabled": false
    }
  }
}
```

**效果**：
- 不启用请求级限流
- 与现有系统行为一致

---

## 10. 实施计划

### 10.1 开发阶段

**阶段 1：核心实现**
- [ ] 实现 `RequestRateLimiter` 类
- [ ] 在 `PlaywrightExecutor.__init__` 中初始化限流器
- [ ] 实现 `_rate_limit_check()` 方法
- [ ] 在关键操作点插入限流检查

**阶段 2：日志与监控**
- [ ] 添加限流等待日志
- [ ] WebSocket 推送限流事件
- [ ] 添加 Debug 级别的限流状态日志

**阶段 3：测试**
- [ ] 单元测试（RequestRateLimiter）
- [ ] 集成测试（配置加载）
- [ ] 端到端测试（实际限流效果）
- [ ] 性能测试

### 10.2 部署阶段

**阶段 1：灰度发布**
- 部署到测试环境
- 针对 1-2 个配置启用限流
- 观察效果和性能

**阶段 2：正式发布**
- 部署到生产环境
- 文档更新（用户手册、配置指南）
- 通知用户新功能

**阶段 3：推广使用**
- 根据网站特性推荐限流参数
- 收集用户反馈
- 优化参数建议

---

## 11. 风险与缓解

### 11.1 潜在风险

| 风险 | 影响 | 概率 | 缓解措施 |
|------|------|------|----------|
| 限流器 bug 导致任务卡死 | 高 | 低 | 异常处理，跳过限流检查 |
| 配置错误导致过度等待 | 中 | 中 | 配置验证，日志提示 |
| 多进程场景下限流不符合预期 | 中 | 中 | 文档说明，明确行为 |
| 性能开销（时间戳管理） | 低 | 低 | 性能测试，优化算法 |

### 11.2 回滚方案

**如果出现问题**：
1. 通过 API 禁用限流（`enabled: false`）
2. 回滚代码（限流器代码独立，易于移除）
3. 恢复到现有行为

---

## 12. 未来扩展

### 12.1 可能的增强

**1. 全局共享限流**
- 使用全局 `RateLimiter` 实现跨进程限流
- 适用于需要严格控制全局请求数的场景

**2. 按操作类型分别限流**
- 查询操作：每分钟 20 次
- 详情操作：每分钟 50 次
- 配置更灵活，但复杂度增加

**3. 动态调整限流参数**
- 根据失败率自动调整 `max_requests`
- 触发反爬时自动降低频率

**4. 限流统计 API**
- 查询当前限流状态
- 查看历史限流触发记录

---

## 13. 总结

### 13.1 设计要点

- **轻量级**：不修改全局架构，仅在执行器内部增加限流逻辑
- **独立性**：每个配置独立限流，互不干扰
- **灵活性**：可配置启用/禁用，参数可调
- **兼容性**：向后兼容，不影响现有配置

### 13.2 预期效果

- 有效防止触发网站反爬机制
- 与现有 `wait_times` 配合，提供多层防护
- 配置简单，易于使用和调整

### 13.3 下一步

完成设计评审后，进入实施阶段（编写实现计划）。
