"""Documents module (execution priority #5, Phase 1 document attachment).

Phase 1 scope: contract document attachment with hash-verified immutable
versions stored via the local storage provider.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from backend.core.base.module import Module
from backend.modules.documents.application.document_service import DocumentService
from backend.modules.documents.interfaces import router

if TYPE_CHECKING:
  from backend.api.gateway import APIGateway
  from backend.bootstrap.container import ModuleContainer
  from backend.core.events import EventBus


class DocumentsModule(Module):
  name = 'documents'
  version = '0.1.0'
  dependencies = ('contracts',)

  def initialize(self, container: ModuleContainer) -> None:
    from infrastructure.database.repositories import SqlDocumentRepository
    from infrastructure.storage import get_storage_provider

    self._repository = SqlDocumentRepository()
    self._storage = get_storage_provider()

  def register_services(self, container: ModuleContainer) -> None:
    contracts = container.get_service('contracts.service')
    event_bus = container.get_service('event_bus')
    service = DocumentService(self._repository, self._storage, contracts, event_bus)
    container.register_service('documents.service', service)

  def register_routes(self, gateway: APIGateway) -> None:
    gateway.mount('documents', router)

  def register_events(self, bus: EventBus) -> None:
    return None
