# 数据库字段清理分析

根据代码分析，以下是可以删除的无用字段和表：

## 🗑️ 可以删除的字段

### 1. `crawler_configs.schedule_config` 字段

**原因**：
- ✅ 已改为配置文件方式（`config/scheduled_tasks.yaml`）
- ✅ 代码中不再使用此字段
- ✅ 调度器已改为从配置文件读取

**影响**：
- 无影响，已完全迁移到配置文件

**删除方法**：
```sql
-- 删除字段
ALTER TABLE crawler_configs DROP COLUMN schedule_config;
```

**迁移建议**：
如果已有数据在 `schedule_config` 字段中，请先导出并转换为配置文件格式。

---

## 🗑️ 可以删除的表

### 1. `alert_rules` 表

**原因**：
- ✅ 告警功能已完全删除
- ✅ 代码中不再引用 `AlertRule` 模型
- ✅ 相关 API 和服务已删除

**删除方法**：
```sql
DROP TABLE IF EXISTS alert_rules;
```

### 2. `alert_history` 表

**原因**：
- ✅ 告警功能已完全删除
- ✅ 代码中不再引用 `AlertHistory` 模型
- ✅ 依赖于 `alert_rules` 表

**删除方法**：
```sql
-- 先删除依赖表
DROP TABLE IF EXISTS alert_history;
-- 再删除主表
DROP TABLE IF EXISTS alert_rules;
```

---

## 📊 保留的表和字段

### 保留：`metrics_timeseries` 表

**原因**：
- ⚠️ 虽然告警功能已删除，但此表可能用于其他指标收集
- ⚠️ 模型仍然存在于 `app/models/metrics.py`
- ⚠️ 可能有其他代码在使用

**建议**：
- 如果确定不需要指标收集功能，可以删除
- 如果未来需要监控功能，可以保留

**删除方法（可选）**：
```sql
DROP TABLE IF EXISTS metrics_timeseries;
```

---

## 🔧 清理步骤

### 方式 1：手动执行 SQL（推荐）

```sql
-- 1. 删除告警相关表
DROP TABLE IF EXISTS alert_history;
DROP TABLE IF EXISTS alert_rules;

-- 2. 删除 schedule_config 字段
ALTER TABLE crawler_configs DROP COLUMN schedule_config;

-- 3. 可选：删除 metrics_timeseries 表（如果确定不需要）
-- DROP TABLE IF EXISTS metrics_timeseries;
```

### 方式 2：创建数据库迁移脚本

创建 Alembic 迁移脚本自动清理：

```python
"""remove unused fields and tables

Revision ID: 8d9e0f1a2b3c
Revises: 7c8d9e4f5a6b
Create Date: 2026-10-19 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8d9e0f1a2b3c'
down_revision: Union[str, None] = '7c8d9e4f5a6b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """删除无用字段和表"""
    # 1. 删除告警相关表
    op.drop_table('alert_history')
    op.drop_table('alert_rules')
    
    # 2. 删除 schedule_config 字段
    op.drop_column('crawler_configs', 'schedule_config')
    
    # 3. 可选：删除 metrics_timeseries 表
    # op.drop_table('metrics_timeseries')


def downgrade() -> None:
    """恢复字段和表（不建议使用）"""
    # 恢复 schedule_config 字段
    op.add_column(
        'crawler_configs',
        sa.Column(
            'schedule_config',
            sa.JSON().with_variant(sa.NVARCHAR(collation='Chinese_PRC_CI_AS'), 'mssql'),
            nullable=True,
            comment='调度配置'
        )
    )
    
    # 恢复告警表（省略具体字段定义）
    # ...
```

---

## ⚠️ 注意事项

### 数据备份

在删除前务必备份数据：

```sql
-- 备份整个数据库
BACKUP DATABASE bap TO DISK = 'D:\backup\bap_backup.bak';

-- 或导出特定表数据（如果需要保留）
SELECT * INTO alert_rules_backup FROM alert_rules;
SELECT * INTO alert_history_backup FROM alert_history;
```

### 迁移 schedule_config

如果 `schedule_config` 字段中有数据，先导出：

```sql
-- 查看有哪些配置了 schedule_config
SELECT 
    id,
    config_name,
    schedule_config
FROM crawler_configs
WHERE schedule_config IS NOT NULL;
```

然后转换为 YAML 格式写入 `config/scheduled_tasks.yaml`。

### 确认无依赖

删除前确认没有其他代码依赖这些字段：

```bash
# 搜索代码中的引用
grep -r "schedule_config" app --include="*.py"
grep -r "AlertRule\|AlertHistory" app --include="*.py"
grep -r "alert_rules\|alert_history" app --include="*.py"
```

---

## 📋 清理清单

| 项目 | 类型 | 状态 | 是否可删除 | 影响 |
|------|------|------|-----------|------|
| `schedule_config` 字段 | 字段 | 已弃用 | ✅ 可删除 | 无影响，已迁移到配置文件 |
| `alert_rules` 表 | 表 | 已弃用 | ✅ 可删除 | 无影响，告警功能已删除 |
| `alert_history` 表 | 表 | 已弃用 | ✅ 可删除 | 无影响，告警功能已删除 |
| `metrics_timeseries` 表 | 表 | 保留 | ⚠️ 可选 | 如不需要指标收集可删除 |

---

## 🎯 推荐操作

### 最小清理（推荐）

```sql
-- 只删除明确无用的内容
DROP TABLE IF EXISTS alert_history;
DROP TABLE IF EXISTS alert_rules;
ALTER TABLE crawler_configs DROP COLUMN schedule_config;
```

### 完全清理

```sql
-- 删除所有无用内容
DROP TABLE IF EXISTS alert_history;
DROP TABLE IF EXISTS alert_rules;
DROP TABLE IF EXISTS metrics_timeseries;
ALTER TABLE crawler_configs DROP COLUMN schedule_config;
```

---

## ✅ 清理后的代码更新

删除字段后，需要同步更新模型代码：

### 更新 `app/models/config.py`

删除 `schedule_config` 字段定义：

```python
# 删除这部分代码
# schedule_config: Mapped[Optional[dict]] = mapped_column(
#     ChineseJSON,
#     nullable=True,
#     comment="调度配置 {enabled: true, type: 'interval', interval_minutes: 1440, ...}"
# )
```

### 更新 `app/models/metrics.py`

如果删除了 `alert_rules` 和 `alert_history` 表，这些模型定义已经删除了（在前面的告警删除操作中已完成）。

如果删除 `metrics_timeseries` 表，则删除整个文件或只保留空文件。

---

## 📝 总结

**必须删除**（已完全无用）：
1. ✅ `alert_rules` 表
2. ✅ `alert_history` 表
3. ✅ `schedule_config` 字段

**可选删除**（取决于需求）：
1. ⚠️ `metrics_timeseries` 表（如果不需要指标收集功能）

建议先删除明确无用的内容，保留可能有用的表以备将来使用。
