"""add tags to contracts"""

import sqlalchemy as sa
from alembic import op

revision = 'a6b7c8d9e0f1'
down_revision = 'f5a6b7c8d9e0'
branch_labels = None
depends_on = None


def upgrade() -> None:
  op.add_column('contracts', sa.Column('tags_json', sa.Text(), nullable=True))


def downgrade() -> None:
  op.drop_column('contracts', 'tags_json')
