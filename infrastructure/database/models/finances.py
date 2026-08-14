"""SQLAlchemy ORM models for the finances module."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from infrastructure.database.session import Base


class FinanceCommitmentModel(Base):
  __tablename__ = 'finance_commitments'

  id: Mapped[str] = mapped_column(String(32), primary_key=True)
  organization_id: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
  contract_id: Mapped[str] = mapped_column(
    String(32), ForeignKey('contracts.id', name='fk_finance_commitments_contract'), index=True, nullable=False
  )
  description: Mapped[str] = mapped_column(Text, nullable=False)
  amount: Mapped[float] = mapped_column(Float, nullable=False)
  currency: Mapped[str] = mapped_column(String(10), nullable=False, default='USD')
  status: Mapped[str] = mapped_column(String(30), nullable=False, default='OPEN', index=True)
  created_by: Mapped[str] = mapped_column(String(32), nullable=False)
  created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
  updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class FinancePaymentModel(Base):
  __tablename__ = 'finance_payments'

  id: Mapped[str] = mapped_column(String(32), primary_key=True)
  organization_id: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
  commitment_id: Mapped[str] = mapped_column(
    String(32), ForeignKey('finance_commitments.id', name='fk_finance_payments_commitment'), index=True, nullable=False
  )
  amount: Mapped[float] = mapped_column(Float, nullable=False)
  due_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
  status: Mapped[str] = mapped_column(String(30), nullable=False, default='SCHEDULED', index=True)
  paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
  created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
  updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
