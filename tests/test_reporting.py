"""Tests for the Analytics & Reporting module (Phase 4, read-only)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta


def _create_contract(client, headers, title='Report Test'):
  created = client.post(
    '/api/v1/contracts',
    json={'title': title, 'reference_number': 'RPT-1', 'counterparty': 'ACME'},
    headers=headers,
  )
  assert created.status_code == 200, created.text
  return created.json()['data']['id']


def _transition(client, headers, contract_id, to):
  r = client.post(
    f'/api/v1/contracts/{contract_id}/transition',
    json={'new_state': to},
    headers=headers,
  )
  assert r.status_code == 200 and r.json()['success'] is True, r.text


def test_reporting_requires_permission(authed_client):
  client, headers = authed_client
  r = client.get('/api/v1/reporting/overview', headers=headers)
  assert r.status_code == 200, r.text
  body = r.json()
  assert body['success'] is True
  assert set(body['data'].keys()) == {'contracts', 'workflows', 'obligations', 'finances'}


def test_reporting_requires_authentication():
  from fastapi.testclient import TestClient

  from backend.main import app

  with TestClient(app) as client:
    r = client.get('/api/v1/reporting/overview')
    assert r.json()['error']['code'] == 'UNAUTHORIZED'


def test_contract_analytics(authed_client):
  client, headers = authed_client
  c1 = _create_contract(client, headers, 'Active One')
  _create_contract(client, headers, 'Draft Two')

  # Drive c1 to ACTIVE, leave c2 as DRAFT.
  for s in ['SUBMITTED', 'UNDER_REVIEW', 'APPROVED', 'EXECUTED', 'ACTIVE']:
    _transition(client, headers, c1, s)

  r = client.get('/api/v1/reporting/overview', headers=headers)
  contracts = r.json()['data']['contracts']
  assert contracts['total_contracts'] == 2
  assert contracts['by_state']['ACTIVE'] == 1
  assert contracts['by_state']['DRAFT'] == 1
  assert contracts['active'] == 1


def test_finance_analytics(authed_client):
  client, headers = authed_client
  contract_id = _create_contract(client, headers, 'Finance Report')

  c = client.post(
    '/api/v1/finances/commitments',
    json={'contract_id': contract_id, 'description': 'Value', 'amount': 10000.0, 'currency': 'USD'},
    headers=headers,
  )
  commitment_id = c.json()['data']['id']

  due = (datetime.now(UTC) + timedelta(days=30)).isoformat()
  p = client.post(
    f'/api/v1/finances/commitments/{commitment_id}/payments',
    json={'amount': 10000.0, 'due_date': due},
    headers=headers,
  )
  payment_id = p.json()['data']['id']

  r = client.get('/api/v1/reporting/overview', headers=headers)
  finance = r.json()['data']['finances']
  assert finance['total_payments'] == 1
  assert finance['paid'] == 0.0
  assert finance['payment_completion_rate'] == 0.0

  client.post(f'/api/v1/finances/payments/{payment_id}/pay', headers=headers)
  r = client.get('/api/v1/reporting/overview', headers=headers)
  finance = r.json()['data']['finances']
  assert finance['paid'] == 10000.0
  assert finance['payment_completion_rate'] == 1.0


def test_obligation_analytics(authed_client):
  client, headers = authed_client
  contract_id = _create_contract(client, headers, 'Obligation Report')
  due = (datetime.now(UTC) + timedelta(days=7)).isoformat()

  created = client.post(
    '/api/v1/obligations',
    json={'contract_id': contract_id, 'description': 'Deliver', 'due_date': due},
    headers=headers,
  )
  obligation_id = created.json()['data']['id']

  r = client.get('/api/v1/reporting/overview', headers=headers)
  obligations = r.json()['data']['obligations']
  assert obligations['total_obligations'] == 1

  client.post(f'/api/v1/obligations/{obligation_id}/complete', headers=headers)
  r = client.get('/api/v1/reporting/overview', headers=headers)
  obligations = r.json()['data']['obligations']
  assert obligations['by_status']['COMPLETED'] == 1
  assert obligations['sla_compliance_rate'] == 1.0


def test_report_is_org_scoped(authed_client):
  client, headers = authed_client
  _create_contract(client, headers, 'Org Scoped')

  r = client.get('/api/v1/reporting/overview', headers=headers)
  assert r.json()['data']['contracts']['total_contracts'] == 1


def test_portfolio_trends_return_fixed_month_buckets(authed_client):
  client, headers = authed_client
  contract_id = _create_contract(client, headers, 'Trend Contract')
  due = (datetime.now(UTC) + timedelta(days=1)).isoformat()
  commitment = client.post(
    '/api/v1/finances/commitments',
    json={'contract_id': contract_id, 'description': 'Trend value', 'amount': 250.0, 'currency': 'USD'},
    headers=headers,
  )
  client.post(
    f"/api/v1/finances/commitments/{commitment.json()['data']['id']}/payments",
    json={'amount': 250.0, 'due_date': due},
    headers=headers,
  )

  response = client.get('/api/v1/reporting/trends?months=6', headers=headers)
  assert response.status_code == 200, response.text
  buckets = response.json()['data']['months']
  assert len(buckets) == 6
  assert all(set(bucket) == {
    'month', 'contracts_created', 'payments_scheduled', 'payments_paid', 'obligations_due'
  } for bucket in buckets)
  assert sum(bucket['contracts_created'] for bucket in buckets) == 1
  assert sum(bucket['payments_scheduled'] for bucket in buckets) == 250.0
