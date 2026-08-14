from __future__ import annotations

from backend.core.utils import new_id


class ContractTemplateService:
  def __init__(self, repository, storage):
    self._repository = repository
    self._storage = storage

  async def upload(self, *, organization_id: str, name: str, contract_type: str, description: str | None, file_name: str, content: bytes, created_by: str) -> dict:
    safe_name = file_name.replace('\\', '_').replace('/', '_')
    path = f'templates/{organization_id}/{new_id()}-{safe_name}'
    await self._storage.put(path, content, content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
    item = await self._repository.create(organization_id=organization_id, name=name, contract_type=contract_type, description=description, storage_path=path, file_name=safe_name, created_by=created_by)
    return self._serialize(item)

  async def list(self, organization_id: str) -> list[dict]:
    return [self._serialize(item) for item in await self._repository.list(organization_id)]

  async def active_bytes(self, organization_id: str) -> bytes | None:
    item = await self._repository.get_active(organization_id)
    return await self._storage.get(item.storage_path) if item else None

  @staticmethod
  def _serialize(item) -> dict:
    return {'id': item.id, 'name': item.name, 'contract_type': item.contract_type, 'description': item.description, 'file_name': item.file_name, 'is_active': item.is_active, 'created_at': item.created_at}
