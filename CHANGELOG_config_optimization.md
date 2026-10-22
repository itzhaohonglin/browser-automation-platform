# 配置文件优化说明

**日期**: 2026-10-22  
**影响文件**: `.env.example`, `app/core/config.py`

## 优化内容

### 1. 调整默认参数

| 配置项 | 原值 | 新值 | 说明 |
|--------|------|------|------|
| `DISPATCH_INTERVAL_MINUTES` | 30 | 1 | 任务分发间隔从 30 分钟改为 1 分钟，快速响应新任务 |
| `TASK_TIMEOUT_MINUTES` | 60 | 30 | 任务超时阈值从 60 分钟改为 30 分钟，更快检测卡死任务 |
| `REQUEST_RATE_LIMIT_INTERVAL_SECONDS` | 6 | 5 | 请求间隔统一为 5 秒 |

### 2. 移除不常用配置

从 `.env.example` 中移除以下配置项（代码中保留默认值）：

- `SCHEDULE_CHECK_INTERVAL_MINUTES` - 周期性任务检查间隔（默认 5 分钟）
- `SCHEDULE_FIRST_RUN_DELAY_MINUTES` - 首次检查延迟（默认 2 分钟）
- `AUTO_RECREATE_SUCCESS_JOBS` - 自动重新执行功能（默认 false）
- `AUTO_RECREATE_INTERVAL_MINUTES` - 重新执行间隔（默认 1440 分钟）

**原因**：
- 这些配置项用于自动重新执行成功的任务，是高级功能
- 大多数用户不需要这个功能（默认禁用）
- 减少配置文件复杂度，降低用户困惑

### 3. 同步更新 config.py

从 `app/core/config.py` 中移除已删除配置项的定义，改为：

```python
# 任务超时检测配置
TASK_TIMEOUT_CHECK_ENABLED: bool = True
TASK_TIMEOUT_MINUTES: int = 30  # 从 60 改为 30
TASK_TIMEOUT_CHECK_INTERVAL_MINUTES: int = 10
```

## 兼容性说明

### 对现有用户的影响

**如果已经有 .env 文件**：
- ✅ 不受影响，install.bat 会跳过复制 .env.example
- ✅ 现有配置继续生效
- ✅ 如需使用新默认值，手动编辑 .env 文件

**如果使用了被移除的配置项**：
- ✅ 代码中保留了这些配置项的默认值
- ✅ 功能继续正常工作
- ⚠️ 如需启用自动重新执行功能，需手动添加到 .env 文件：
  ```
  AUTO_RECREATE_SUCCESS_JOBS=true
  AUTO_RECREATE_INTERVAL_MINUTES=1440
  SCHEDULE_CHECK_INTERVAL_MINUTES=5
  SCHEDULE_FIRST_RUN_DELAY_MINUTES=2
  ```

## 优化效果

### 优点
1. **更快响应**：任务分发间隔从 30 分钟降到 1 分钟
2. **更早发现问题**：超时检测从 60 分钟降到 30 分钟
3. **配置更简洁**：移除 4 个不常用配置项
4. **降低学习成本**：新用户只需关注核心配置

### 保持兼容
1. 代码中保留所有配置项的默认值
2. 现有 .env 文件不受影响
3. 高级用户仍可手动启用高级功能

## 推荐配置

### 快速响应场景（推荐）
```bash
DISPATCH_INTERVAL_MINUTES=1      # 1 分钟分发一次
TASK_TIMEOUT_MINUTES=30          # 30 分钟超时
MAX_WORKERS=3                    # 3 个并发任务
```

### 批量处理场景
```bash
DISPATCH_INTERVAL_MINUTES=10     # 10 分钟分发一次
TASK_TIMEOUT_MINUTES=60          # 60 分钟超时
MAX_WORKERS=5                    # 5 个并发任务
```

### 高负载场景
```bash
DISPATCH_INTERVAL_MINUTES=5      # 5 分钟分发一次
TASK_TIMEOUT_MINUTES=45          # 45 分钟超时
MAX_WORKERS=10                   # 10 个并发任务
WORKER_MEMORY_LIMIT_MB=1024      # 增加内存限制
```
