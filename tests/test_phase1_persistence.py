"""Phase 1 persistence tests: contract versioning, documents, audit trail."""

import asyncio


def await_sync(coro):
  return asyncio.run(coro)


def test_contract_versioning_via_api(authed_client):
  client, headers = authed_client
  created = client.post(
    '/api/v1/contracts',
    json={'title': 'Lease', 'reference_number': 'L-1', 'counterparty': 'Beta Ltd'},
    headers=headers,
  )
  assert created.status_code == 200
  contract_id = created.json()['data']['id']

  versions = client.get(f'/api/v1/contracts/{contract_id}/versions', headers=headers)
  assert versions.status_code == 200
  items = versions.json()['data']['items']
  assert len(items) == 1
  assert items[0]['version_number'] == 1
  assert items[0]['is_active'] is True

  updated = client.patch(
    f'/api/v1/contracts/{contract_id}',
    json={'title': 'Lease (Amended)'},
    headers=headers,
  )
  assert updated.status_code == 200

  versions = client.get(f'/api/v1/contracts/{contract_id}/versions', headers=headers)
  items = versions.json()['data']['items']
  assert [v['version_number'] for v in items] == [1, 2]
  assert items[0]['is_active'] is False
  assert items[1]['is_active'] is True


def test_document_upload_via_api(authed_client, tmp_path):
  client, headers = authed_client
  created = client.post(
    '/api/v1/contracts',
    json={'title': 'Supply', 'reference_number': 'S-9', 'counterparty': 'Gamma Co'},
    headers=headers,
  )
  contract_id = created.json()['data']['id']

  upload = client.post(
    '/api/v1/documents/upload',
    data={'contract_id': contract_id, 'doc_type': 'attachment'},
    files={'file': ('agreement.pdf', b'%PDF-1.4 fake content', 'application/pdf')},
    headers=headers,
  )
  assert upload.status_code == 200
  body = upload.json()
  assert body['success'] is True
  assert body['data']['file_name'] == 'agreement.pdf'
  assert len(body['data']['content_hash']) == 64

  listing = client.get(f'/api/v1/documents/contract/{contract_id}', headers=headers)
  assert listing.status_code == 200
  items = listing.json()['data']['items']
  assert len(items) == 1
  assert items[0]['version_count'] == 1


def test_document_upload_requires_existing_contract(authed_client):
  client, headers = authed_client
  upload = client.post(
    '/api/v1/documents/upload',
    data={'contract_id': 'does-not-exist'},
    files={'file': ('a.txt', b'hello', 'text/plain')},
    headers=headers,
  )
  assert upload.json()['success'] is False
  assert upload.json()['error']['code'] == 'NOT_FOUND'


def test_audit_events_persisted_to_database(authed_client):
  client, headers = authed_client
  created = client.post(
    '/api/v1/contracts',
    json={'title': 'Audit Me', 'reference_number': 'A-1', 'counterparty': 'Delta LLC'},
    headers=headers,
  )
  contract_id = created.json()['data']['id']
  client.post(f'/api/v1/contracts/{contract_id}/transition', json={'new_state': 'SUBMITTED'}, headers=headers)

  from infrastructure.database.repositories import SqlAuditStore

  store = SqlAuditStore()
  events = await_sync(store.list_all())
  event_types = {e['event_type'] for e in events}
  assert 'contract.created' in event_types
  assert 'contract.state_changed' in event_types
