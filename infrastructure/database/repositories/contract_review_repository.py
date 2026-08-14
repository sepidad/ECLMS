from __future__ import annotations

from sqlalchemy import select

from backend.modules.contracts.domain.review import ReviewFeedback
from infrastructure.database.models.contract_reviews import ContractReviewFeedbackModel
from infrastructure.database.session import get_session_factory


class SqlContractReviewRepository:
  async def save(self, item: ReviewFeedback) -> ReviewFeedback:
    async with get_session_factory()() as session:
      session.add(ContractReviewFeedbackModel(
        id=item.id, contract_id=item.contract_id, version_id=item.version_id,
        reviewer_id=item.reviewer_id, reviewer_role=item.reviewer_role,
        kind=item.kind, body=item.body, proposed_text=item.proposed_text,
        status=item.status, created_at=item.created_at,
      ))
      await session.commit()
    return item

  async def list_for_contract(self, contract_id: str) -> list[dict]:
    async with get_session_factory()() as session:
      rows = (await session.execute(select(ContractReviewFeedbackModel).where(
        ContractReviewFeedbackModel.contract_id == contract_id,
      ).order_by(ContractReviewFeedbackModel.created_at))).scalars().all()
      return [{
        'id': row.id, 'version_id': row.version_id, 'reviewer_id': row.reviewer_id,
        'reviewer_role': row.reviewer_role, 'kind': row.kind, 'body': row.body,
        'proposed_text': row.proposed_text, 'status': row.status,
        'created_at': row.created_at,
      } for row in rows]

  async def decide(self, feedback_id: str, status: str) -> bool:
    async with get_session_factory()() as session:
      row = await session.get(ContractReviewFeedbackModel, feedback_id)
      if row is None:
        return False
      row.status = status
      await session.commit()
      return True
