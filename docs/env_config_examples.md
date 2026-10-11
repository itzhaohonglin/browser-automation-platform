# .env 配置示例

> **📝 更新说明 (2026-10-11)**
> 
> 任务级限流配置（`RATE_LIMIT_*`）已被移除。新的请求级限流通过数据库配置 `extraction_config.request_rate_limit`，详见 CLAUDE.md。
> 
> ---

## 完整配置模板

```bash
# ==================== 数据库配置 ====================
# 必填项
DATABASE_URL=mssql+aioodbc://sa:YourPassword@localhost:1433/bap?driver=ODBC+Driver+17+for+SQL+Server

# ==================== 应用配置 ====================
APP_HOST=0.0.0.0
APP_PORT=8000
DEBUG=False

# ==================== Playwright 配置 ====================
HEADLESS_MODE=True

# ==================== 日志配置 ====================
LOG_LEVEL=INFO

# ==================== 进程池配置 ====================
# 最大工作进程数（同时执行的任务数）
MAX_WORKERS=3

# 工作进程内存限制（MB）
WORKER_MEMORY_LIMIT_MB=512

# ==================== 任务调度配置 ====================
# 失败任务重试间隔（分钟）
RETRY_INTERVAL_MINUTES=30

# 最大重试次数
MAX_RETRY_COUNT=3

# 每批重试的任务数量
RETRY_BATCH_SIZE=100

# 智能重试策略
RETRY_MIN_WAIT_MINUTES=60
RETRY_SKIP_IF_PENDING_OVER=100

# ==================== 告警邮件配置（可选）====================
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USE_TLS=True
SMTP_USER=
SMTP_PASSWORD=
ALERT_EMAIL_FROM=
ALERT_EMAIL_TO=

# ==================== 钉钉机器人（可选）====================
DINGTALK_WEBHOOK_URL=

# ==================== 企业微信机器人（可选）====================
WECOM_WEBHOOK_URL=
```

## 场景化配置示例

### 场景1：开发测试环境
**特点**：快速迭代，资源有限

```bash
# 数据库
DATABASE_URL=mssql+aioodbc://sa:Dev123456@localhost:1433/bap_dev?driver=ODBC+Driver+17+for+SQL+Server

# 应用
DEBUG=True
HEADLESS_MODE=False  # 有头模式便于调试

# 进程池
MAX_WORKERS=2  # 资源有限，降低并发

# 调度
RETRY_INTERVAL_MINUTES=5  # 快速重试
MAX_RETRY_COUNT=2
```

### 场景2：生产环境 - 标准配置
**特点**：稳定可靠，资源充足

```bash
# 数据库
DATABASE_URL=mssql+aioodbc://sa:Prod@2024@prod-server:1433/bap?driver=ODBC+Driver+17+for+SQL+Server

# 应用
DEBUG=False
HEADLESS_MODE=True

# 进程池
MAX_WORKERS=3

# 调度
RETRY_INTERVAL_MINUTES=30
MAX_RETRY_COUNT=3
RETRY_BATCH_SIZE=50
```

### 场景3：生产环境 - 高吞吐量
**特点**：服务器资源充足，需要高并发

```bash
# 数据库
DATABASE_URL=mssql+aioodbc://sa:Prod@2024@prod-server:1433/bap?driver=ODBC+Driver+17+for+SQL+Server

# 应用
DEBUG=False
HEADLESS_MODE=True

# 进程池
MAX_WORKERS=5  # 提高并发数

# 调度
RETRY_INTERVAL_MINUTES=10  # 快速重试
MAX_RETRY_COUNT=3
RETRY_BATCH_SIZE=200  # 大批量重试
```

### 场景4：大批量任务 + 智能重试
**特点**：
- 1000+ 个任务需要执行
- 需要智能重试避免队列竞争

```bash
# 数据库
DATABASE_URL=mssql+aioodbc://sa:Prod@2024@prod-server:1433/bap?driver=ODBC+Driver+17+for+SQL+Server

# 应用
DEBUG=False
HEADLESS_MODE=True

# 进程池
MAX_WORKERS=3

# 智能重试（关键配置）
RETRY_INTERVAL_MINUTES=60  # 每小时扫描一次
MAX_RETRY_COUNT=5  # 增加重试次数
RETRY_BATCH_SIZE=50  # 减少批量重试数量
RETRY_MIN_WAIT_MINUTES=800  # 失败后等待较长时间再重试
RETRY_SKIP_IF_PENDING_OVER=100  # pending>100时跳过重试，优先处理新任务
```

**效果**：
- 大批量任务稳定执行
- 重试任务不会在大量 pending 时竞争资源
- 等大部分任务执行完后才处理重试
- 避免队列竞争

## 配置参数速查表

| 参数 | 默认值 | 说明 | 推荐值 |
|------|--------|------|--------|
| MAX_WORKERS | 3 | 并发任务数 | 低配2，中配3-5，高配5-10 |
| RETRY_INTERVAL_MINUTES | 30 | 重试间隔 | 快速5-10，正常30，低频60 |
| MAX_RETRY_COUNT | 3 | 最大重试次数 | 2-5次 |
| RETRY_BATCH_SIZE | 100 | 每批重试数量 | 少50，中100，多200-500 |
| RETRY_MIN_WAIT_MINUTES | 60 | 重试最小等待时间 | 根据任务总量计算 |
| RETRY_SKIP_IF_PENDING_OVER | 100 | pending超过此数量跳过重试 | 总任务数 × 0.1 |

## 请求级限流配置

请求级限流不通过环境变量配置，而是在数据库的 `extraction_config` 字段中配置：

```python
# 在数据库中配置
config.extraction_config = {
    "request_rate_limit": {
        "enabled": True,
        "interval_seconds": 5  # 每个 HTTP 请求间隔 5 秒
    }
}
```

**限流示例**：
- **严格限流**：`interval_seconds: 10` (每 10 秒一个请求)
- **中等限流**：`interval_seconds: 5` (每 5 秒一个请求)
- **宽松限流**：`interval_seconds: 2` (每 2 秒一个请求)

详细说明请参考 CLAUDE.md 中的"请求级限流配置"章节。

## 配置调优流程

### 1. 初始配置（保守）
```bash
MAX_WORKERS=2
RETRY_INTERVAL_MINUTES=30
MAX_RETRY_COUNT=3
```

同时在数据库配置请求级限流：
```python
extraction_config = {
    "request_rate_limit": {
        "enabled": True,
        "interval_seconds": 5
    }
}
```

### 2. 监控观察（运行一段时间）
- 查看任务执行情况
- 观察是否有被封禁或限流错误
- 检查任务完成速度

### 3. 逐步调优
**如果任务执行太慢**：
- 减少 `interval_seconds`（如从 5 改为 3）
- 增加 `MAX_WORKERS`（如从 2 改为 3）

**如果出现429错误或被封禁**：
- 增加 `interval_seconds`（如从 5 改为 10）
- 降低 `MAX_WORKERS`

### 4. 稳定运行
找到平衡点后，在此基础上保持安全余量。

## 注意事项

1. **环境变量修改需重启**：修改 `.env` 后需要重启应用
2. **请求级限流立即生效**：修改数据库配置后立即生效，无需重启
3. **合理设置并发**：根据服务器资源和目标网站限制设置
4. **监控日志**：定期检查日志中的错误和警告
5. **测试先行**：在测试环境验证配置后再上生产

## 相关文档

- 完整配置说明：`CLAUDE.md`
- 智能重试说明：`docs/smart_retry_optimization.md`
- 项目文档：`README.md`
