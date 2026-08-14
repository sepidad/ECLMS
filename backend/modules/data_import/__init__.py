"""Data Import module (CSV bulk import for contracts / obligations / finances).

Depends on the contracts, obligations and finances modules for their
application services, which the import engine delegates to.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from backend.core.base.module import Module
from backend.modules.data_import.interfaces import router

if TYPE_CHECKING:
  from backend.api.gateway import APIGateway
  from backend.bootstrap.container import ModuleContainer
  from backend.core.events.bus import EventBus


class ImportModule(Module):
  name = 'import'
  version = '0.1.0'
  dependencies = ('contracts', 'obligations', 'finances')

  def initialize(self, container: ModuleContainer) -> None:
    return None

  def register_services(self, container: ModuleContainer) -> None:
    from backend.modules.data_import.application.import_service import ImportService

    contracts = container.get_service('contracts.service')
    obligations = container.get_service('obligations.service')
    finances = container.get_service('finances.service')
    container.register_service('import.service', ImportService(contracts, obligations, finances))

  def register_routes(self, gateway: APIGateway) -> None:
    gateway.mount('import', router)

  def register_events(self, bus: EventBus) -> None:
    return None