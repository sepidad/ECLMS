"""Route-level RBAC guards for contracts and documents endpoints."""


def _viewer_headers(client) -> dict:
  login = client.post('/api/v1/identity/auth/login', json={'username': 'alice', 'password': 'password123'})
  return {'Authorization': f'Bearer {login.json()["data"]["access_token"]}'}


def test_contract_create_read_update_guarded(authed_client):
  client, admin_headers = authed_client

  # Create a VIEWER (read-only: no contract.create/update/transition).
  client.post(
    '/api/v1/identity/users',
    json={'username': 'alice', 'email': 'alice@eclms.local', 'full_name': 'Alice', 'password': 'password123', 'role': 'VIEWER'},
    headers=admin_headers,
  )
  viewer = _viewer_headers(client)

  # VIEWER cannot create.
  denied = client.post(
    '/api/v1/contracts',
    json={'title': 'Blocked', 'reference_number': 'B-1', 'counterparty': 'X'},
    headers=viewer,
  )
  assert denied.json()['success'] is False
  assert denied.json()['error']['code'] == 'FORBIDDEN'

  # VIEWER can read.
  created = client.post(
    '/api/v1/contracts',
    json={'title': 'Readable', 'reference_number': 'R-1', 'counterparty': 'X'},
    headers=admin_headers,
  )
  contract_id = created.json()['data']['id']
  read = client.get(f'/api/v1/contracts/{contract_id}', headers=viewer)
  assert read.json()['success'] is True

  # VIEWER cannot update or transition.
  update = client.patch(f'/api/v1/contracts/{contract_id}', json={'title': 'Nope'}, headers=viewer)
  assert update.json()['error']['code'] == 'FORBIDDEN'
  transition = client.post(
    f'/api/v1/contracts/{contract_id}/transition',
    json={'new_state': 'SUBMITTED'},
    headers=viewer,
  )
  assert transition.json()['error']['code'] == 'FORBIDDEN'


def test_document_upload_guarded(authed_client):
  client, admin_headers = authed_client
  client.post(
    '/api/v1/identity/users',
    json={'username': 'alice', 'email': 'alice@eclms.local', 'full_name': 'Alice', 'password': 'password123', 'role': 'VIEWER'},
    headers=admin_headers,
  )
  viewer = _viewer_headers(client)

  created = client.post(
    '/api/v1/contracts',
    json={'title': 'Doc Guard', 'reference_number': 'DG-1', 'counterparty': 'X'},
    headers=admin_headers,
  )
  contract_id = created.json()['data']['id']

  # VIEWER cannot upload.
  denied = client.post(
    '/api/v1/documents/upload',
    data={'contract_id': contract_id},
    files={'file': ('a.txt', b'hello', 'text/plain')},
    headers=viewer,
  )
  assert denied.json()['success'] is False
  assert denied.json()['error']['code'] == 'FORBIDDEN'

  # VIEWER can list documents.
  listing = client.get(f'/api/v1/documents/contract/{contract_id}', headers=viewer)
  assert listing.json()['success'] is True


def test_workflow_start_requires_transition_permission(authed_client):
  client, admin_headers = authed_client
  client.post(
    '/api/v1/identity/users',
    json={'username': 'alice', 'email': 'alice@eclms.local', 'full_name': 'Alice', 'password': 'password123', 'role': 'VIEWER'},
    headers=admin_headers,
  )
  viewer = _viewer_headers(client)

  created = client.post(
    '/api/v1/contracts',
    json={'title': 'WF Guard', 'reference_number': 'WFG-1', 'counterparty': 'X'},
    headers=admin_headers,
  )
  contract_id = created.json()['data']['id']

  # VIEWER cannot start a workflow (requires contract.transition).
  denied = client.post('/api/v1/workflows/start', json={'contract_id': contract_id}, headers=viewer)
  assert denied.json()['success'] is False
  assert denied.json()['error']['code'] == 'FORBIDDEN'
