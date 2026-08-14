"""Phase 1 RBAC / user management tests."""

from fastapi.testclient import TestClient

from backend.main import app


def _admin_token(client) -> str:
  login = client.post('/api/v1/identity/auth/login', json={'username': 'admin', 'password': 'admin'})
  assert login.json()['success'] is True
  return login.json()['data']['access_token']


def test_create_user_requires_permission():
  with TestClient(app) as client:
    unauth = client.post(
      '/api/v1/identity/users',
      json={'username': 'alice', 'email': 'alice@eclms.local', 'full_name': 'Alice', 'password': 'password123'},
    )
    assert unauth.json()['success'] is False
    assert unauth.json()['error']['code'] == 'UNAUTHORIZED'

    token = _admin_token(client)
    headers = {'Authorization': f'Bearer {token}'}
    created = client.post(
      '/api/v1/identity/users',
      json={'username': 'alice', 'email': 'alice@eclms.local', 'full_name': 'Alice', 'password': 'password123', 'role': 'VIEWER'},
      headers=headers,
    )
    assert created.status_code == 200
    assert created.json()['data']['username'] == 'alice'

    # A VIEWER lacks user.manage: authenticated but forbidden.
    viewer_login = client.post('/api/v1/identity/auth/login', json={'username': 'alice', 'password': 'password123'})
    viewer_token = viewer_login.json()['data']['access_token']
    forbidden = client.post(
      '/api/v1/identity/users',
      json={'username': 'charlie', 'email': 'charlie@eclms.local', 'full_name': 'Charlie', 'password': 'password123'},
      headers={'Authorization': f'Bearer {viewer_token}'},
    )
    assert forbidden.json()['success'] is False
    assert forbidden.json()['error']['code'] == 'FORBIDDEN'


def test_list_users_and_roles():
  with TestClient(app) as client:
    token = _admin_token(client)
    headers = {'Authorization': f'Bearer {token}'}

    users = client.get('/api/v1/identity/users', headers=headers)
    assert users.status_code == 200
    usernames = {u['username'] for u in users.json()['data']['items']}
    assert 'admin' in usernames

    roles = client.get('/api/v1/identity/roles', headers=headers)
    assert roles.status_code == 200
    role_names = {r['name'] for r in roles.json()['data']['roles']}
    assert 'ADMIN' in role_names
    assert 'CONTRACT_MANAGER' in role_names


def test_duplicate_username_rejected():
  with TestClient(app) as client:
    token = _admin_token(client)
    headers = {'Authorization': f'Bearer {token}'}
    client.post(
      '/api/v1/identity/users',
      json={'username': 'bob', 'email': 'bob@eclms.local', 'full_name': 'Bob', 'password': 'password123'},
      headers=headers,
    )
    dup = client.post(
      '/api/v1/identity/users',
      json={'username': 'bob', 'email': 'bob2@eclms.local', 'full_name': 'Bob', 'password': 'password123'},
      headers=headers,
    )
    assert dup.json()['success'] is False
    assert dup.json()['error']['code'] == 'CONFLICT'


def test_admin_role_has_contract_permissions():
  from infrastructure.database.repositories import SqlUserRepository

  repo = SqlUserRepository()
  import asyncio

  admin = asyncio.run(repo.get_by_username('admin'))
  assert admin is not None
  permissions = asyncio.run(repo.permissions_for_user(admin.id))
  assert {'contract.create', 'contract.read', 'user.manage'} <= permissions


def test_role_permission_mapping():
  from infrastructure.database.repositories import SqlUserRepository

  repo = SqlUserRepository()
  import asyncio

  admin = asyncio.run(repo.get_by_username('admin'))
  permissions = asyncio.run(repo.permissions_for_user(admin.id))
  assert {'contract.create', 'contract.read', 'contract.update', 'contract.transition', 'document.upload', 'document.read'} <= permissions
