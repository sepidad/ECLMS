"""Contracts module (execution priority #2, Phase 1 core).

MVP scope: contract creation, lifecycle state machine, basic audit.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from backend.core.base.module import Module
from backend.modules.contracts.application.contract_service import ContractService
from backend.modules.contracts.application.guarantee_service import GuaranteeService
from backend.modules.contracts.application.review_service import ContractReviewService
from backend.modules.contracts.application.template_service import ContractTemplateService
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
    from infrastructure.database.repositories.contract_review_repository import SqlContractReviewRepository
    from infrastructure.database.repositories.guarantee_repository import SqlGuaranteeRepository
    from infrastructure.database.repositories.contract_template_repository import SqlContractTemplateRepository
    from infrastructure.storage import get_storage_provider
    self._repositories = {'contracts': SqlContractRepository(), 'reviews': SqlContractReviewRepository(), 'guarantees': SqlGuaranteeRepository(), 'templates': SqlContractTemplateRepository()}
    self._storage = get_storage_provider()

  def register_services(self, container: ModuleContainer) -> None:
    event_bus = container.get_service('event_bus')
    service = ContractService(self._repositories['contracts'], event_bus)
    container.register_service('contracts.service', service)
    container.register_service('contracts.review.service', ContractReviewService(self._repositories['reviews'], service))
    container.register_service('contracts.guarantee.service', GuaranteeService(self._repositories['guarantees'], service))
    container.register_service('contracts.template.service', ContractTemplateService(self._repositories['templates'], self._storage))

  def register_routes(self, gateway: APIGateway) -> None:
    gateway.mount('contracts', router)

  def register_events(self, bus: EventBus) -> None:
    return None
