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

    # 1. 删除告警历史表（先删除依赖表）
    try:
        op.drop_table('alert_history')
    except Exception as e:
        print(f"删除 alert_history 表失败（可能不存在）: {e}")

    # 2. 删除告警规则表
    try:
        op.drop_table('alert_rules')
    except Exception as e:
        print(f"删除 alert_rules 表失败（可能不存在）: {e}")

    # 3. 删除 schedule_config 字段（已改为配置文件方式）
    try:
        op.drop_column('crawler_configs', 'schedule_config')
    except Exception as e:
        print(f"删除 schedule_config 字段失败（可能不存在）: {e}")


def downgrade() -> None:
    """回滚操作（恢复字段和表）"""

    # 恢复 schedule_config 字段
    op.add_column(
        'crawler_configs',
        sa.Column(
            'schedule_config',
            sa.JSON().with_variant(sa.NVARCHAR(collation='Chinese_PRC_CI_AS'), 'mssql'),
            nullable=True,
            comment='调度配置（已弃用，改用配置文件）'
        )
    )

    # 恢复告警规则表
    op.create_table(
        'alert_rules',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('rule_name', sa.String(length=100), nullable=False, comment='规则名称'),
        sa.Column('metric_name', sa.String(length=100), nullable=False, comment='监控指标'),
        sa.Column('condition', sa.String(length=10), nullable=False, comment='条件'),
        sa.Column('threshold', sa.Float(), nullable=False, comment='阈值'),
        sa.Column('duration_seconds', sa.Integer(), nullable=False, comment='持续时长'),
        sa.Column('channels', sa.JSON(), nullable=False, comment='通知渠道'),
        sa.Column('enabled', sa.Boolean(), nullable=False, comment='是否启用'),
        sa.Column('silence_duration', sa.Integer(), nullable=False, comment='静默时长（秒）'),
        sa.Column('last_alert_at', sa.DateTime(timezone=True), nullable=True, comment='上次告警时间'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, comment='创建时间'),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, comment='更新时间'),
        sa.PrimaryKeyConstraint('id')
    )

    # 恢复告警历史表
    op.create_table(
        'alert_history',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('rule_id', sa.Integer(), nullable=False, comment='关联alert_rules.id'),
        sa.Column('triggered_at', sa.DateTime(), nullable=False, comment='触发时间'),
        sa.Column('resolved_at', sa.DateTime(), nullable=True, comment='恢复时间'),
        sa.Column('is_active', sa.Boolean(), nullable=False, comment='是否活跃'),
        sa.Column('alert_message', sa.Text(), nullable=False, comment='告警消息'),
        sa.Column('metric_value', sa.Float(), nullable=False, comment='指标值'),
        sa.Column('notify_status', sa.String(length=20), nullable=False, comment='通知状态'),
        sa.Column('notify_error', sa.Text(), nullable=True, comment='通知错误'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_rule_id', 'alert_history', ['rule_id'])
