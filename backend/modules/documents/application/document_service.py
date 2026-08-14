"""Document application service (Phase 1 document attachment).

Coordinates attachment uploads: validates the target contract exists,
stores the blob via the storage provider, records content hashes, and
publishes domain events.
"""

from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING

from backend.core.events import Event
from backend.core.exceptions import NotFoundError
from backend.core.utils import new_id
from backend.modules.contracts.application.contract_service import ContractService
from infrastructure.database.repositories import SqlDocumentRepository

if TYPE_CHECKING:
  from backend.core.events import EventBus
  from infrastructure.storage.provider import StorageProvider


class DocumentService:
  def __init__(
    self,
    repository: SqlDocumentRepository,
    storage: StorageProvider,
    contracts: ContractService,
    event_bus: EventBus,
  ) -> None:
    self._repository = repository
    self._storage = storage
    self._contracts = contracts
    self._event_bus = event_bus

  async def upload(
    self,
    *,
    contract_id: str,
    file_name: str,
    content: bytes,
    organization_id: str,
    created_by: str,
    doc_type: str = 'attachment',
  ) -> dict:
    # Validate the contract exists and belongs to the caller's org.
    await self._contracts.get_contract(contract_id, organization_id=organization_id)

    storage_key = f'contracts/{contract_id}/{new_id()}-{file_name}'
    content_hash = hashlib.sha256(content).hexdigest()
    await self._storage.put(storage_key, content)

    document = await self._repository.create_document(
      contract_id=contract_id,
      doc_type=doc_type,
      title=file_name,
      created_by=created_by,
    )
    await self._repository.add_version(
      document.id,
      storage_path=storage_key,
      content_hash=content_hash,
      file_name=file_name,
    )
    await self._event_bus.publish(
      Event(
        event_type='document.uploaded',
        source_module='documents',
        payload={
          'document_id': document.id,
          'contract_id': contract_id,
          'file_name': file_name,
          'content_hash': content_hash,
        },
        metadata={'entity_type': 'document', 'entity_id': document.id, 'actor_id': created_by, 'organization_id': organization_id},
      )
    )
    return {'id': document.id, 'contract_id': contract_id, 'file_name': file_name, 'content_hash': content_hash}

  async def list_for_contract(self, contract_id: str, *, organization_id: str) -> list[dict]:
    await self._contracts.get_contract(contract_id, organization_id=organization_id)
    documents = await self._repository.list_by_contract(contract_id)
    return [
      {
        'id': d.id,
        'contract_id': d.contract_id,
        'doc_type': d.doc_type,
        'title': d.title,
        'created_at': d.created_at,
        'version_count': len(d.versions),
      }
      for d in documents
    ]

  async def get_content(self, document_id: str, *, organization_id: str) -> tuple[bytes, str]:
    """Return the latest version's bytes and original filename for download.

    Verifies the owning contract belongs to the caller's organization so
    documents remain org-scoped (ADR-003).
    """
    document = await self._repository.get_by_id(document_id)
    if document is None:
      raise NotFoundError(f'Document not found: {document_id}')
    await self._contracts.get_contract(document.contract_id, organization_id=organization_id)

    versions = sorted(document.versions, key=lambda v: v.version_number)
    if not versions:
      raise NotFoundError(f'Document has no versions: {document_id}')
    latest = versions[-1]
    content = await self._storage.get(latest.storage_path)
    return content, latest.file_name
