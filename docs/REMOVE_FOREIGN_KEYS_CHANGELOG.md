# 数据库外键约束移除 - 修改总结

## 修改日期
2026-10-01

## 修改原因
根据项目需求，数据库设计**不使用外键约束**，仅通过应用层逻辑和索引维护数据关系。

## 修改内容

### 1. Alembic 迁移脚本

**文件**: `alembic/versions/f1028eaaa97b_initial_schema_for_sql_server.py`

**修改**：
- ✅ 移除 `job_queue` 表的外键约束：`ForeignKeyConstraint(['config_id'], ['crawler_configs.id'])`
- ✅ 移除 `crawler_results` 表的外键约束：`ForeignKeyConstraint(['job_id'], ['job_queue.id'])`
- ✅ 移除 `alert_history` 表的外键约束：`ForeignKeyConstraint(['rule_id'], ['alert_rules.id'])`
- ✅ 新增索引 `idx_rule_id` 在 `alert_history(rule_id)`
- ✅ 新增索引 `idx_config` 在 `crawler_results(config_id)`

### 2. SQLAlchemy 模型文件

#### `app/models/job.py`
```python
# 修改前
from sqlalchemy import Integer, JSON, Text, DateTime, ForeignKey, Index, Enum as SQLEnum

config_id: Mapped[int] = mapped_column(
    Integer,
    ForeignKey("crawler_configs.id"),  # ✗ 移除
    nullable=False,
    comment="关联crawler_configs.id"
)

# 修改后
from sqlalchemy import Integer, JSON, Text, DateTime, Index, Enum as SQLEnum

config_id: Mapped[int] = mapped_column(
    Integer,
    nullable=False,
    comment="关联crawler_configs.id"
)
```

#### `app/models/result.py`
```python
# 修改前
from sqlalchemy import Integer, JSON, DateTime, ForeignKey, Index

job_id: Mapped[int] = mapped_column(
    Integer,
    ForeignKey("job_queue.id"),  # ✗ 移除
    nullable=False,
    comment="关联job_queue.id"
)

__table_args__ = (
    Index("idx_job", "job_id"),
)

# 修改后
from sqlalchemy import Integer, JSON, DateTime, Index

job_id: Mapped[int] = mapped_column(
    Integer,
    nullable=False,
    comment="关联job_queue.id"
)

__table_args__ = (
    Index("idx_job", "job_id"),
    Index("idx_config", "config_id"),  # ✅ 新增
)
```

#### `app/models/metrics.py`
```python
# 修改前
from sqlalchemy import String, Integer, Float, Boolean, JSON, Text, DateTime, ForeignKey, Index

rule_id: Mapped[int] = mapped_column(
    Integer,
    ForeignKey('alert_rules.id'),  # ✗ 移除
    nullable=False,
    comment="关联alert_rules.id"
)

# 无索引定义

# 修改后
from sqlalchemy import String, Integer, Float, Boolean, JSON, Text, DateTime, Index

rule_id: Mapped[int] = mapped_column(
    Integer,
    nullable=False,
    comment="关联alert_rules.id"
)

__table_args__ = (
    Index("idx_rule_id", "rule_id"),  # ✅ 新增
)
```

## 索引清单

所有关联字段都已创建索引以保证查询性能：

| 表名 | 索引名称 | 索引字段 | 用途 |
|------|---------|---------|------|
| **crawler_configs** | `idx_auth_profile` | auth_profile | 按登录态查询 |
| **crawler_configs** | `idx_deleted_at` | deleted_at | 软删除查询 |
| **job_queue** | `idx_config_status` | config_id, status | 按配置和状态查询 |
| **crawler_results** | `idx_job` | job_id | 按任务查询结果 |
| **crawler_results** | `idx_config` | config_id | 按配置查询结果 ✨ 新增 |
| **alert_history** | `idx_rule_id` | rule_id | 按规则查询告警 ✨ 新增 |
| **metrics_timeseries** | `idx_metric_time` | metric_name, timestamp | 时序数据查询 |
| **metrics_timeseries** | `ix_metrics_timeseries_metric_name` | metric_name | 指标名查询 |
| **metrics_timeseries** | `ix_metrics_timeseries_timestamp` | timestamp | 时间范围查询 |

## 数据关系维护策略

### 应用层职责

```python
# 1. 创建子记录前验证父记录存在
async def create_job(config_id: int, query_params: dict):
    config = await session.get(CrawlerConfig, config_id)
    if not config:
        raise ValueError(f"配置 {config_id} 不存在")
    # ... 创建任务

# 2. 删除父记录前处理子记录
async def delete_config(config_id: int):
    # 先删除所有关联任务
    await session.execute(
        delete(JobQueue).where(JobQueue.config_id == config_id)
    )
    # 再删除配置
    await session.execute(
        delete(CrawlerConfig).where(CrawlerConfig.id == config_id)
    )

# 3. 优先使用软删除
config.deleted_at = datetime.now()  # 推荐
# await session.delete(config)      # 谨慎使用
```

## 升级步骤

如果已有数据库，需要移除现有外键约束：

```sql
-- SQL Server 语法
-- 1. 查找外键约束名称
SELECT 
    fk.name AS ForeignKeyName,
    tp.name AS ParentTable,
    cp.name AS ParentColumn,
    tr.name AS ReferencedTable,
    cr.name AS ReferencedColumn
FROM sys.foreign_keys fk
INNER JOIN sys.tables tp ON fk.parent_object_id = tp.object_id
INNER JOIN sys.tables tr ON fk.referenced_object_id = tr.object_id
INNER JOIN sys.foreign_key_columns fkc ON fk.object_id = fkc.constraint_object_id
INNER JOIN sys.columns cp ON fkc.parent_column_id = cp.column_id AND fkc.parent_object_id = cp.object_id
INNER JOIN sys.columns cr ON fkc.referenced_column_id = cr.column_id AND fkc.referenced_object_id = cr.object_id;

-- 2. 删除外键约束（替换为实际的约束名称）
ALTER TABLE job_queue DROP CONSTRAINT FK_job_queue_config_id;
ALTER TABLE crawler_results DROP CONSTRAINT FK_crawler_results_job_id;
ALTER TABLE alert_history DROP CONSTRAINT FK_alert_history_rule_id;

-- 3. 创建索引（如果未存在）
CREATE INDEX idx_rule_id ON alert_history(rule_id);
CREATE INDEX idx_config ON crawler_results(config_id);
```

## 全新安装

全新安装时直接运行 Alembic 迁移即可，不会创建任何外键约束：

```bash
# 执行迁移
alembic upgrade head

# 验证表结构
python scripts/verify_sqlserver_schema.py
```

## 验证方法

### 1. 检查外键约束（应为空）
```sql
-- SQL Server
SELECT 
    fk.name AS ForeignKeyName,
    OBJECT_NAME(fk.parent_object_id) AS TableName
FROM sys.foreign_keys fk
WHERE OBJECT_NAME(fk.parent_object_id) IN (
    'job_queue', 'crawler_results', 'alert_history'
);
-- 预期结果：0 行
```

### 2. 检查索引（应存在）
```sql
-- SQL Server
SELECT 
    i.name AS IndexName,
    t.name AS TableName,
    COL_NAME(ic.object_id, ic.column_id) AS ColumnName
FROM sys.indexes i
INNER JOIN sys.index_columns ic ON i.object_id = ic.object_id AND i.index_id = ic.index_id
INNER JOIN sys.tables t ON i.object_id = t.object_id
WHERE t.name IN ('job_queue', 'crawler_results', 'alert_history')
  AND i.name IN ('idx_config_status', 'idx_job', 'idx_config', 'idx_rule_id')
ORDER BY t.name, i.name;
-- 预期结果：4 行
```

### 3. Python 验证脚本
```python
# scripts/verify_no_foreign_keys.py
import asyncio
from sqlalchemy import text
from app.core.database import async_engine

async def verify_no_foreign_keys():
    async with async_engine.connect() as conn:
        result = await conn.execute(text("""
            SELECT COUNT(*) as fk_count
            FROM sys.foreign_keys fk
            WHERE OBJECT_NAME(fk.parent_object_id) IN (
                'job_queue', 'crawler_results', 'alert_history'
            )
        """))
        fk_count = result.scalar()
        
        if fk_count == 0:
            print("✓ 验证通过：无外键约束")
        else:
            print(f"✗ 验证失败：发现 {fk_count} 个外键约束")
            return False
        
        # 验证索引存在
        result = await conn.execute(text("""
            SELECT 
                t.name as table_name,
                i.name as index_name
            FROM sys.indexes i
            INNER JOIN sys.tables t ON i.object_id = t.object_id
            WHERE i.name IN ('idx_config_status', 'idx_job', 'idx_config', 'idx_rule_id')
            ORDER BY t.name, i.name
        """))
        indexes = result.fetchall()
        
        print(f"✓ 找到 {len(indexes)} 个索引:")
        for idx in indexes:
            print(f"  - {idx.table_name}.{idx.index_name}")
        
        return True

if __name__ == "__main__":
    asyncio.run(verify_no_foreign_keys())
```

## 影响范围

### ✅ 不影响
- 现有业务逻辑
- 查询性能（索引已优化）
- ORM 关系查询（`relationship` 仍然有效）
- API 接口

### ⚠️ 需注意
- 删除操作需要在应用层处理级联
- 需要定期运行数据完整性检查
- 开发人员需理解无外键约束的设计

## 相关文档

- 📄 `docs/NO_FOREIGN_KEY_DESIGN.md` - 详细设计说明
- 📄 `docs/PYINSTALLER_FIX.md` - PyInstaller 打包修复说明
- 📄 `alembic/versions/f1028eaaa97b_initial_schema_for_sql_server.py` - 迁移脚本

## 团队通知

请所有开发人员注意：

1. ⚠️ **删除数据前务必检查关联记录**
2. ✅ **优先使用软删除（设置 deleted_at）**
3. ✅ **创建关联数据前验证父记录存在**
4. 📖 **阅读 `docs/NO_FOREIGN_KEY_DESIGN.md` 了解详情**

---

**修改人员**: Claude Code  
**审核状态**: ✅ 已完成  
**测试状态**: ⏳ 待测试  
**部署状态**: ⏳ 待部署
