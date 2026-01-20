"""add_security_enhancements

Revision ID: a1b2c3d4e5f6
Revises: 6507752e3bfd
Create Date: 2026-01-20 19:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '6507752e3bfd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Add security and audit enhancements:
    - Add role field to users table
    - Add enhanced audit fields to audit_log table
    - Add performance indices for audit queries
    
    INDEX NOTES:
    - ix_audit_log_entity: Composite index for entity lookups (entity_type, entity_id)
      Purpose: Fast lookup of audit logs for specific entities
      Performance: O(log n) for entity audit history queries
      
    - ix_audit_log_user_id: Single column index for user activity tracking
      Purpose: Fast lookup of all actions by a specific user
      Performance: O(log n) for user activity queries
      
    - ix_audit_log_approval_status: Single column index for pending reviews
      Purpose: Fast lookup of AI suggestions awaiting review
      Performance: O(log n) for review queue queries
      
    These indices support the enhanced audit system without significant write overhead.
    Monitor query performance and adjust if needed based on actual usage patterns.
    """
    # Add role to users table
    op.add_column('users', sa.Column('role', sa.String(), nullable=False, server_default='user'))
    
    # Add enhanced audit fields to audit_log table
    op.add_column('audit_log', sa.Column('user_id', sa.Integer(), nullable=True))
    op.add_column('audit_log', sa.Column('approval_status', sa.String(), nullable=True))
    op.add_column('audit_log', sa.Column('reviewed_by', sa.Integer(), nullable=True))
    op.add_column('audit_log', sa.Column('reviewed_at', sa.DateTime(), nullable=True))
    op.add_column('audit_log', sa.Column('error_message', sa.Text(), nullable=True))
    
    # Add performance indices for audit queries
    # These indices are essential for:
    # 1. Efficient entity audit history lookups
    # 2. User activity tracking
    # 3. Review queue management
    op.create_index('ix_audit_log_entity', 'audit_log', ['entity_type', 'entity_id'], unique=False)
    op.create_index('ix_audit_log_user_id', 'audit_log', ['user_id'], unique=False)
    op.create_index('ix_audit_log_approval_status', 'audit_log', ['approval_status'], unique=False)


def downgrade() -> None:
    """Downgrade schema - remove security enhancements."""
    # Remove indices
    op.drop_index('ix_audit_log_approval_status', table_name='audit_log')
    op.drop_index('ix_audit_log_user_id', table_name='audit_log')
    op.drop_index('ix_audit_log_entity', table_name='audit_log')
    
    # Remove audit log columns
    op.drop_column('audit_log', 'error_message')
    op.drop_column('audit_log', 'reviewed_at')
    op.drop_column('audit_log', 'reviewed_by')
    op.drop_column('audit_log', 'approval_status')
    op.drop_column('audit_log', 'user_id')
    
    # Remove role from users
    op.drop_column('users', 'role')
