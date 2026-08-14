"""Reporting module (Phase 4, roadmap priority #10 - Intelligence layer).

Provides read-only analytics and reporting aggregates over contracts,
workflows, obligations, and finances.  Follows RPT-022: reports are
derived views, never source truth, and never mutate operational data.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from backend.core.base.module import Module
from backend.modules.reporting.application.reporting_service import ReportingService
from backend.modules.reporting.interfaces import router

if TYPE_CHECKING:
  from backend.api.gateway import APIGateway
  from backend.bootstrap.container import ModuleContainer
  from backend.core.events import EventBus


class ReportingModule(Module):
  name = 'reporting'
  version = '0.1.0'
  dependencies = ('contracts',)

  def initialize(self, container: ModuleContainer) -> None:
    from infrastructure.database.repositories import SqlReportingRepository

    self._repository = SqlReportingRepository()

  def register_services(self, container: ModuleContainer) -> None:
    service = ReportingService(self._repository)
    container.register_service('reporting.service', service)

  def register_routes(self, gateway: APIGateway) -> None:
    gateway.mount('reporting', router)

  def register_events(self, bus: EventBus) -> None:
    return None