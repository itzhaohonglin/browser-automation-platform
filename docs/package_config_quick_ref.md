# 打包版本配置快速参考

## 🚀 新增配置项速查表

### ⚠️ 限流控制（防止被封禁）

```bash
RATE_LIMIT_ENABLED=true              # 启用限流
RATE_LIMIT_WINDOW_MINUTES=60         # 时间窗口：60分钟
RATE_LIMIT_MAX_TASKS=100             # 窗口内最多100个任务
RATE_LIMIT_PER_CONFIG=false          # 全局限流（多站点设为true）
```

**推荐配置**:
| 场景 | 窗口(分钟) | 任务数 | 说明 |
|------|----------|--------|------|
| 严格 | 60 | 50 | 每小时50个，适合严格网站 |
| 中等 | 60 | 100 | 每小时100个，常规场景 |
| 宽松 | 60 | 300 | 每小时300个，宽松网站 |

### 🔄 智能重试（优化重试策略）

```bash
RETRY_MIN_WAIT_MINUTES=60            # 失败后至少等60分钟才重试
RETRY_SKIP_IF_PENDING_OVER=100       # pending>100时跳过重试
RETRY_RESPECT_RATE_LIMIT=true        # 重试遵守限流
```

**计算公式**:
- `RETRY_MIN_WAIT_MINUTES` = 预计全量任务耗时(分钟) × 0.8
- `RETRY_SKIP_IF_PENDING_OVER` = 总任务数 × 0.1

### ⚙️ 并发控制（性能调优）

```bash
MAX_WORKERS=3                        # 同时3个任务
WORKER_MEMORY_LIMIT_MB=512           # 每进程512MB内存
```

**推荐配置**:
| 机器配置 | MAX_WORKERS | 说明 |
|---------|------------|------|
| 4核8G | 2-3 | 低配机器 |
| 8核16G | 3-5 | 中配机器 |
| 16核32G | 5-10 | 高配机器 |

## 📝 配置步骤

### 新安装（推荐）

1. **重新打包**（包含新配置模板）
   ```bash
   scripts\deployment\build_release.bat
   ```

2. **客户端安装**
   ```bash
   install.bat  # 会自动创建包含所有配置的 .env
   ```

### 已部署更新

1. **停止服务** (Ctrl+C)

2. **编辑 .env**，添加上述配置

3. **重启服务**
   ```bash
   startup.bat
   ```

## 🔍 验证配置

```bash
# 检查配置文件
check_config.bat

# 查看限流状态（浏览器）
http://localhost:8000/api/rate-limit/status

# 观察日志输出
# 启动时会显示当前配置
```

## 💡 常见场景配置

### 场景1: 国家医保局（严格限流）

```bash
RATE_LIMIT_ENABLED=true
RATE_LIMIT_WINDOW_MINUTES=60
RATE_LIMIT_MAX_TASKS=50
RETRY_MIN_WAIT_MINUTES=960  # 1000任务÷50/小时=20小时×0.8=16小时=960分钟
```

### 场景2: 内部系统（无限流）

```bash
RATE_LIMIT_ENABLED=false
RETRY_MIN_WAIT_MINUTES=10
MAX_WORKERS=5
```

### 场景3: 多站点（分别限流）

```bash
RATE_LIMIT_ENABLED=true
RATE_LIMIT_PER_CONFIG=true  # 关键！
RATE_LIMIT_WINDOW_MINUTES=60
RATE_LIMIT_MAX_TASKS=100
```

## 📚 详细文档

- 📖 完整指南: `docs/package_config_update.md`
- 🎯 限流详解: `docs/rate_limit_guide.md`
- 🔄 智能重试: `docs/smart_retry_optimization.md`
