# 打包版本配置更新指南

## 概述

本文档说明如何更新打包版本（`dist/browser-automation-platform/`）中的环境配置，特别是新增的限流和智能重试配置。

## 新增配置项

### 1. 限流控制配置

**用途**: 防止因访问频率过高被目标网站封禁

```bash
# 是否启用限流
RATE_LIMIT_ENABLED=true

# 限流时间窗口（分钟）
RATE_LIMIT_WINDOW_MINUTES=60

# 时间窗口内最多执行的任务数
RATE_LIMIT_MAX_TASKS=100

# 是否按配置ID分别限流
RATE_LIMIT_PER_CONFIG=false
```

**配置示例**:
- **严格限流**: `RATE_LIMIT_WINDOW_MINUTES=60, RATE_LIMIT_MAX_TASKS=50` (每小时50个任务)
- **中等限流**: `RATE_LIMIT_WINDOW_MINUTES=60, RATE_LIMIT_MAX_TASKS=100` (每小时100个任务)
- **宽松限流**: `RATE_LIMIT_WINDOW_MINUTES=60, RATE_LIMIT_MAX_TASKS=300` (每小时300个任务)

### 2. 智能重试配置

**用途**: 优化失败任务的重试策略，避免与新任务竞争

```bash
# 失败后至少等待多久才重试（分钟）
RETRY_MIN_WAIT_MINUTES=60

# 如果 pending 任务超过此数量，跳过重试
RETRY_SKIP_IF_PENDING_OVER=100

# 重试时是否遵守限流
RETRY_RESPECT_RATE_LIMIT=true
```

**配置建议**:
- `RETRY_MIN_WAIT_MINUTES`: 根据任务总量和限流计算
  - 公式: 预计全量任务耗时 × 0.8
  - 示例: 1000个任务需16小时 → 设置为 800 分钟
- `RETRY_SKIP_IF_PENDING_OVER`: 总任务数 × 0.1
- `RETRY_RESPECT_RATE_LIMIT`: 建议设为 `true`

### 3. 并发控制配置

**用途**: 控制同时执行的任务数量

```bash
# 最大工作进程数（同时执行的任务数）
MAX_WORKERS=3

# 工作进程内存限制（MB）
WORKER_MEMORY_LIMIT_MB=512
```

**配置建议**:
- 低配机器（4核8G）: `MAX_WORKERS=2-3`
- 中配机器（8核16G）: `MAX_WORKERS=3-5`
- 高配机器（16核32G）: `MAX_WORKERS=5-10`

## 配置文件更新流程

### 方式一：使用配置模板（推荐）

1. **重新打包项目**
   ```bash
   # 在项目根目录运行
   scripts\deployment\build_release.bat
   ```

2. **配置模板已自动包含**
   - `.env.template` 包含所有配置项及说明
   - 打包时会自动复制到 `dist/browser-automation-platform/`

3. **客户端安装时配置**
   ```bash
   # 运行安装脚本
   install.bat
   
   # 会自动创建 .env 文件（从 .env.template 复制）
   # 按提示修改配置项
   ```

### 方式二：手动更新现有 .env 文件

如果打包版本已经部署，可以手动在 `.env` 文件中添加新配置：

```bash
# 1. 停止服务
# 按 Ctrl+C 停止 startup.bat

# 2. 编辑 .env 文件，添加以下配置

# === 限流控制（如果目标网站有频率限制） ===
RATE_LIMIT_ENABLED=true
RATE_LIMIT_WINDOW_MINUTES=60
RATE_LIMIT_MAX_TASKS=100
RATE_LIMIT_PER_CONFIG=false

# === 智能重试（优化重试策略） ===
RETRY_MIN_WAIT_MINUTES=60
RETRY_SKIP_IF_PENDING_OVER=100
RETRY_RESPECT_RATE_LIMIT=true

# === 并发控制（可选调整） ===
MAX_WORKERS=3
WORKER_MEMORY_LIMIT_MB=512

# 3. 保存并重新启动服务
startup.bat
```

## 配置验证

### 1. 检查配置是否生效

```bash
# 运行配置检查脚本
check_config.bat
```

### 2. 查看限流状态（需要服务已启动）

```bash
# 方法1：浏览器访问
http://localhost:8000/api/rate-limit/status

# 方法2：使用 curl（如果已安装）
curl http://localhost:8000/api/rate-limit/status
```

### 3. 监控日志

```bash
# 启动服务后观察日志输出
# 会显示当前配置的限流参数和工作进程数
```

## 配置场景示例

### 场景1：国家医保局网站采集（有限流要求）

```bash
DATABASE_URL=mssql+aioodbc://sa:MyPassword@localhost:1433/bap?driver=ODBC+Driver+17+for+SQL+Server&charset=UTF-8
APP_PORT=8000
MAX_WORKERS=3

# 严格限流：每小时50个任务
RATE_LIMIT_ENABLED=true
RATE_LIMIT_WINDOW_MINUTES=60
RATE_LIMIT_MAX_TASKS=50
RATE_LIMIT_PER_CONFIG=false

# 智能重试：1000个任务预计20小时完成
RETRY_MIN_WAIT_MINUTES=960
RETRY_SKIP_IF_PENDING_OVER=100
RETRY_RESPECT_RATE_LIMIT=true
```

### 场景2：内部系统采集（无限流要求）

```bash
DATABASE_URL=mssql+aioodbc://sa:MyPassword@localhost:1433/bap?driver=ODBC+Driver+17+for+SQL+Server&charset=UTF-8
APP_PORT=8000
MAX_WORKERS=5

# 不启用限流
RATE_LIMIT_ENABLED=false

# 快速重试
RETRY_MIN_WAIT_MINUTES=10
RETRY_SKIP_IF_PENDING_OVER=50
RETRY_RESPECT_RATE_LIMIT=false
```

### 场景3：多站点采集（分别限流）

```bash
DATABASE_URL=mssql+aioodbc://sa:MyPassword@localhost:1433/bap?driver=ODBC+Driver+17+for+SQL+Server&charset=UTF-8
APP_PORT=8000
MAX_WORKERS=3

# 每个配置独立限流
RATE_LIMIT_ENABLED=true
RATE_LIMIT_WINDOW_MINUTES=60
RATE_LIMIT_MAX_TASKS=100
RATE_LIMIT_PER_CONFIG=true  # 关键配置

RETRY_MIN_WAIT_MINUTES=60
RETRY_SKIP_IF_PENDING_OVER=200
RETRY_RESPECT_RATE_LIMIT=true
```

## 常见问题

### Q1: 修改配置后需要重启服务吗？

**A**: 是的，必须重启。`.env` 文件只在服务启动时加载。

```bash
# 停止服务：按 Ctrl+C
# 重新启动：
startup.bat
```

### Q2: 限流配置对性能有影响吗？

**A**: 有轻微影响，但可忽略不计。限流检查非常快速（内存查询），每次任务执行前仅需 1-2ms。

### Q3: 如何知道当前限流是否触发？

**A**: 有三种方式：
1. 查看日志输出（会显示 "Rate limit exceeded"）
2. 访问 API：`http://localhost:8000/api/rate-limit/status`
3. 前端看板会显示任务等待状态

### Q4: 已经部署的打包版本如何更新配置模板？

**A**: 两种方式：
1. 重新打包并替换整个目录
2. 手动在现有 `.env` 文件中添加新配置项（参考本文档）

### Q5: 配置文件位置在哪里？

**A**: 
- 开发环境：项目根目录 `.env`
- 打包版本：`dist/browser-automation-platform/.env`
- 配置模板：`.env.template` 或 `.env.example`

## 相关文档

- **完整配置指南**: `docs/env_config_update.md`
- **限流配置详解**: `docs/rate_limit_guide.md`
- **智能重试说明**: `docs/smart_retry_optimization.md`
- **批量导入指南**: `docs/BATCH_IMPORT_GUIDE.md`

## 更新日志

- **2026-10-11**: 
  - 新增限流控制配置
  - 新增智能重试配置
  - 更新 install.bat 安装提示
  - 更新 .env.template 配置模板
