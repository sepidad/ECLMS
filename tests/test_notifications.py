"""Tests for the notifications and webhooks module."""

import pytest

from backend.core.events import Event


def test_notifications_and_webhooks(authed_client):
  client, admin_headers = authed_client

  # List notifications (empty initially)
  res = client.get('/api/v1/notifications', headers=admin_headers)
  assert res.json()['success'] is True
  assert res.json()['data']['items'] == []

  # Subscribe webhook
  sub = client.post(
    '/api/v1/notifications/webhooks',
    json={'url': 'https://example.com/hook', 'event_type': 'contract.state_changed', 'secret': 'supersecret'},
    headers=admin_headers,
  )
  assert sub.json()['success'] is True
  assert sub.json()['data']['url'] == 'https://example.com/hook'

  # List webhooks
  subs = client.get('/api/v1/notifications/webhooks', headers=admin_headers)
  assert subs.json()['success'] is True
  assert len(subs.json()['data']['items']) == 1


@pytest.mark.asyncio
async def test_handle_event_creates_in_app_notification_for_routed_event(authed_client, monkeypatch):
  """A routed domain event produces an in-app notification for the audience."""
  from backend.core.events import EventBus
  from backend.modules.notifications.application.notification_service import (
    NotificationRepository,
    NotificationService,
  )
  from infrastructure.database.repositories import SqlUserRepository

  # Resolve the admin user id from the live database (seeded by the app).
  users = SqlUserRepository()
  admin = await users.get_by_username('admin')
  assert admin is not None

  class _Repo(NotificationRepository):
    def __init__(self):
      self.created: list = []

    async def create_notification(self, notification):
      self.created.append(notification)
      return notification

  service = NotificationService(_Repo(), user_repository=users)
  bus = EventBus()
  bus.subscribe_all(service.handle_event)

  await bus.publish(
    Event(
      event_type='contract.created',
      source_module='contracts',
      payload={'contract_id': 'c-123', 'reference_number': 'REF-1'},
      metadata={'organization_id': admin.organization_id, 'actor_id': admin.id},
    )
  )

  repo = service._repository
  assert repo.created, 'expected at least one notification'
  subjects = {n.subject for n in repo.created}
  assert 'Contract Created' in subjects


@pytest.mark.asyncio
async def test_handle_event_skips_unrouted_events():
  from backend.modules.notifications.application.notification_service import (
    NotificationRepository,
    NotificationService,
  )

  class _Repo(NotificationRepository):
    def __init__(self):
      self.created: list = []

    async def create_notification(self, notification):
      self.created.append(notification)
      return notification

  repo = _Repo()
  service = NotificationService(repo)

  await service.handle_event(
    Event(event_type='some.unknown.event', source_module='x', payload={}, metadata={'organization_id': 'org-1'})
  )
  assert repo.created == []


def test_webhook_deliveries_endpoint(authed_client, monkeypatch):
  """Delivery history for a webhook is visible, including failure status."""
  client, admin_headers = authed_client

  # Subscribe a webhook, then force a delivery record to exist.
  sub = client.post(
    '/api/v1/notifications/webhooks',
    json={'url': 'https://example.com/hook', 'event_type': 'contract.created', 'secret': 'supersecret'},
    headers=admin_headers,
  ).json()
  assert sub['success'] is True
  webhook_id = sub['data']['id']
  url = sub['data']['url']

  import asyncio

  from backend.modules.integration.application.webhook_service import WebhookDeliveryService
  from backend.modules.notifications.application.notification_service import (
    NotificationRepository,
  )

  class FakeClient:
    async def post(self, url, **kwargs):
      return type('R', (), {'status_code': 500})()

  async def _deliver():
    repo = NotificationRepository()
    svc = WebhookDeliveryService(repo, http_client=FakeClient(), max_attempts=1)
    await svc._record(
      organization_id='org-default',
      subscription_id=webhook_id,
      event_type='contract.created',
      url=url,
      status_code=500,
      error='HTTP 500',
    )

  asyncio.new_event_loop().run_until_complete(_deliver())

  res = client.get(f'/api/v1/notifications/webhooks/{webhook_id}/deliveries', headers=admin_headers)
  data = res.json()['data']
  assert res.json()['success'] is True
  assert data['total'] == 1
  assert data['failed'] == 1
  assert data['succeeded'] == 0
  assert data['items'][0]['status_code'] == 500
  assert data['items'][0]['error'] == 'HTTP 500'

  # Unknown subscription -> not found envelope
  missing = client.get('/api/v1/notifications/webhooks/nope/deliveries', headers=admin_headers)
  assert missing.json()['success'] is False


def test_event_fires_notification_and_mark_all_read(authed_client):
  """Creating a contract fires a domain event that produces an in-app
  notification for the actor, then read-all clears the unread badge."""
  client, admin_headers = authed_client

  created = client.post(
    '/api/v1/contracts',
    json={'title': 'Route Test Contract', 'reference_number': 'RT-1', 'counterparty': 'Acme'},
    headers=admin_headers,
  )
  assert created.json()['success'] is True
  contract_id = created.json()['data']['id']

  # The contract.created event should have produced an in-app notification
  # addressed to the admin actor.
  res = client.get('/api/v1/notifications', headers=admin_headers)
  data = res.json()['data']
  assert data['unread_count'] >= 1
  assert any(n['subject'] == 'Contract Created' for n in data['items'])
  assert any(contract_id in n['body'] for n in data['items'])

  ra = client.post('/api/v1/notifications/read-all', headers=admin_headers)
  assert ra.json()['success'] is True
  assert ra.json()['data']['marked'] == data['unread_count']

  res2 = client.get('/api/v1/notifications', headers=admin_headers)
  assert res2.json()['data']['unread_count'] == 0
  assert all(item['is_read'] for item in res2.json()['data']['items'])


def test_email_deliveries_endpoint(authed_client, monkeypatch):
  """Email delivery history is visible with status counts."""
  import asyncio

  from backend.modules.integration.application.email_service import EmailDeliveryService

  client, admin_headers = authed_client

  class _Settings:
    email_enabled = True
    smtp_host = 'localhost'
    smtp_port = 587
    smtp_user = ''
    smtp_password = ''
    smtp_from = 'eclms@eclms.local'

  async def _record():
    svc = EmailDeliveryService(_Settings())
    await svc._record(
      organization_id='org-default',
      recipient_id='u-admin',
      recipient_email='admin@eclms.local',
      event_type='contract.created',
      subject='[ECLMS] Contract Created',
      body='Contract c-1 created.',
      success=False,
      error='Connection refused',
    )

  asyncio.new_event_loop().run_until_complete(_record())

  res = client.get('/api/v1/notifications/email/deliveries', headers=admin_headers)
  data = res.json()['data']
  assert res.json()['success'] is True
  assert data['total'] == 1
  assert data['failed'] == 1
  assert data['sent'] == 0
  assert data['items'][0]['recipient_email'] == 'admin@eclms.local'
  assert data['items'][0]['status'] == 'failed'
  assert data['items'][0]['error'] == 'Connection refused'

  # limit/offset paging
  paged = client.get('/api/v1/notifications/email/deliveries?limit=1&offset=1', headers=admin_headers)
  assert paged.json()['success'] is True
  assert paged.json()['data']['total'] == 1
  assert paged.json()['data']['items'] == []
