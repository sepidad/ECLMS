"""Integration models (webhook + email + SMS delivery logs, connector syncs)."""

from __future__ import annotations

from sqlalchemy import JSON, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from infrastructure.database.session import Base


class WebhookDeliveryModel(Base):
  __tablename__ = 'webhook_deliveries'

  id: Mapped[str] = mapped_column(String(32), primary_key=True)
  organization_id: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
  subscription_id: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
  event_type: Mapped[str] = mapped_column(String(100), nullable=False)
  url: Mapped[str] = mapped_column(String(500), nullable=False)
  status_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
  error: Mapped[str | None] = mapped_column(Text, nullable=True)
  delivered_at = mapped_column(DateTime(timezone=True), nullable=False)


class EmailDeliveryModel(Base):
  __tablename__ = 'email_deliveries'

  id: Mapped[str] = mapped_column(String(32), primary_key=True)
  organization_id: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
  recipient_id: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
  recipient_email: Mapped[str] = mapped_column(String(200), nullable=False)
  event_type: Mapped[str] = mapped_column(String(100), nullable=False)
  subject: Mapped[str] = mapped_column(String(200), nullable=False)
  body: Mapped[str] = mapped_column(Text, nullable=False)
  status: Mapped[str] = mapped_column(String(16), nullable=False)  # 'sent' | 'failed'
  error: Mapped[str | None] = mapped_column(Text, nullable=True)
  delivered_at = mapped_column(DateTime(timezone=True), nullable=False)


class SmsDeliveryModel(Base):
  __tablename__ = 'sms_deliveries'

  id: Mapped[str] = mapped_column(String(32), primary_key=True)
  organization_id: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
  recipient_id: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
  recipient_phone: Mapped[str] = mapped_column(String(32), nullable=False)
  event_type: Mapped[str] = mapped_column(String(100), nullable=False)
  body: Mapped[str] = mapped_column(Text, nullable=False)
  status: Mapped[str] = mapped_column(String(16), nullable=False)  # 'sent' | 'failed'
  error: Mapped[str | None] = mapped_column(Text, nullable=True)
  delivered_at = mapped_column(DateTime(timezone=True), nullable=False)


class ConnectorSyncModel(Base):
  __tablename__ = 'connector_syncs'

  id: Mapped[str] = mapped_column(String(32), primary_key=True)
  organization_id: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
  connector_id: Mapped[str] = mapped_column(String(64), nullable=False)
  status: Mapped[str] = mapped_column(String(16), nullable=False)  # 'ok' | 'failed'
  detail: Mapped[dict | None] = mapped_column(JSON, nullable=True)
  executed_at = mapped_column(DateTime(timezone=True), nullable=False)
