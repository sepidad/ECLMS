from datetime import date

from sqlalchemy import select

from backend.modules.contracts.domain.guarantee import Guarantee
from infrastructure.database.models.guarantees import GuaranteeModel
from infrastructure.database.session import get_session_factory


class SqlGuaranteeRepository:
  async def save(self, item: Guarantee):
    async with get_session_factory()() as session:
      session.add(GuaranteeModel(**item.__dict__))
      await session.commit()
    return item

  async def list_for_contract(self, contract_id):
    async with get_session_factory()() as session:
      rows = (await session.execute(select(GuaranteeModel).where(GuaranteeModel.contract_id == contract_id))).scalars().all()
      return [self._serialize(row) for row in rows]

  async def list_expiring(self, before: date):
    async with get_session_factory()() as session:
      rows = (await session.execute(select(GuaranteeModel).where(GuaranteeModel.expires_on <= before, GuaranteeModel.state == 'ACTIVE'))).scalars().all()
      return [self._serialize(row) for row in rows]

  @staticmethod
  def _serialize(row):
    return {key: getattr(row, key) for key in ('id', 'contract_id', 'guarantee_type', 'direction', 'amount', 'currency', 'issuer', 'beneficiary', 'serial_number', 'valid_from', 'expires_on', 'state', 'created_at')}
