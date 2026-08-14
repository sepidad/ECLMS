"""AI-Assisted Contract Review Service (Phase 4 Intelligence).

Loads the active version's text of a contract and runs it through the
configured review provider (deterministic rules by default, optional
external LLM).  Org-scoped through the contracts module.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from backend.modules.intelligence.application.review_provider import ReviewProvider, _worst_level
from backend.modules.intelligence.domain.review import ContractReviewResult

if TYPE_CHECKING:
  from backend.modules.contracts.application.contract_service import ContractService


class ReviewService:
  def __init__(self, contracts: ContractService, provider: ReviewProvider) -> None:
    self._contracts = contracts
    self._provider = provider

  async def review_contract(
    self, contract_id: str, *, organization_id: str, provider: ReviewProvider | None = None
  ) -> ContractReviewResult:
    selected = provider or self._provider
    contract = await self._contracts.get_contract(contract_id, organization_id=organization_id)
    versions = await self._contracts.list_versions(contract_id, organization_id=organization_id)
    active = next((v for v in versions if v.get('is_active')), None)
    text = (active or {}).get('content') or ''
    version_number = (active or {}).get('version_number')

    if not text:
      return ContractReviewResult(
        contract_id=contract_id,
        version_number=version_number,
        provider=selected.name,
        overall_risk_level='LOW',
        findings=[],
      )

    findings = await selected.review(text, context={'contract_id': contract_id, 'title': contract.title})
    return ContractReviewResult(
      contract_id=contract_id,
      version_number=version_number,
      provider=selected.name,
      overall_risk_level=_worst_level(findings),
      findings=findings,
    )
