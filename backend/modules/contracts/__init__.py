"""Contracts module (execution priority #2, Phase 1 core).

MVP scope: contract creation, lifecycle state machine, basic audit.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from backend.core.base.module import Module
from backend.modules.contracts.application.contract_service import ContractService
from backend.modules.contracts.interfaces import router

if TYPE_CHECKING:
  from backend.api.gateway import APIGateway
  from backend.bootstrap.container import ModuleContainer
  from backend.core.events import EventBus


class ContractsModule(Module):
  name = 'contracts'
  version = '0.1.0'
  dependencies = ('identity',)

  def initialize(self, container: ModuleContainer) -> None:
    from infrastructure.database.repositories import SqlContractRepository

    self._repositories = {'contracts': SqlContractRepository()}

  def register_services(self, container: ModuleContainer) -> None:
    event_bus = container.get_service('event_bus')
    service = ContractService(self._repositories['contracts'], event_bus)
    container.register_service('contracts.service', service)

  def register_routes(self, gateway: APIGateway) -> None:
    gateway.mount('contracts', router)

  def register_events(self, bus: EventBus) -> None:
    return None
