"""SMS delivery integration service.

Subscribes to the internal event bus and dispatches SMS alerts to
organizational recipients (configured via ``ECLMS_SMS_RECIPIENTS``).
Delivery is abstracted behind an ``SmsProvider`` (mock by default, HTTP
gateway when configured), and every attempt is recorded in
``sms_deliveries`` for auditability and delivery history.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

import httpx

from backend.core.events import Event
from backend.core.logging import get_logger
from backend.core.utils import new_id, utc_now
from backend.modules.notifications.application.notification_service import NotificationService
from infrastructure.database.models.integration import SmsDeliveryModel
from infrastructure.database.session import get_session_factory

logger = get_logger('eclms.integration.sms')


class SmsProvider(ABC):
  """Pluggable SMS gateway.  Implementations must be safe to call concurrently."""

  @abstractmethod
  async def send(self, *, to: str, body: str) -> None:
    """Deliver an SMS message.  Raise on failure."""


class MockSmsProvider(SmsProvider):
  """Development provider that logs instead of sending."""

  async def send(self, *, to: str, body: str) -> None:
    logger.info('Mock SMS sent to %s: %s', to, body)


class HttpSmsProvider(SmsProvider):
  """Generic HTTP SMS gateway (best-effort REST).

  Expects ``settings.sms_http_url``; the message is POSTed as JSON
  ``{"to": ..., "body": ...}`` with basic auth from the settings.
  """

  def __init__(self, settings, client: httpx.AsyncClient | None = None) -> None:
    self._settings = settings
    self._client = client or httpx.AsyncClient(timeout=10.0)

  async def send(self, *, to: str, body: str) -> None:
    if not self._settings.sms_http_url:
      raise RuntimeError('ECLMS_SMS_HTTP_URL not configured for the http sms provider')
    auth = None
    if self._settings.sms_http_username:
      auth = (self._settings.sms_http_username, self._settings.sms_http_password)
    response = await self._client.post(
      self._settings.sms_http_url,
      json={'to': to, 'body': body},
      auth=auth,
    )
    response.raise_for_status()


def build_sms_provider(settings) -> SmsProvider:
  if settings.sms_provider == 'http':
    return HttpSmsProvider(settings)
  return MockSmsProvider()


class SmsDeliveryService:
  """Delivers high-priority alerts by SMS and records every attempt."""

  #: Route domain events to SMS bodies + audience roles (shared routing).
  ROUTES = NotificationService.ROUTES

  def __init__(self, settings, provider: SmsProvider | None = None) -> None:
    self._settings = settings
    self._provider = provider or build_sms_provider(settings)

  async def handle_event(self, event: Event) -> None:
    if not self._settings.sms_enabled:
      return
    route = self.ROUTES.get(event.event_type)
    if route is None:
      return
    subject_template, body_template, _roles = route
    organization_id = event.metadata.get('organization_id')
    if not organization_id:
      return
    payload = {**event.payload}
    try:
      body = f'{subject_template.format(**payload)}. {body_template.format(**payload)}'
    except (KeyError, ValueError):
      body = f'{event.event_type}: {event.payload}'
    recipients = self._sms_recipients(event)
    if not recipients:
      return
    for phone in recipients:
      await self.send_sms(
        to=phone,
        body=body,
        organization_id=organization_id,
        event_type=event.event_type,
      )

  def _sms_recipients(self, event: Event) -> list[str]:
    """Resolve SMS recipients: event payload phone, then configured defaults."""
    explicit = event.payload.get('phone') or event.payload.get('sms_to')
    if explicit:
      return [str(explicit)]
    raw = self._settings.sms_recipients or ''
    return [p.strip() for p in raw.split(',') if p.strip()]

  async def send_sms(
    self,
    *,
    to: str,
    body: str,
    organization_id: str | None = None,
    recipient_id: str = 'system',
    event_type: str = 'manual',
  ) -> dict:
    """Send an SMS via the configured provider and record the attempt."""
    success = True
    error: str | None = None
    try:
      await self._provider.send(to=to, body=body)
    except Exception as exc:
      success = False
      error = str(exc)
      logger.exception('Failed to send SMS to %s', to)
    if organization_id:
      await self._record(
        organization_id=organization_id,
        recipient_id=recipient_id,
        recipient_phone=to,
        event_type=event_type,
        body=body,
        success=success,
        error=error,
      )
    return {'success': success, 'error': error}

  async def _record(
    self,
    *,
    organization_id: str,
    recipient_id: str,
    recipient_phone: str,
    event_type: str,
    body: str,
    success: bool,
    error: str | None,
  ) -> str:
    delivery_id = new_id()
    async with get_session_factory()() as session:
      session.add(
        SmsDeliveryModel(
          id=delivery_id,
          organization_id=organization_id,
          recipient_id=recipient_id,
          recipient_phone=recipient_phone,
          event_type=event_type,
          body=body,
          status='sent' if success else 'failed',
          error=error,
          delivered_at=utc_now(),
        )
      )
      await session.commit()
    return delivery_id