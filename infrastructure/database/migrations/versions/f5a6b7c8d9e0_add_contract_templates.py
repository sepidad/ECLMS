"""add organization Word contract templates"""

import sqlalchemy as sa
from alembic import op

revision = 'f5a6b7c8d9e0'
down_revision = 'e4f5a6b7c8d9'
branch_labels = None
depends_on = None


def upgrade() -> None:
  op.create_table(
    'contract_templates',
    sa.Column('id', sa.String(length=32), nullable=False),
    sa.Column('organization_id', sa.String(length=32), nullable=False),
    sa.Column('name', sa.String(length=200), nullable=False),
    sa.Column('contract_type', sa.String(length=80), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('storage_path', sa.String(length=500), nullable=False),
    sa.Column('file_name', sa.String(length=300), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('created_by', sa.String(length=32), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['organization_id'], ['organizations.id']),
    sa.PrimaryKeyConstraint('id'),
  )
  op.create_index('ix_contract_templates_organization_id', 'contract_templates', ['organization_id'])


def downgrade() -> None:
  op.drop_index('ix_contract_templates_organization_id', table_name='contract_templates')
  op.drop_table('contract_templates')
