"""Webhook delivery service for external integrations.

Subscribes to the internal event bus and forwards domain events to
registered webhook subscriptions.  Each delivery is HMAC-SHA256 signed
with the subscription secret (X-ECLMS-Signature header) so receivers can
verify authenticity, and the attempt is recorded in webhook_deliveries
for auditability and retry.
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import logging

import httpx

from backend.core.events import Event
from backend.core.utils import utc_now
from backend.modules.notifications.application.notification_service import (
  NotificationRepository,
  WebhookSubscription,
)
from infrastructure.database.models.integration import WebhookDeliveryModel
from infrastructure.database.session import get_session_factory

logger = logging.getLogger('eclms.integration')

SIGNATURE_HEADER = 'X-ECLMS-Signature'
TIMEOUT_SECONDS = 10.0
MAX_ATTEMPTS = 3
BACKOFF_BASE_SECONDS = 0.5
BACKOFF_MAX_SECONDS = 8.0

#: Status codes that indicate a transient failure worth retrying.
RETRYABLE_STATUSES = frozenset({429, 500, 502, 503, 504})


def sign_payload(secret: str, body: bytes) -> str:
  return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


class WebhookDeliveryService:
  def __init__(
    self,
    repository: NotificationRepository,
    http_client: httpx.AsyncClient | None = None,
    enabled: bool = True,
    max_attempts: int = MAX_ATTEMPTS,
    backoff_base_seconds: float = BACKOFF_BASE_SECONDS,
    backoff_max_seconds: float = BACKOFF_MAX_SECONDS,
  ) -> None:
    self._repository = repository
    self._client = http_client or httpx.AsyncClient(timeout=TIMEOUT_SECONDS)
    self._enabled = enabled
    self._max_attempts = max(max_attempts, 1)
    self._backoff_base = max(backoff_base_seconds, 0.0)
    self._backoff_max = max(backoff_max_seconds, self._backoff_base)

  async def handle_event(self, event: Event) -> None:
    """Dispatch a domain event to matching webhook subscriptions."""
    if not self._enabled:
      return
    organization_id = event.metadata.get('organization_id')
    if not organization_id:
      return
    subscriptions = await self._repository.list_active_for_event(organization_id, event.event_type)
    if not subscriptions:
      return
    body = json.dumps(event.to_dict()).encode()
    for sub in subscriptions:
      await self._deliver_with_retries(sub, body)

  async def _deliver_with_retries(self, sub: WebhookSubscription, body: bytes) -> None:
    last_status: int | None = None
    last_error: str | None = None
    for attempt in range(1, self._max_attempts + 1):
      status_code, error = await self._deliver(sub, body)
      last_status, last_error = status_code, error
      transient_http = status_code in RETRYABLE_STATUSES
      network_failure = status_code is None and error is not None
      if not (transient_http or network_failure) or attempt == self._max_attempts:
        break
      delay = min(self._backoff_base * (2 ** (attempt - 1)), self._backoff_max)
      logger.info(
        'Webhook delivery retry %s/%s for %s in %.1fs (status=%s, error=%s)',
        attempt,
        self._max_attempts,
        sub.url,
        delay,
        status_code,
        error,
      )
      await asyncio.sleep(delay)
    await self._record(
      organization_id=sub.organization_id,
      subscription_id=sub.id,
      event_type=sub.event_type,
      url=sub.url,
      status_code=last_status,
      error=last_error,
    )

  async def _deliver(self, sub: WebhookSubscription, body: bytes) -> tuple[int | None, str | None]:
    signature = sign_payload(sub.secret, body)
    headers = {'Content-Type': 'application/json', SIGNATURE_HEADER: signature}
    status_code: int | None = None
    error: str | None = None
    try:
      response = await self._client.post(sub.url, content=body, headers=headers)
      status_code = response.status_code
      if status_code >= 300:
        error = f'HTTP {status_code}'
        logger.warning('Webhook delivery failed: %s -> %s (%s)', sub.event_type, sub.url, status_code)
    except httpx.HTTPError as exc:
      error = str(exc)
      logger.warning('Webhook delivery error: %s -> %s (%s)', sub.event_type, sub.url, error)
    return status_code, error

  async def _record(
    self,
    *,
    organization_id: str,
    subscription_id: str,
    event_type: str,
    url: str,
    status_code: int | None,
    error: str | None,
  ) -> str:
    from backend.core.utils import new_id

    delivery_id = new_id()
    async with get_session_factory()() as session:
      session.add(
        WebhookDeliveryModel(
          id=delivery_id,
          organization_id=organization_id,
          subscription_id=subscription_id,
          event_type=event_type,
          url=url,
          status_code=status_code,
          error=error,
          delivered_at=utc_now(),
        )
      )
      await session.commit()
    return delivery_id
