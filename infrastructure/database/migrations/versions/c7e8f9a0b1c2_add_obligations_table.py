"""add obligations table

Revision ID: c7e8f9a0b1c2
Revises: 6dcb594622ee
Create Date: 2026-08-07 14:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = 'c7e8f9a0b1c2'
down_revision: str | Sequence[str] | None = '6dcb594622ee'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
  op.create_table(
    'obligations',
    sa.Column('id', sa.String(length=32), nullable=False),
    sa.Column('organization_id', sa.String(length=32), nullable=False),
    sa.Column('contract_id', sa.String(length=32), nullable=False),
    sa.Column('description', sa.Text(), nullable=False),
    sa.Column('due_date', sa.DateTime(timezone=True), nullable=False),
    sa.Column('status', sa.String(length=30), nullable=False),
    sa.Column('created_by', sa.String(length=32), nullable=False),
    sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['contract_id'], ['contracts.id'], name='fk_obligations_contract'),
    sa.PrimaryKeyConstraint('id'),
  )
  op.create_index(op.f('ix_obligations_organization_id'), 'obligations', ['organization_id'], unique=False)
  op.create_index(op.f('ix_obligations_contract_id'), 'obligations', ['contract_id'], unique=False)
  op.create_index(op.f('ix_obligations_due_date'), 'obligations', ['due_date'], unique=False)
  op.create_index(op.f('ix_obligations_status'), 'obligations', ['status'], unique=False)


def downgrade() -> None:
  op.drop_index(op.f('ix_obligations_status'), table_name='obligations')
  op.drop_index(op.f('ix_obligations_due_date'), table_name='obligations')
  op.drop_index(op.f('ix_obligations_contract_id'), table_name='obligations')
  op.drop_index(op.f('ix_obligations_organization_id'), table_name='obligations')
  op.drop_table('obligations')
