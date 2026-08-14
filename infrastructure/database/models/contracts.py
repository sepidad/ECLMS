"""SQLAlchemy ORM models for the contracts module.

Implements the contract data model from DATA-019:
- Contract (with CurrentVersionId)
- ContractVersion (immutable, one active version per contract)
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from infrastructure.database.session import Base


class ContractModel(Base):
  __tablename__ = 'contracts'

  id: Mapped[str] = mapped_column(String(32), primary_key=True)
  title: Mapped[str] = mapped_column(String(300), nullable=False)
  reference_number: Mapped[str] = mapped_column(String(64), nullable=False)
  counterparty: Mapped[str] = mapped_column(String(200), nullable=False)
  state: Mapped[str] = mapped_column(String(30), nullable=False, default='DRAFT', index=True)
  organization_id: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
  owner_id: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
  current_version_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
  effective_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
  expiry_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
  created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
  updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

  versions: Mapped[list[ContractVersionModel]] = relationship(
    back_populates='contract', lazy='selectin'
  )


class ContractVersionModel(Base):
  __tablename__ = 'contract_versions'

  id: Mapped[str] = mapped_column(String(32), primary_key=True)
  contract_id: Mapped[str] = mapped_column(String(32), ForeignKey('contracts.id'), index=True, nullable=False)
  version_number: Mapped[int] = mapped_column(Integer, nullable=False)
  title: Mapped[str] = mapped_column(String(300), nullable=False)
  counterparty: Mapped[str] = mapped_column(String(200), nullable=False)
  content: Mapped[str | None] = mapped_column(Text, nullable=True)
  structure_json: Mapped[str | None] = mapped_column(Text, nullable=True)
  is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
  created_by: Mapped[str] = mapped_column(String(32), nullable=False)
  created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

  contract: Mapped[ContractModel] = relationship(back_populates='versions')
