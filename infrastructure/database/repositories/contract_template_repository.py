from __future__ import annotations

from sqlalchemy import select

from backend.core.utils import new_id, utc_now
from infrastructure.database.models.contracts import ContractTemplateModel
from infrastructure.database.session import get_session_factory


class SqlContractTemplateRepository:
  async def create(self, *, organization_id: str, name: str, contract_type: str, description: str | None, storage_path: str, file_name: str, created_by: str) -> ContractTemplateModel:
    item = ContractTemplateModel(id=new_id(), organization_id=organization_id, name=name, contract_type=contract_type, description=description, storage_path=storage_path, file_name=file_name, is_active=True, created_by=created_by, created_at=utc_now())
    async with get_session_factory()() as session:
      session.add(item); await session.commit(); await session.refresh(item)
    return item

  async def list(self, organization_id: str) -> list[ContractTemplateModel]:
    async with get_session_factory()() as session:
      result = await session.execute(select(ContractTemplateModel).where(ContractTemplateModel.organization_id == organization_id).order_by(ContractTemplateModel.created_at.desc()))
      return list(result.scalars().all())

  async def get_active(self, organization_id: str) -> ContractTemplateModel | None:
    async with get_session_factory()() as session:
      result = await session.execute(select(ContractTemplateModel).where(ContractTemplateModel.organization_id == organization_id, ContractTemplateModel.is_active.is_(True)).order_by(ContractTemplateModel.created_at.desc()).limit(1))
      return result.scalars().first()
