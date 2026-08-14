"""Tests for the ABAC-protected demo contract route (/contracts/{id}/abac-demo).

The demo ABAC policy ('contract-read-owner', registered in CommonModule)
allows the 'contract:read' action only for the contract's owner.  RBAC only
proves the user holds ``contract.read``; the ABAC engine additionally requires
ownership.  So an authenticated VIEWER with read permission is denied, while
the owner (admin) is granted.
"""

from fastapi.testclient import TestClient

from backend.main import app


def _create_contract(client, headers) -> str:
  r = client.post(
    '/api/v1/contracts',
    json={'title': 'ABAC Demo', 'reference_number': 'ABAC-1', 'counterparty': 'ACME'},
    headers=headers,
  )
  assert r.status_code == 200, r.text
  return r.json()['data']['id']


def test_owner_is_granted_by_abac(authed_client):
  client, admin_headers = authed_client
  contract_id = _create_contract(client, admin_headers)

  r = client.get(f'/api/v1/contracts/{contract_id}/abac-demo', headers=admin_headers)
  assert r.status_code == 200, r.text
  body = r.json()
  assert body['success'] is True
  assert body['data']['access'] == 'granted_by_abac'
  assert body['data']['contract']['owner_id']


def test_non_owner_viewer_is_denied_by_abac(authed_client):
  client, admin_headers = authed_client
  contract_id = _create_contract(client, admin_headers)

  # Create a VIEWER user with contract.read (but not owner of the contract).
  create = client.post(
    '/api/v1/identity/users',
    json={'username': 'viewer1', 'email': 'viewer1@eclms.local', 'full_name': 'Viewer One', 'password': 'viewerpass', 'role': 'VIEWER'},
    headers=admin_headers,
  )
  assert create.status_code == 200, create.text

  login = client.post('/api/v1/identity/auth/login', json={'username': 'viewer1', 'password': 'viewerpass'})
  viewer_headers = {'Authorization': f"Bearer {login.json()['data']['access_token']}"}

  # VIEWER passes the RBAC check (has contract.read) but the ABAC policy
  # denies the read because they are not the owner.
  r = client.get(f'/api/v1/contracts/{contract_id}/abac-demo', headers=viewer_headers)
  assert r.status_code == 200, r.text
  body = r.json()
  assert body['success'] is False
  assert body['error']['code'] == 'FORBIDDEN'


def test_abac_demo_requires_authentication():
  with TestClient(app) as client:
    r = client.get('/api/v1/contracts/unknown/abac-demo')
    assert r.json()['error']['code'] == 'UNAUTHORIZED'