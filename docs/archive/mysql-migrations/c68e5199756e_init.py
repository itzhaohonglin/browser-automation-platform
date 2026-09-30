"""init

Revision ID: c68e5199756e
Revises: 
Create Date: 2026-08-30 21:21:27.028332

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c68e5199756e'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create crawler_configs table
    op.create_table(
        'crawler_configs',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('config_name', sa.String(length=100), nullable=False, comment='任务名称'),
        sa.Column('target_url', sa.String(length=500), nullable=False, comment='目标页面URL'),
        sa.Column('need_login', sa.Boolean(), nullable=False, comment='是否需要登录'),
        sa.Column('auth_profile', sa.String(length=50), nullable=True, comment='登录态标识'),
        sa.Column('login_url', sa.String(length=500), nullable=True, comment='登录页地址'),
        sa.Column('input_configs', sa.JSON(), nullable=False, comment='多输入框配置'),
        sa.Column('submit_selector', sa.String(length=200), nullable=False, comment='查询按钮选择器'),
        sa.Column('wait_selector', sa.String(length=200), nullable=False, comment='等待加载完成的选择器'),
        sa.Column('fields_mapping', sa.JSON(), nullable=False, comment='数据提取规则'),
        sa.Column('pagination_selector', sa.String(length=200), nullable=True, comment='下一页按钮选择器'),
        sa.Column('max_pages', sa.Integer(), nullable=False, comment='最大翻页数'),
        sa.Column('is_active', sa.Boolean(), nullable=False, comment='是否启用'),
        sa.Column('created_at', sa.DateTime(), nullable=False, comment='创建时间'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_auth_profile', 'crawler_configs', ['auth_profile'], unique=False)

    # Create job_queue table
    op.create_table(
        'job_queue',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('config_id', sa.Integer(), nullable=False, comment='关联crawler_configs.id'),
        sa.Column('query_params', sa.JSON(), nullable=False, comment='查询参数'),
        sa.Column('status', sa.Enum('PENDING', 'PROCESSING', 'SUCCESS', 'FAILED', name='jobstatus'), nullable=False, comment='任务状态'),
        sa.Column('retry_count', sa.Integer(), nullable=False, comment='重试次数'),
        sa.Column('error_msg', sa.Text(), nullable=True, comment='错误信息'),
        sa.Column('created_at', sa.DateTime(), nullable=False, comment='创建时间'),
        sa.Column('updated_at', sa.DateTime(), nullable=False, comment='更新时间'),
        sa.ForeignKeyConstraint(['config_id'], ['crawler_configs.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_config_status', 'job_queue', ['config_id', 'status'], unique=False)

    # Create crawler_results table
    op.create_table(
        'crawler_results',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('job_id', sa.Integer(), nullable=False, comment='关联job_queue.id'),
        sa.Column('config_id', sa.Integer(), nullable=False, comment='冗余字段便于查询'),
        sa.Column('query_params', sa.JSON(), nullable=False, comment='查询参数快照'),
        sa.Column('extracted_data', sa.JSON(), nullable=False, comment='提取的业务数据'),
        sa.Column('page_count', sa.Integer(), nullable=False, comment='实际抓取页数'),
        sa.Column('created_at', sa.DateTime(), nullable=False, comment='创建时间'),
        sa.ForeignKeyConstraint(['job_id'], ['job_queue.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_job', 'crawler_results', ['job_id'], unique=False)


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_index('idx_job', table_name='crawler_results')
    op.drop_table('crawler_results')

    op.drop_index('idx_config_status', table_name='job_queue')
    op.drop_table('job_queue')

    op.drop_index('idx_auth_profile', table_name='crawler_configs')
    op.drop_table('crawler_configs')
