# 日志轮转配置指南

**更新日期**: 2026-10-22  
**功能**: 支持按天或按小时自动分类日志文件

## 功能概述

日志轮转功能可以自动将日志文件按时间分类，避免单个日志文件过大，便于查找和归档。

### 支持的轮转策略

| 策略 | 说明 | 文件名示例 | 适用场景 |
|------|------|------------|----------|
| `daily` | 按天轮转，每天午夜生成新文件 | `app.log.20261022` | **推荐**，适合大多数场景 |
| `hourly` | 按小时轮转，每小时生成新文件 | `app.log.20261022_14` | 高频日志，需要精细化管理 |
| `none` | 不轮转，所有日志写入同一文件 | `app.log` | 日志量很小，或需要简单管理 |

## 配置方法

### 1. 编辑 .env 文件

```bash
# 启用日志文件（同时输出到控制台）
LOG_FILE=logs/app.log

# 选择轮转策略
LOG_ROTATION=daily        # daily | hourly | none

# 设置保留天数
LOG_RETENTION_DAYS=30     # 保留最近 30 天的日志
```

### 2. 配置示例

#### 按天轮转（推荐）

```bash
LOG_FILE=logs/app.log
LOG_ROTATION=daily
LOG_RETENTION_DAYS=30
```

**效果**：
- 每天午夜 (00:00) 自动生成新日志文件
- 当前日志: `logs/app.log`
- 历史日志: `logs/app.log.20261022`, `logs/app.log.20261021`, ...
- 自动删除 30 天前的旧日志

#### 按小时轮转

```bash
LOG_FILE=logs/app.log
LOG_ROTATION=hourly
LOG_RETENTION_DAYS=7      # 保留 7 天 = 168 小时
```

**效果**：
- 每小时整点自动生成新日志文件
- 当前日志: `logs/app.log`
- 历史日志: `logs/app.log.20261022_14`, `logs/app.log.20261022_13`, ...
- 自动删除 7*24=168 小时前的旧日志

#### 不轮转

```bash
LOG_FILE=logs/app.log
LOG_ROTATION=none
# LOG_RETENTION_DAYS 不生效
```

**效果**：
- 所有日志追加到 `logs/app.log` 同一个文件
- 不会自动清理，需要手动管理

### 3. 禁用日志文件

如果只需要控制台输出，注释掉 `LOG_FILE` 配置：

```bash
# LOG_FILE=logs/app.log
```

## 日志文件命名规则

### 按天轮转 (daily)

```
logs/
├── app.log                 # 当前日志（今天）
├── app.log.20261022        # 2026-10-22 的日志
├── app.log.20261021        # 2026-10-21 的日志
└── app.log.20261020        # 2026-10-20 的日志
```

### 按小时轮转 (hourly)

```
logs/
├── app.log                 # 当前日志（本小时）
├── app.log.20261022_14     # 2026-10-22 14:00-15:00 的日志
├── app.log.20261022_13     # 2026-10-22 13:00-14:00 的日志
└── app.log.20261022_12     # 2026-10-22 12:00-13:00 的日志
```

## 常见问题

### Q1: 日志文件在哪里？

A: 默认在 `logs/app.log`，相对于应用根目录。如果配置了其他路径（如 `LOG_FILE=/var/log/bap.log`），则在该路径。

### Q2: 日志文件会自动清理吗？

A: 是的。启用轮转后（daily 或 hourly），超过 `LOG_RETENTION_DAYS` 的旧日志会自动删除。

### Q3: 轮转时会丢失日志吗？

A: 不会。Python 的 `TimedRotatingFileHandler` 会在轮转时安全地关闭旧文件并打开新文件，不会丢失任何日志。

### Q4: 如何查看历史日志？

```bash
# 查看今天的日志
cat logs/app.log

# 查看昨天的日志（按天轮转）
cat logs/app.log.20261021

# 查看指定小时的日志（按小时轮转）
cat logs/app.log.20261022_14

# 搜索所有日志
grep "ERROR" logs/app.log*
```

### Q5: 日志文件太大怎么办？

**按天轮转时单个文件太大**：
- 改用按小时轮转（`LOG_ROTATION=hourly`）

**按小时轮转仍然太大**：
- 调整日志级别（`LOG_LEVEL=WARNING` 或 `ERROR`）
- 减少详细日志输出
- 考虑使用日志聚合系统（如 ELK）

### Q6: 修改配置后需要重启吗？

A: 是的。日志配置在应用启动时加载，修改 `.env` 后需要重启服务。

### Q7: 如何测试日志轮转？

运行测试脚本：

```bash
python scripts/test_log_rotation.py
```

## 推荐配置

### 开发环境

```bash
LOG_FILE=logs/app.log
LOG_ROTATION=daily
LOG_RETENTION_DAYS=7      # 保留一周
LOG_LEVEL=DEBUG           # 详细日志
```

### 生产环境

```bash
LOG_FILE=logs/app.log
LOG_ROTATION=daily
LOG_RETENTION_DAYS=30     # 保留一个月
LOG_LEVEL=INFO            # 正常日志
```

### 高负载环境

```bash
LOG_FILE=logs/app.log
LOG_ROTATION=hourly       # 按小时分类
LOG_RETENTION_DAYS=7      # 保留一周（168小时）
LOG_LEVEL=WARNING         # 只记录警告和错误
```

## 技术细节

### 实现原理

使用 Python 标准库的 `logging.handlers.TimedRotatingFileHandler`：

- **按天轮转**: `when="midnight"` - 每天午夜触发
- **按小时轮转**: `when="H"` - 每小时整点触发
- **自动删除**: `backupCount=N` - 只保留最近 N 个文件

### 文件名后缀

- 按天: `suffix="%Y%m%d"` → `app.log.20261022`
- 按小时: `suffix="%Y%m%d_%H"` → `app.log.20261022_14`

### 日志输出

启用 `LOG_FILE` 后：
- ✓ 同时输出到文件和控制台
- ✓ 文件和控制台使用相同的格式和级别
- ✓ 文件使用 UTF-8 编码，支持中文

## 相关配置

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `LOG_FILE` | 日志文件路径 | `None`（禁用） |
| `LOG_ROTATION` | 轮转策略 | `daily` |
| `LOG_RETENTION_DAYS` | 保留天数 | `30` |
| `LOG_LEVEL` | 日志级别 | `INFO` |

## 参考资料

- [Python logging.handlers 文档](https://docs.python.org/3/library/logging.handlers.html#timedrotatingfilehandler)
- [日志最佳实践](https://12factor.net/logs)
