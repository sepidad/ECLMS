"""Tests for SMTP email integration service."""

import pytest

from backend.core.events import Event
from backend.modules.integration.application.email_service import EMAIL_ROUTES, EmailDeliveryService


class MockSettings:
  email_enabled = True
  smtp_host = 'localhost'
  smtp_port = 587
  smtp_user = ''
  smtp_password = ''
  smtp_from = 'eclms@eclms.local'


class FakeUser:
  def __init__(self, user_id, email, organization_id='org-default', roles=None):
    self.id = user_id
    self.email = email
    self.organization_id = organization_id
    self.roles = roles or []


class FakeUserRepository:
  def __init__(self, users: list[FakeUser]):
    self._users = users
    self._by_id = {u.id: u for u in users}

  async def list_by_role_in_org(self, organization_id: str, role: str):
    return [u for u in self._users if u.organization_id == organization_id and role in u.roles]

  async def get_by_id(self, user_id: str):
    return self._by_id.get(user_id)


def _admin_event(event_type='workflow.step_escalated', org='org-default', actor='u-admin'):
  return Event(
    event_type=event_type,
    source_module='workflow',
    payload={'workflow_id': 'w1', 'contract_id': 'c1', 'step': 'Legal Review', 'escalation_role': 'ADMIN'},
    metadata={'organization_id': org, 'actor_id': actor},
  )


@pytest.mark.anyio
async def test_email_service_sends_to_role_audience():
  users = [
    FakeUser('u-admin', 'admin@eclms.local', roles=['ADMIN']),
    FakeUser('u-manager', 'manager@eclms.local', roles=['CONTRACT_MANAGER']),
  ]
  settings = MockSettings()
  service = EmailDeliveryService(settings, user_repository=FakeUserRepository(users))
  sent = []

  async def fake_record(**kwargs):
    sent.append(kwargs)
    return 'e1'

  service._record = fake_record

  await service.handle_event(_admin_event())

  assert len(sent) == 1
  assert sent[0]['recipient_email'] == 'admin@eclms.local'
  assert sent[0]['recipient_id'] == 'u-admin'
  assert sent[0]['success'] is True
  assert '[ECLMS] Workflow Step Escalated' in sent[0]['subject']


@pytest.mark.anyio
async def test_email_service_skips_unrouted_event():
  settings = MockSettings()
  service = EmailDeliveryService(settings, user_repository=FakeUserRepository([]))
  sent = []

  async def fake_record(**kwargs):
    sent.append(kwargs)
    return 'e1'

  service._record = fake_record

  await service.handle_event(_admin_event(event_type='some.unknown.event'))
  assert sent == []


@pytest.mark.anyio
async def test_email_service_disabled():
  settings = MockSettings()
  settings.email_enabled = False
  service = EmailDeliveryService(settings, user_repository=FakeUserRepository([]))
  sent = []

  async def fake_record(**kwargs):
    sent.append(kwargs)
    return 'e1'

  service._record = fake_record

  await service.handle_event(_admin_event())
  assert sent == []


@pytest.mark.anyio
async def test_email_service_records_failure():
  settings = MockSettings()
  service = EmailDeliveryService(settings, user_repository=FakeUserRepository([]))
  recorded = {}

  async def fake_record(**kwargs):
    recorded.update(kwargs)
    return 'e1'

  service._record = fake_record

  # Force SMTP failure (non-localhost host with no server running).
  settings.smtp_host = '127.0.0.1'
  settings.smtp_port = 1

  result = await service.send_email(
    to='admin@eclms.local',
    subject='Boom',
    body='x',
    organization_id='org-default',
    recipient_id='u-admin',
    event_type='workflow.step_escalated',
  )

  assert result['success'] is False
  assert result['error']
  assert recorded['success'] is False
  assert recorded['error'] == result['error']


@pytest.mark.anyio
async def test_email_routes_exist_for_routed_events():
  assert 'workflow.step_escalated' in EMAIL_ROUTES
  assert 'contract.created' in EMAIL_ROUTES
  assert 'finance.payment_overdue' in EMAIL_ROUTES
