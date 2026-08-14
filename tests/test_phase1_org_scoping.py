"""Organization scoping (multi-tenancy, ADR-003) isolation tests.

Every tenant's data is scoped by the authenticated user's organization:
cross-tenant access must be denied (NOT_FOUND) and lists must not leak
rows from other orgs.  Organization is always derived from the JWT/user,
never from the request body.
"""

import asyncio

from backend.core.utils import utc_now
from infrastructure.database.models.identity import OrganizationModel
from infrastructure.database.repositories import SqlUserRepository
from infrastructure.database.seed import assign_role
from infrastructure.database.session import get_session_factory


def await_sync(coro):
  return asyncio.run(coro)


def _seed_org(org_id: str, name: str) -> None:
  async def _run():
    async with get_session_factory()() as session:
      if await session.get(OrganizationModel, org_id) is None:
        session.add(
          OrganizationModel(
            id=org_id,
            name=name,
            org_type='default',
            status='active',
            created_at=utc_now(),
            updated_at=utc_now(),
          )
        )
        await session.commit()

  await_sync(_run())


def _seed_user(username: str, email: str, org_id: str, role: str) -> None:
  from backend.modules.identity.application.auth_service import hash_password
  from backend.modules.identity.domain.user import User

  async def _run():
    repo = SqlUserRepository()
    if await repo.get_by_username(username) is None:
      user = User(
        username=username,
        email=email,
        full_name=username.title(),
        password_hash=hash_password('password123'),
        organization_id=org_id,
      )
      await repo.save(user)
      await assign_role(user.id, role)

  await_sync(_run())


def _headers(client, username: str) -> dict:
  login = client.post('/api/v1/identity/auth/login', json={'username': username, 'password': 'password123'})
  assert login.json()['success'] is True
  return {'Authorization': f"Bearer {login.json()['data']['access_token']}"}


def test_contracts_are_org_scoped(authed_client):
  client, admin_headers = authed_client

  # Seed a second tenant: org-acme + its admin.
  _seed_org('org-acme', 'Acme Corp')
  _seed_user('acme', 'acme@acme.local', 'org-acme', 'ADMIN')
  acme = _headers(client, 'acme')

  # org-default contract owned by the default admin.
  created = client.post(
    '/api/v1/contracts',
    json={'title': 'Tenant A Contract', 'reference_number': 'TA-1', 'counterparty': 'X'},
    headers=admin_headers,
  )
  assert created.json()['success'] is True
  assert created.json()['data']['id']
  contract_id = created.json()['data']['id']

  # The contract is created in the caller's org (org-default), not a body-supplied org.
  detail = client.get(f'/api/v1/contracts/{contract_id}', headers=admin_headers)
  assert detail.json()['data']['organization_id'] == 'org-default'

  # Cross-tenant reads are denied (NOT_FOUND so existence is not leaked).
  denied = client.get(f'/api/v1/contracts/{contract_id}', headers=acme)
  assert denied.json()['success'] is False
  assert denied.json()['error']['code'] == 'NOT_FOUND'

  # Cross-tenant list does not leak other org's contracts.
  listing = client.get('/api/v1/contracts', headers=acme)
  assert listing.json()['success'] is True
  ids = [c['id'] for c in listing.json()['data']['items']]
  assert contract_id not in ids

  # Cross-tenant update and transition are denied.
  patch = client.patch(f'/api/v1/contracts/{contract_id}', json={'title': 'Hijack'}, headers=acme)
  assert patch.json()['error']['code'] == 'NOT_FOUND'
  transition = client.post(f'/api/v1/contracts/{contract_id}/transition', json={'new_state': 'SUBMITTED'}, headers=acme)
  assert transition.json()['error']['code'] == 'NOT_FOUND'

  # Cross-tenant versions listing is denied.
  versions = client.get(f'/api/v1/contracts/{contract_id}/versions', headers=acme)
  assert versions.json()['error']['code'] == 'NOT_FOUND'

  # Acme can create contracts in its own org.
  own = client.post(
    '/api/v1/contracts',
    json={'title': 'Acme Contract', 'reference_number': 'AC-1', 'counterparty': 'Y'},
    headers=acme,
  )
  assert own.json()['success'] is True
  own_detail = client.get(f"/api/v1/contracts/{own.json()['data']['id']}", headers=acme)
  assert own_detail.json()['data']['organization_id'] == 'org-acme'


def test_documents_are_org_scoped(authed_client):
  client, admin_headers = authed_client
  _seed_org('org-acme', 'Acme Corp')
  _seed_user('acme', 'acme@acme.local', 'org-acme', 'ADMIN')
  acme = _headers(client, 'acme')

  created = client.post(
    '/api/v1/contracts',
    json={'title': 'Doc Scope', 'reference_number': 'DS-1', 'counterparty': 'X'},
    headers=admin_headers,
  )
  contract_id = created.json()['data']['id']

  # Upload a doc to the org-default contract as the owner.
  upload = client.post(
    '/api/v1/documents/upload',
    data={'contract_id': contract_id},
    files={'file': ('a.txt', b'hello', 'text/plain')},
    headers=admin_headers,
  )
  assert upload.json()['success'] is True

  # Cross-tenant upload is denied.
  denied = client.post(
    '/api/v1/documents/upload',
    data={'contract_id': contract_id},
    files={'file': ('b.txt', b'evil', 'text/plain')},
    headers=acme,
  )
  assert denied.json()['error']['code'] == 'NOT_FOUND'

  # Cross-tenant document listing is denied.
  listing = client.get(f'/api/v1/documents/contract/{contract_id}', headers=acme)
  assert listing.json()['error']['code'] == 'NOT_FOUND'

  # Same-tenant listing works.
  own_listing = client.get(f'/api/v1/documents/contract/{contract_id}', headers=admin_headers)
  assert own_listing.json()['success'] is True
  assert len(own_listing.json()['data']['items']) == 1


def test_workflows_are_org_scoped(authed_client):
  client, admin_headers = authed_client
  _seed_org('org-acme', 'Acme Corp')
  _seed_user('acme', 'acme@acme.local', 'org-acme', 'ADMIN')
  acme = _headers(client, 'acme')

  created = client.post(
    '/api/v1/contracts',
    json={'title': 'WF Scope', 'reference_number': 'WFS-1', 'counterparty': 'X'},
    headers=admin_headers,
  )
  contract_id = created.json()['data']['id']

  # Cross-tenant workflow start is denied.
  start = client.post('/api/v1/workflows/start', json={'contract_id': contract_id}, headers=acme)
  assert start.json()['error']['code'] == 'NOT_FOUND'

  # Start a workflow in the owner's org, then confirm cross-tenant read/decide denied.
  owner_start = client.post('/api/v1/workflows/start', json={'contract_id': contract_id}, headers=admin_headers)
  assert owner_start.json()['success'] is True
  workflow_id = owner_start.json()['data']['id']

  denied_get = client.get(f'/api/v1/workflows/{workflow_id}', headers=acme)
  assert denied_get.json()['error']['code'] == 'NOT_FOUND'
  denied_history = client.get(f'/api/v1/workflows/{workflow_id}/history', headers=acme)
  assert denied_history.json()['error']['code'] == 'NOT_FOUND'
  denied_decide = client.post(
    f'/api/v1/workflows/{workflow_id}/transition',
    json={'decision': 'APPROVE'},
    headers=acme,
  )
  assert denied_decide.json()['error']['code'] == 'NOT_FOUND'

  # Same-tenant access still works.
  ok = client.get(f'/api/v1/workflows/{workflow_id}', headers=admin_headers)
  assert ok.json()['success'] is True


def test_users_are_org_scoped(authed_client):
  client, admin_headers = authed_client
  _seed_org('org-acme', 'Acme Corp')
  _seed_user('acme', 'acme@acme.local', 'org-acme', 'ADMIN')
  acme = _headers(client, 'acme')

  # A user created via the API lands in the caller's org (org-default).
  created = client.post(
    '/api/v1/identity/users',
    json={'username': 'bob', 'email': 'bob@default.local', 'full_name': 'Bob', 'password': 'password123', 'role': 'VIEWER'},
    headers=admin_headers,
  )
  assert created.json()['success'] is True
  assert created.json()['data']['organization_id'] == 'org-default'

  # Cross-tenant user listing does not leak other org's users.
  admin_listing = client.get('/api/v1/identity/users', headers=admin_headers)
  admin_usernames = {u['username'] for u in admin_listing.json()['data']['items']}
  assert 'acme' not in admin_usernames

  acme_listing = client.get('/api/v1/identity/users', headers=acme)
  acme_usernames = {u['username'] for u in acme_listing.json()['data']['items']}
  assert acme_usernames == {'acme'}
