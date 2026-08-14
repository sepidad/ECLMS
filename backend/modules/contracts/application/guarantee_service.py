from datetime import timedelta

from backend.core.exceptions import NotFoundError
from backend.core.utils import utc_now
from backend.modules.contracts.domain.guarantee import Guarantee


class GuaranteeService:
  def __init__(self, repository, contracts):
    self._repository = repository
    self._contracts = contracts

  async def create(self, *, organization_id, **data):
    await self._contracts.get_contract(data['contract_id'], organization_id=organization_id)
    return await self._repository.save(Guarantee(**data))

  async def list(self, contract_id, organization_id):
    await self._contracts.get_contract(contract_id, organization_id=organization_id)
    return await self._repository.list_for_contract(contract_id)

  async def warnings(self, organization_id, days=30):
    # The repository is contract-scoped; filter through the owning contract to
    # preserve organization isolation.
    rows = await self._repository.list_expiring(utc_now().date() + timedelta(days=days))
    result = []
    for row in rows:
      try:
        await self._contracts.get_contract(row['contract_id'], organization_id=organization_id)
      except NotFoundError:
        continue
      row['warning'] = Guarantee(**{key: row[key] for key in ('contract_id','guarantee_type','direction','amount','currency','issuer','beneficiary','serial_number','valid_from','expires_on','id','state','created_at')}).warning()
      result.append(row)
    return result
