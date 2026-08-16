"""Phase 6 slice 1: template-backed contract preparation."""

import pytest

from backend.modules.contracts.domain.template import get_template, prepare_from_template


def test_prepare_from_template_renders_structured_data_into_content():
  template = get_template('general-service')
  assert template is not None

  content, fields = prepare_from_template(
    template,
    {
      'parties': 'Acme Ltd and Beta GmbH',
      'contract_value': '1,200,000 EUR',
      'start_date': '2026-09-01',
      'end_date': '2027-08-31',
      'insurance_percentage': '10%',
      'payment_terms': 'Milestone-based',
    },
  )

  assert fields['parties'] == 'Acme Ltd and Beta GmbH'
  assert 'SCHEDULE OF COMMERCIAL DATA' in content
  assert 'Parties: Acme Ltd and Beta GmbH' in content
  assert 'GENERAL SERVICE CONTRACT' in content


def test_prepare_from_template_rejects_unknown_fields():
  template = get_template('general-service')
  with pytest.raises(ValueError, match='Unknown template fields'):
    prepare_from_template(template, {'parties': 'Acme', 'not_a_field': 'x'})


def test_prepare_from_template_requires_required_fields():
  template = get_template('general-service')
  with pytest.raises(ValueError, match='Contract value'):
    prepare_from_template(template, {'parties': 'Acme'})


def test_api_creates_contract_from_template(authed_client):
  client, headers = authed_client

  response = client.post(
    '/api/v1/contracts/from-template',
    headers=headers,
    json={
      'template_key': 'procurement',
      'title': 'Server procurement',
      'reference_number': 'PUR-2026-042',
      'counterparty': 'Delta Hardware',
      'field_values': {
        'parties': 'Ministry of Infrastructure and Delta Hardware',
        'contract_value': '450,000 EUR',
        'delivery_date': '2026-12-15',
        'advance_percentage': '20%',
        'insurance_percentage': '5%',
      },
      'tags': ['procurement', 'hardware'],
    },
  )
  assert response.status_code == 200
  body = response.json()
  assert body['success'] is True
  contract_id = body['data']['id']
  assert body['data']['template_key'] == 'procurement'
  assert body['data']['template_fields']['contract_value'] == '450,000 EUR'

  detail = client.get(f'/api/v1/contracts/{contract_id}', headers=headers).json()
  assert detail['success'] is True
  assert detail['data']['template_key'] == 'procurement'
  assert detail['data']['template_fields']['delivery_date'] == '2026-12-15'

  versions = client.get(f'/api/v1/contracts/{contract_id}/versions', headers=headers).json()
  assert versions['success'] is True
  active = next(item for item in versions['data']['items'] if item['is_active'])
  assert 'SCHEDULE OF COMMERCIAL DATA' in (active['content'] or '')
  assert 'Contract value: 450,000 EUR' in (active['content'] or '')


def test_api_rejects_unknown_template(authed_client):
  client, headers = authed_client

  response = client.post(
    '/api/v1/contracts/from-template',
    headers=headers,
    json={
      'template_key': 'does-not-exist',
      'title': 'X',
      'reference_number': 'X-1',
      'counterparty': 'Y',
      'field_values': {},
    },
  )
  assert response.status_code == 200
  body = response.json()
  assert body['success'] is False
  assert 'Unknown contract template' in body['error']['message']


def test_api_rejects_missing_required_fields(authed_client):
  client, headers = authed_client

  response = client.post(
    '/api/v1/contracts/from-template',
    headers=headers,
    json={
      'template_key': 'procurement',
      'title': 'Incomplete procurement',
      'reference_number': 'PUR-2026-043',
      'counterparty': 'Delta Hardware',
      'field_values': {'parties': 'Only parties'},
    },
  )
  assert response.status_code == 200
  body = response.json()
  assert body['success'] is False
  assert 'Delivery date' in body['error']['message']


def _viewer_headers(client):
  client.post(
    '/api/v1/identity/users',
    json={'username': 'alice6', 'email': 'alice6@eclms.local', 'full_name': 'Alice', 'password': 'password123', 'role': 'VIEWER'},
    headers={'Authorization': _admin_token(client)},
  )
  login = client.post('/api/v1/identity/auth/login', json={'username': 'alice6', 'password': 'password123'})
  return {'Authorization': f"Bearer {login.json()['data']['access_token']}"}


def _admin_token(client):
  login = client.post('/api/v1/identity/auth/login', json={'username': 'admin', 'password': 'admin'})
  return f"Bearer {login.json()['data']['access_token']}"


def test_api_from_template_requires_create_permission(authed_client):
  client, _ = authed_client
  viewer = _viewer_headers(client)

  response = client.post(
    '/api/v1/contracts/from-template',
    headers=viewer,
    json={
      'template_key': 'general-service',
      'title': 'X',
      'reference_number': 'X-2',
      'counterparty': 'Y',
      'field_values': {},
    },
  )
  body = response.json()
  assert body['success'] is False
  assert body['error']['code'] != 'OK'
