"""add structured article tree to contract versions"""

from alembic import op
import sqlalchemy as sa

revision = 'e4f5a6b7c8d9'
down_revision = 'c9d0e1f2a3b4'
branch_labels = None
depends_on = None


def upgrade() -> None:
  op.add_column('contract_versions', sa.Column('structure_json', sa.Text(), nullable=True))


def downgrade() -> None:
  op.drop_column('contract_versions', 'structure_json')
