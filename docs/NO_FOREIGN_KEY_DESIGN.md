# 无外键约束设计说明

## 设计决策

本项目数据库**不使用外键约束（Foreign Key Constraints）**，仅通过应用层逻辑维护数据关系。

## 原因

### 1. 灵活性
- ✅ 避免外键级联删除的复杂性
- ✅ 支持更灵活的数据清理策略
- ✅ 便于分布式部署和数据迁移

### 2. 性能
- ✅ 减少数据库层面的约束检查开销
- ✅ 提高写入性能（INSERT/UPDATE/DELETE）
- ✅ 避免锁等待和死锁问题

### 3. 维护性
- ✅ 简化数据库备份和恢复
- ✅ 便于数据归档和历史数据处理
- ✅ 支持逻辑删除而不影响关联数据

## 数据关系

虽然不使用外键约束，但数据表之间仍然存在**逻辑关系**，通过索引和应用层代码维护：

### 关系图

```
crawler_configs (id)
    ↓ (应用层维护)
job_queue (config_id)
    ↓ (应用层维护)
crawler_results (job_id, config_id)

alert_rules (id)
    ↓ (应用层维护)
alert_history (rule_id)
```

### 索引策略

为了保证查询性能，在关联字段上创建索引：

| 表名 | 索引字段 | 索引名称 | 用途 |
|------|---------|---------|------|
| **crawler_configs** | auth_profile | idx_auth_profile | 按登录态查询配置 |
| **crawler_configs** | deleted_at | idx_deleted_at | 软删除查询 |
| **job_queue** | config_id, status | idx_config_status | 按配置和状态查询任务 |
| **crawler_results** | job_id | idx_job | 按任务查询结果 |
| **crawler_results** | config_id | idx_config | 按配置查询结果 |
| **alert_history** | rule_id | idx_rule_id | 按规则查询告警历史 |
| **metrics_timeseries** | metric_name, timestamp | idx_metric_time | 时序数据查询 |

## 应用层数据完整性保证

### 1. 创建关联数据时的检查

```python
# 创建任务前检查配置是否存在
async def create_job(config_id: int, query_params: dict):
    async with get_session() as session:
        # 验证配置存在
        config = await session.get(CrawlerConfig, config_id)
        if not config:
            raise ValueError(f"配置 {config_id} 不存在")
        
        # 创建任务
        job = JobQueue(
            config_id=config_id,
            query_params=query_params
        )
        session.add(job)
        await session.commit()
```

### 2. 删除数据时的处理策略

```python
# 软删除配置（不影响历史任务）
async def delete_config(config_id: int):
    async with get_session() as session:
        config = await session.get(CrawlerConfig, config_id)
        if config:
            config.deleted_at = datetime.now()  # 软删除
            await session.commit()

# 删除任务时同时删除结果
async def delete_job(job_id: int):
    async with get_session() as session:
        # 先删除结果
        await session.execute(
            delete(CrawlerResult).where(CrawlerResult.job_id == job_id)
        )
        # 再删除任务
        await session.execute(
            delete(JobQueue).where(JobQueue.id == job_id)
        )
        await session.commit()
```

### 3. 查询时的 JOIN

```python
# 联合查询（通过索引优化）
async def get_job_with_config(job_id: int):
    async with get_session() as session:
        stmt = select(JobQueue, CrawlerConfig).join(
            CrawlerConfig,
            JobQueue.config_id == CrawlerConfig.id
        ).where(JobQueue.id == job_id)
        
        result = await session.execute(stmt)
        return result.first()
```

## 数据一致性检查

定期运行数据一致性检查脚本（可选）：

```python
# scripts/check_data_integrity.py
async def check_orphan_jobs():
    """检查孤立的任务（config_id 不存在）"""
    async with get_session() as session:
        stmt = select(JobQueue).where(
            ~exists(
                select(CrawlerConfig.id).where(
                    CrawlerConfig.id == JobQueue.config_id
                )
            )
        )
        result = await session.execute(stmt)
        orphan_jobs = result.scalars().all()
        
        if orphan_jobs:
            print(f"发现 {len(orphan_jobs)} 个孤立任务")
            for job in orphan_jobs:
                print(f"  - Job #{job.id}, config_id={job.config_id}")

async def check_orphan_results():
    """检查孤立的结果（job_id 不存在）"""
    async with get_session() as session:
        stmt = select(CrawlerResult).where(
            ~exists(
                select(JobQueue.id).where(
                    JobQueue.id == CrawlerResult.job_id
                )
            )
        )
        result = await session.execute(stmt)
        orphan_results = result.scalars().all()
        
        if orphan_results:
            print(f"发现 {len(orphan_results)} 个孤立结果")
```

## SQLAlchemy ORM 配置

在 SQLAlchemy 模型中，我们仍然定义 `relationship`，但不使用 `ForeignKey`：

```python
# app/models/job.py
class JobQueue(Base):
    __tablename__ = "job_queue"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    
    # 关联字段（不使用外键约束）
    config_id: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="关联crawler_configs.id"
    )
    
    # 关系定义（仅用于 ORM，不创建数据库外键）
    config: Mapped["CrawlerConfig"] = relationship(
        "CrawlerConfig",
        back_populates="jobs",
        foreign_keys=[config_id],
        viewonly=True  # 只读关系
    )
    
    # 索引
    __table_args__ = (
        Index("idx_config_status", "config_id", "status"),
    )
```

**注意**：`relationship` 中的 `foreign_keys` 参数仅用于 ORM 的关系映射，**不会在数据库中创建外键约束**。

## 迁移脚本修改

Alembic 迁移脚本中已移除所有 `ForeignKeyConstraint`：

```python
# alembic/versions/f1028eaaa97b_initial_schema_for_sql_server.py

# ✓ 正确：不包含外键约束
op.create_table('job_queue',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('config_id', sa.Integer(), nullable=False, comment='关联crawler_configs.id'),
    # ... 其他字段
    sa.PrimaryKeyConstraint('id')
)
op.create_index('idx_config_status', 'job_queue', ['config_id', 'status'], unique=False)

# ✗ 错误（已移除）：
# sa.ForeignKeyConstraint(['config_id'], ['crawler_configs.id']),
```

## 优势总结

| 维度 | 有外键约束 | 无外键约束（本项目） |
|------|-----------|-------------------|
| **写入性能** | 较低（需检查约束） | ✅ 高 |
| **删除灵活性** | 受限（级联或阻止） | ✅ 灵活 |
| **数据迁移** | 复杂（需维护顺序） | ✅ 简单 |
| **分布式支持** | 困难（跨库外键） | ✅ 友好 |
| **数据完整性** | 数据库保证 | 应用层保证 ⚠️ |
| **调试复杂度** | 低（数据库报错） | 中（需应用层检查）|

## 注意事项

⚠️ **开发人员须知**：

1. **创建关联数据前必须验证父记录存在**
   ```python
   # ✓ 正确
   config = await session.get(CrawlerConfig, config_id)
   if not config:
       raise ValueError("配置不存在")
   
   # ✗ 错误
   job = JobQueue(config_id=999999)  # 可能指向不存在的配置
   ```

2. **删除父记录前处理子记录**
   ```python
   # ✓ 正确：先删除任务，再删除配置
   await session.execute(delete(JobQueue).where(JobQueue.config_id == config_id))
   await session.execute(delete(CrawlerConfig).where(CrawlerConfig.id == config_id))
   
   # ✗ 错误：直接删除配置会导致孤立任务
   await session.execute(delete(CrawlerConfig).where(CrawlerConfig.id == config_id))
   ```

3. **使用软删除代替物理删除**
   ```python
   # ✓ 推荐：软删除（设置 deleted_at）
   config.deleted_at = datetime.now()
   
   # ⚠️ 谨慎：物理删除
   await session.delete(config)
   ```

4. **定期运行数据一致性检查**
   ```bash
   python scripts/check_data_integrity.py
   ```

## 相关文件

- **模型定义**：
  - `app/models/job.py` - 任务队列模型
  - `app/models/result.py` - 采集结果模型
  - `app/models/metrics.py` - 告警相关模型

- **迁移脚本**：
  - `alembic/versions/f1028eaaa97b_initial_schema_for_sql_server.py`

- **检查脚本**（可选创建）：
  - `scripts/check_data_integrity.py` - 数据完整性检查

---

**更新日期**：2026-10-01  
**适用版本**：v1.0.0+  
**设计决策人**：项目团队
