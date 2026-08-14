"""SQLAlchemy-backed document repository (Phase 1).

Documents carry immutable versions; only a new version may be added.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from backend.core.utils import new_id, utc_now
from infrastructure.database.models.documents_audit import DocumentModel, DocumentVersionModel
from infrastructure.database.session import get_session_factory


class SqlDocumentRepository:
  async def create_document(
    self,
    *,
    contract_id: str,
    doc_type: str,
    title: str,
    created_by: str,
  ) -> DocumentModel:
    async with get_session_factory()() as session:
      document = DocumentModel(
        id=new_id(),
        contract_id=contract_id,
        doc_type=doc_type,
        title=title,
        created_by=created_by,
        created_at=utc_now(),
      )
      session.add(document)
      await session.commit()
      return document

  async def add_version(
    self,
    document_id: str,
    *,
    storage_path: str,
    content_hash: str,
    file_name: str,
  ) -> DocumentVersionModel:
    async with get_session_factory()() as session:
      stmt = select(DocumentVersionModel.version_number).where(
        DocumentVersionModel.document_id == document_id
      )
      numbers = (await session.execute(stmt)).scalars().all()
      version = DocumentVersionModel(
        id=new_id(),
        document_id=document_id,
        version_number=max(numbers, default=0) + 1,
        storage_path=storage_path,
        content_hash=content_hash,
        file_name=file_name,
        created_at=utc_now(),
      )
      session.add(version)
      await session.commit()
      return version

  async def get_by_id(self, document_id: str) -> DocumentModel | None:
    async with get_session_factory()() as session:
      stmt = (
        select(DocumentModel)
        .where(DocumentModel.id == document_id)
        .options(selectinload(DocumentModel.versions))
      )
      return (await session.execute(stmt)).scalar_one_or_none()

  async def list_by_contract(self, contract_id: str) -> list[DocumentModel]:
    async with get_session_factory()() as session:
      stmt = (
        select(DocumentModel)
        .where(DocumentModel.contract_id == contract_id)
        .options(selectinload(DocumentModel.versions))
      )
      return (await session.execute(stmt)).scalars().all()
