"""Notifications and integration models (ORM)."""

from __future__ import annotations

from sqlalchemy import Boolean, DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from infrastructure.database.session import Base


class NotificationModel(Base):
  __tablename__ = 'notifications'

  id: Mapped[str] = mapped_column(String(32), primary_key=True)
  recipient_id: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
  organization_id: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
  channel: Mapped[str] = mapped_column(String(32), nullable=False)  # 'email', 'in_app', 'webhook'
  subject: Mapped[str] = mapped_column(String(200), nullable=False)
  body: Mapped[str] = mapped_column(Text, nullable=False)
  is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
  created_at = mapped_column(DateTime(timezone=True), nullable=False)


class WebhookSubscriptionModel(Base):
  __tablename__ = 'webhook_subscriptions'

  id: Mapped[str] = mapped_column(String(32), primary_key=True)
  organization_id: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
  url: Mapped[str] = mapped_column(String(500), nullable=False)
  event_type: Mapped[str] = mapped_column(String(100), nullable=False)  # e.g. 'contract.state_changed', '*'
  secret: Mapped[str] = mapped_column(String(100), nullable=False)
  is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
  created_at = mapped_column(DateTime(timezone=True), nullable=False)
