# 任务执行性能优化指南

## 问题现象

执行完一个任务后，长时间没有继续执行下一个任务，导致大量任务积压在队列中。

## 根本原因

系统默认配置较为保守，适合小规模任务，但不适合大批量任务处理：

1. **分发间隔太长**：`DISPATCH_INTERVAL_MINUTES=30`（默认30分钟）
   - 每30分钟才扫描一次待处理任务
   - 导致任务分发不及时

2. **并发度太低**：`MAX_WORKERS=1`（默认3，但可能被修改为1）
   - 每次只能执行1个任务
   - 无法充分利用机器性能

## 性能计算

假设有 1625 个任务：

### 当前配置（慢）
- `MAX_WORKERS=1`，`DISPATCH_INTERVAL_MINUTES=30`
- 每30分钟处理1个任务
- **总耗时：1625 × 30分钟 ≈ 812.5小时（约34天）**

### 优化后配置（快）
- `MAX_WORKERS=5`，`DISPATCH_INTERVAL_MINUTES=5`
- 每5分钟分发一批，同时运行5个任务
- **总耗时：1625 ÷ 5 × 5分钟 ≈ 27小时**

## 解决方案

### 打包版本（推荐）

#### 步骤1：检查配置文件

首先检查 `.env` 文件是否包含必要的配置项：

```bash
# 在打包目录下
type .env | findstr "DISPATCH_INTERVAL_MINUTES"
type .env | findstr "MAX_WORKERS"
```

#### 步骤2：添加或修改配置

**情况A：配置项已存在**

直接编辑 `dist/browser-automation-platform/.env` 文件，修改数值：

```bash
MAX_WORKERS=5                    # 修改这行
DISPATCH_INTERVAL_MINUTES=5      # 修改这行
```

**情况B：配置项不存在（旧版本）**

如果你的 `.env` 文件缺少这些配置项，有两种方法：

**方法1：手动添加（推荐）**

在 `.env` 文件末尾添加以下内容（或参考 `docs/env_task_scheduling_snippet.txt`）：

```bash
# ==================== 进程池配置 ====================
MAX_WORKERS=5
WORKER_MEMORY_LIMIT_MB=512

# ==================== 任务调度配置 ====================
DISPATCH_INTERVAL_MINUTES=5
RETRY_INTERVAL_MINUTES=30
MAX_RETRY_COUNT=3
RETRY_BATCH_SIZE=100

# ==================== 智能重试配置 ====================
RETRY_MIN_WAIT_MINUTES=60
RETRY_SKIP_IF_PENDING_OVER=100
```

**方法2：从模板重新生成**

```bash
# 1. 备份当前配置
copy .env .env.backup

# 2. 从模板复制
copy .env.template .env

# 3. 编辑 .env，填入你的实际配置（DATABASE_URL 等）
notepad .env
```

#### 步骤3：重启服务

```bash
# 1. 停止当前服务（Ctrl+C）
# 2. 重新启动
startup.bat
```

### 开发环境

编辑项目根目录的 `.env` 文件，修改相同参数。

## 配置说明

### MAX_WORKERS（并发数）

**作用**：控制同时执行的任务数量

**推荐值**：
- **2-3**：低配机器（4核8G内存）
- **3-5**：中配机器（8核16G内存）
- **5-10**：高配机器（16核32G内存）

**注意事项**：
- 每个进程约消耗 200-500MB 内存
- 过高会导致浏览器卡顿、内存不足
- 建议从低值开始，逐步调高测试

### DISPATCH_INTERVAL_MINUTES（分发间隔）

**作用**：控制多久扫描一次待处理任务

**推荐值**：
- **5-10 分钟**：批量任务处理（1000+任务）
- **15-20 分钟**：中等任务量（100-1000任务）
- **30 分钟**：日常零散任务（<100任务）

**注意事项**：
- 间隔太短会增加数据库查询压力
- 间隔太长会导致任务分发不及时
- 建议根据任务总量动态调整

## 其他相关配置

### 智能重试配置

如果有大量待处理任务，可以暂时关闭失败任务重试：

```bash
# 如果 pending 任务超过此数量，跳过失败任务重试
RETRY_SKIP_IF_PENDING_OVER=100

# 失败后至少等待多久才重试（分钟）
# 建议值：预计全量任务耗时 × 0.8
# 示例：1625个任务预计27小时 → 设置 1200 分钟
RETRY_MIN_WAIT_MINUTES=1200
```

### 请求级限流

如果目标网站有访问频率限制，启用请求级限流：

```bash
# 启用请求级限流（防止被封禁）
REQUEST_RATE_LIMIT_ENABLED=true

# 每个 HTTP 请求间隔（秒）
REQUEST_RATE_LIMIT_INTERVAL_SECONDS=6.0
```

**注意**：启用限流会降低单个任务的执行速度，但可以通过增加 `MAX_WORKERS` 来补偿。

## 监控与调优

### 查看实时状态

打开监控看板：http://127.0.0.1:8000/static/index.html

观察指标：
- **活跃工作进程数**：应接近 `MAX_WORKERS`
- **待处理任务数**：应逐渐减少
- **成功率**：应保持在 90% 以上

### 查看日志

```bash
# 打包版本
type logs\app.log | findstr "分发"

# 开发环境
tail -f log/app.log | grep "分发"
```

### 性能调优建议

1. **首次运行**：使用保守配置（`MAX_WORKERS=2`，`DISPATCH_INTERVAL_MINUTES=10`）
2. **观察资源使用**：通过任务管理器查看 CPU 和内存占用
3. **逐步提高并发**：如果资源充足，逐步增加 `MAX_WORKERS`
4. **缩短分发间隔**：如果任务积压，减小 `DISPATCH_INTERVAL_MINUTES`
5. **平衡限流与速度**：根据目标网站限制，调整 `REQUEST_RATE_LIMIT_INTERVAL_SECONDS`

## 常见问题

### Q1：修改配置后没有生效？
**A**：必须重启服务才能生效。停止当前进程（Ctrl+C），然后重新运行 `startup.bat`。

### Q2：增加 MAX_WORKERS 后系统变卡？
**A**：降低 `MAX_WORKERS`，或者增加 `REQUEST_RATE_LIMIT_INTERVAL_SECONDS` 减缓请求速度。

### Q3：任务失败率突然升高？
**A**：可能触发了目标网站的反爬虫机制，启用请求级限流或降低并发数。

### Q4：如何计算最优配置？
**A**：
```
预计总耗时 = 任务总数 ÷ MAX_WORKERS × 单任务平均耗时（分钟）
            + 任务总数 ÷ MAX_WORKERS ÷ (60 ÷ DISPATCH_INTERVAL_MINUTES) × DISPATCH_INTERVAL_MINUTES

简化公式：
预计总耗时 ≈ (任务总数 ÷ MAX_WORKERS + 任务总数 ÷ (60 ÷ DISPATCH_INTERVAL_MINUTES)) × 单任务平均耗时
```

实际上，只要 `DISPATCH_INTERVAL_MINUTES` 远小于单任务耗时，分发延迟可以忽略。

## 推荐配置模板

### 场景1：快速处理大批量任务（1000+）

```bash
MAX_WORKERS=5
DISPATCH_INTERVAL_MINUTES=5
REQUEST_RATE_LIMIT_ENABLED=true
REQUEST_RATE_LIMIT_INTERVAL_SECONDS=5.0
```

### 场景2：稳定处理中等任务（100-1000）

```bash
MAX_WORKERS=3
DISPATCH_INTERVAL_MINUTES=10
REQUEST_RATE_LIMIT_ENABLED=true
REQUEST_RATE_LIMIT_INTERVAL_SECONDS=6.0
```

### 场景3：日常零散任务（<100）

```bash
MAX_WORKERS=2
DISPATCH_INTERVAL_MINUTES=30
REQUEST_RATE_LIMIT_ENABLED=false
```

### 场景4：严格限流（政府网站）

```bash
MAX_WORKERS=3
DISPATCH_INTERVAL_MINUTES=10
REQUEST_RATE_LIMIT_ENABLED=true
REQUEST_RATE_LIMIT_INTERVAL_SECONDS=10.0
```
