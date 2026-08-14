"""Contract application services (sequence/01_Contract_Creation.md).

Orchestrates contract creation and state transitions, publishing domain
events so other modules can react without direct coupling.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from backend.core.events import Event
from backend.core.exceptions import NotFoundError
from backend.core.utils import utc_now
from backend.modules.contracts.domain.contract import Contract

if TYPE_CHECKING:
  from backend.core.events import EventBus


class ContractService:
  """Use cases for the contract aggregate."""

  def __init__(self, repository, event_bus: EventBus) -> None:
    self._repository = repository
    self._event_bus = event_bus

  async def _require_scoped(self, contract_id: str, organization_id: str) -> Contract:
    """Load a contract, enforcing that it belongs to the organization.

    A contract outside the caller's org is reported as not found so the
    caller cannot infer it exists (org scoping, ADR-003).
    """
    contract = await self._repository.require_by_id(contract_id)
    if contract.organization_id != organization_id:
      raise NotFoundError(f'Contract not found: {contract_id}')
    return contract

  async def create_contract(
    self,
    *,
    title: str,
    reference_number: str,
    counterparty: str,
    organization_id: str,
    owner_id: str,
    tags: list[str] | None = None,
    content: str | None = None,
    structure: list[dict] | None = None,
  ) -> Contract:
    contract = Contract(
      title=title,
      reference_number=reference_number,
      counterparty=counterparty,
      organization_id=organization_id,
      owner_id=owner_id,
    )
    contract.tags = self._normalize_tags(tags)
    await self._repository.save(contract)
    await self._repository.create_version(contract, content=content, structure=structure)
    await self._event_bus.publish(
      Event(
        event_type='contract.created',
        source_module='contracts',
        payload={
          'contract_id': contract.id,
          'reference_number': contract.reference_number,
          'version': contract.current_version_id,
        },
        metadata={'entity_type': 'contract', 'entity_id': contract.id, 'actor_id': owner_id, 'organization_id': organization_id},
      )
    )
    return contract

  async def update_contract(
    self,
    contract_id: str,
    *,
    organization_id: str,
    title: str | None = None,
    reference_number: str | None = None,
    counterparty: str | None = None,
    content: str | None = None,
    structure: list[dict] | None = None,
    tags: list[str] | None = None,
  ) -> Contract:
    """Update mutable fields and snapshot a new immutable version."""
    contract = await self._require_scoped(contract_id, organization_id)
    if title is not None:
      contract.title = title
    if reference_number is not None:
      contract.reference_number = reference_number
    if counterparty is not None:
      contract.counterparty = counterparty
    if tags is not None:
      contract.tags = self._normalize_tags(tags)
    contract.updated_at = utc_now()
    await self._repository.save(contract)
    await self._repository.create_version(contract, content=content, structure=structure)
    await self._event_bus.publish(
      Event(
        event_type='contract.updated',
        source_module='contracts',
        payload={'contract_id': contract.id, 'version': contract.current_version_id},
        metadata={'entity_type': 'contract', 'entity_id': contract.id, 'actor_id': contract.owner_id, 'organization_id': organization_id},
      )
    )
    return contract

  async def transition(self, contract_id: str, new_state: str, *, organization_id: str) -> Contract:
    contract = await self._require_scoped(contract_id, organization_id)
    previous = contract.state
    contract.transition_to(new_state)
    await self._repository.save(contract)
    await self._event_bus.publish(
      Event(
        event_type='contract.state_changed',
        source_module='contracts',
        payload={'contract_id': contract.id, 'from': previous, 'to': contract.state},
        metadata={'entity_type': 'contract', 'entity_id': contract.id, 'actor_id': contract.owner_id, 'organization_id': organization_id},
      )
    )
    return contract

  async def get_contract(self, contract_id: str, *, organization_id: str) -> Contract:
    return await self._require_scoped(contract_id, organization_id)

  async def list_contracts(self, *, organization_id: str, limit: int = 100, offset: int = 0) -> list[Contract]:
    return await self._repository.list_all(organization_id=organization_id, limit=limit, offset=offset)

  async def count_contracts(self, *, organization_id: str) -> int:
    return await self._repository.count(organization_id=organization_id)

  async def list_versions(self, contract_id: str, *, organization_id: str) -> list[dict]:
    await self._require_scoped(contract_id, organization_id)
    return await self._repository.list_versions(contract_id)

  @staticmethod
  def _normalize_tags(tags: list[str] | None) -> list[str]:
    result: list[str] = []
    for tag in tags or []:
      value = ' '.join(str(tag).strip().split())
      if value and value.lower() not in {item.lower() for item in result}:
        result.append(value[:80])
    return result[:30]
