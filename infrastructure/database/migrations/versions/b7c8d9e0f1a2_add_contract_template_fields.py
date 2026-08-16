"""add template provenance to contracts (Phase 6 preparation)"""

import sqlalchemy as sa
from alembic import op

revision = 'b7c8d9e0f1a2'
down_revision = 'a6b7c8d9e0f1'
branch_labels = None
depends_on = None


def upgrade() -> None:
  op.add_column('contracts', sa.Column('template_key', sa.String(length=64), nullable=True))
  op.add_column('contracts', sa.Column('template_fields_json', sa.Text(), nullable=True))


def downgrade() -> None:
  op.drop_column('contracts', 'template_fields_json')
  op.drop_column('contracts', 'template_key')
