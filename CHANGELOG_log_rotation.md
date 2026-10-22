# 日志轮转功能实现总结

**日期**: 2026-10-22  
**功能**: 支持按天或按小时自动轮转日志文件

## 实现内容

### 1. 新增配置项

在 `app/core/config.py` 中添加：

```python
# 日志配置
LOG_LEVEL: str = "INFO"
LOG_FILE: Optional[str] = None
LOG_ROTATION: str = "daily"  # 日志轮转策略: daily(按天), hourly(按小时), none(不轮转)
LOG_RETENTION_DAYS: int = 30  # 日志保留天数
```

### 2. 修改日志初始化逻辑

在 `app/main.py` 中实现：

**原有方式**：
- 使用 `logging.basicConfig()` 配置
- 只支持追加模式，不支持自动轮转

**新方式**：
- 使用 `TimedRotatingFileHandler` 实现自动轮转
- 支持按天 (midnight) 和按小时 (H) 轮转
- 自动清理过期日志文件
- 同时输出到文件和控制台

### 3. 更新 .env.example

添加日志轮转相关配置：

```bash
# 日志文件路径（启用后同时输出到文件和控制台）
LOG_FILE=logs/app.log

# 日志轮转策略: daily(按天), hourly(按小时), none(不轮转)
LOG_ROTATION=daily

# 日志保留天数（轮转模式下生效）
LOG_RETENTION_DAYS=30
```

### 4. 创建文档和测试

- `docs/log_rotation_guide.md` - 完整的配置指南
- `scripts/test_log_rotation.py` - 功能测试脚本

## 功能特性

### 支持的轮转策略

| 策略 | 轮转时机 | 文件名格式 | 适用场景 |
|------|----------|------------|----------|
| `daily` | 每天午夜 | `app.log.20261022` | **推荐**，适合大多数场景 |
| `hourly` | 每小时整点 | `app.log.20261022_14` | 高频日志，需要精细化管理 |
| `none` | 不轮转 | `app.log` | 日志量很小 |

### 自动清理

- **按天轮转**: 保留最近 N 天的日志文件
- **按小时轮转**: 保留最近 N*24 小时的日志文件
- **不轮转**: 不自动清理

### 文件名示例

**按天轮转 (LOG_ROTATION=daily)**:
```
logs/
├── app.log                 # 当前日志（今天）
├── app.log.20261022        # 2026-10-22 的日志
├── app.log.20261021        # 2026-10-21 的日志
└── app.log.20261020        # 2026-10-20 的日志
```

**按小时轮转 (LOG_ROTATION=hourly)**:
```
logs/
├── app.log                 # 当前日志（本小时）
├── app.log.20261022_14     # 2026-10-22 14:00-15:00
├── app.log.20261022_13     # 2026-10-22 13:00-14:00
└── app.log.20261022_12     # 2026-10-22 12:00-13:00
```

## 使用方法

### 启用日志文件（按天轮转）

编辑 `.env` 文件：

```bash
LOG_FILE=logs/app.log
LOG_ROTATION=daily
LOG_RETENTION_DAYS=30
```

重启应用后生效。

### 启用按小时轮转

```bash
LOG_FILE=logs/app.log
LOG_ROTATION=hourly
LOG_RETENTION_DAYS=7      # 保留 7 天 = 168 小时
```

### 禁用日志文件

注释掉 `LOG_FILE` 配置：

```bash
# LOG_FILE=logs/app.log
```

## 测试结果

运行 `python scripts/test_log_rotation.py` 测试结果：

```
✓ 按天轮转测试通过
✓ 按小时轮转测试通过
✓ 不轮转测试通过
✓ 生成的日志文件:
  - test_daily.log (780 bytes)
  - test_hourly.log (410 bytes)
  - test_no_rotation.log (405 bytes)
```

日志内容示例：
```
2026-10-22 09:48:28,692 - test_daily - INFO - 测试日志 #1 - 按天轮转
2026-10-22 09:48:28,793 - test_daily - INFO - 测试日志 #2 - 按天轮转
2026-10-22 09:48:28,893 - test_daily - INFO - 测试日志 #3 - 按天轮转
```

## 技术实现

### TimedRotatingFileHandler

使用 Python 标准库的 `logging.handlers.TimedRotatingFileHandler`：

```python
from logging.handlers import TimedRotatingFileHandler

# 按天轮转
handler = TimedRotatingFileHandler(
    filename=settings.LOG_FILE,
    when="midnight",        # 每天午夜触发
    interval=1,             # 每1天
    backupCount=30,         # 保留30个备份
    encoding="utf-8",
    delay=False,
    utc=False
)
handler.suffix = "%Y%m%d"  # 文件名后缀格式

# 按小时轮转
handler = TimedRotatingFileHandler(
    filename=settings.LOG_FILE,
    when="H",               # 每小时触发
    interval=1,             # 每1小时
    backupCount=720,        # 保留720个备份（30天*24小时）
    encoding="utf-8",
    delay=False,
    utc=False
)
handler.suffix = "%Y%m%d_%H"  # 文件名后缀格式
```

### 双输出

启用 `LOG_FILE` 后，日志会同时输出到：
1. 日志文件（支持轮转）
2. 控制台（实时查看）

## 兼容性

### 现有用户

- ✅ 不影响现有配置
- ✅ 如果 `.env` 中未配置 `LOG_FILE`，则只输出到控制台（与之前一致）
- ✅ 新配置项有默认值，不需要立即更新

### 新用户

- ✅ `.env.example` 中包含完整的日志配置示例
- ✅ 默认启用按天轮转
- ✅ 保留 30 天日志

## 推荐配置

### 开发环境
```bash
LOG_FILE=logs/app.log
LOG_ROTATION=daily
LOG_RETENTION_DAYS=7
LOG_LEVEL=DEBUG
```

### 生产环境
```bash
LOG_FILE=logs/app.log
LOG_ROTATION=daily
LOG_RETENTION_DAYS=30
LOG_LEVEL=INFO
```

### 高负载环境
```bash
LOG_FILE=logs/app.log
LOG_ROTATION=hourly
LOG_RETENTION_DAYS=7       # 保留168小时
LOG_LEVEL=WARNING
```

## 文件清单

### 修改的文件
- `app/core/config.py` - 添加日志轮转配置项
- `app/main.py` - 实现日志轮转逻辑
- `.env.example` - 更新配置模板

### 新增的文件
- `docs/log_rotation_guide.md` - 配置指南
- `scripts/test_log_rotation.py` - 测试脚本
- `CHANGELOG_log_rotation.md` - 本文档

## 注意事项

1. **修改配置后需要重启应用**：日志配置在启动时加载
2. **日志目录权限**：确保应用有权限写入 `logs/` 目录
3. **磁盘空间**：按小时轮转会生成大量文件，注意磁盘空间
4. **时区**：轮转基于系统本地时间（`utc=False`）
5. **编码**：日志文件使用 UTF-8 编码，支持中文

## 下一步

建议用户在生产环境启用日志轮转：

```bash
# 编辑 .env 文件
LOG_FILE=logs/app.log
LOG_ROTATION=daily
LOG_RETENTION_DAYS=30

# 重启应用
# 开发环境: uvicorn app.main:app --reload
# 打包版本: startup.bat
```
