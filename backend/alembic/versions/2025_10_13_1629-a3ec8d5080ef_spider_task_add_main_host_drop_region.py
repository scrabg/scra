"""spider_task add main_host drop region

Revision ID: a3ec8d5080ef
Revises: 
Create Date: 2025-10-13 16:29:26.884353

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a3ec8d5080ef'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # add column main_host
    op.add_column(
        'spider_task',
        sa.Column('main_host', sa.String(length=255), nullable=True, comment='主域名'),
    )
    # drop column region if exists
    try:
        op.drop_column('spider_task', 'region')
    except Exception:
        # column might not exist in current env; ignore
        pass


def downgrade() -> None:
    """Downgrade schema."""
    # recreate region column (nullable, String(20))
    try:
        op.add_column('spider_task', sa.Column('region', sa.String(length=20), nullable=True))
    except Exception:
        pass
    # remove main_host column
    try:
        op.drop_column('spider_task', 'main_host')
    except Exception:
        pass
