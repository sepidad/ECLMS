"""Tests for the integration module (webhook delivery)."""

import pytest

from backend.core.events import Event
from backend.modules.integration.application.webhook_service import sign_payload
from backend.modules.notifications.application.notification_service import (
  NotificationRepository,
  WebhookSubscription,
)


class FakeClient:
  """HTTP client double recording calls and forcing outcomes."""

  def __init__(self, status=200, raises=None) -> None:
    self.calls: list[tuple[str, bytes, dict]] = []
    self.status = status
    self.raises = raises
    self.raise_count = 0
    self.status_sequence: list[int] | None = None
    self._index = 0

  async def post(self, url, *, content, headers):
    if self.raises:
      self.raise_count += 1
      raise self.raises
    if self.status_sequence is not None:
      status = self.status_sequence[min(self._index, len(self.status_sequence) - 1)]
      self._index += 1
    else:
      status = self.status
    self.calls.append((url, content, headers))
    return _FakeResponse(status)


class _FakeResponse:
  def __init__(self, status: int) -> None:
    self.status_code = status


class _FakeRepo(NotificationRepository):
  def __init__(self, subscriptions: list[WebhookSubscription]) -> None:
    self.subscriptions = subscriptions

  async def list_active_for_event(self, organization_id: str, event_type: str) -> list[WebhookSubscription]:
    return [
      s
      for s in self.subscriptions
      if s.organization_id == organization_id and s.event_type in (event_type, '*')
    ]


def _sub(org='org-1', event_type='contract.state_changed', url='https://hooks.example.com/eclms'):
  return WebhookSubscription(organization_id=org, url=url, event_type=event_type, secret='supersecret', subscription_id='sub-1')


def _event(event_type='contract.state_changed', org='org-1') -> Event:
  return Event(
    event_type=event_type,
    source_module='contracts',
    payload={'contract_id': 'c1', 'from': 'DRAFT', 'to': 'SUBMITTED'},
    metadata={'organization_id': org, 'entity_type': 'contract'},
  )


@pytest.mark.asyncio
async def test_sign_payload_is_stable_hmac_sha256():
  a = sign_payload('secret', b'hello')
  b = sign_payload('secret', b'hello')
  c = sign_payload('secret', b'hello!')
  assert a == b
  assert a != c
  assert len(a) == 64


@pytest.mark.asyncio
async def test_delivers_to_matching_subscription():
  from backend.modules.integration.application.webhook_service import WebhookDeliveryService

  client = FakeClient()
  repo = _FakeRepo([_sub()])
  service = WebhookDeliveryService(repo, http_client=client)

  # Avoid DB writes in this unit test.
  async def noop_record(**kwargs):
    return None

  service._record = noop_record
  await service.handle_event(_event())

  assert len(client.calls) == 1
  url, body, headers = client.calls[0]
  assert url == 'https://hooks.example.com/eclms'
  assert 'X-ECLMS-Signature' in headers
  assert headers['X-ECLMS-Signature'] == sign_payload('supersecret', body)
  assert 'contract.state_changed' in body.decode()


@pytest.mark.asyncio
async def test_wildcard_subscription_matches_any_event():
  from backend.modules.integration.application.webhook_service import WebhookDeliveryService

  client = FakeClient()
  repo = _FakeRepo([_sub(event_type='*')])
  service = WebhookDeliveryService(repo, http_client=client)

  async def noop_record(**kwargs):
    return None

  service._record = noop_record
  await service.handle_event(_event(event_type='document.uploaded'))

  assert len(client.calls) == 1
  assert 'document.uploaded' in client.calls[0][1].decode()


@pytest.mark.asyncio
async def test_event_without_org_is_ignored():
  from backend.modules.integration.application.webhook_service import WebhookDeliveryService

  client = FakeClient()
  repo = _FakeRepo([_sub()])
  service = WebhookDeliveryService(repo, http_client=client)
  await service.handle_event(_event(org=None))
  assert client.calls == []


@pytest.mark.asyncio
async def test_delivery_failure_is_recorded_not_raised():
  import httpx

  from backend.modules.integration.application.webhook_service import WebhookDeliveryService

  client = FakeClient(raises=httpx.ConnectError('no route to host'))
  repo = _FakeRepo([_sub()])
  service = WebhookDeliveryService(repo, http_client=client, max_attempts=1)
  recorded = {}

  async def fake_record(**kwargs):
    recorded.update(kwargs)
    return 'd1'

  service._record = fake_record
  await service.handle_event(_event())

  assert recorded['error'] == 'no route to host'
  assert recorded['status_code'] is None


@pytest.mark.asyncio
async def test_http_error_status_is_recorded():
  from backend.modules.integration.application.webhook_service import WebhookDeliveryService

  client = FakeClient(status=500)
  repo = _FakeRepo([_sub()])
  service = WebhookDeliveryService(repo, http_client=client, max_attempts=1)
  recorded = {}

  async def fake_record(**kwargs):
    recorded.update(kwargs)
    return 'd1'

  service._record = fake_record
  await service.handle_event(_event())

  assert recorded['status_code'] == 500
  assert recorded['error'] == 'HTTP 500'


@pytest.mark.asyncio
async def test_disabled_service_skips_delivery():
  from backend.modules.integration.application.webhook_service import WebhookDeliveryService

  client = FakeClient()
  repo = _FakeRepo([_sub()])
  service = WebhookDeliveryService(repo, http_client=client, enabled=False)
  await service.handle_event(_event())
  assert client.calls == []


@pytest.mark.asyncio
async def test_retries_transient_500_until_success():
  from backend.modules.integration.application.webhook_service import WebhookDeliveryService

  client = FakeClient()
  client.status_sequence = [500, 500, 200]
  repo = _FakeRepo([_sub()])
  service = WebhookDeliveryService(repo, http_client=client, max_attempts=3, backoff_base_seconds=0.0)
  recorded = {}

  async def fake_record(**kwargs):
    recorded.update(kwargs)
    return 'd1'

  service._record = fake_record
  await service.handle_event(_event())

  assert len(client.calls) == 3
  assert recorded['status_code'] == 200
  assert recorded['error'] is None


@pytest.mark.asyncio
async def test_network_error_retries_then_records_last_error():
  import httpx

  from backend.modules.integration.application.webhook_service import WebhookDeliveryService

  client = FakeClient(raises=httpx.ConnectError('timeout'))
  repo = _FakeRepo([_sub()])
  service = WebhookDeliveryService(repo, http_client=client, max_attempts=3, backoff_base_seconds=0.0)
  recorded = {}

  async def fake_record(**kwargs):
    recorded.update(kwargs)
    return 'd1'

  service._record = fake_record
  await service.handle_event(_event())

  assert client.raise_count == 3
  assert recorded['error'] == 'timeout'
  assert recorded['status_code'] is None


@pytest.mark.asyncio
async def test_non_retryable_status_no_retry():
  from backend.modules.integration.application.webhook_service import WebhookDeliveryService

  client = FakeClient()
  client.status_sequence = [400, 200]
  repo = _FakeRepo([_sub()])
  service = WebhookDeliveryService(repo, http_client=client, max_attempts=3, backoff_base_seconds=0.0)
  recorded = {}

  async def fake_record(**kwargs):
    recorded.update(kwargs)
    return 'd1'

  service._record = fake_record
  await service.handle_event(_event())

  assert len(client.calls) == 1
  assert recorded['status_code'] == 400
