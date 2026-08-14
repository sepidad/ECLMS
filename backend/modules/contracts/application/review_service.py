from __future__ import annotations

from backend.core.exceptions import NotFoundError
from backend.modules.contracts.domain.review import ReviewFeedback


class ContractReviewService:
  def __init__(self, repository, contracts) -> None:
    self._repository = repository
    self._contracts = contracts

  async def add_feedback(self, *, contract_id, version_id, reviewer_id, reviewer_role, kind, body, proposed_text, organization_id):
    contract = await self._contracts.get_contract(contract_id, organization_id=organization_id)
    if contract.current_version_id != version_id:
      raise ValueError('Feedback must target the current official version')
    if kind not in {'COMMENT', 'SUGGESTION', 'REJECTION'}:
      raise ValueError('Unsupported feedback kind')
    if kind in {'SUGGESTION', 'REJECTION'} and not body.strip():
      raise ValueError('Feedback reason is required')
    return await self._repository.save(ReviewFeedback(
      contract_id, version_id, reviewer_id, reviewer_role, kind, body, proposed_text,
    ))

  async def list_feedback(self, contract_id, organization_id):
    await self._contracts.get_contract(contract_id, organization_id=organization_id)
    return await self._repository.list_for_contract(contract_id)

  async def decide(self, feedback_id, status):
    if status not in {'ACCEPTED', 'REJECTED'}:
      raise ValueError('Decision must be ACCEPTED or REJECTED')
    if not await self._repository.decide(feedback_id, status):
      raise NotFoundError(f'Feedback not found: {feedback_id}')
