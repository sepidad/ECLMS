"""SQLAlchemy-backed obligation repository."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select

from backend.core.exceptions import NotFoundError
from backend.modules.obligations.domain.obligation import Obligation
from infrastructure.database.models.obligations import ObligationModel
from infrastructure.database.session import get_session_factory


def _to_domain(model: ObligationModel) -> Obligation:
  obligation = Obligation(
    contract_id=model.contract_id,
    description=model.description,
    due_date=model.due_date,
    organization_id=model.organization_id,
    created_by=model.created_by,
    obligation_id=model.id,
  )
  obligation.status = model.status
  obligation.completed_at = model.completed_at
  obligation.created_at = model.created_at
  obligation.updated_at = model.updated_at
  return obligation


class SqlObligationRepository:
  async def get_by_id(self, obligation_id: str) -> Obligation | None:
    async with get_session_factory()() as session:
      model = await session.get(ObligationModel, obligation_id)
      return _to_domain(model) if model else None

  async def require_by_id(self, obligation_id: str) -> Obligation:
    obligation = await self.get_by_id(obligation_id)
    if obligation is None:
      raise NotFoundError(f'Obligation not found: {obligation_id}')
    return obligation

  async def save(self, obligation: Obligation) -> Obligation:
    async with get_session_factory()() as session:
      existing = await session.get(ObligationModel, obligation.id)
      if existing is None:
        session.add(
          ObligationModel(
            id=obligation.id,
            organization_id=obligation.organization_id,
            contract_id=obligation.contract_id,
            description=obligation.description,
            due_date=obligation.due_date,
            status=obligation.status,
            created_by=obligation.created_by,
            completed_at=obligation.completed_at,
            created_at=obligation.created_at,
            updated_at=obligation.updated_at,
          )
        )
      else:
        existing.description = obligation.description
        existing.due_date = obligation.due_date
        existing.status = obligation.status
        existing.completed_at = obligation.completed_at
        existing.updated_at = obligation.updated_at
      await session.commit()
    return obligation

  async def list_for_contract(
    self, contract_id: str, *, organization_id: str, limit: int = 100, offset: int = 0
  ) -> list[Obligation]:
    async with get_session_factory()() as session:
      stmt = (
        select(ObligationModel)
        .where(
          ObligationModel.contract_id == contract_id,
          ObligationModel.organization_id == organization_id,
        )
        .order_by(ObligationModel.due_date)
        .limit(limit)
        .offset(offset)
      )
      models = (await session.execute(stmt)).scalars().all()
      return [_to_domain(m) for m in models]

  async def list_all(
    self, *, organization_id: str, status: str | None = None, limit: int = 100, offset: int = 0
  ) -> list[Obligation]:
    async with get_session_factory()() as session:
      stmt = select(ObligationModel).where(ObligationModel.organization_id == organization_id)
      if status is not None:
        stmt = stmt.where(ObligationModel.status == status)
      stmt = stmt.order_by(ObligationModel.due_date).limit(limit).offset(offset)
      models = (await session.execute(stmt)).scalars().all()
      return [_to_domain(m) for m in models]

  async def find_open_past_due(self, *, as_of: datetime) -> list[Obligation]:
    """Return OPEN obligations whose due_date is before ``as_of`` (for overdue sweep)."""
    async with get_session_factory()() as session:
      stmt = select(ObligationModel).where(
        ObligationModel.status == 'OPEN',
        ObligationModel.due_date < as_of,
      )
      models = (await session.execute(stmt)).scalars().all()
      return [_to_domain(m) for m in models]
