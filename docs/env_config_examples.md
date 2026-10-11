# .env 配置示例

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
# 待处理任务分发间隔（分钟）
DISPATCH_INTERVAL_MINUTES=30

# 失败任务重试间隔（分钟）
RETRY_INTERVAL_MINUTES=30

# 最大重试次数
MAX_RETRY_COUNT=3

# 每批重试的任务数量
RETRY_BATCH_SIZE=100

# ==================== 限流配置 ====================
# 是否启用限流
RATE_LIMIT_ENABLED=true

# 时间窗口（分钟）
RATE_LIMIT_WINDOW_MINUTES=60

# 时间窗口内最多执行的任务数
RATE_LIMIT_MAX_TASKS=100

# 是否按配置ID分别限流（true=每个配置独立计数，false=全局统一计数）
RATE_LIMIT_PER_CONFIG=false

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
**特点**：快速迭代，资源有限，不限流

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

# 限流
RATE_LIMIT_ENABLED=false  # 测试环境不限流
```

### 场景2：生产环境 - 严格限流
**特点**：目标网站有严格限制，防止被封禁

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
RETRY_BATCH_SIZE=50  # 控制批量重试数量

# 限流（严格）
RATE_LIMIT_ENABLED=true
RATE_LIMIT_WINDOW_MINUTES=60
RATE_LIMIT_MAX_TASKS=50  # 每小时50个任务
RATE_LIMIT_PER_CONFIG=false
```

### 场景3：生产环境 - 高吞吐量
**特点**：服务器资源充足，目标网站限制宽松

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

# 限流（宽松）
RATE_LIMIT_ENABLED=true
RATE_LIMIT_WINDOW_MINUTES=60
RATE_LIMIT_MAX_TASKS=300  # 每小时300个任务
RATE_LIMIT_PER_CONFIG=false
```

### 场景4：多站点采集
**特点**：同时采集多个网站，每个网站独立限流

```bash
# 数据库
DATABASE_URL=mssql+aioodbc://sa:Prod@2024@prod-server:1433/bap?driver=ODBC+Driver+17+for+SQL+Server

# 应用
DEBUG=False
HEADLESS_MODE=True

# 进程池
MAX_WORKERS=4

# 调度
RETRY_INTERVAL_MINUTES=30
MAX_RETRY_COUNT=3
RETRY_BATCH_SIZE=100

# 限流（按配置独立计数）
RATE_LIMIT_ENABLED=true
RATE_LIMIT_WINDOW_MINUTES=60
RATE_LIMIT_MAX_TASKS=100  # 每个配置每小时100个任务
RATE_LIMIT_PER_CONFIG=true  # 关键：启用按配置限流
```

### 场景5：短时间窗口精细控制
**特点**：需要精细控制短期内的访问频率

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

# 限流（短窗口）
RATE_LIMIT_ENABLED=true
RATE_LIMIT_WINDOW_MINUTES=10  # 10分钟窗口
RATE_LIMIT_MAX_TASKS=20  # 每10分钟20个任务（相当于每小时120个）
RATE_LIMIT_PER_CONFIG=false
```

### 场景6：大批量任务 + 严格限流（重要场景）
**特点**：
- 1000+ 个任务需要执行
- 严格的访问频率限制（如每2分钟2个任务）
- 需要智能重试避免队列竞争

```bash
# 数据库
DATABASE_URL=mssql+aioodbc://sa:Prod@2024@prod-server:1433/bap?driver=ODBC+Driver+17+for+SQL+Server

# 应用
DEBUG=False
HEADLESS_MODE=True

# 进程池（匹配限流速率）
MAX_WORKERS=2

# 严格限流
RATE_LIMIT_ENABLED=true
RATE_LIMIT_WINDOW_MINUTES=2
RATE_LIMIT_MAX_TASKS=2  # 每2分钟2个任务
RATE_LIMIT_PER_CONFIG=false

# 智能重试（关键配置）
RETRY_INTERVAL_MINUTES=60  # 每小时扫描一次
MAX_RETRY_COUNT=5  # 增加重试次数
RETRY_BATCH_SIZE=50  # 减少批量重试数量

# 智能重试策略
RETRY_MIN_WAIT_MINUTES=800  # 失败后等待13小时再重试（1000任务约需16小时）
RETRY_SKIP_IF_PENDING_OVER=100  # pending>100时跳过重试，优先处理新任务
RETRY_RESPECT_RATE_LIMIT=true  # 遵守限流，避免加重压力
```

**效果**：
- 1000个任务慢慢执行（约16小时）
- 重试任务不会在大量 pending 时竞争资源
- 等大部分任务执行完后才处理重试
- 避免限流冲突

## 配置参数速查表

| 参数 | 默认值 | 说明 | 推荐值 |
|------|--------|------|--------|
| MAX_WORKERS | 3 | 并发任务数 | 低配2，中配3-5，高配5-10 |
| RETRY_INTERVAL_MINUTES | 30 | 重试间隔 | 快速5-10，正常30，低频60 |
| MAX_RETRY_COUNT | 3 | 最大重试次数 | 2-5次 |
| RETRY_BATCH_SIZE | 100 | 每批重试数量 | 少50，中100，多200-500 |
| RATE_LIMIT_ENABLED | false | 启用限流 | 有限制的网站必须true |
| RATE_LIMIT_WINDOW_MINUTES | 60 | 限流窗口 | 30-120分钟 |
| RATE_LIMIT_MAX_TASKS | 100 | 窗口内任务数 | 严格50，正常100，宽松300 |
| RATE_LIMIT_PER_CONFIG | false | 按配置限流 | 多站点true，单站点false |

## 性能计算

### 理论最大吞吐量

**公式**：`实际吞吐量 = min(并发限制, 限流限制)`

#### 示例1：并发受限
```bash
MAX_WORKERS=3
RATE_LIMIT_ENABLED=false
```
**理论吞吐量**：取决于单个任务耗时
- 单任务耗时 1 分钟 → 3个/分钟 = 180个/小时
- 单任务耗时 2 分钟 → 1.5个/分钟 = 90个/小时

#### 示例2：限流受限
```bash
MAX_WORKERS=5
RATE_LIMIT_ENABLED=true
RATE_LIMIT_WINDOW_MINUTES=60
RATE_LIMIT_MAX_TASKS=100
```
**理论吞吐量**：100个/小时（限流上限）

#### 示例3：均衡配置
```bash
MAX_WORKERS=3
RATE_LIMIT_ENABLED=true
RATE_LIMIT_WINDOW_MINUTES=60
RATE_LIMIT_MAX_TASKS=180
# 单任务耗时约1分钟
```
**理论吞吐量**：3个/分钟 × 60分钟 = 180个/小时
**实际吞吐量**：min(180, 180) = 180个/小时（完全利用）

## 配置调优流程

### 1. 初始配置（保守）
```bash
MAX_WORKERS=2
RATE_LIMIT_ENABLED=true
RATE_LIMIT_WINDOW_MINUTES=60
RATE_LIMIT_MAX_TASKS=50
```

### 2. 监控观察（运行1小时）
- 查看限流使用率：`GET /api/rate-limit/status`
- 查看任务执行情况
- 观察是否有被封禁或限流错误

### 3. 逐步调优
**如果限流使用率 < 50%**：
```bash
# 提高限流上限
RATE_LIMIT_MAX_TASKS=100
```

**如果经常有任务被跳过**：
```bash
# 增加并发或提高限流
MAX_WORKERS=3
RATE_LIMIT_MAX_TASKS=100
```

**如果出现429错误或被封禁**：
```bash
# 降低限流和并发
MAX_WORKERS=2
RATE_LIMIT_MAX_TASKS=30
```

### 4. 稳定运行
找到平衡点后，在此基础上保持 20% 的安全余量。

## 注意事项

1. **必须重启生效**：所有配置修改后需要重启应用
2. **限流优先级高**：即使有空闲进程，达到限流上限也不会执行
3. **合理设置窗口**：过短会导致频繁检查，过长会延迟响应
4. **监控日志**：定期检查日志中的限流警告
5. **测试先行**：在测试环境验证配置后再上生产

## 相关文档

- 完整配置说明：`docs/env_config_update.md`
- 限流详细指南：`docs/rate_limit_guide.md`
- 配置迁移总结：`docs/config_migration_summary.md`
- 项目文档：`CLAUDE.md`
