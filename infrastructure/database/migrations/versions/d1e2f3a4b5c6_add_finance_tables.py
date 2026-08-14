"""add finance commitments and payments tables

Revision ID: d1e2f3a4b5c6
Revises: c7e8f9a0b1c2
Create Date: 2026-08-07 15:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'd1e2f3a4b5c6'
down_revision: str | Sequence[str] | None = 'c7e8f9a0b1c2'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
  op.create_table(
    'finance_commitments',
    sa.Column('id', sa.String(length=32), nullable=False),
    sa.Column('organization_id', sa.String(length=32), nullable=False),
    sa.Column('contract_id', sa.String(length=32), nullable=False),
    sa.Column('description', sa.Text(), nullable=False),
    sa.Column('amount', sa.Float(), nullable=False),
    sa.Column('currency', sa.String(length=10), nullable=False),
    sa.Column('status', sa.String(length=30), nullable=False),
    sa.Column('created_by', sa.String(length=32), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['contract_id'], ['contracts.id'], name='fk_finance_commitments_contract'),
    sa.PrimaryKeyConstraint('id'),
  )
  op.create_index(op.f('ix_finance_commitments_organization_id'), 'finance_commitments', ['organization_id'], unique=False)
  op.create_index(op.f('ix_finance_commitments_contract_id'), 'finance_commitments', ['contract_id'], unique=False)
  op.create_index(op.f('ix_finance_commitments_status'), 'finance_commitments', ['status'], unique=False)

  op.create_table(
    'finance_payments',
    sa.Column('id', sa.String(length=32), nullable=False),
    sa.Column('organization_id', sa.String(length=32), nullable=False),
    sa.Column('commitment_id', sa.String(length=32), nullable=False),
    sa.Column('amount', sa.Float(), nullable=False),
    sa.Column('due_date', sa.DateTime(timezone=True), nullable=False),
    sa.Column('status', sa.String(length=30), nullable=False),
    sa.Column('paid_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['commitment_id'], ['finance_commitments.id'], name='fk_finance_payments_commitment'),
    sa.PrimaryKeyConstraint('id'),
  )
  op.create_index(op.f('ix_finance_payments_organization_id'), 'finance_payments', ['organization_id'], unique=False)
  op.create_index(op.f('ix_finance_payments_commitment_id'), 'finance_payments', ['commitment_id'], unique=False)
  op.create_index(op.f('ix_finance_payments_due_date'), 'finance_payments', ['due_date'], unique=False)
  op.create_index(op.f('ix_finance_payments_status'), 'finance_payments', ['status'], unique=False)


def downgrade() -> None:
  op.drop_index(op.f('ix_finance_payments_status'), table_name='finance_payments')
  op.drop_index(op.f('ix_finance_payments_due_date'), table_name='finance_payments')
  op.drop_index(op.f('ix_finance_payments_commitment_id'), table_name='finance_payments')
  op.drop_index(op.f('ix_finance_payments_organization_id'), table_name='finance_payments')
  op.drop_table('finance_payments')
  op.drop_index(op.f('ix_finance_commitments_status'), table_name='finance_commitments')
  op.drop_index(op.f('ix_finance_commitments_contract_id'), table_name='finance_commitments')
  op.drop_index(op.f('ix_finance_commitments_organization_id'), table_name='finance_commitments')
  op.drop_table('finance_commitments')