"""add query optimization indexes

Revision ID: b83afc2b63a8
Revises: a9a74a570a8d
Create Date: 2026-05-04 03:38:19.381199

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b83afc2b63a8'
down_revision: Union[str, Sequence[str], None] = 'a9a74a570a8d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_index(op.f('ix_items_category_id'), 'items', ['category_id'], unique=False)
    op.create_index(op.f('ix_media_item_id'), 'media', ['item_id'], unique=False)
    op.create_index(op.f('ix_audit_log_entity_id'), 'audit_log', ['entity_id'], unique=False)
    op.create_index(op.f('ix_audit_log_entity_type'), 'audit_log', ['entity_type'], unique=False)
    op.create_index(op.f('ix_audit_log_timestamp'), 'audit_log', ['timestamp'], unique=False)
    op.create_index(op.f('ix_locations_parent_id'), 'locations', ['parent_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_locations_parent_id'), table_name='locations')
    op.drop_index(op.f('ix_audit_log_timestamp'), table_name='audit_log')
    op.drop_index(op.f('ix_audit_log_entity_type'), table_name='audit_log')
    op.drop_index(op.f('ix_audit_log_entity_id'), table_name='audit_log')
    op.drop_index(op.f('ix_media_item_id'), table_name='media')
    op.drop_index(op.f('ix_items_category_id'), table_name='items')
