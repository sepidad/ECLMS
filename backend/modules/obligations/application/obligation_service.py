"""Obligation application service (Phase 2 obligation tracking).

Coordinates creation, completion, cancellation, and overdue sweeping of
contractual obligations.  Every mutation is org-scoped (ADR-003) and
publishes a domain event for audit / notifications.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from backend.core.events import Event
from backend.core.exceptions import NotFoundError
from backend.core.utils import utc_now
from backend.modules.obligations.domain.obligation import Obligation

if TYPE_CHECKING:
  from backend.core.events import EventBus
  from backend.modules.contracts.application.contract_service import ContractService
  from infrastructure.database.repositories.obligation_repository import SqlObligationRepository


class ObligationService:
  def __init__(
    self,
    repository: SqlObligationRepository,
    contracts: ContractService,
    event_bus: EventBus,
  ) -> None:
    self._repository = repository
    self._contracts = contracts
    self._event_bus = event_bus

  async def _require_scoped(self, obligation_id: str, organization_id: str) -> Obligation:
    obligation = await self._repository.require_by_id(obligation_id)
    if obligation.organization_id != organization_id:
      raise NotFoundError(f'Obligation not found: {obligation_id}')
    return obligation

  async def create(
    self,
    *,
    contract_id: str,
    description: str,
    due_date: datetime,
    organization_id: str,
    created_by: str,
  ) -> Obligation:
    await self._contracts.get_contract(contract_id, organization_id=organization_id)
    obligation = Obligation(
      contract_id=contract_id,
      description=description,
      due_date=due_date,
      organization_id=organization_id,
      created_by=created_by,
    )
    await self._repository.save(obligation)
    await self._event_bus.publish(
      Event(
        event_type='obligation.created',
        source_module='obligations',
        payload={
          'obligation_id': obligation.id,
          'contract_id': contract_id,
          'due_date': due_date.isoformat(),
          'description': description,
        },
        metadata={
          'entity_type': 'obligation',
          'entity_id': obligation.id,
          'actor_id': created_by,
          'organization_id': organization_id,
        },
      )
    )
    return obligation

  async def complete(
    self, obligation_id: str, *, organization_id: str, actor_id: str
  ) -> Obligation:
    obligation = await self._require_scoped(obligation_id, organization_id)
    obligation.complete()
    await self._repository.save(obligation)
    await self._event_bus.publish(
      Event(
        event_type='obligation.completed',
        source_module='obligations',
        payload={'obligation_id': obligation.id, 'contract_id': obligation.contract_id},
        metadata={
          'entity_type': 'obligation',
          'entity_id': obligation.id,
          'actor_id': actor_id,
          'organization_id': organization_id,
        },
      )
    )
    return obligation

  async def cancel(
    self, obligation_id: str, *, organization_id: str, actor_id: str
  ) -> Obligation:
    obligation = await self._require_scoped(obligation_id, organization_id)
    obligation.cancel()
    await self._repository.save(obligation)
    await self._event_bus.publish(
      Event(
        event_type='obligation.cancelled',
        source_module='obligations',
        payload={'obligation_id': obligation.id, 'contract_id': obligation.contract_id},
        metadata={
          'entity_type': 'obligation',
          'entity_id': obligation.id,
          'actor_id': actor_id,
          'organization_id': organization_id,
        },
      )
    )
    return obligation

  async def get(self, obligation_id: str, *, organization_id: str) -> Obligation:
    return await self._require_scoped(obligation_id, organization_id)

  async def list_for_contract(
    self, contract_id: str, *, organization_id: str, limit: int = 100, offset: int = 0
  ) -> list[Obligation]:
    await self._contracts.get_contract(contract_id, organization_id=organization_id)
    return await self._repository.list_for_contract(
      contract_id, organization_id=organization_id, limit=limit, offset=offset
    )

  async def list_all(
    self, *, organization_id: str, status: str | None = None, limit: int = 100, offset: int = 0
  ) -> list[Obligation]:
    return await self._repository.list_all(
      organization_id=organization_id, status=status, limit=limit, offset=offset
    )

  async def sweep_overdue(self) -> int:
    """Mark OPEN obligations past their due_date as OVERDUE. Returns count."""
    now = utc_now()
    overdue = await self._repository.find_open_past_due(as_of=now)
    count = 0
    for obligation in overdue:
      if obligation.mark_overdue():
        await self._repository.save(obligation)
        count += 1
        await self._event_bus.publish(
          Event(
            event_type='obligation.overdue',
            source_module='obligations',
            payload={
              'obligation_id': obligation.id,
              'contract_id': obligation.contract_id,
              'due_date': obligation.due_date.isoformat(),
            },
            metadata={
              'entity_type': 'obligation',
              'entity_id': obligation.id,
              'actor_id': 'system',
              'organization_id': obligation.organization_id,
            },
          )
        )
    return count
