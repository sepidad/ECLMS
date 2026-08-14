"""Integration tests exercising the running application through its HTTP API."""

from fastapi.testclient import TestClient

from backend.main import app


def test_health_check():
  with TestClient(app) as client:
    response = client.get('/health')
    assert response.status_code == 200
    body = response.json()
    assert body['status'] == 'ok'
    assert 'identity' in body['modules']
    assert 'contracts' in body['modules']


def test_health_exposes_database_pool_stats():
  with TestClient(app) as client:
    body = client.get('/health').json()
    pool = body.get('database_pool')
    assert pool is not None
    assert set(pool.keys()) == {'checked_out', 'size', 'overflow'}
    assert isinstance(pool['checked_out'], int)
    assert pool['size'] > 0
    assert isinstance(pool['overflow'], int)


def test_login_and_me_flow():
  with TestClient(app) as client:
    login = client.post('/api/v1/identity/auth/login', json={'username': 'admin', 'password': 'admin'})
    assert login.status_code == 200
    body = login.json()
    assert body['success'] is True
    token = body['data']['access_token']
    assert token

    me = client.get('/api/v1/identity/auth/me', headers={'Authorization': f'Bearer {token}'})
    assert me.status_code == 200
    assert me.json()['data']['username'] == 'admin'


def test_login_with_invalid_credentials():
  with TestClient(app) as client:
    response = client.post('/api/v1/identity/auth/login', json={'username': 'admin', 'password': 'wrong'})
    assert response.status_code == 200
    body = response.json()
    assert body['success'] is False
    assert body['error']['code'] == 'UNAUTHORIZED'


def test_contract_lifecycle_via_api(authed_client):
  client, headers = authed_client
  created = client.post(
    '/api/v1/contracts',
    json={'title': 'Rental', 'reference_number': 'R-100', 'counterparty': 'ACME Corp'},
    headers=headers,
  )
  assert created.status_code == 200
  contract_id = created.json()['data']['id']

  submitted = client.post(f'/api/v1/contracts/{contract_id}/transition', json={'new_state': 'SUBMITTED'}, headers=headers)
  assert submitted.json()['data']['state'] == 'SUBMITTED'

  bad = client.post(f'/api/v1/contracts/{contract_id}/transition', json={'new_state': 'ACTIVE'}, headers=headers)
  assert bad.json()['success'] is False
  assert bad.json()['error']['code'] == 'INVALID_STATE_TRANSITION'

  fetched = client.get(f'/api/v1/contracts/{contract_id}', headers=headers)
  assert fetched.json()['data']['reference_number'] == 'R-100'


def test_contracts_require_authentication():
  with TestClient(app) as client:
    created = client.post(
      '/api/v1/contracts',
      json={'title': 'No Auth', 'reference_number': 'NA-1', 'counterparty': 'X'},
    )
    assert created.json()['success'] is False
    assert created.json()['error']['code'] == 'UNAUTHORIZED'


def test_contract_list_pagination(authed_client):
  client, headers = authed_client
  for i in range(3):
    client.post(
      '/api/v1/contracts',
      json={'title': f'Page Test {i}', 'reference_number': f'PT-{i}', 'counterparty': 'ACME'},
      headers=headers,
    )

  res = client.get('/api/v1/contracts?limit=2&offset=0', headers=headers)
  data = res.json()['data']
  assert data['limit'] == 2
  assert data['offset'] == 0
  assert data['total'] >= 3
  assert len(data['items']) == 2

  res2 = client.get('/api/v1/contracts?limit=2&offset=2', headers=headers)
  data2 = res2.json()['data']
  assert len(data2['items']) >= 1


def test_contract_list_limit_clamped(authed_client):
  client, headers = authed_client
  res = client.get('/api/v1/contracts?limit=9999', headers=headers)
  data = res.json()['data']
  assert data['limit'] == 200


def test_running_workflows_are_listed_for_approval_inbox(authed_client):
  client, headers = authed_client
  created = client.post(
    '/api/v1/contracts',
    json={'title': 'Inbox Contract', 'reference_number': 'INBOX-1', 'counterparty': 'ACME'},
    headers=headers,
  )
  contract_id = created.json()['data']['id']
  started = client.post(
    '/api/v1/workflows/start',
    json={'contract_id': contract_id, 'definition_id': 'contract-approval'},
    headers=headers,
  )
  assert started.json()['success'] is True

  response = client.get('/api/v1/workflows?status=RUNNING', headers=headers)
  assert response.status_code == 200
  data = response.json()['data']
  assert any(item['contract_id'] == contract_id for item in data['items'])
  item = next(item for item in data['items'] if item['contract_id'] == contract_id)
  assert item['current_step'] == 'Legal Review'
  assert item['steps'][0]['timeout_hours'] == 24


def test_response_has_trace_id_header():
  with TestClient(app) as client:
    response = client.get('/health')
    assert response.headers.get('X-Trace-Id')


def test_sms_deliveries_requires_auth():
  with TestClient(app) as client:
    res = client.get('/api/v1/notifications/sms/deliveries')
    assert res.json()['success'] is False
    assert res.json()['error']['code'] == 'UNAUTHORIZED'


def test_sms_deliveries_returns_envelope(authed_client):
  client, headers = authed_client
  res = client.get('/api/v1/notifications/sms/deliveries', headers=headers)
  assert res.status_code == 200
  body = res.json()
  assert body['success'] is True
  assert 'items' in body['data']
  assert 'total' in body['data']


def test_import_contracts_requires_auth():
  with TestClient(app) as client:
    res = client.post('/api/v1/import/contracts', content='title,reference_number,counterparty\n')
    assert res.json()['success'] is False
    assert res.json()['error']['code'] == 'UNAUTHORIZED'


def test_import_contracts_csv(authed_client):
  client, headers = authed_client
  csv_text = 'title,reference_number,counterparty\nImported A,IMP-1,ACME\nImported B,IMP-2,Beta'
  res = client.post('/api/v1/import/contracts', content=csv_text, headers={**headers, 'Content-Type': 'text/plain'})
  assert res.status_code == 200
  body = res.json()
  assert body['success'] is True
  assert body['data']['total'] == 2
  assert body['data']['created'] == 2
  assert body['data']['failed'] == 0


def test_import_contracts_empty_body(authed_client):
  client, headers = authed_client
  res = client.post('/api/v1/import/contracts', content='   ', headers={**headers, 'Content-Type': 'text/plain'})
  assert res.json()['success'] is False
  assert res.json()['error']['code'] == 'BAD_REQUEST'


def test_connectors_list_requires_auth():
  with TestClient(app) as client:
    res = client.get('/api/v1/integration/connectors')
    assert res.json()['success'] is False
    assert res.json()['error']['code'] == 'UNAUTHORIZED'


def test_connectors_list_returns_registry(authed_client):
  client, headers = authed_client
  res = client.get('/api/v1/integration/connectors', headers=headers)
  assert res.status_code == 200
  body = res.json()
  assert body['success'] is True
  ids = {c['id'] for c in body['data']['items']}
  assert 'erp' in ids
  assert 'accounting' in ids


def test_connectors_sync_unknown_returns_404(authed_client):
  client, headers = authed_client
  res = client.post('/api/v1/integration/connectors/bogus/sync', headers=headers)
  assert res.json()['success'] is False
  assert res.json()['error']['code'] == 'NOT_FOUND'


def test_audit_csv_export(authed_client):
  client, headers = authed_client
  res = client.get('/api/v1/audit/export.csv', headers=headers)
  assert res.status_code == 200
  assert 'text/csv' in res.headers.get('content-type', '')
  assert 'attachment' in res.headers.get('content-disposition', '')
  body = res.text
  assert 'event_type' in body
  assert 'source_module' in body
