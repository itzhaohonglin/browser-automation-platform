# 周期性任务配置（.env 方式）

## 配置说明

在 `.env` 文件中配置 `SCHEDULED_TASKS` 变量，使用 JSON 格式：

```bash
# 周期性任务配置（JSON 数组格式）
SCHEDULED_TASKS='[{"config_id": 44, "enabled": true, "interval_minutes": 1440, "query_params": {"registration_no": "滇械注准20192140008"}, "keep_history": true, "max_history": 30}]'
```

---

## 📝 配置格式

### 单个任务

```bash
SCHEDULED_TASKS='[
  {
    "config_id": 44,
    "enabled": true,
    "interval_minutes": 1440,
    "query_params": {
      "registration_no": "滇械注准20192140008"
    },
    "keep_history": true,
    "max_history": 30
  }
]'
```

### 多个任务

```bash
SCHEDULED_TASKS='[
  {
    "config_id": 44,
    "enabled": true,
    "interval_minutes": 1440,
    "query_params": {"registration_no": "滇械注准20192140008"},
    "keep_history": true,
    "max_history": 30
  },
  {
    "config_id": 50,
    "enabled": true,
    "interval_minutes": 60,
    "query_params": {"keyword": "医疗器械"},
    "keep_history": true,
    "max_history": 48
  }
]'
```

---

## 📋 参数说明

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `config_id` | int | ✅ | 采集配置ID |
| `enabled` | bool | ✅ | 是否启用 |
| `interval_minutes` | int | ✅ | 执行间隔（分钟） |
| `query_params` | object | ✅ | 任务参数 |
| `keep_history` | bool | ❌ | 是否保留历史（默认 true） |
| `max_history` | int | ❌ | 保留历史数量（默认 100） |

---

## 💡 配置示例

### 示例 1：每天执行

```bash
# 每天采集一次
SCHEDULED_TASKS='[{"config_id": 44, "enabled": true, "interval_minutes": 1440, "query_params": {"registration_no": "滇械注准20192140008"}, "keep_history": true, "max_history": 30}]'
```

### 示例 2：每小时执行

```bash
# 每小时监控一次
SCHEDULED_TASKS='[{"config_id": 50, "enabled": true, "interval_minutes": 60, "query_params": {"keyword": "医疗器械"}, "keep_history": true, "max_history": 48}]'
```

### 示例 3：多个任务

```bash
# 配置多个周期性任务（注意：需要在一行）
SCHEDULED_TASKS='[{"config_id": 44, "enabled": true, "interval_minutes": 1440, "query_params": {"registration_no": "滇械注准20192140008"}, "keep_history": true, "max_history": 30}, {"config_id": 50, "enabled": true, "interval_minutes": 60, "query_params": {"keyword": "医疗器械"}, "keep_history": true, "max_history": 48}]'
```

### 示例 4：格式化配置（推荐）

为了便于阅读和维护，可以使用多行格式（注意反斜杠转义）：

```bash
# 使用多行格式（Windows 使用 ^ 连接，Linux 使用 \）
SCHEDULED_TASKS='[\
  {\
    "config_id": 44,\
    "enabled": true,\
    "interval_minutes": 1440,\
    "query_params": {"registration_no": "滇械注准20192140008"},\
    "keep_history": true,\
    "max_history": 30\
  },\
  {\
    "config_id": 50,\
    "enabled": true,\
    "interval_minutes": 60,\
    "query_params": {"keyword": "医疗器械"},\
    "keep_history": true,\
    "max_history": 48\
  }\
]'
```

---

## ⏰ 常用时间间隔

| 频率 | interval_minutes |
|------|-----------------|
| 每5分钟 | 5 |
| 每15分钟 | 15 |
| 每30分钟 | 30 |
| 每小时 | 60 |
| 每6小时 | 360 |
| 每12小时 | 720 |
| 每天 | 1440 |
| 每周 | 10080 |

---

## 🔧 修改配置

### 启用/禁用任务

修改 `enabled` 字段：

```bash
# 禁用任务
SCHEDULED_TASKS='[{"config_id": 44, "enabled": false, ...}]'

# 启用任务
SCHEDULED_TASKS='[{"config_id": 44, "enabled": true, ...}]'
```

### 修改执行间隔

修改 `interval_minutes` 字段：

```bash
# 从每天改为每6小时
SCHEDULED_TASKS='[{"config_id": 44, "enabled": true, "interval_minutes": 360, ...}]'
```

### 添加新任务

在 JSON 数组中添加新对象：

```bash
SCHEDULED_TASKS='[
  {"config_id": 44, "enabled": true, ...},
  {"config_id": 50, "enabled": true, ...},
  {"config_id": 60, "enabled": true, ...}
]'
```

---

## ✅ 验证配置

### 方法 1：检查日志

启动服务后查看日志：

```log
INFO - 成功加载 2 个周期性任务配置
INFO - 从配置文件加载了 2 个启用的周期性任务
```

### 方法 2：Python 验证

```python
from app.core.scheduled_config import scheduled_task_config_loader

# 查看所有配置
for config in scheduled_task_config_loader.configs:
    print(f"Config ID: {config.config_id}, Enabled: {config.enabled}")

# 查看启用的配置
enabled = scheduled_task_config_loader.get_enabled_configs()
print(f"启用的任务数: {len(enabled)}")
```

---

## 🐛 常见错误

### 错误 1：JSON 格式错误

**错误信息**：
```
ERROR - JSON 解析错误: Expecting property name enclosed in double quotes
```

**原因**：JSON 格式不正确（缺少引号、逗号等）

**解决**：
- 使用双引号（不是单引号）
- 检查逗号和括号是否匹配
- 使用在线 JSON 验证工具检查

### 错误 2：单引号问题

**错误配置**：
```bash
# ❌ 错误：JSON 内部使用单引号
SCHEDULED_TASKS='[{'config_id': 44, 'enabled': true}]'
```

**正确配置**：
```bash
# ✅ 正确：JSON 内部使用双引号，外部使用单引号
SCHEDULED_TASKS='[{"config_id": 44, "enabled": true}]'
```

### 错误 3：换行问题

**错误配置**：
```bash
# ❌ 错误：直接换行
SCHEDULED_TASKS='[
  {"config_id": 44}
]'
```

**正确配置**：
```bash
# ✅ 方式1：一行
SCHEDULED_TASKS='[{"config_id": 44}]'

# ✅ 方式2：使用转义
SCHEDULED_TASKS='[\
  {"config_id": 44}\
]'
```

---

## 📚 完整示例

### .env 文件示例

```bash
# 数据库配置
DATABASE_URL=mssql+aioodbc://sa:YourPassword@localhost:1433/bap?driver=ODBC+Driver+17+for+SQL+Server

# 应用配置
APP_HOST=0.0.0.0
APP_PORT=8000
DEBUG=False
HEADLESS_MODE=True

# 进程池配置
MAX_WORKERS=3
WORKER_MEMORY_LIMIT_MB=512

# 任务调度配置
DISPATCH_INTERVAL_MINUTES=1
RETRY_INTERVAL_MINUTES=30
MAX_RETRY_COUNT=3

# 周期性任务配置
SCHEDULE_CHECK_INTERVAL_MINUTES=5
SCHEDULE_FIRST_RUN_DELAY_MINUTES=2

# 周期性任务列表（JSON 格式）
SCHEDULED_TASKS='[{"config_id": 44, "enabled": true, "interval_minutes": 1440, "query_params": {"registration_no": "滇械注准20192140008"}, "keep_history": true, "max_history": 30}, {"config_id": 50, "enabled": true, "interval_minutes": 60, "query_params": {"keyword": "医疗器械"}, "keep_history": true, "max_history": 48}]'

# 请求级限流
REQUEST_RATE_LIMIT_ENABLED=False
REQUEST_RATE_LIMIT_INTERVAL_SECONDS=5.0
```

---

## 🔄 vs YAML 方式对比

| 对比项 | .env 方式 | YAML 方式 |
|-------|----------|----------|
| 配置位置 | .env 文件 | config/scheduled_tasks.yaml |
| 格式 | JSON 字符串 | YAML 格式 |
| 可读性 | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| 统一性 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| 易于编辑 | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| 版本控制 | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| 环境隔离 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |

---

## ✨ 优势

使用 `.env` 配置的优势：

1. ✅ **统一配置**：所有配置都在 .env 文件中
2. ✅ **环境隔离**：开发/测试/生产环境分别配置
3. ✅ **无需额外文件**：不需要维护额外的 YAML 文件
4. ✅ **标准做法**：符合 12-factor 应用原则
5. ✅ **安全性**：.env 文件不提交到 Git

---

## 📝 总结

**配置步骤**：

1. 编辑 `.env` 文件
2. 添加 `SCHEDULED_TASKS` 配置（JSON 格式）
3. 重启服务

**注意事项**：

- JSON 内部使用双引号
- 外部使用单引号包裹
- 确保 JSON 格式正确
- 修改后需要重启服务
