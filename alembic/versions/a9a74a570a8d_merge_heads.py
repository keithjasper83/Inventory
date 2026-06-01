"""Merge heads

Revision ID: a9a74a570a8d
Revises: a1b2c3d4e5f6, ff7ac738ad3b
Create Date: 2026-06-01 12:59:21.463628

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a9a74a570a8d'
down_revision: Union[str, Sequence[str], None] = ('a1b2c3d4e5f6', 'ff7ac738ad3b')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
