from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from infrastructure.database.session import Base


class GuaranteeModel(Base):
  __tablename__ = 'contract_guarantees'
  id: Mapped[str] = mapped_column(String(32), primary_key=True)
  contract_id: Mapped[str] = mapped_column(String(32), ForeignKey('contracts.id'), index=True, nullable=False)
  guarantee_type: Mapped[str] = mapped_column(String(32), nullable=False)
  direction: Mapped[str] = mapped_column(String(16), nullable=False)
  amount: Mapped[float] = mapped_column(Float, nullable=False)
  currency: Mapped[str] = mapped_column(String(8), nullable=False)
  issuer: Mapped[str] = mapped_column(String(200), nullable=False)
  beneficiary: Mapped[str] = mapped_column(String(200), nullable=False)
  serial_number: Mapped[str] = mapped_column(String(100), nullable=False)
  valid_from: Mapped[date] = mapped_column(Date, nullable=False)
  expires_on: Mapped[date] = mapped_column(Date, nullable=False, index=True)
  state: Mapped[str] = mapped_column(String(24), nullable=False, default='ACTIVE')
  created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
