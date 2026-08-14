"""Notifications module registration."""

from __future__ import annotations

from typing import TYPE_CHECKING

from backend.core.base.module import Module
from backend.modules.notifications.application.notification_service import (
  NotificationRepository,
  NotificationService,
)
from backend.modules.notifications.interfaces.routes import router

if TYPE_CHECKING:
  from backend.api.gateway import APIGateway
  from backend.bootstrap.container import ModuleContainer
  from backend.core.events import EventBus


class NotificationsModule(Module):
  name = 'notifications'
  version = '0.1.0'
  dependencies = ('audit',)

  def initialize(self, container: ModuleContainer) -> None:
    pass

  def register_services(self, container: ModuleContainer) -> None:
    repo = NotificationRepository()
    users = container.get_service('identity.users')
    service = NotificationService(repo, user_repository=users)
    self._service = service
    container.register_service('notifications.repository', repo)
    container.register_service('notifications.service', service)

  def register_routes(self, gateway: APIGateway) -> None:
    gateway.mount('notifications', router)

  def register_events(self, bus: EventBus) -> None:
    if hasattr(self, '_service'):
      bus.subscribe_all(self._service.handle_event)
