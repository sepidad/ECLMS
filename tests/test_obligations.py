"""Tests for the Obligation Tracking module."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta


def _create_contract(client, headers, title='Obligation Test') -> str:
  created = client.post(
    '/api/v1/contracts',
    json={'title': title, 'reference_number': 'OBL-1', 'counterparty': 'ACME'},
    headers=headers,
  )
  return created.json()['data']['id']


def test_create_and_list_obligations(authed_client):
  client, headers = authed_client
  contract_id = _create_contract(client, headers)
  due = (datetime.now(UTC) + timedelta(days=30)).isoformat()

  created = client.post(
    '/api/v1/obligations',
    json={'contract_id': contract_id, 'description': 'Pay initial fee', 'due_date': due},
    headers=headers,
  )
  assert created.status_code == 200, created.text
  body = created.json()
  assert body['success'] is True
  assert body['data']['status'] == 'OPEN'
  assert body['data']['contract_id'] == contract_id
  obligation_id = body['data']['id']

  listed = client.get(f'/api/v1/obligations?contract_id={contract_id}', headers=headers)
  assert listed.json()['success'] is True
  items = listed.json()['data']['items']
  assert len(items) == 1
  assert items[0]['id'] == obligation_id

  fetched = client.get(f'/api/v1/obligations/{obligation_id}', headers=headers)
  assert fetched.json()['data']['description'] == 'Pay initial fee'


def test_complete_obligation(authed_client):
  client, headers = authed_client
  contract_id = _create_contract(client, headers)
  due = (datetime.now(UTC) + timedelta(days=7)).isoformat()
  created = client.post(
    '/api/v1/obligations',
    json={'contract_id': contract_id, 'description': 'Deliver report', 'due_date': due},
    headers=headers,
  )
  obligation_id = created.json()['data']['id']

  completed = client.post(f'/api/v1/obligations/{obligation_id}/complete', headers=headers)
  assert completed.json()['success'] is True
  assert completed.json()['data']['status'] == 'COMPLETED'
  assert completed.json()['data']['completed_at'] is not None


def test_cancel_obligation(authed_client):
  client, headers = authed_client
  contract_id = _create_contract(client, headers)
  due = (datetime.now(UTC) + timedelta(days=7)).isoformat()
  created = client.post(
    '/api/v1/obligations',
    json={'contract_id': contract_id, 'description': 'Optional milestone', 'due_date': due},
    headers=headers,
  )
  obligation_id = created.json()['data']['id']

  cancelled = client.post(f'/api/v1/obligations/{obligation_id}/cancel', headers=headers)
  assert cancelled.json()['success'] is True
  assert cancelled.json()['data']['status'] == 'CANCELLED'


def test_cannot_complete_cancelled(authed_client):
  client, headers = authed_client
  contract_id = _create_contract(client, headers)
  due = (datetime.now(UTC) + timedelta(days=7)).isoformat()
  created = client.post(
    '/api/v1/obligations',
    json={'contract_id': contract_id, 'description': 'X', 'due_date': due},
    headers=headers,
  )
  obligation_id = created.json()['data']['id']
  client.post(f'/api/v1/obligations/{obligation_id}/cancel', headers=headers)

  again = client.post(f'/api/v1/obligations/{obligation_id}/complete', headers=headers)
  assert again.json()['success'] is False
  assert again.json()['error']['code'] == 'INVALID_STATE_TRANSITION'


def test_overdue_sweep(authed_client):
  client, headers = authed_client
  contract_id = _create_contract(client, headers)
  past = (datetime.now(UTC) - timedelta(days=1)).isoformat()
  created = client.post(
    '/api/v1/obligations',
    json={'contract_id': contract_id, 'description': 'Past due item', 'due_date': past},
    headers=headers,
  )
  obligation_id = created.json()['data']['id']
  assert created.json()['data']['status'] == 'OPEN'

  swept = client.post('/api/v1/obligations/sweep-overdue', headers=headers)
  assert swept.json()['success'] is True
  assert swept.json()['data']['overdue'] >= 1

  fetched = client.get(f'/api/v1/obligations/{obligation_id}', headers=headers)
  assert fetched.json()['data']['status'] == 'OVERDUE'


def test_obligation_requires_authentication():
  from fastapi.testclient import TestClient

  from backend.main import app

  with TestClient(app) as client:
    r = client.get('/api/v1/obligations')
    assert r.json()['error']['code'] == 'UNAUTHORIZED'


def test_obligation_viewer_can_read_not_create(authed_client):
  client, admin_headers = authed_client
  client.post(
    '/api/v1/identity/users',
    json={
      'username': 'viewer_obl',
      'email': 'viewer_obl@eclms.local',
      'full_name': 'Viewer Obl',
      'password': 'password123',
      'role': 'VIEWER',
    },
    headers=admin_headers,
  )
  login = client.post(
    '/api/v1/identity/auth/login',
    json={'username': 'viewer_obl', 'password': 'password123'},
  )
  viewer_headers = {'Authorization': f"Bearer {login.json()['data']['access_token']}"}

  contract_id = _create_contract(client, admin_headers)
  due = (datetime.now(UTC) + timedelta(days=7)).isoformat()
  denied = client.post(
    '/api/v1/obligations',
    json={'contract_id': contract_id, 'description': 'Nope', 'due_date': due},
    headers=viewer_headers,
  )
  assert denied.json()['success'] is False
  assert denied.json()['error']['code'] == 'FORBIDDEN'

  # Admin creates one; viewer can list
  client.post(
    '/api/v1/obligations',
    json={'contract_id': contract_id, 'description': 'Visible', 'due_date': due},
    headers=admin_headers,
  )
  listed = client.get(f'/api/v1/obligations?contract_id={contract_id}', headers=viewer_headers)
  assert listed.json()['success'] is True
  assert len(listed.json()['data']['items']) >= 1
