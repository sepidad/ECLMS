"""add per-user permission overrides"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision = 'c9d0e1f2a3b4'
down_revision: str | Sequence[str] | None = 'b8c9d0e1f2a3'
branch_labels = None
depends_on = None

def upgrade():
  op.create_table('user_permission_overrides',
    sa.Column('user_id', sa.String(32), sa.ForeignKey('users.id'), primary_key=True),
    sa.Column('permission_id', sa.String(100), sa.ForeignKey('permissions.id'), primary_key=True),
    sa.Column('enabled', sa.Boolean, nullable=False))

def downgrade():
  op.drop_table('user_permission_overrides')
