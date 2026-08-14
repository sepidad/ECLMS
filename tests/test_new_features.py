"""Tests for SMS integration, CSV data import, and external connectors."""

import pytest

from backend.core.events import Event
from backend.modules.data_import.application.import_service import ImportService
from backend.modules.integration.application.sms_service import (
  MockSmsProvider,
  SmsDeliveryService,
)

# ---------- SMS ----------


class SmsSettings:
  sms_enabled = True
  sms_provider = 'mock'
  sms_recipients = '+10000000001,+10000000002'
  sms_http_url = ''
  sms_http_username = ''
  sms_http_password = ''


def _routed_event(org='org-default', actor='u-admin'):
  return Event(
    event_type='workflow.step_escalated',
    source_module='workflow',
    payload={'workflow_id': 'w1', 'contract_id': 'c1', 'step': 'Legal Review', 'escalation_role': 'ADMIN'},
    metadata={'organization_id': org, 'actor_id': actor},
  )


@pytest.mark.anyio
async def test_sms_service_dispatches_to_configured_recipients():
  sent = []

  class Recording(MockSmsProvider):
    async def send(self, *, to, body):
      sent.append((to, body))

  service = SmsDeliveryService(SmsSettings(), provider=Recording())
  recorded = []

  async def fake_record(**kwargs):
    recorded.append(kwargs)
    return 's1'

  service._record = fake_record
  await service.handle_event(_routed_event())

  assert len(sent) == 2
  assert sent[0][0] == '+10000000001'
  assert sent[1][0] == '+10000000002'
  assert len(recorded) == 2
  assert all(r['success'] is True for r in recorded)
  assert all(r['error'] is None for r in recorded)


@pytest.mark.anyio
async def test_sms_service_uses_explicit_phone_when_present():
  sent = []

  class Recording(MockSmsProvider):
    async def send(self, *, to, body):
      sent.append(to)

  service = SmsDeliveryService(SmsSettings(), provider=Recording())

  async def fake_record(**kwargs):
    return 's1'

  service._record = fake_record
  event = _routed_event()
  event.payload['phone'] = '+19999999999'
  await service.handle_event(event)
  assert sent == ['+19999999999']


@pytest.mark.anyio
async def test_sms_service_disabled():
  settings = SmsSettings()
  settings.sms_enabled = False
  sent = []

  class Recording(MockSmsProvider):
    async def send(self, *, to, body):
      sent.append(to)

  service = SmsDeliveryService(settings, provider=Recording())

  async def fake_record(**kwargs):
    return 's1'

  service._record = fake_record
  await service.handle_event(_routed_event())
  assert sent == []


@pytest.mark.anyio
async def test_sms_service_records_failure():
  class Boom(MockSmsProvider):
    async def send(self, *, to, body):
      raise RuntimeError('gateway down')

  service = SmsDeliveryService(SmsSettings(), provider=Boom())
  recorded = {}

  async def fake_record(**kwargs):
    recorded.update(kwargs)
    return 's1'

  service._record = fake_record
  result = await service.send_sms(
    to='+10000000001',
    body='hello',
    organization_id='org-default',
    event_type='manual',
  )
  assert result['success'] is False
  assert 'gateway down' in result['error']
  assert recorded['success'] is False
  assert 'gateway down' in recorded['error']


@pytest.mark.anyio
async def test_sms_service_skips_unrouted_event():
  sent = []

  class Recording(MockSmsProvider):
    async def send(self, *, to, body):
      sent.append(to)

  service = SmsDeliveryService(SmsSettings(), provider=Recording())

  async def fake_record(**kwargs):
    return 's1'

  service._record = fake_record
  event = Event(
    event_type='some.unknown.event',
    source_module='workflow',
    payload={'workflow_id': 'w1'},
    metadata={'organization_id': 'org-default', 'actor_id': 'u-admin'},
  )
  await service.handle_event(event)
  assert sent == []


# ---------- Import (unit, no DB) ----------


class FakeEntity:
  def __init__(self, entity_id):
    self.id = entity_id


class FakeContracts:
  def __init__(self):
    self.calls = []

  async def create_contract(self, **kwargs):
    self.calls.append(kwargs)
    return FakeEntity(f'c{len(self.calls)}')


class FakeObligations:
  def __init__(self, contracts):
    self.calls = []
    self._contracts = contracts

  async def create(self, **kwargs):
    await self._contracts.get_contract(kwargs['contract_id'], organization_id=kwargs['organization_id'])
    self.calls.append(kwargs)
    return FakeEntity(f'o{len(self.calls)}')

  async def get_contract(self, contract_id, *, organization_id):
    return FakeEntity(contract_id)


class FakeFinances:
  def __init__(self, contracts):
    self.calls = []
    self._contracts = contracts

  async def create_commitment(self, **kwargs):
    await self._contracts.get_contract(kwargs['contract_id'], organization_id=kwargs['organization_id'])
    self.calls.append(kwargs)
    return FakeEntity(f'f{len(self.calls)}')

  async def get_contract(self, contract_id, *, organization_id):
    return FakeEntity(contract_id)


class FakeContractGateway:
  async def get_contract(self, contract_id, *, organization_id):
    return FakeEntity(contract_id)


@pytest.mark.anyio
async def test_import_contracts_parses_csv_and_creates():
  contracts = FakeContracts()
  service = ImportService(contracts, FakeObligations(contracts), FakeFinances(contracts))
  csv_text = 'title,reference_number,counterparty\nFoo,C-1,ACME\nBar,C-2,Bexar'
  result = await service.import_contracts(csv_text=csv_text, organization_id='org-default', actor_id='u1')
  assert result['total'] == 2
  assert result['created'] == 2
  assert result['failed'] == 0
  assert [item['id'] for item in result['created_items']] == ['c1', 'c2']
  assert contracts.calls[0]['title'] == 'Foo'
  assert contracts.calls[0]['owner_id'] == 'u1'


@pytest.mark.anyio
async def test_import_contracts_reports_row_failures():
  contracts = FakeContracts()
  service = ImportService(contracts, FakeObligations(contracts), FakeFinances(contracts))
  csv_text = 'title,reference_number,counterparty\n,C-1,ACME\nBar,,Bexar'
  result = await service.import_contracts(csv_text=csv_text, organization_id='org-default', actor_id='u1')
  assert result['total'] == 2
  assert result['created'] == 0
  assert result['failed'] == 2
  assert 'title' in result['failed_items'][0]['reason'] or 'reference_number' in result['failed_items'][0]['reason']


@pytest.mark.anyio
async def test_import_commitments_parses_amount_and_currency():
  gateway = FakeContractGateway()

  class Contracts:
    async def create_contract(self, **kwargs):
      return FakeEntity('cx')

  class Obss:
    async def create(self, **kwargs):
      return FakeEntity('ox')

  fin = FakeFinances(gateway)
  service = ImportService(Contracts(), Obss(), fin)
  csv_text = 'contract_reference,description,amount,currency\nc1,First tranche,1500.50,EUR'
  result = await service.import_commitments(csv_text=csv_text, organization_id='org-default', actor_id='u1')
  assert result['created'] == 1
  assert fin.calls[0]['amount'] == 1500.5
  assert fin.calls[0]['currency'] == 'EUR'


@pytest.mark.anyio
async def test_import_commitments_invalid_amount_reports_failure():
  gateway = FakeContractGateway()

  class Contracts:
    async def create_contract(self, **kwargs):
      return FakeEntity('cx')

  class Obss:
    async def create(self, **kwargs):
      return FakeEntity('ox')

  fin = FakeFinances(gateway)
  service = ImportService(Contracts(), Obss(), fin)
  csv_text = 'contract_reference,description,amount,currency\nc1,First tranche,not-a-number,USD'
  result = await service.import_commitments(csv_text=csv_text, organization_id='org-default', actor_id='u1')
  assert result['failed'] == 1
  assert 'amount' in result['failed_items'][0]['reason']


@pytest.mark.anyio
async def test_import_empty_csv_returns_zero_totals():
  contracts = FakeContracts()
  service = ImportService(contracts, FakeObligations(contracts), FakeFinances(contracts))
  csv_text = 'title,reference_number,counterparty\n'
  result = await service.import_contracts(csv_text=csv_text, organization_id='org-default', actor_id='u1')
  assert result['total'] == 0
  assert result['created'] == 0
  assert result['failed'] == 0


# ---------- Connectors ----------


class ConnectorSettings:
  erp_endpoint = ''
  accounting_endpoint = ''


class HttpConnectorSettings:
  erp_endpoint = 'http://example.local/erp'
  accounting_endpoint = 'http://example.local/acct'


class FakeResponse:
  status_code = 200

  def raise_for_status(self):
    return None


class FakeHttp:
  def __init__(self):
    self.posted = []

  async def post(self, url, json=None, auth=None):
    self.posted.append((url, json))
    return FakeResponse()


@pytest.mark.anyio
async def test_connector_dry_run_when_no_endpoint():
  from backend.modules.integration.application.connector_service import ConnectorService

  service = ConnectorService(ConnectorSettings())

  async def fake_record(**kwargs):
    return 'x'

  service._record_sync = fake_record
  result = await service.sync('erp', organization_id='org-default')
  assert result['dry_run'] is True
  assert result['sent'] == 0


@pytest.mark.anyio
async def test_connector_sync_posts_when_endpoint_configured():
  from backend.modules.integration.application.connector_service import ConnectorService, ErpConnector

  http = FakeHttp()
  connectors = [ErpConnector(client=http)]
  service = ConnectorService(HttpConnectorSettings(), connectors=connectors)

  async def fake_record(**kwargs):
    return 'x'

  service._record_sync = fake_record
  result = await service.sync('erp', organization_id='org-default')
  assert result['dry_run'] is False
  assert result['sent'] == 1
  assert http.posted[0][0] == 'http://example.local/erp'


def test_connector_list_reports_configuration_state():
  from backend.modules.integration.application.connector_service import ConnectorService

  service = ConnectorService(HttpConnectorSettings())
  listing = service.list_connectors()
  assert len(listing) == 2
  by_id = {c['id']: c for c in listing}
  assert by_id['erp']['configured'] is True
  assert by_id['accounting']['configured'] is True
  assert by_id['erp']['endpoint'] == 'http://example.local/erp'


def test_connector_list_reports_unconfigured():
  from backend.modules.integration.application.connector_service import ConnectorService

  service = ConnectorService(ConnectorSettings())
  listing = service.list_connectors()
  assert all(c['configured'] is False for c in listing)