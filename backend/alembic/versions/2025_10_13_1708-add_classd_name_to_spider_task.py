"""add classd_name to spider_task

Revision ID: 4b6f3c2c1d7a
Revises: a3ec8d5080ef
Create Date: 2025-10-13 17:08:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4b6f3c2c1d7a'
down_revision: Union[str, Sequence[str], None] = 'a3ec8d5080ef'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema: add classd_name column for column_name mapping."""
    try:
        op.add_column(
            'spider_task',
            sa.Column('classd_name', sa.String(length=255), nullable=True, comment='栏目名称'),
        )
    except Exception:
        # ignore if column already exists
        pass


def downgrade() -> None:
    """Downgrade schema: drop classd_name column."""
    try:
        op.drop_column('spider_task', 'classd_name')
    except Exception:
        pass