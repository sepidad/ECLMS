"""Semantic Search Service (Phase 4 Intelligence).

Indexes contract version text into an in-memory vector store and ranks
matches by cosine similarity against a query.  The index is built
lazily per organization and refreshed when version fingerprints change.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from backend.core.utils import utc_now_iso
from backend.modules.intelligence.domain.semantic import IndexedDocument, InMemoryVectorIndex, embed

if TYPE_CHECKING:
  from backend.modules.contracts.application.contract_service import ContractService


class SemanticSearchService:
  def __init__(self, contracts: ContractService, index: InMemoryVectorIndex | None = None) -> None:
    self._contracts = contracts
    self._index = index or InMemoryVectorIndex()
    self._fingerprints: dict[str, tuple] = {}
    self._indexed_at: str | None = None

  async def _rebuild_for_org(self, organization_id: str) -> None:
    contracts = await self._contracts.list_contracts(organization_id=organization_id)
    fingerprint: list = []
    for contract in contracts:
      versions = await self._contracts.list_versions(contract.id, organization_id=organization_id)
      active = next((v for v in versions if v.get('is_active')), None)
      fingerprint.append((contract.id, (active or {}).get('id')))

    current = tuple(fingerprint)
    if self._fingerprints.get(organization_id) == current:
      return

    self._index.clear(organization_id)
    for contract in contracts:
      versions = await self._contracts.list_versions(contract.id, organization_id=organization_id)
      active = next((v for v in versions if v.get('is_active')), None)
      version_id = (active or {}).get('id') or contract.id
      text = (active or {}).get('content') or ''
      self._index.upsert(
        IndexedDocument(
          document_id=version_id,
          contract_id=contract.id,
          title=contract.title,
          text=text or contract.title,
          organization_id=organization_id,
          vector=embed(f'{contract.title}\n{text}'),
        )
      )
    self._fingerprints[organization_id] = current
    self._indexed_at = utc_now_iso()

  async def search(self, query: str, *, organization_id: str, limit: int = 10) -> list[dict]:
    """Return ranked matches for a natural-language query."""
    await self._rebuild_for_org(organization_id)
    return self._index.search(query, organization_id=organization_id, limit=limit)

  @property
  def indexed_at(self) -> str | None:
    return self._indexed_at
