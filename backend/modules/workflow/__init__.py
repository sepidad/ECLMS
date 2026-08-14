"""Workflow module (execution priority #3, Phase 1 minimal approval transitions).

Phase 1 scope: sequential approval workflow engine (start / decide /
history) driving contract lifecycle transitions.  Phase 2 adds the full
engine (parallel/conditional approvals, escalation).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from backend.core.base.module import Module
from backend.modules.workflow.application.workflow_service import WorkflowService
from backend.modules.workflow.interfaces import router

if TYPE_CHECKING:
  from backend.api.gateway import APIGateway
  from backend.bootstrap.container import ModuleContainer
  from backend.core.events import EventBus


class WorkflowModule(Module):
  name = 'workflow'
  version = '0.1.0'
  dependencies = ('contracts',)

  def initialize(self, container: ModuleContainer) -> None:
    from infrastructure.database.repositories import SqlWorkflowRepository

    self._repository = SqlWorkflowRepository()

  def register_services(self, container: ModuleContainer) -> None:
    contracts = container.get_service('contracts.service')
    users = container.get_service('identity.users')
    event_bus = container.get_service('event_bus')
    service = WorkflowService(self._repository, contracts, users, event_bus)
    container.register_service('workflow.service', service)

  def register_routes(self, gateway: APIGateway) -> None:
    gateway.mount('workflows', router)

  def register_events(self, bus: EventBus) -> None:
    return None
