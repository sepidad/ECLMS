"""Obligations module (execution priority #7, Phase 2 obligation tracking).

Tracks contractual obligations (deliverables, payments, renewals, ...)
tied to a contract's lifecycle, with OPEN/OVERDUE/COMPLETED/CANCELLED
status and an automated overdue sweep.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from backend.core.base.module import Module
from backend.modules.obligations.application.obligation_service import ObligationService
from backend.modules.obligations.interfaces import router

if TYPE_CHECKING:
  from backend.api.gateway import APIGateway
  from backend.bootstrap.container import ModuleContainer
  from backend.core.events import EventBus


class ObligationsModule(Module):
  name = 'obligations'
  version = '0.1.0'
  dependencies = ('contracts',)

  def initialize(self, container: ModuleContainer) -> None:
    from infrastructure.database.repositories import SqlObligationRepository

    self._repository = SqlObligationRepository()

  def register_services(self, container: ModuleContainer) -> None:
    contracts = container.get_service('contracts.service')
    event_bus = container.get_service('event_bus')
    service = ObligationService(self._repository, contracts, event_bus)
    container.register_service('obligations.service', service)

  def register_routes(self, gateway: APIGateway) -> None:
    gateway.mount('obligations', router)

  def register_events(self, bus: EventBus) -> None:
    return None
