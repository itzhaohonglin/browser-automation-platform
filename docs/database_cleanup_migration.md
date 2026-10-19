# 数据库清理迁移说明

## 📋 迁移内容

本次迁移删除以下无用字段和表：

### 删除的表
1. ✅ `alert_history` - 告警历史表（告警功能已删除）
2. ✅ `alert_rules` - 告警规则表（告警功能已删除）

### 删除的字段
1. ✅ `crawler_configs.schedule_config` - 周期性调度配置（已改为配置文件方式）

---

## 🚀 执行迁移

### 方式 1：使用 Alembic（推荐）

```bash
# 执行迁移
alembic upgrade head

# 查看迁移历史
alembic history

# 查看当前版本
alembic current
```

### 方式 2：手动执行 SQL

如果 Alembic 无法连接数据库，可以手动执行：

```sql
-- 1. 删除告警历史表
DROP TABLE IF EXISTS alert_history;

-- 2. 删除告警规则表
DROP TABLE IF EXISTS alert_rules;

-- 3. 删除 schedule_config 字段
ALTER TABLE crawler_configs DROP COLUMN schedule_config;
```

---

## ⚠️ 迁移前准备

### 1. 备份数据库

```sql
-- SQL Server 备份
BACKUP DATABASE bap TO DISK = 'D:\backup\bap_before_cleanup.bak';
```

### 2. 检查是否有数据（可选）

```sql
-- 检查 schedule_config 是否有数据
SELECT COUNT(*) FROM crawler_configs WHERE schedule_config IS NOT NULL;

-- 检查告警表是否有数据
SELECT COUNT(*) FROM alert_rules;
SELECT COUNT(*) FROM alert_history;
```

如果 `schedule_config` 有数据，需要先迁移到配置文件 `config/scheduled_tasks.yaml`。

---

## 🔄 迁移步骤

### 完整流程

```bash
# 1. 备份数据库（重要！）
# 在 SQL Server Management Studio 中执行备份

# 2. 查看当前迁移状态
alembic current

# 3. 执行迁移
alembic upgrade head

# 4. 验证迁移结果
# 检查表是否已删除
```

### 验证迁移

```sql
-- 检查表是否已删除
SELECT TABLE_NAME 
FROM INFORMATION_SCHEMA.TABLES 
WHERE TABLE_NAME IN ('alert_rules', 'alert_history');
-- 应该返回空结果

-- 检查字段是否已删除
SELECT COLUMN_NAME 
FROM INFORMATION_SCHEMA.COLUMNS 
WHERE TABLE_NAME = 'crawler_configs' 
  AND COLUMN_NAME = 'schedule_config';
-- 应该返回空结果
```

---

## 🔙 回滚（如果需要）

如果迁移后发现问题，可以回滚：

```bash
# 回滚到上一个版本
alembic downgrade -1

# 回滚到特定版本
alembic downgrade 7c8d9e4f5a6b
```

**注意**：回滚会重新创建表和字段，但数据不会恢复，需要从备份恢复。

---

## 📊 迁移影响

### 正面影响
- ✅ 清理了无用的数据库表和字段
- ✅ 减少数据库存储空间
- ✅ 简化数据库结构
- ✅ 提高维护效率

### 无负面影响
- ✅ 告警功能已完全删除，不影响现有功能
- ✅ 周期性任务已改为配置文件，不影响调度功能
- ✅ 所有代码已更新，不会引用已删除的字段和表

---

## 🐛 常见问题

### Q1: 迁移失败怎么办？

**错误示例**：
```
sqlalchemy.exc.OperationalError: (pyodbc.OperationalError) 
表 'alert_history' 不存在
```

**原因**：表可能已经被手动删除或不存在

**解决**：
- 迁移脚本已包含异常处理，会自动跳过不存在的表
- 可以继续执行，不影响其他清理操作

### Q2: schedule_config 字段中有数据怎么办？

**解决步骤**：

1. 导出数据：
```sql
SELECT id, config_name, schedule_config
FROM crawler_configs
WHERE schedule_config IS NOT NULL;
```

2. 转换为 YAML 格式：
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

3. 保存到 `config/scheduled_tasks.yaml`

4. 执行迁移

### Q3: 可以只删除部分内容吗？

**可以**。修改迁移脚本，注释掉不想删除的部分：

```python
def upgrade() -> None:
    # 删除告警表
    # op.drop_table('alert_history')
    # op.drop_table('alert_rules')
    
    # 只删除 schedule_config 字段
    op.drop_column('crawler_configs', 'schedule_config')
```

---

## ✅ 迁移完成检查清单

- [ ] 数据库已备份
- [ ] schedule_config 数据已迁移（如有）
- [ ] 执行 `alembic upgrade head` 成功
- [ ] 验证表已删除（alert_rules, alert_history）
- [ ] 验证字段已删除（schedule_config）
- [ ] 应用启动正常
- [ ] 周期性任务功能正常
- [ ] 无错误日志

---

## 📝 迁移记录

| 迁移版本 | 迁移内容 | 执行日期 | 执行人 | 备注 |
|---------|---------|---------|--------|------|
| 8d9e0f1a2b3c | 删除告警表和 schedule_config 字段 | 2026-10-19 | - | 清理无用字段和表 |

---

## 📚 相关文档

- 清理指南：`docs/database_cleanup_guide.md`
- 迁移脚本：`alembic/versions/8d9e0f1a2b3c_remove_unused_fields_and_tables.py`
- 配置文件指南：`docs/scheduled_tasks_config_file.md`
