"""Tests for the Financial Module (commitments + payment schedules)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta


def _create_contract(client, headers, title='Finance Test') -> str:
  created = client.post(
    '/api/v1/contracts',
    json={'title': title, 'reference_number': 'FIN-1', 'counterparty': 'ACME'},
    headers=headers,
  )
  return created.json()['data']['id']


def _create_commitment(client, headers, contract_id, amount=10000.0) -> dict:
  created = client.post(
    '/api/v1/finances/commitments',
    json={
      'contract_id': contract_id,
      'description': 'Total contract value',
      'amount': amount,
      'currency': 'USD',
    },
    headers=headers,
  )
  assert created.status_code == 200, created.text
  return created.json()['data']


def test_create_and_list_commitments(authed_client):
  client, headers = authed_client
  contract_id = _create_contract(client, headers)
  commitment = _create_commitment(client, headers, contract_id)

  assert commitment['status'] == 'OPEN'
  assert commitment['amount'] == 10000.0
  assert commitment['currency'] == 'USD'

  listed = client.get(f'/api/v1/finances/commitments?contract_id={contract_id}', headers=headers)
  assert listed.json()['success'] is True
  items = listed.json()['data']['items']
  assert len(items) == 1
  assert items[0]['id'] == commitment['id']

  all_items = client.get('/api/v1/finances/commitments', headers=headers)
  assert all_items.json()['data']['items'][0]['id'] == commitment['id']


def test_payment_schedule_lifecycle(authed_client):
  client, headers = authed_client
  contract_id = _create_contract(client, headers)
  commitment = _create_commitment(client, headers, contract_id)
  commitment_id = commitment['id']
  due = (datetime.now(UTC) + timedelta(days=30)).isoformat()

  # Create two installments
  p1 = client.post(
    f'/api/v1/finances/commitments/{commitment_id}/payments',
    json={'amount': 4000.0, 'due_date': due},
    headers=headers,
  )
  assert p1.json()['success'] is True
  payment_id = p1.json()['data']['id']
  assert p1.json()['data']['status'] == 'SCHEDULED'

  p2 = client.post(
    f'/api/v1/finances/commitments/{commitment_id}/payments',
    json={'amount': 6000.0, 'due_date': due},
    headers=headers,
  )
  assert p2.json()['success'] is True

  listed = client.get(f'/api/v1/finances/commitments/{commitment_id}/payments', headers=headers)
  assert len(listed.json()['data']['items']) == 2

  # Mark first payment paid
  paid = client.post(f'/api/v1/finances/payments/{payment_id}/pay', headers=headers)
  assert paid.json()['data']['status'] == 'PAID'
  assert paid.json()['data']['paid_at'] is not None


def test_cancel_payment(authed_client):
  client, headers = authed_client
  contract_id = _create_contract(client, headers)
  commitment = _create_commitment(client, headers, contract_id)
  due = (datetime.now(UTC) + timedelta(days=30)).isoformat()
  created = client.post(
    f"/api/v1/finances/commitments/{commitment['id']}/payments",
    json={'amount': 1000.0, 'due_date': due},
    headers=headers,
  )
  payment_id = created.json()['data']['id']

  cancelled = client.post(f'/api/v1/finances/payments/{payment_id}/cancel', headers=headers)
  assert cancelled.json()['data']['status'] == 'CANCELLED'

  # Cannot pay a cancelled payment
  paid = client.post(f'/api/v1/finances/payments/{payment_id}/pay', headers=headers)
  assert paid.json()['success'] is False
  assert paid.json()['error']['code'] == 'INVALID_STATE_TRANSITION'


def test_finance_overdue_sweep(authed_client):
  client, headers = authed_client
  contract_id = _create_contract(client, headers)
  commitment = _create_commitment(client, headers, contract_id)
  past = (datetime.now(UTC) - timedelta(days=1)).isoformat()
  created = client.post(
    f"/api/v1/finances/commitments/{commitment['id']}/payments",
    json={'amount': 5000.0, 'due_date': past},
    headers=headers,
  )
  payment_id = created.json()['data']['id']

  swept = client.post('/api/v1/finances/sweep-overdue', headers=headers)
  assert swept.json()['success'] is True
  assert swept.json()['data']['overdue'] >= 1

  listed = client.get('/api/v1/finances/payments?status=OVERDUE', headers=headers)
  items = listed.json()['data']['items']
  assert any(i['id'] == payment_id for i in items)


def test_finance_requires_authentication():
  from fastapi.testclient import TestClient

  from backend.main import app

  with TestClient(app) as client:
    r = client.get('/api/v1/finances/commitments')
    assert r.json()['error']['code'] == 'UNAUTHORIZED'


def test_viewer_cannot_create_commitment(authed_client):
  client, admin_headers = authed_client
  client.post(
    '/api/v1/identity/users',
    json={
      'username': 'viewer_fin',
      'email': 'viewer_fin@eclms.local',
      'full_name': 'Viewer Fin',
      'password': 'password123',
      'role': 'VIEWER',
    },
    headers=admin_headers,
  )
  login = client.post(
    '/api/v1/identity/auth/login',
    json={'username': 'viewer_fin', 'password': 'password123'},
  )
  viewer_headers = {'Authorization': f"Bearer {login.json()['data']['access_token']}"}

  contract_id = _create_contract(client, admin_headers)
  denied = client.post(
    '/api/v1/finances/commitments',
    json={'contract_id': contract_id, 'description': 'Nope', 'amount': 1.0, 'currency': 'USD'},
    headers=viewer_headers,
  )
  assert denied.json()['error']['code'] == 'FORBIDDEN'

  # Viewer can read after admin creates one
  _create_commitment(client, admin_headers, contract_id)
  listed = client.get(f'/api/v1/finances/commitments?contract_id={contract_id}', headers=viewer_headers)
  assert listed.json()['success'] is True
  assert len(listed.json()['data']['items']) >= 1