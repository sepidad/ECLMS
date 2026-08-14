"""add contract guarantee register"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision = 'b8c9d0e1f2a3'
down_revision: str | Sequence[str] | None = 'a7b8c9d0e1f2'
branch_labels = None
depends_on = None

def upgrade():
  op.create_table('contract_guarantees',
    sa.Column('id', sa.String(32), primary_key=True), sa.Column('contract_id', sa.String(32), sa.ForeignKey('contracts.id'), nullable=False),
    sa.Column('guarantee_type', sa.String(32), nullable=False), sa.Column('direction', sa.String(16), nullable=False),
    sa.Column('amount', sa.Float, nullable=False), sa.Column('currency', sa.String(8), nullable=False),
    sa.Column('issuer', sa.String(200), nullable=False), sa.Column('beneficiary', sa.String(200), nullable=False),
    sa.Column('serial_number', sa.String(100), nullable=False), sa.Column('valid_from', sa.Date, nullable=False),
    sa.Column('expires_on', sa.Date, nullable=False), sa.Column('state', sa.String(24), nullable=False, server_default='ACTIVE'),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False))
  op.create_index('ix_contract_guarantees_expires_on', 'contract_guarantees', ['expires_on'])

def downgrade():
  op.drop_index('ix_contract_guarantees_expires_on', table_name='contract_guarantees')
  op.drop_table('contract_guarantees')
