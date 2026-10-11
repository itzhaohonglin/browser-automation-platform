"""fix_chinese_encoding_add_collate

Revision ID: 19798be7d82c
Revises: f1028eaaa97b
Create Date: 2026-10-11 14:27:29.302159

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '19798be7d82c'
down_revision: Union[str, None] = 'f1028eaaa97b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    修复 SQL Server 中文编码问题
    为所有文本列添加 COLLATE Chinese_PRC_CI_AS
    """
    # 修改 crawler_configs 表
    # 注意：auth_profile 列有索引，需要先删除索引再修改
    op.drop_index('idx_auth_profile', table_name='crawler_configs')

    op.execute("ALTER TABLE crawler_configs ALTER COLUMN config_name NVARCHAR(100) COLLATE Chinese_PRC_CI_AS NOT NULL")
    op.execute("ALTER TABLE crawler_configs ALTER COLUMN target_url NVARCHAR(500) COLLATE Chinese_PRC_CI_AS NOT NULL")
    op.execute("ALTER TABLE crawler_configs ALTER COLUMN auth_profile NVARCHAR(50) COLLATE Chinese_PRC_CI_AS NULL")
    op.execute("ALTER TABLE crawler_configs ALTER COLUMN login_url NVARCHAR(500) COLLATE Chinese_PRC_CI_AS NULL")
    op.execute("ALTER TABLE crawler_configs ALTER COLUMN submit_selector NVARCHAR(200) COLLATE Chinese_PRC_CI_AS NOT NULL")
    op.execute("ALTER TABLE crawler_configs ALTER COLUMN wait_selector NVARCHAR(200) COLLATE Chinese_PRC_CI_AS NOT NULL")
    op.execute("ALTER TABLE crawler_configs ALTER COLUMN pagination_selector NVARCHAR(200) COLLATE Chinese_PRC_CI_AS NULL")

    # 重新创建索引
    op.create_index('idx_auth_profile', 'crawler_configs', ['auth_profile'], unique=False)

    # 修改 job_queue 表
    op.execute("ALTER TABLE job_queue ALTER COLUMN error_msg NVARCHAR(MAX) COLLATE Chinese_PRC_CI_AS NULL")

    # 修改 alert_rules 表
    op.execute("ALTER TABLE alert_rules ALTER COLUMN rule_name NVARCHAR(100) COLLATE Chinese_PRC_CI_AS NOT NULL")
    op.execute("ALTER TABLE alert_rules ALTER COLUMN metric_name NVARCHAR(100) COLLATE Chinese_PRC_CI_AS NOT NULL")
    op.execute("ALTER TABLE alert_rules ALTER COLUMN condition NVARCHAR(10) COLLATE Chinese_PRC_CI_AS NOT NULL")

    # 修改 alert_history 表
    op.execute("ALTER TABLE alert_history ALTER COLUMN notify_status NVARCHAR(20) COLLATE Chinese_PRC_CI_AS NOT NULL")
    op.execute("ALTER TABLE alert_history ALTER COLUMN alert_message NVARCHAR(MAX) COLLATE Chinese_PRC_CI_AS NOT NULL")
    op.execute("ALTER TABLE alert_history ALTER COLUMN notify_error NVARCHAR(MAX) COLLATE Chinese_PRC_CI_AS NULL")

    # 修改 system_configs 表
    # 注意：config_key 列有 UNIQUE 约束，需要先删除约束再修改
    # 查找并删除实际的约束名称（SQL Server 自动生成的名称）
    op.execute("""
        DECLARE @ConstraintName nvarchar(200)
        SELECT @ConstraintName = kc.name
        FROM sys.key_constraints kc
        INNER JOIN sys.index_columns ic ON kc.parent_object_id = ic.object_id AND kc.unique_index_id = ic.index_id
        INNER JOIN sys.columns c ON ic.object_id = c.object_id AND ic.column_id = c.column_id
        WHERE kc.type = 'UQ'
        AND OBJECT_NAME(kc.parent_object_id) = 'system_configs'
        AND c.name = 'config_key'

        IF @ConstraintName IS NOT NULL
            EXEC('ALTER TABLE system_configs DROP CONSTRAINT ' + @ConstraintName)
    """)

    op.execute("ALTER TABLE system_configs ALTER COLUMN config_key NVARCHAR(100) COLLATE Chinese_PRC_CI_AS NOT NULL")
    op.execute("ALTER TABLE system_configs ALTER COLUMN config_value NVARCHAR(500) COLLATE Chinese_PRC_CI_AS NOT NULL")
    op.execute("ALTER TABLE system_configs ALTER COLUMN description NVARCHAR(200) COLLATE Chinese_PRC_CI_AS NULL")

    # 重新创建 UNIQUE 约束
    op.create_unique_constraint(None, 'system_configs', ['config_key'])

    # 修改 metrics_timeseries 表
    # 注意：metric_name 列有多个索引，需要先删除索引再修改
    op.drop_index('idx_metric_time', table_name='metrics_timeseries')
    op.drop_index(op.f('ix_metrics_timeseries_metric_name'), table_name='metrics_timeseries')

    op.execute("ALTER TABLE metrics_timeseries ALTER COLUMN metric_name NVARCHAR(100) COLLATE Chinese_PRC_CI_AS NOT NULL")

    # 重新创建索引
    op.create_index('idx_metric_time', 'metrics_timeseries', ['metric_name', 'timestamp'], unique=False)
    op.create_index(op.f('ix_metrics_timeseries_metric_name'), 'metrics_timeseries', ['metric_name'], unique=False)


def downgrade() -> None:
    """
    回滚：移除 COLLATE 设置（使用数据库默认）
    """
    # 回滚 crawler_configs 表
    # 注意：auth_profile 列有索引，需要先删除索引再修改
    op.drop_index('idx_auth_profile', table_name='crawler_configs')

    op.execute("ALTER TABLE crawler_configs ALTER COLUMN config_name VARCHAR(100) NOT NULL")
    op.execute("ALTER TABLE crawler_configs ALTER COLUMN target_url VARCHAR(500) NOT NULL")
    op.execute("ALTER TABLE crawler_configs ALTER COLUMN auth_profile VARCHAR(50) NULL")
    op.execute("ALTER TABLE crawler_configs ALTER COLUMN login_url VARCHAR(500) NULL")
    op.execute("ALTER TABLE crawler_configs ALTER COLUMN submit_selector VARCHAR(200) NOT NULL")
    op.execute("ALTER TABLE crawler_configs ALTER COLUMN wait_selector VARCHAR(200) NOT NULL")
    op.execute("ALTER TABLE crawler_configs ALTER COLUMN pagination_selector VARCHAR(200) NULL")

    # 重新创建索引
    op.create_index('idx_auth_profile', 'crawler_configs', ['auth_profile'], unique=False)

    # 回滚 job_queue 表
    op.execute("ALTER TABLE job_queue ALTER COLUMN error_msg TEXT NULL")

    # 回滚 alert_rules 表
    op.execute("ALTER TABLE alert_rules ALTER COLUMN rule_name VARCHAR(100) NOT NULL")
    op.execute("ALTER TABLE alert_rules ALTER COLUMN metric_name VARCHAR(100) NOT NULL")
    op.execute("ALTER TABLE alert_rules ALTER COLUMN condition VARCHAR(10) NOT NULL")

    # 回滚 alert_history 表
    op.execute("ALTER TABLE alert_history ALTER COLUMN notify_status VARCHAR(20) NOT NULL")
    op.execute("ALTER TABLE alert_history ALTER COLUMN alert_message TEXT NOT NULL")
    op.execute("ALTER TABLE alert_history ALTER COLUMN notify_error TEXT NULL")

    # 回滚 system_configs 表
    # 注意：config_key 列有 UNIQUE 约束，需要先删除约束再修改
    # 查找并删除实际的约束名称（SQL Server 自动生成的名称）
    op.execute("""
        DECLARE @ConstraintName nvarchar(200)
        SELECT @ConstraintName = kc.name
        FROM sys.key_constraints kc
        INNER JOIN sys.index_columns ic ON kc.parent_object_id = ic.object_id AND kc.unique_index_id = ic.index_id
        INNER JOIN sys.columns c ON ic.object_id = c.object_id AND ic.column_id = c.column_id
        WHERE kc.type = 'UQ'
        AND OBJECT_NAME(kc.parent_object_id) = 'system_configs'
        AND c.name = 'config_key'

        IF @ConstraintName IS NOT NULL
            EXEC('ALTER TABLE system_configs DROP CONSTRAINT ' + @ConstraintName)
    """)

    op.execute("ALTER TABLE system_configs ALTER COLUMN config_key VARCHAR(100) NOT NULL")
    op.execute("ALTER TABLE system_configs ALTER COLUMN config_value VARCHAR(500) NOT NULL")
    op.execute("ALTER TABLE system_configs ALTER COLUMN description VARCHAR(200) NULL")

    # 重新创建 UNIQUE 约束
    op.create_unique_constraint(None, 'system_configs', ['config_key'])

    # 回滚 metrics_timeseries 表
    # 注意：metric_name 列有多个索引，需要先删除索引再修改
    op.drop_index('idx_metric_time', table_name='metrics_timeseries')
    op.drop_index(op.f('ix_metrics_timeseries_metric_name'), table_name='metrics_timeseries')

    op.execute("ALTER TABLE metrics_timeseries ALTER COLUMN metric_name VARCHAR(100) NOT NULL")

    # 重新创建索引
    op.create_index('idx_metric_time', 'metrics_timeseries', ['metric_name', 'timestamp'], unique=False)
    op.create_index(op.f('ix_metrics_timeseries_metric_name'), 'metrics_timeseries', ['metric_name'], unique=False)
