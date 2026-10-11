"""use ChineseJSON for all JSON fields

Revision ID: 6b5ba5232367
Revises: 19798be7d82c
Create Date: 2026-10-11 15:30:14.768961

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6b5ba5232367'
down_revision: Union[str, None] = '19798be7d82c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
