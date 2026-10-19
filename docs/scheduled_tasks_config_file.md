# 周期性任务配置文件使用指南

## 📋 概述

周期性任务现在通过 **配置文件** 管理，无需在数据库中配置。配置文件位于：
```
config/scheduled_tasks.yaml
```

---

## 🚀 快速开始

### 步骤 1：编辑配置文件

```yaml
scheduled_tasks:
  # 国家医保局-注册证号查询（每天执行一次）
  - config_id: 44
    enabled: true
    interval_minutes: 1440  # 24小时
    query_params:
      registration_no: "滇械注准20192140008"
    keep_history: true
    max_history: 30
```

### 步骤 2：启动服务

```bash
python -m app.main
```

就这么简单！服务会自动：
- ✅ 读取配置文件
- ✅ 按照间隔时间自动创建任务
- ✅ 执行任务并管理历史记录

---

## 📝 配置说明

### 配置文件结构

```yaml
scheduled_tasks:
  - config_id: 44              # 必填：采集配置ID（crawler_configs 表的 id）
    enabled: true              # 必填：是否启用（true/false）
    interval_minutes: 1440     # 必填：执行间隔（分钟）
    query_params:              # 必填：任务参数（JSON格式）
      registration_no: "xxx"
    keep_history: true         # 可选：是否保留历史（默认 true）
    max_history: 30            # 可选：保留历史数量（默认 100）
```

### 参数详解

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `config_id` | int | ✅ | - | 采集配置ID |
| `enabled` | bool | ✅ | - | 是否启用此任务 |
| `interval_minutes` | int | ✅ | - | 执行间隔（分钟） |
| `query_params` | dict | ✅ | - | 任务参数，JSON格式 |
| `keep_history` | bool | ❌ | true | 是否保留历史任务 |
| `max_history` | int | ❌ | 100 | 最多保留历史任务数 |

---

## 💡 配置示例

### 示例 1：每天定时采集

```yaml
scheduled_tasks:
  - config_id: 44
    enabled: true
    interval_minutes: 1440  # 每天（24小时）
    query_params:
      registration_no: "滇械注准20192140008"
    keep_history: true
    max_history: 30  # 保留最近30天
```

### 示例 2：每小时监控

```yaml
scheduled_tasks:
  - config_id: 50
    enabled: true
    interval_minutes: 60  # 每小时
    query_params:
      keyword: "医疗器械"
    keep_history: true
    max_history: 48  # 保留最近48小时
```

### 示例 3：多个任务

```yaml
scheduled_tasks:
  # 任务1：每天采集
  - config_id: 44
    enabled: true
    interval_minutes: 1440
    query_params:
      registration_no: "滇械注准20192140008"
    keep_history: true
    max_history: 30

  # 任务2：每6小时采集
  - config_id: 50
    enabled: true
    interval_minutes: 360
    query_params:
      category: "高值耗材"
    keep_history: true
    max_history: 100

  # 任务3：暂时禁用
  - config_id: 55
    enabled: false
    interval_minutes: 60
    query_params:
      keyword: "测试"
    keep_history: false
```

### 示例 4：复杂参数

```yaml
scheduled_tasks:
  - config_id: 60
    enabled: true
    interval_minutes: 720  # 每12小时
    query_params:
      # 支持多个参数
      keyword: "医疗设备"
      category: "高值耗材"
      status: "已审批"
      date_from: "2024-01-01"
    keep_history: true
    max_history: 50
```

---

## 🔧 管理操作

### 启用/禁用任务

只需修改 `enabled` 字段：

```yaml
# 启用
- config_id: 44
  enabled: true
  ...

# 禁用
- config_id: 44
  enabled: false
  ...
```

修改后重启服务即可生效。

### 修改执行间隔

修改 `interval_minutes` 字段：

```yaml
# 从每天改为每6小时
- config_id: 44
  enabled: true
  interval_minutes: 360  # 原来是 1440
  ...
```

修改后重启服务即可生效。

### 修改任务参数

修改 `query_params` 字段：

```yaml
- config_id: 44
  enabled: true
  interval_minutes: 1440
  query_params:
    registration_no: "新的注册证号"  # 修改参数
  ...
```

修改后重启服务即可生效。

### 添加新任务

在 `scheduled_tasks` 列表中添加新配置：

```yaml
scheduled_tasks:
  # 已有任务
  - config_id: 44
    ...

  # 新增任务
  - config_id: 70
    enabled: true
    interval_minutes: 60
    query_params:
      keyword: "新产品"
    keep_history: true
    max_history: 100
```

### 删除任务

直接从配置文件中删除对应的配置块，或设置 `enabled: false`。

---

## ⏰ 常用时间间隔

| 频率 | interval_minutes | 说明 |
|------|-----------------|------|
| 每5分钟 | 5 | 高频监控 |
| 每15分钟 | 15 | 常规监控 |
| 每30分钟 | 30 | 中频采集 |
| 每小时 | 60 | 标准采集 |
| 每6小时 | 360 | 定期更新 |
| 每12小时 | 720 | 半日更新 |
| 每天 | 1440 | 日常采集 |
| 每周 | 10080 | 周期采集 |

---

## 🔍 验证和调试

### 检查配置加载

启动服务后查看日志：

```log
INFO - 成功加载 3 个周期性任务配置
INFO - 从配置文件加载了 2 个启用的周期性任务
INFO - 为配置 #44 (国家医保局-注册证号查询) 创建周期性任务
```

### 验证脚本

```bash
python scripts/test_scheduled_tasks.py
```

### 查看配置状态

```python
# 在 Python 中检查配置
from app.core.scheduled_config import scheduled_task_config_loader

# 重新加载配置
scheduled_task_config_loader.reload()

# 查看所有配置
for config in scheduled_task_config_loader.configs:
    print(f"Config ID: {config.config_id}, Enabled: {config.enabled}")

# 查看启用的配置
enabled = scheduled_task_config_loader.get_enabled_configs()
print(f"启用的任务数: {len(enabled)}")
```

---

## 🐛 常见问题

### Q1: 修改配置后没有生效？

**原因**：配置文件在服务启动时加载，修改后需要重启服务。

**解决**：
```bash
# 重启服务
python -m app.main
```

### Q2: 配置文件格式错误？

**原因**：YAML 格式要求严格，缩进必须正确。

**解决**：
- 使用空格缩进，不要用 Tab
- 检查每行缩进是否对齐
- 使用 YAML 在线验证工具检查格式

### Q3: 任务不会自动创建？

**检查清单**：
1. ✅ `enabled: true`
2. ✅ `config_id` 在数据库中存在
3. ✅ 最新任务状态是 `success`
4. ✅ 已经过了 `interval_minutes` 时间
5. ✅ 服务正在运行

### Q4: 如何查看哪些任务已配置？

```bash
# 查看配置文件
cat config/scheduled_tasks.yaml

# 或使用验证脚本
python scripts/test_scheduled_tasks.py
```

### Q5: 配置文件位置在哪里？

- 开发环境：`项目根目录/config/scheduled_tasks.yaml`
- 打包版本：`dist/browser-automation-platform/config/scheduled_tasks.yaml`

---

## 🔄 迁移指南

### 从数据库配置迁移到文件配置

如果之前使用数据库的 `schedule_config` 字段配置，需要迁移：

**旧方式（数据库）**：
```sql
UPDATE crawler_configs
SET schedule_config = N'{
  "enabled": true,
  "interval_minutes": 1440,
  ...
}'
WHERE id = 44;
```

**新方式（配置文件）**：
```yaml
scheduled_tasks:
  - config_id: 44
    enabled: true
    interval_minutes: 1440
    query_params:
      registration_no: "xxx"
    keep_history: true
    max_history: 30
```

迁移步骤：
1. 导出数据库中的 `schedule_config` 配置
2. 转换为 YAML 格式写入 `config/scheduled_tasks.yaml`
3. 重启服务
4. 验证任务是否正常执行

---

## 💾 配置文件备份

建议定期备份配置文件：

```bash
# 创建备份
cp config/scheduled_tasks.yaml config/scheduled_tasks.yaml.backup

# 恢复备份
cp config/scheduled_tasks.yaml.backup config/scheduled_tasks.yaml
```

---

## ✅ 优势总结

配置文件方式的优势：

| 对比项 | 数据库配置 | 配置文件 |
|-------|-----------|---------|
| 管理方式 | SQL 修改 | 文本编辑 |
| 版本控制 | 困难 | ✅ 支持 Git |
| 批量修改 | 复杂 | ✅ 简单 |
| 可读性 | 低 | ✅ 高 |
| 备份恢复 | 需要数据库 | ✅ 简单复制 |
| 环境迁移 | 复杂 | ✅ 文件拷贝 |

---

## 📚 相关文档

- 详细使用指南：`docs/scheduled_tasks_guide.md`
- 验证脚本：`scripts/test_scheduled_tasks.py`
- 配置加载器：`app/core/scheduled_config.py`
