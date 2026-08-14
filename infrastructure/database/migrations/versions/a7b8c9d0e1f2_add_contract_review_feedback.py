"""add independent contract review feedback"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = 'a7b8c9d0e1f2'
down_revision: str | Sequence[str] | None = 'f2g3h4i5j6k7'
branch_labels = None
depends_on = None


def upgrade() -> None:
  op.create_table(
    'contract_review_feedback',
    sa.Column('id', sa.String(32), primary_key=True),
    sa.Column('contract_id', sa.String(32), sa.ForeignKey('contracts.id'), nullable=False),
    sa.Column('version_id', sa.String(32), sa.ForeignKey('contract_versions.id'), nullable=False),
    sa.Column('reviewer_id', sa.String(32), nullable=False),
    sa.Column('reviewer_role', sa.String(32), nullable=False),
    sa.Column('kind', sa.String(24), nullable=False),
    sa.Column('body', sa.Text, nullable=False),
    sa.Column('proposed_text', sa.Text, nullable=True),
    sa.Column('status', sa.String(24), nullable=False, server_default='OPEN'),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
  )
  op.create_index('ix_contract_review_feedback_contract_id', 'contract_review_feedback', ['contract_id'])


def downgrade() -> None:
  op.drop_index('ix_contract_review_feedback_contract_id', table_name='contract_review_feedback')
  op.drop_table('contract_review_feedback')
