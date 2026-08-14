"""Phase 1 workflow engine tests: start, approve, reject, history, RBAC."""


def _manager_token(client) -> str:
  login = client.post('/api/v1/identity/auth/login', json={'username': 'manager', 'password': 'password123'})
  return login.json()['data']['access_token']


def _create_contract(client, headers, title='Approval Test') -> str:
  created = client.post(
    '/api/v1/contracts',
    json={'title': title, 'reference_number': 'W-1', 'counterparty': 'ACME'},
    headers=headers,
  )
  return created.json()['data']['id']


def test_full_approval_flow(authed_client):
  client, admin_headers = authed_client

  # Create a CONTRACT_MANAGER user for the first two steps.
  client.post(
    '/api/v1/identity/users',
    json={'username': 'manager', 'email': 'manager@eclms.local', 'full_name': 'Manager', 'password': 'password123', 'role': 'CONTRACT_MANAGER'},
    headers=admin_headers,
  )
  manager = _manager_token(client)

  contract_id = _create_contract(client, admin_headers)

  started = client.post(
    '/api/v1/workflows/start',
    json={'contract_id': contract_id},
    headers=admin_headers,
  )
  assert started.status_code == 200
  body = started.json()['data']
  workflow_id = body['id']
  assert body['status'] == 'RUNNING'
  assert body['current_step'] == 'Legal Review'
  assert body['current_step_role'] == 'CONTRACT_MANAGER'

  # Step 1 (Legal Review) requires CONTRACT_MANAGER.
  ok = client.post(
    f'/api/v1/workflows/{workflow_id}/transition',
    json={'decision': 'APPROVE', 'comment': 'Legal OK'},
    headers={'Authorization': f'Bearer {manager}'},
  )
  assert ok.json()['data']['current_step'] == 'Finance Review'

  # Step 2 (Finance Review) requires CONTRACT_MANAGER.
  ok = client.post(
    f'/api/v1/workflows/{workflow_id}/transition',
    json={'decision': 'APPROVE', 'comment': 'Finance OK'},
    headers={'Authorization': f'Bearer {manager}'},
  )
  assert ok.json()['data']['current_step'] == 'Final Approval'

  # Step 3 (Final Approval) requires ADMIN.
  ok = client.post(
    f'/api/v1/workflows/{workflow_id}/transition',
    json={'decision': 'APPROVE', 'comment': 'Approved'},
    headers=admin_headers,
  )
  assert ok.json()['data']['status'] == 'APPROVED'

  # Contract should now be APPROVED.
  contract = client.get(f'/api/v1/contracts/{contract_id}', headers=admin_headers)
  assert contract.json()['data']['state'] == 'APPROVED'

  # History should record start + three decisions.
  history = client.get(f'/api/v1/workflows/{workflow_id}/history', headers=admin_headers)
  items = history.json()['data']['items']
  assert len(items) == 4


def test_workflow_rejection(authed_client):
  client, admin_headers = authed_client
  client.post(
    '/api/v1/identity/users',
    json={'username': 'manager', 'email': 'manager@eclms.local', 'full_name': 'Manager', 'password': 'password123', 'role': 'CONTRACT_MANAGER'},
    headers=admin_headers,
  )
  manager = _manager_token(client)
  contract_id = _create_contract(client, admin_headers)

  started = client.post(
    '/api/v1/workflows/start',
    json={'contract_id': contract_id},
    headers=admin_headers,
  )
  workflow_id = started.json()['data']['id']

  rejected = client.post(
    f'/api/v1/workflows/{workflow_id}/transition',
    json={'decision': 'REJECT', 'comment': 'Missing clause'},
    headers={'Authorization': f'Bearer {manager}'},
  )
  assert rejected.json()['data']['status'] == 'REJECTED'

  contract = client.get(f'/api/v1/contracts/{contract_id}', headers=admin_headers)
  assert contract.json()['data']['state'] == 'REJECTED'


def test_workflow_requires_role_permission(authed_client):
  client, admin_headers = authed_client
  admin = admin_headers['Authorization'].split(' ')[1]
  contract_id = _create_contract(client, admin_headers)

  started = client.post(
    '/api/v1/workflows/start',
    json={'contract_id': contract_id},
    headers=admin_headers,
  )
  workflow_id = started.json()['data']['id']

  # ADMIN does not hold CONTRACT_MANAGER, so step 1 is forbidden.
  denied = client.post(
    f'/api/v1/workflows/{workflow_id}/transition',
    json={'decision': 'APPROVE'},
    headers={'Authorization': f'Bearer {admin}'},
  )
  assert denied.json()['success'] is False
  assert denied.json()['error']['code'] == 'FORBIDDEN'


def test_duplicate_workflow_rejected(authed_client):
  client, admin_headers = authed_client
  contract_id = _create_contract(client, admin_headers)

  client.post('/api/v1/workflows/start', json={'contract_id': contract_id}, headers=admin_headers)
  dup = client.post('/api/v1/workflows/start', json={'contract_id': contract_id}, headers=admin_headers)
  assert dup.json()['success'] is False
  assert dup.json()['error']['code'] == 'CONFLICT'


def test_decision_after_completion_rejected(authed_client):
  client, admin_headers = authed_client
  admin = admin_headers['Authorization'].split(' ')[1]
  client.post(
    '/api/v1/identity/users',
    json={'username': 'manager', 'email': 'manager@eclms.local', 'full_name': 'Manager', 'password': 'password123', 'role': 'CONTRACT_MANAGER'},
    headers=admin_headers,
  )
  manager = _manager_token(client)
  contract_id = _create_contract(client, admin_headers)

  started = client.post(
    '/api/v1/workflows/start',
    json={'contract_id': contract_id},
    headers=admin_headers,
  )
  workflow_id = started.json()['data']['id']

  client.post(
    f'/api/v1/workflows/{workflow_id}/transition',
    json={'decision': 'APPROVE', 'comment': 'legal'},
    headers={'Authorization': f'Bearer {manager}'},
  )
  client.post(
    f'/api/v1/workflows/{workflow_id}/transition',
    json={'decision': 'APPROVE', 'comment': 'finance'},
    headers={'Authorization': f'Bearer {manager}'},
  )
  client.post(
    f'/api/v1/workflows/{workflow_id}/transition',
    json={'decision': 'APPROVE', 'comment': 'final'},
    headers=admin_headers,
  )

  extra = client.post(
    f'/api/v1/workflows/{workflow_id}/transition',
    json={'decision': 'APPROVE'},
    headers={'Authorization': f'Bearer {admin}'},
  )
  assert extra.json()['success'] is False
  assert extra.json()['error']['code'] == 'INVALID_STATE_TRANSITION'
