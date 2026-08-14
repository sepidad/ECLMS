"""SQLAlchemy ORM models for the obligations module.

Implements the obligation data model from the domain:
- ObligationModel
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from infrastructure.database.session import Base


class ObligationModel(Base):
  __tablename__ = 'obligations'

  id: Mapped[str] = mapped_column(String(32), primary_key=True)
  organization_id: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
  contract_id: Mapped[str] = mapped_column(
    String(32), ForeignKey('contracts.id', name='fk_obligations_contract'), index=True, nullable=False
  )
  description: Mapped[str] = mapped_column(Text, nullable=False)
  due_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
  status: Mapped[str] = mapped_column(String(30), nullable=False, default='OPEN', index=True)
  created_by: Mapped[str] = mapped_column(String(32), nullable=False)
  completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
  created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
  updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
