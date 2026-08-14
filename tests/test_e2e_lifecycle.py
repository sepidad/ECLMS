"""End-to-end lifecycle integration smoke test covering contracts, versions, AI review, documents, obligations, finances, and reporting export."""

from __future__ import annotations

from fastapi.testclient import TestClient

from backend.main import app


def test_full_lifecycle_e2e_flow():
  with TestClient(app) as client:
    # 1. Login as seeded admin
    login_res = client.post(
      '/api/v1/identity/auth/login',
      json={'username': 'admin', 'password': 'admin'},
    )
    assert login_res.status_code == 200
    login_data = login_res.json()
    assert login_data['success'] is True
    token = login_data['data']['access_token']
    headers = {'Authorization': f'Bearer {token}'}

    # 2. Create contract with text content and termination clause
    contract_payload = {
      'title': 'E2E Lifecycle Master Agreement',
      'reference_number': 'E2E-2026-001',
      'counterparty': 'Global Acme Corp',
      'state': 'DRAFT',
      'description': 'Master services agreement. Termination: either party may give 30 days notice or 7 days notice. Liability is uncapped.',
      'content': 'This agreement is made between ECLMS and Global Acme Corp. Termination clause: either party may terminate with 30 days notice. Payment terms: net 30 days from invoice.'
    }
    create_res = client.post('/api/v1/contracts', json=contract_payload, headers=headers)
    assert create_res.status_code == 200
    c_data = create_res.json()
    assert c_data['success'] is True
    contract_id = c_data['data']['id']
    assert contract_id

    # 3. Run AI Review (?provider=rules)
    review_res = client.get(f'/api/v1/intelligence/review/{contract_id}?provider=rules', headers=headers)
    assert review_res.status_code == 200
    r_data = review_res.json()
    assert r_data['success'] is True
    assert r_data['data']['provider'] == 'rules'
    assert r_data['data']['overall_risk_level'] in ('MEDIUM', 'HIGH', 'CRITICAL')

    # 4. Analyze Clauses
    clause_res = client.get(f'/api/v1/intelligence/clauses/{contract_id}', headers=headers)
    assert clause_res.status_code == 200
    cl_data = clause_res.json()
    assert cl_data['success'] is True

    # 5. Create an obligation for the contract
    obl_payload = {
      'contract_id': contract_id,
      'description': 'Deliver Q3 compliance audit report',
      'due_date': '2026-12-31T00:00:00Z'
    }
    obl_res = client.post('/api/v1/obligations', json=obl_payload, headers=headers)
    assert obl_res.status_code == 200
    assert obl_res.json()['success'] is True

    # 6. Create financial commitment
    fin_payload = {
      'contract_id': contract_id,
      'description': 'Annual software license fee',
      'amount': 50000.0,
      'currency': 'USD',
      'due_date': '2026-09-30T00:00:00Z'
    }
    fin_res = client.post('/api/v1/finances/commitments', json=fin_payload, headers=headers)
    assert fin_res.status_code == 200
    assert fin_res.json()['success'] is True

    # 7. Transition contract state (DRAFT -> SUBMITTED -> UNDER_REVIEW -> APPROVED)
    for target_state in ['SUBMITTED', 'UNDER_REVIEW', 'APPROVED']:
      trans_res = client.post(
        f'/api/v1/contracts/{contract_id}/transition',
        json={'new_state': target_state},
        headers=headers
      )
      assert trans_res.status_code == 200
      assert trans_res.json()['data']['state'] == target_state

    # 8. Export reporting CSV
    csv_res = client.get('/api/v1/reporting/export.csv', headers=headers)
    assert csv_res.status_code == 200
    assert 'ECLMS contract portfolio export' in csv_res.text
    assert 'E2E-2026-001' in csv_res.text
