"""SQLAlchemy ORM models for the documents and audit modules.

- Document / DocumentVersion: immutable storage, hash-based integrity
- AuditEvent: append-only, never updated, never deleted (DATA-019)
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from infrastructure.database.session import Base


class DocumentModel(Base):
  __tablename__ = 'documents'

  id: Mapped[str] = mapped_column(String(32), primary_key=True)
  contract_id: Mapped[str] = mapped_column(String(32), ForeignKey('contracts.id'), index=True, nullable=False)
  doc_type: Mapped[str] = mapped_column(String(50), nullable=False, default='attachment')
  title: Mapped[str] = mapped_column(String(300), nullable=False)
  created_by: Mapped[str] = mapped_column(String(32), nullable=False)
  created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

  versions: Mapped[list[DocumentVersionModel]] = relationship(back_populates='document', lazy='selectin')


class DocumentVersionModel(Base):
  __tablename__ = 'document_versions'

  id: Mapped[str] = mapped_column(String(32), primary_key=True)
  document_id: Mapped[str] = mapped_column(String(32), ForeignKey('documents.id'), index=True, nullable=False)
  version_number: Mapped[int] = mapped_column(Integer, nullable=False)
  storage_path: Mapped[str] = mapped_column(String(500), nullable=False)
  content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
  file_name: Mapped[str] = mapped_column(String(300), nullable=False)
  created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

  document: Mapped[DocumentModel] = relationship(back_populates='versions')


class AuditEventModel(Base):
  __tablename__ = 'audit_events'

  id: Mapped[str] = mapped_column(String(32), primary_key=True)
  event_type: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
  source_module: Mapped[str] = mapped_column(String(50), nullable=False)
  actor_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
  entity_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
  entity_id: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
  before_state: Mapped[str | None] = mapped_column(Text, nullable=True)
  after_state: Mapped[str | None] = mapped_column(Text, nullable=True)
  payload: Mapped[str | None] = mapped_column(Text, nullable=True)
  created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True, nullable=False)
