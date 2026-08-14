"""SQLAlchemy-backed contract repository (replaces the in-memory store).

Self-sessioning: each operation opens its own session from the shared
async session factory and commits on success.  Immutable contract
versions are written within the same unit of work as the parent
contract so the version snapshot is atomic with the save.
"""

from __future__ import annotations

import json

from sqlalchemy import select

from backend.core.exceptions import NotFoundError
from backend.core.utils import new_id
from backend.modules.contracts.domain.contract import Contract
from backend.modules.contracts.domain.structure import numbered_structure
from infrastructure.database.models.contracts import ContractModel, ContractVersionModel
from infrastructure.database.session import get_session_factory


def _to_domain(model: ContractModel) -> Contract:
  contract = Contract(
    title=model.title,
    reference_number=model.reference_number,
    counterparty=model.counterparty,
    organization_id=model.organization_id,
    owner_id=model.owner_id,
    contract_id=model.id,
  )
  contract.state = model.state
  contract.effective_date = model.effective_date
  contract.expiry_date = model.expiry_date
  contract.created_at = model.created_at
  contract.updated_at = model.updated_at
  contract.current_version_id = model.current_version_id
  return contract


class SqlContractRepository:
  async def get_by_id(self, contract_id: str) -> Contract | None:
    async with get_session_factory()() as session:
      model = await session.get(ContractModel, contract_id)
      return _to_domain(model) if model else None

  async def require_by_id(self, contract_id: str) -> Contract:
    contract = await self.get_by_id(contract_id)
    if contract is None:
      raise NotFoundError(f'Contract not found: {contract_id}')
    return contract

  async def save(self, contract: Contract) -> Contract:
    async with get_session_factory()() as session:
      existing = await session.get(ContractModel, contract.id)
      if existing is None:
        session.add(
          ContractModel(
            id=contract.id,
            title=contract.title,
            reference_number=contract.reference_number,
            counterparty=contract.counterparty,
            state=contract.state,
            organization_id=contract.organization_id,
            owner_id=contract.owner_id,
            current_version_id=contract.current_version_id,
            effective_date=contract.effective_date,
            expiry_date=contract.expiry_date,
            created_at=contract.created_at,
            updated_at=contract.updated_at,
          )
        )
      else:
        existing.title = contract.title
        existing.reference_number = contract.reference_number
        existing.counterparty = contract.counterparty
        existing.state = contract.state
        existing.current_version_id = contract.current_version_id
        existing.effective_date = contract.effective_date
        existing.expiry_date = contract.expiry_date
        existing.updated_at = contract.updated_at
      await session.commit()
    return contract

  async def list_all(self, *, organization_id: str, limit: int = 100, offset: int = 0) -> list[Contract]:
    async with get_session_factory()() as session:
      stmt = (
        select(ContractModel)
        .where(ContractModel.organization_id == organization_id)
        .order_by(ContractModel.created_at)
        .limit(limit)
        .offset(offset)
      )
      models = (await session.execute(stmt)).scalars().all()
      return [_to_domain(m) for m in models]

  async def count(self, *, organization_id: str) -> int:
    async with get_session_factory()() as session:
      stmt = (
        select(ContractModel.id)
        .where(ContractModel.organization_id == organization_id)
      )
      rows = await session.execute(stmt)
      return len(rows.scalars().all())

  async def create_version(self, contract: Contract, content: str | None = None, structure: list[dict] | None = None) -> int:
    """Create the next immutable version snapshot and mark it active.

    Written in the same transaction as the parent contract save.
    """
    async with get_session_factory()() as session:
      stmt = select(ContractVersionModel.version_number).where(
        ContractVersionModel.contract_id == contract.id
      )
      numbers = (await session.execute(stmt)).scalars().all()
      version_number = max(numbers, default=0) + 1
      version_id = new_id()

      await session.execute(
        ContractVersionModel.__table__.update()
        .where(ContractVersionModel.contract_id == contract.id)
        .values(is_active=False)
      )
      session.add(
        ContractVersionModel(
          id=version_id,
          contract_id=contract.id,
          version_number=version_number,
          title=contract.title,
          counterparty=contract.counterparty,
          content=content,
          structure_json=json.dumps(structure, ensure_ascii=False) if structure is not None else None,
          is_active=True,
          created_by=contract.owner_id,
          created_at=contract.updated_at,
        )
      )
      await session.execute(
        ContractModel.__table__.update()
        .where(ContractModel.id == contract.id)
        .values(current_version_id=version_id, updated_at=contract.updated_at)
      )
      await session.commit()
    contract.current_version_id = version_id
    return version_number

  async def list_versions(self, contract_id: str) -> list[dict]:
    async with get_session_factory()() as session:
      stmt = (
        select(ContractVersionModel)
        .where(ContractVersionModel.contract_id == contract_id)
        .order_by(ContractVersionModel.version_number)
      )
      models = (await session.execute(stmt)).scalars().all()
      result = [
        {
          'id': v.id,
          'version_number': v.version_number,
          'title': v.title,
          'counterparty': v.counterparty,
          'content': v.content,
          'structure': json.loads(v.structure_json) if v.structure_json else None,
          'is_active': v.is_active,
          'created_at': v.created_at,
        }
        for v in models
      ]
      for item in result:
        _, articles, notes = numbered_structure(item['structure'])
        item['article_count'] = articles
        item['note_count'] = notes
      return result
