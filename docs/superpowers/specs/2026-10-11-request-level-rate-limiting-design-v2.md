# 请求级限流设计文档（简化版）

## 文档信息
- **日期**: 2026-10-11
- **版本**: 2.0（简化版 - 删除任务级限流）
- **状态**: 设计完成，待实施

---

## 1. 背景与目标

### 1.1 问题陈述

当前系统的限流机制过于复杂，存在两层限流：
1. **任务级限流**（全局）：控制每小时执行多少个任务
2. **任务内部无限流**：单个任务内的多次HTTP请求无频率控制

**实际问题**：
- 任务级限流配置复杂（`RATE_LIMIT_*` 参数多达4个）
- 真正需要的是控制HTTP请求频率，而不是任务数量
- 两层限流概念混淆，用户难以理解

### 1.2 新设计目标

**简化为单一限流机制**：
- ✅ 只保留请求级限流（控制HTTP请求频率）
- ✅ 删除任务级限流（`RateLimiter`、相关配置）
- ✅ 简化配置，减少用户困惑
- ✅ 通过并发控制（`MAX_WORKERS`）+ 请求限流实现完整控制

---

## 2. 架构简化

### 2.1 删除的组件

**文件删除**：
- `app/services/rate_limiter.py` - 全局限流器（整个文件删除）
- `app/api/rate_limit.py` - 限流API端点（整个文件删除）

**配置删除**（`.env` / `app/core/config.py`）：
- `RATE_LIMIT_ENABLED`
- `RATE_LIMIT_WINDOW_MINUTES`
- `RATE_LIMIT_MAX_TASKS`
- `RATE_LIMIT_PER_CONFIG`

**代码删除**（`app/services/scheduler.py`）：
- `dispatch_pending_jobs()` 中的限流检查逻辑
- `retry_failed_jobs()` 中的 `RETRY_RESPECT_RATE_LIMIT` 检查

**配置删除**（智能重试相关）：
- `RETRY_RESPECT_RATE_LIMIT` - 不再需要

### 2.2 保留的组件

**并发控制**（保留）：
- `MAX_WORKERS` - 控制同时执行的任务数
- `WORKER_MEMORY_LIMIT_MB` - 工作进程内存限制

**新增组件**：
- `RequestRateLimiter` - 请求级限流器（在执行器内部）
- `extraction_config.request_rate_limit` - 请求限流配置

### 2.3 新架构

```
并发控制层（MAX_WORKERS）
  ↓ 控制同时运行的任务数
任务调度器
  ↓ 分发 pending 任务到进程池
进程池（工作进程）
  ↓ 执行任务
PlaywrightExecutor
  ├─ RequestRateLimiter ← 新增（控制HTTP请求频率）
  └─ 任务执行逻辑
```

**优势**：
- 架构更简单，只有一个限流层
- 配置更直观，直接控制HTTP请求频率
- 减少 4 个全局配置项，降低复杂度

---

## 3. 简化后的配置

### 3.1 全局配置（`.env`）

**删除**：
```bash
# ❌ 以下配置全部删除
RATE_LIMIT_ENABLED=false
RATE_LIMIT_WINDOW_MINUTES=60
RATE_LIMIT_MAX_TASKS=100
RATE_LIMIT_PER_CONFIG=false
RETRY_RESPECT_RATE_LIMIT=true
```

**保留**：
```bash
# ✅ 并发控制（保留）
MAX_WORKERS=3
WORKER_MEMORY_LIMIT_MB=512

# ✅ 智能重试（简化）
RETRY_MIN_WAIT_MINUTES=60
RETRY_SKIP_IF_PENDING_OVER=100
```

### 3.2 任务配置（`extraction_config`）

**新增字段**：
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

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `enabled` | boolean | false | 是否启用请求级限流 |
| `interval_seconds` | int/float | 5 | 每个请求之间的间隔时间（秒） |

**配置示例**：

```json
// 严格限流：每12秒一个请求
{
  "request_rate_limit": {
    "enabled": true,
    "interval_seconds": 12
  }
}

// 中等限流：每6秒一个请求
{
  "request_rate_limit": {
    "enabled": true,
    "interval_seconds": 6
  }
}

// 宽松限流：每3秒一个请求
{
  "request_rate_limit": {
    "enabled": true,
    "interval_seconds": 3
  }
}

// 不限流（默认）
{
  "request_rate_limit": {
    "enabled": false
  }
}
```

### 3.3 删除的配置清理

**数据库字段**（不需要删除，保持兼容）：
- `extraction_config` 字段保留（JSON类型，向后兼容）
- 旧配置中的 `rate_limit` 相关字段会被忽略

**环境变量清理**：
用户需要手动从 `.env` 文件中删除以下配置：
```bash
# 删除这些行
RATE_LIMIT_ENABLED=...
RATE_LIMIT_WINDOW_MINUTES=...
RATE_LIMIT_MAX_TASKS=...
RATE_LIMIT_PER_CONFIG=...
RETRY_RESPECT_RATE_LIMIT=...
```

---

## 4. 核心实现

### 4.1 RequestRateLimiter 类

**位置**：`app/services/executor.py`（作为内部类）

**实现**（固定间隔方式）：
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

### 4.2 执行器集成

**初始化**：
```python
# 在 execute_job() 开始
extraction_cfg = self._load_extraction_config(config)
rate_limit_cfg = extraction_cfg.get("request_rate_limit", {})

if rate_limit_cfg.get("enabled", False):
    interval = rate_limit_cfg.get("interval_seconds", 5)
    if interval <= 0:
        self.logger.warning("request_rate_limit.interval_seconds 必须大于 0，已禁用限流")
        self._request_limiter = None
    else:
        self._request_limiter = RequestRateLimiter(interval_seconds=interval)
        self.logger.info(f"[限流] 已启用请求级限流: 每 {interval} 秒一个请求")
else:
    self._request_limiter = None
```

**使用方式**：
```python
async def _rate_limit_check(self, operation_name: str = "请求"):
    """执行限流检查"""
    if not self._request_limiter:
        return
    
    wait_time = await self._request_limiter.acquire()
    if wait_time > 0:
        self.logger.info(f"[限流] {operation_name} - 等待 {wait_time:.1f} 秒")
        if self.ws_manager:
            await self._broadcast_log("info", f"[限流] 等待 {wait_time:.1f} 秒")

# 使用
await self._rate_limit_check("访问页面")
await page.goto(config.target_url)
```

### 4.3 需要限流的操作点

| 操作 | 代码位置 |
|------|----------|
| 访问页面 | `page.goto(target_url)` |
| 点击查询 | `page.click(submit_selector)` |
| 点击详情 | `detail_button.click()` |
| 翻页 | `next_button.click()` |

---

## 5. 代码删除清单

### 5.1 删除文件

```bash
# 删除限流相关文件
rm app/services/rate_limiter.py
rm app/api/rate_limit.py
```

### 5.2 修改文件

**`app/core/config.py`**：
```python
# 删除这些配置项
class Settings(BaseSettings):
    # ❌ 删除
    # RATE_LIMIT_ENABLED: bool = False
    # RATE_LIMIT_WINDOW_MINUTES: int = 60
    # RATE_LIMIT_MAX_TASKS: int = 100
    # RATE_LIMIT_PER_CONFIG: bool = False
    
    # ❌ 删除
    # RETRY_RESPECT_RATE_LIMIT: bool = True
    
    # ✅ 保留其他配置
    MAX_WORKERS: int = 3
    RETRY_MIN_WAIT_MINUTES: int = 60
    ...
```

**`app/services/scheduler.py`**：
```python
# 删除导入
# from app.services.rate_limiter import rate_limiter  # ❌ 删除

class TaskScheduler:
    async def dispatch_pending_jobs(self):
        """分发待处理任务"""
        # ... 前面代码保持不变 ...
        
        for job in pending_jobs:
            try:
                # ❌ 删除限流检查
                # can_execute = await rate_limiter.can_execute(job.config_id)
                # if not can_execute:
                #     wait_time = await rate_limiter.get_wait_time(job.config_id)
                #     logger.info(f"任务 #{job.id} 因限流跳过...")
                #     continue
                
                # ❌ 删除限流记录
                # await rate_limiter.record_execution(job.config_id)
                
                # ✅ 直接分发任务
                job.status = JobStatus.PROCESSING
                await session.commit()
                await self.pool_manager.submit_job(job.id)
                
            except Exception as e:
                logger.error(f"分发任务失败: {e}")
    
    async def retry_failed_jobs(self):
        """重试失败任务"""
        # ... 前面代码保持不变 ...
        
        # ❌ 删除限流压力检查
        # if settings.RETRY_RESPECT_RATE_LIMIT:
        #     rate_limit_status = await rate_limiter.get_status()
        #     if rate_limit_status.get('enabled'):
        #         utilization = ...
        #         if utilization > 0.8:
        #             return
        
        # ✅ 直接查询失败任务
        stmt = select(JobQueue).where(...)
        ...
```

**`app/main.py`**：
```python
# 删除路由注册
# from app.api.rate_limit import router as rate_limit_router  # ❌ 删除
# app.include_router(rate_limit_router)  # ❌ 删除

# ✅ 保留其他路由
app.include_router(router)
app.include_router(config_router)
...
```

### 5.3 文档更新

**需要更新的文档**：
- `CLAUDE.md` - 删除任务级限流相关说明
- `README.md` - 删除 `.env` 中的限流配置说明
- `docs/rate_limit_guide.md` - 删除或重写（仅说明请求级限流）
- `docs/配置参数详解与设置指南.md` - 删除任务级限流部分

---

## 6. 迁移指南

### 6.1 用户迁移步骤

**步骤 1：备份配置**
```bash
cp .env .env.backup
```

**步骤 2：更新代码**
```bash
git pull origin main
```

**步骤 3：清理 `.env` 配置**
手动删除以下配置行：
```bash
# 删除这些
RATE_LIMIT_ENABLED=...
RATE_LIMIT_WINDOW_MINUTES=...
RATE_LIMIT_MAX_TASKS=...
RATE_LIMIT_PER_CONFIG=...
RETRY_RESPECT_RATE_LIMIT=...
```

**步骤 4：配置请求级限流**
通过 API 或数据库更新 `extraction_config`：
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

**步骤 5：重启服务**
```bash
# 停止服务
Ctrl+C

# 重新启动
startup.bat
```

### 6.2 配置转换建议

**旧配置 → 新配置**：

```
旧配置（任务级限流）:
RATE_LIMIT_ENABLED=true
RATE_LIMIT_WINDOW_MINUTES=60
RATE_LIMIT_MAX_TASKS=100
MAX_WORKERS=3

转换逻辑：
- 任务级限流: 100 任务/小时
- 每个任务约 5-10 个HTTP请求
- 总请求: 100 × 7.5 = 750 请求/小时
- 每个进程: 750 ÷ 3 = 250 请求/小时

新配置（请求级限流）:
extraction_config:
  request_rate_limit:
    enabled: true
    window_minutes: 60
    max_requests: 250  # 每个任务独立限流
```

**推荐配置**：

| 场景 | interval_seconds | 说明 |
|------|------------------|------|
| 严格限流 | 12 | 每12秒一个请求（5个/分钟） |
| 中等限流 | 6 | 每6秒一个请求（10个/分钟） |
| 宽松限流 | 3 | 每3秒一个请求（20个/分钟） |
| 快速采集 | 1 | 每1秒一个请求（60个/分钟） |
| 不限流 | - | enabled: false |

---

## 7. 优势对比

### 7.1 简化前 vs 简化后

| 维度 | 简化前 | 简化后 |
|------|--------|--------|
| **配置数量** | 4个全局 + N个任务 | 0个全局 + N个任务 |
| **限流层级** | 2层（任务 + 请求） | 1层（请求） |
| **代码文件** | 2个额外文件 | 0个额外文件 |
| **用户理解** | 复杂（两层概念） | 简单（单一概念） |
| **控制精度** | 粗粒度（任务） | 细粒度（请求） |

### 7.2 效果对比

**场景：1000个任务，每个任务10个HTTP请求**

**简化前（任务级限流）**：
```
配置: 100 任务/小时
结果: 10小时完成
问题: 无法控制单个任务内的请求频率
风险: 任务内连续10次请求可能触发反爬
```

**简化后（请求级限流）**：
```
配置: 每任务 10 请求/分钟
结果: 每个任务约1分钟完成
      总耗时取决于 MAX_WORKERS
优势: 精确控制每个HTTP请求间隔
风险: 低，请求间隔均匀分布
```

---

## 8. 测试计划

### 8.1 单元测试

**测试 RequestRateLimiter**：
```python
async def test_request_rate_limiter():
    limiter = RequestRateLimiter(window_minutes=1, max_requests=3)
    
    # 前3个请求立即通过
    for i in range(3):
        wait = await limiter.acquire()
        assert wait == 0
    
    # 第4个请求应等待
    wait = await limiter.acquire()
    assert wait > 0
```

### 8.2 集成测试

**测试配置加载**：
```python
async def test_executor_no_global_rate_limiter():
    """验证全局限流器已删除"""
    from app.services import rate_limiter
    # 应该抛出 ImportError
```

**测试调度器**：
```python
async def test_scheduler_dispatch_without_rate_limit():
    """验证调度器不再检查全局限流"""
    # 创建10个pending任务
    # 如果有3个空闲插槽，应立即分发3个
    # 不应有限流等待
```

### 8.3 回归测试

**验证删除不影响其他功能**：
- [ ] 任务正常执行
- [ ] 调度器正常分发任务
- [ ] 失败任务正常重试
- [ ] WebSocket 推送正常
- [ ] 日志正常输出

---

## 9. 文档更新清单

### 9.1 需要更新的文档

**配置文档**：
- [ ] `CLAUDE.md` - 删除任务级限流说明，添加请求级限流
- [ ] `README.md` - 更新 `.env` 配置示例
- [ ] `docs/配置参数详解与设置指南.md` - 重写限流部分
- [ ] `docs/rate_limit_guide.md` - 重写或删除

**用户指南**：
- [ ] `docs/env_config_update.md` - 删除相关配置
- [ ] `docs/package_config_update.md` - 更新打包版本配置说明
- [ ] `配置生效情况检查报告.md` - 更新限流配置检查结果

**部署文档**：
- [ ] `scripts/deployment/README.txt` - 更新配置说明
- [ ] `scripts/deployment/client/配置说明.txt` - 删除限流配置

### 9.2 需要生成的新文档

- [ ] `docs/request_rate_limit_guide.md` - 请求级限流使用指南
- [ ] `docs/migration_remove_task_rate_limit.md` - 迁移指南

---

## 10. 实施计划

### 10.1 Phase 1: 代码删除（第1天）

- [ ] 删除 `app/services/rate_limiter.py`
- [ ] 删除 `app/api/rate_limit.py`
- [ ] 从 `app/core/config.py` 删除配置项
- [ ] 从 `app/services/scheduler.py` 删除限流检查
- [ ] 从 `app/main.py` 删除路由注册
- [ ] 运行测试，确保无编译错误

### 10.2 Phase 2: 实现请求级限流（第2-3天）

- [ ] 实现 `RequestRateLimiter` 类
- [ ] 在执行器中集成限流检查
- [ ] 添加日志和WebSocket推送
- [ ] 单元测试

### 10.3 Phase 3: 测试与验证（第4天）

- [ ] 集成测试
- [ ] 端到端测试
- [ ] 回归测试
- [ ] 性能测试

### 10.4 Phase 4: 文档更新（第5天）

- [ ] 更新所有相关文档
- [ ] 编写迁移指南
- [ ] 生成新的用户手册

### 10.5 Phase 5: 部署与迁移（第6-7天）

- [ ] 部署到测试环境
- [ ] 用户迁移测试
- [ ] 生产环境部署
- [ ] 用户通知和支持

---

## 11. 风险评估

### 11.1 潜在风险

| 风险 | 影响 | 概率 | 缓解措施 |
|------|------|------|----------|
| 删除代码导致其他功能异常 | 高 | 低 | 完整的回归测试 |
| 用户配置迁移困难 | 中 | 中 | 详细迁移文档 + 工具脚本 |
| 请求级限流不符合预期 | 中 | 低 | 充分测试，提供回滚方案 |
| 文档遗漏导致用户困惑 | 低 | 中 | 文档审查清单 |

### 11.2 回滚方案

如果新设计出现问题：
1. 回滚到上一个稳定版本（保留旧代码的分支）
2. 恢复 `.env` 配置
3. 重启服务

---

## 12. 总结

### 12.1 核心改进

- ✅ 删除 4 个全局配置项
- ✅ 删除 2 个代码文件（~500 行代码）
- ✅ 简化限流概念（2层 → 1层）
- ✅ 提高控制精度（任务级 → 请求级）
- ✅ 降低用户学习成本

### 12.2 预期效果

- 配置更简单易懂
- 限流更精确有效
- 代码更易维护
- 架构更清晰

### 12.3 下一步

完成设计评审后，开始实施（编写实现计划）。
