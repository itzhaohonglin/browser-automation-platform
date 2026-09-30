"""add_flexible_config_and_monitoring

Revision ID: 4c6fb90372b0
Revises: d1ac828134df
Create Date: 2026-09-28 21:33:27.372034

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4c6fb90372b0'
down_revision: Union[str, None] = 'd1ac828134df'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. crawler_configs 表新增字段
    op.add_column('crawler_configs',
        sa.Column('timeout_config', sa.JSON(), nullable=True,
                  comment='超时配置 JSON')
    )

    op.add_column('crawler_configs',
        sa.Column('extraction_config', sa.JSON(), nullable=True,
                  comment='提取规则配置 JSON')
    )

    op.add_column('crawler_configs',
        sa.Column('priority', sa.Integer(), nullable=False,
                  server_default='5', comment='任务优先级 1-10')
    )

    # 2. 创建 system_configs 表
    op.create_table('system_configs',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('config_key', sa.String(100), nullable=False,
                  comment='配置键'),
        sa.Column('config_value', sa.String(500), nullable=False,
                  comment='配置值'),
        sa.Column('description', sa.String(200), nullable=True,
                  comment='配置说明'),
        sa.Column('updated_at', sa.DateTime(), nullable=True,
                  comment='更新时间'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('config_key')
    )

    # 3. 插入默认系统配置
    op.execute("""
        INSERT INTO system_configs (config_key, config_value, description)
        VALUES
        ('max_concurrent_workers', '3', '最大并发进程数'),
        ('worker_memory_limit_mb', '512', '单进程内存限制(MB)'),
        ('queue_warning_threshold', '50', '队列积压告警阈值')
    """)

    # 4. job_queue 表新增 priority 字段（如果不存在）
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    columns = [col['name'] for col in inspector.get_columns('job_queue')]

    if 'priority' not in columns:
        op.add_column('job_queue',
            sa.Column('priority', sa.Integer(), nullable=False,
                      server_default='5', comment='任务优先级')
        )


def downgrade() -> None:
    # 回滚操作
    op.drop_column('crawler_configs', 'priority')
    op.drop_column('crawler_configs', 'extraction_config')
    op.drop_column('crawler_configs', 'timeout_config')
    op.drop_table('system_configs')

    # 尝试删除 job_queue.priority（如果存在）
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    columns = [col['name'] for col in inspector.get_columns('job_queue')]

    if 'priority' in columns:
        op.drop_column('job_queue', 'priority')
