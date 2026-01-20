"""add_system_settings_and_audit_enhancements

Revision ID: ff7ac738ad3b
Revises: 6507752e3bfd
Create Date: 2026-01-20 11:16:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'ff7ac738ad3b'
down_revision = '6507752e3bfd'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create system_settings table
    op.create_table('system_settings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('key', sa.String(), nullable=False),
        sa.Column('value', sa.Text(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_system_settings_key'), 'system_settings', ['key'], unique=True)

    # Add new columns to audit_log table
    with op.batch_alter_table('audit_log', schema=None) as batch_op:
        batch_op.add_column(sa.Column('previous_values', sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column('is_undone', sa.Boolean(), nullable=True, server_default='false'))


def downgrade() -> None:
    # Remove columns from audit_log
    with op.batch_alter_table('audit_log', schema=None) as batch_op:
        batch_op.drop_column('is_undone')
        batch_op.drop_column('previous_values')

    # Drop system_settings table
    op.drop_index(op.f('ix_system_settings_key'), table_name='system_settings')
    op.drop_table('system_settings')
