"""Integration module registration (webhooks, email, SMS & connectors).

Subscribes to the internal event bus and forwards domain events to:
  * HMAC-signed webhook subscriptions (``WebhookDeliveryService``)
  * role-based SMTP email alerts (``EmailDeliveryService``)
  * configured SMS recipients (``SmsDeliveryService``)
The notifications module owns the subscription + delivery-history store.
External system connectors (ERP/accounting) are orchestrated by
``ConnectorService``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from backend.core.base.module import Module
from backend.modules.integration.application.connector_service import ConnectorService
from backend.modules.integration.application.email_service import EmailDeliveryService
from backend.modules.integration.application.sms_service import SmsDeliveryService
from backend.modules.integration.application.webhook_service import WebhookDeliveryService
from backend.modules.integration.interfaces.routes import register_connector_routes
from backend.modules.notifications.application.notification_service import NotificationRepository

if TYPE_CHECKING:
  from backend.api.gateway import APIGateway
  from backend.bootstrap.container import ModuleContainer
  from backend.core.events import EventBus


class IntegrationModule(Module):
  name = 'integration'
  version = '0.1.0'
  dependencies = ('notifications',)

  def initialize(self, container: ModuleContainer) -> None:
    self._settings = container.get_service('settings')

  def register_services(self, container: ModuleContainer) -> None:
    repo = NotificationRepository()
    users = container.get_service('identity.users')
    settings = self._settings
    contracts = container.get_service('contracts.service')
    finances = container.get_service('finances.service')
    email_service = EmailDeliveryService(settings, user_repository=users, repository=repo)
    sms_service = SmsDeliveryService(settings)
    service = WebhookDeliveryService(repo)
    connectors = ConnectorService(settings, contracts=contracts, finances=finances)
    container.register_service('integration.webhooks', service)
    container.register_service('integration.email', email_service)
    container.register_service('integration.sms', sms_service)
    container.register_service('integration.connectors', connectors)
    self._email_service = email_service
    self._sms_service = sms_service
    self._service = service
    self._connectors = connectors

  def register_routes(self, gateway: APIGateway) -> None:
    register_connector_routes(gateway)

  def register_events(self, bus: EventBus) -> None:
    if hasattr(self, '_service'):
      bus.subscribe_all(self._service.handle_event)
    if hasattr(self, '_email_service'):
      bus.subscribe_all(self._email_service.handle_event)
    if hasattr(self, '_sms_service'):
      bus.subscribe_all(self._sms_service.handle_event)
