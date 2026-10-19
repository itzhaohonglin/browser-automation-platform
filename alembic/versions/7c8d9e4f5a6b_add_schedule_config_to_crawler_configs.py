"""add schedule_config to crawler_configs

Revision ID: 7c8d9e4f5a6b
Revises: 6b5ba5232367
Create Date: 2026-10-19 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7c8d9e4f5a6b'
down_revision: Union[str, None] = '6b5ba5232367'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """添加 schedule_config 字段到 crawler_configs 表"""
    op.add_column(
        'crawler_configs',
        sa.Column(
            'schedule_config',
            sa.JSON().with_variant(sa.NVARCHAR(collation='Chinese_PRC_CI_AS'), 'mssql'),
            nullable=True,
            comment='调度配置 {enabled: true, type: "interval", interval_minutes: 1440, ...}'
        )
    )


def downgrade() -> None:
    """移除 schedule_config 字段"""
    op.drop_column('crawler_configs', 'schedule_config')
