"""Financial module (execution priority #6, Phase 2 contract financial tracking).

Tracks financial commitments (contract value) and payment schedules with
per-payment status (SCHEDULED/PAID/OVERDUE/CANCELLED) tied to contracts.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from backend.core.base.module import Module
from backend.modules.finances.application.finance_service import FinanceService
from backend.modules.finances.interfaces import router

if TYPE_CHECKING:
  from backend.api.gateway import APIGateway
  from backend.bootstrap.container import ModuleContainer
  from backend.core.events import EventBus


class FinancesModule(Module):
  name = 'finances'
  version = '0.1.0'
  dependencies = ('contracts',)

  def initialize(self, container: ModuleContainer) -> None:
    from infrastructure.database.repositories import SqlFinanceRepository

    self._repository = SqlFinanceRepository()

  def register_services(self, container: ModuleContainer) -> None:
    contracts = container.get_service('contracts.service')
    event_bus = container.get_service('event_bus')
    service = FinanceService(self._repository, contracts, event_bus)
    container.register_service('finances.service', service)

  def register_routes(self, gateway: APIGateway) -> None:
    gateway.mount('finances', router)

  def register_events(self, bus: EventBus) -> None:
    return None
