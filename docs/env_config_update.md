# 环境变量配置更新说明

## 新增配置项

以下配置项已添加到 `app/core/config.py`，可以通过 `.env` 文件进行配置：

### 1. 任务调度配置

```bash
# 待处理任务分发间隔（分钟）
DISPATCH_INTERVAL_MINUTES=30

# 失败任务重试间隔（分钟）
RETRY_INTERVAL_MINUTES=30

# 最大重试次数
MAX_RETRY_COUNT=3

# 每批重试的任务数量
RETRY_BATCH_SIZE=100
```

### 2. 进程池配置

```bash
# 最大工作进程数（并发任务数）
MAX_WORKERS=3

# 工作进程内存限制（MB）
WORKER_MEMORY_LIMIT_MB=512
```

## .env 文件示例

将以下配置添加到你的 `.env` 文件中：

```bash
# 数据库配置（必填）
DATABASE_URL=mssql+aioodbc://sa:YourPassword@localhost:1433/bap?driver=ODBC+Driver+17+for+SQL+Server

# 应用配置
APP_HOST=0.0.0.0
APP_PORT=8000
DEBUG=False

# Playwright 配置
HEADLESS_MODE=True

# 日志配置
LOG_LEVEL=INFO

# === 新增：任务调度配置 ===
DISPATCH_INTERVAL_MINUTES=30
RETRY_INTERVAL_MINUTES=30
MAX_RETRY_COUNT=3
RETRY_BATCH_SIZE=100

# === 新增：进程池配置 ===
MAX_WORKERS=3
WORKER_MEMORY_LIMIT_MB=512

# 告警邮件配置（可选）
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USE_TLS=True
SMTP_USER=
SMTP_PASSWORD=
ALERT_EMAIL_FROM=
ALERT_EMAIL_TO=

# 钉钉机器人（可选）
DINGTALK_WEBHOOK_URL=

# 企业微信机器人（可选）
WECOM_WEBHOOK_URL=
```

## 配置说明

### MAX_WORKERS（重要）
- **默认值**: 3
- **含义**: 系统同时最多执行 3 个任务
- **建议值**: 
  - 低配机器（4核8G）: 2-3
  - 中配机器（8核16G）: 3-5
  - 高配机器（16核32G）: 5-10
- **注意**: 每个工作进程会启动一个 Playwright 浏览器实例，消耗约 200-500MB 内存

### RETRY_INTERVAL_MINUTES
- **默认值**: 30
- **含义**: 每 30 分钟扫描一次失败任务并重试
- **建议值**: 
  - 快速重试: 5-10 分钟
  - 正常重试: 30 分钟
  - 低频重试: 60 分钟

### MAX_RETRY_COUNT
- **默认值**: 3
- **含义**: 每个失败任务最多重试 3 次
- **建议值**: 2-5 次

### RETRY_BATCH_SIZE
- **默认值**: 100
- **含义**: 每次扫描最多重置 100 个失败任务
- **建议值**: 
  - 任务量少: 50
  - 任务量中等: 100
  - 任务量大: 200-500

### DISPATCH_INTERVAL_MINUTES
- **默认值**: 30
- **含义**: 每 30 分钟扫描一次待处理任务并分发
- **建议值**: 保持默认值即可，任务会在进程空闲时自动分发

## 生效方式

1. **修改 .env 文件**后，需要**重启应用**才能生效
2. 重启命令：
   ```bash
   # 停止应用（Ctrl+C）
   # 重新启动
   uvicorn app.main:app --reload
   ```

## 验证配置

启动应用后，查看日志中的配置信息：

```
INFO - 初始化进程池管理器: max_workers=3, memory_limit=512MB
INFO - 调度器与进程池已启动
```

## 性能调优建议

### 场景1：大量任务需要快速处理
```bash
MAX_WORKERS=5
RETRY_INTERVAL_MINUTES=10
DISPATCH_INTERVAL_MINUTES=30
```

### 场景2：资源受限的服务器
```bash
MAX_WORKERS=2
WORKER_MEMORY_LIMIT_MB=256
RETRY_INTERVAL_MINUTES=60
```

### 场景3：高稳定性要求
```bash
MAX_WORKERS=3
MAX_RETRY_COUNT=5
RETRY_INTERVAL_MINUTES=30
RETRY_BATCH_SIZE=50
```
