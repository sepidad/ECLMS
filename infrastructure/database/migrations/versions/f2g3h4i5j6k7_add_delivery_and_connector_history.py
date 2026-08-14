"""add email, sms, and connector sync history tables

Revision ID: f2g3h4i5j6k7
Revises: d1e2f3a4b5c6
Create Date: 2026-08-09 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = 'f2g3h4i5j6k7'
down_revision: str | Sequence[str] | None = 'd1e2f3a4b5c6'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
  # Some deployments created these tables from ORM metadata before this
  # migration was introduced. Keep the migration restart-safe for those
  # databases while still creating the full schema on a clean install.
  bind = op.get_bind()
  existing = set(sa.inspect(bind).get_table_names())

  if 'email_deliveries' not in existing:
    op.create_table(
      'email_deliveries',
      sa.Column('id', sa.String(length=32), nullable=False),
      sa.Column('organization_id', sa.String(length=32), nullable=False),
      sa.Column('recipient_id', sa.String(length=32), nullable=False),
      sa.Column('recipient_email', sa.String(length=200), nullable=False),
      sa.Column('event_type', sa.String(length=100), nullable=False),
      sa.Column('subject', sa.String(length=200), nullable=False),
      sa.Column('body', sa.Text(), nullable=False),
      sa.Column('status', sa.String(length=16), nullable=False),
      sa.Column('error', sa.Text(), nullable=True),
      sa.Column('delivered_at', sa.DateTime(timezone=True), nullable=False),
      sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_email_deliveries_organization_id'), 'email_deliveries', ['organization_id'], unique=False)
    op.create_index(op.f('ix_email_deliveries_recipient_id'), 'email_deliveries', ['recipient_id'], unique=False)

  if 'sms_deliveries' not in existing:
    op.create_table(
      'sms_deliveries',
      sa.Column('id', sa.String(length=32), nullable=False),
      sa.Column('organization_id', sa.String(length=32), nullable=False),
      sa.Column('recipient_id', sa.String(length=32), nullable=False),
      sa.Column('recipient_phone', sa.String(length=32), nullable=False),
      sa.Column('event_type', sa.String(length=100), nullable=False),
      sa.Column('body', sa.Text(), nullable=False),
      sa.Column('status', sa.String(length=16), nullable=False),
      sa.Column('error', sa.Text(), nullable=True),
      sa.Column('delivered_at', sa.DateTime(timezone=True), nullable=False),
      sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_sms_deliveries_organization_id'), 'sms_deliveries', ['organization_id'], unique=False)
    op.create_index(op.f('ix_sms_deliveries_recipient_id'), 'sms_deliveries', ['recipient_id'], unique=False)

  if 'connector_syncs' not in existing:
    op.create_table(
      'connector_syncs',
      sa.Column('id', sa.String(length=32), nullable=False),
      sa.Column('organization_id', sa.String(length=32), nullable=False),
      sa.Column('connector_id', sa.String(length=64), nullable=False),
      sa.Column('status', sa.String(length=16), nullable=False),
      sa.Column('detail', sa.JSON(), nullable=True),
      sa.Column('executed_at', sa.DateTime(timezone=True), nullable=False),
      sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_connector_syncs_organization_id'), 'connector_syncs', ['organization_id'], unique=False)


def downgrade() -> None:
  op.drop_index(op.f('ix_connector_syncs_organization_id'), table_name='connector_syncs')
  op.drop_table('connector_syncs')
  op.drop_index(op.f('ix_sms_deliveries_recipient_id'), table_name='sms_deliveries')
  op.drop_index(op.f('ix_sms_deliveries_organization_id'), table_name='sms_deliveries')
  op.drop_table('sms_deliveries')
  op.drop_index(op.f('ix_email_deliveries_recipient_id'), table_name='email_deliveries')
  op.drop_index(op.f('ix_email_deliveries_organization_id'), table_name='email_deliveries')
  op.drop_table('email_deliveries')
