"""Phase 2 workflow engine tests.

Covers the Phase 2 capabilities added to the workflow module:
parallel approvals, conditional steps, pause/resume, delegation,
and escalation (manual + SLA sweep).
"""

from backend.modules.workflow.domain.definitions import WORKFLOW_DEFINITIONS
from backend.modules.workflow.domain.workflow import WorkflowDefinition, WorkflowStepDefinition

PARALLEL = 'contract-approval-parallel'
CONDITIONAL = 'contract-approval-conditional'


def _login(client, username, password='password123') -> str:
  login = client.post(
    '/api/v1/identity/auth/login', json={'username': username, 'password': password},
  )
  return login.json()['data']['access_token']


def _create_user(client, admin_headers, username) -> str:
  created = client.post(
    '/api/v1/identity/users',
    json={
      'username': username,
      'email': f'{username}@eclms.local',
      'full_name': username.title(),
      'password': 'password123',
      'role': 'CONTRACT_MANAGER',
    },
    headers=admin_headers,
  )
  return created.json()['data']['id']


def _create_contract(client, headers, title='Phase2 Test', counterparty='ACME') -> str:
  created = client.post(
    '/api/v1/contracts',
    json={'title': title, 'reference_number': 'P2-1', 'counterparty': counterparty},
    headers=headers,
  )
  return created.json()['data']['id']


def _start_workflow(client, admin_headers, contract_id, definition_id) -> dict:
  started = client.post(
    '/api/v1/workflows/start',
    json={'contract_id': contract_id, 'definition_id': definition_id},
    headers=admin_headers,
  )
  assert started.json()['success'] is True
  return started.json()['data']


def test_parallel_approval_flow(authed_client):
  client, admin_headers = authed_client
  _create_user(client, admin_headers, 'manager')
  manager = _login(client, 'manager')
  contract_id = _create_contract(client, admin_headers)
  started = _start_workflow(client, admin_headers, contract_id, PARALLEL)
  workflow_id = started['id']

  assert {s['name'] for s in started['steps']} == {'Legal Review', 'Compliance Review', 'Final Approval'}

  # Approve the first parallel step by name; the sibling must remain active.
  ok = client.post(
    f'/api/v1/workflows/{workflow_id}/transition',
    json={'decision': 'APPROVE', 'step_name': 'Legal Review'},
    headers={'Authorization': f'Bearer {manager}'},
  )
  body = ok.json()['data']
  assert body['status'] == 'RUNNING'
  assert {s['name'] for s in body['steps'] if s['status'] == 'APPROVED'} == {'Legal Review'}

  # Approve the sibling; the workflow may now advance to Final Approval.
  ok = client.post(
    f'/api/v1/workflows/{workflow_id}/transition',
    json={'decision': 'APPROVE', 'step_name': 'Compliance Review'},
    headers={'Authorization': f'Bearer {manager}'},
  )
  assert ok.json()['data']['current_step'] == 'Final Approval'

  ok = client.post(
    f'/api/v1/workflows/{workflow_id}/transition',
    json={'decision': 'APPROVE'},
    headers=admin_headers,
  )
  assert ok.json()['data']['status'] == 'APPROVED'


def test_parallel_rejection_rejects_workflow(authed_client):
  client, admin_headers = authed_client
  _create_user(client, admin_headers, 'manager')
  manager = _login(client, 'manager')
  contract_id = _create_contract(client, admin_headers)
  started = _start_workflow(client, admin_headers, contract_id, PARALLEL)
  workflow_id = started['id']

  rejected = client.post(
    f'/api/v1/workflows/{workflow_id}/transition',
    json={'decision': 'REJECT', 'step_name': 'Compliance Review'},
    headers={'Authorization': f'Bearer {manager}'},
  )
  assert rejected.json()['data']['status'] == 'REJECTED'
  by_name = {s['name']: s['status'] for s in rejected.json()['data']['steps']}
  assert by_name['Compliance Review'] == 'REJECTED'


def test_conditional_step_skipped(authed_client):
  client, admin_headers = authed_client
  _create_user(client, admin_headers, 'manager')
  manager = _login(client, 'manager')
  # Non-Acme counterparty -> CFO Approval (condition false) is skipped.
  contract_id = _create_contract(client, admin_headers, 'Cond Skip', 'OtherCorp')
  started = _start_workflow(client, admin_headers, contract_id, CONDITIONAL)
  workflow_id = started['id']

  ok = client.post(
    f'/api/v1/workflows/{workflow_id}/transition',
    json={'decision': 'APPROVE', 'comment': 'legal'},
    headers={'Authorization': f'Bearer {manager}'},
  )
  body = ok.json()['data']
  assert body['current_step'] == 'Final Approval'
  by_name = {s['name']: s['status'] for s in body['steps']}
  assert by_name['CFO Approval'] == 'SKIPPED'

  ok = client.post(
    f'/api/v1/workflows/{workflow_id}/transition',
    json={'decision': 'APPROVE'},
    headers=admin_headers,
  )
  assert ok.json()['data']['status'] == 'APPROVED'


def test_conditional_step_runs(authed_client):
  client, admin_headers = authed_client
  _create_user(client, admin_headers, 'manager')
  manager = _login(client, 'manager')
  # Acme counterparty -> CFO Approval (condition true) must run.
  contract_id = _create_contract(client, admin_headers, 'Cond Run', 'Acme')
  started = _start_workflow(client, admin_headers, contract_id, CONDITIONAL)
  workflow_id = started['id']

  ok = client.post(
    f'/api/v1/workflows/{workflow_id}/transition',
    json={'decision': 'APPROVE', 'comment': 'legal'},
    headers={'Authorization': f'Bearer {manager}'},
  )
  assert ok.json()['data']['current_step'] == 'CFO Approval'

  ok = client.post(
    f'/api/v1/workflows/{workflow_id}/transition',
    json={'decision': 'APPROVE', 'comment': 'cfo'},
    headers=admin_headers,
  )
  assert ok.json()['data']['current_step'] == 'Final Approval'

  ok = client.post(
    f'/api/v1/workflows/{workflow_id}/transition',
    json={'decision': 'APPROVE'},
    headers=admin_headers,
  )
  assert ok.json()['data']['status'] == 'APPROVED'


def test_pause_resume(authed_client):
  client, admin_headers = authed_client
  _create_user(client, admin_headers, 'manager')
  manager = _login(client, 'manager')
  contract_id = _create_contract(client, admin_headers)
  started = _start_workflow(client, admin_headers, contract_id, 'contract-approval')
  workflow_id = started['id']

  paused = client.post(
    f'/api/v1/workflows/{workflow_id}/pause',
    json={'reason': 'Awaiting legal input'},
    headers=admin_headers,
  )
  assert paused.json()['data']['status'] == 'PAUSED'

  denied = client.post(
    f'/api/v1/workflows/{workflow_id}/transition',
    json={'decision': 'APPROVE'},
    headers={'Authorization': f'Bearer {manager}'},
  )
  assert denied.json()['success'] is False
  assert denied.json()['error']['code'] == 'INVALID_STATE_TRANSITION'

  resumed = client.post(f'/api/v1/workflows/{workflow_id}/resume', headers=admin_headers)
  assert resumed.json()['data']['status'] == 'RUNNING'

  ok = client.post(
    f'/api/v1/workflows/{workflow_id}/transition',
    json={'decision': 'APPROVE', 'comment': 'resumed'},
    headers={'Authorization': f'Bearer {manager}'},
  )
  assert ok.json()['data']['current_step'] == 'Finance Review'


def test_step_delegation(authed_client):
  client, admin_headers = authed_client
  _create_user(client, admin_headers, 'manager')
  delegatee_id = _create_user(client, admin_headers, 'backup')
  manager = _login(client, 'manager')
  delegatee = _login(client, 'backup')
  contract_id = _create_contract(client, admin_headers)
  started = _start_workflow(client, admin_headers, contract_id, 'contract-approval')
  workflow_id = started['id']

  # ADMIN does not hold CONTRACT_MANAGER, so delegation must be forbidden.
  denied = client.post(
    f'/api/v1/workflows/{workflow_id}/delegate',
    json={'delegated_to': delegatee_id},
    headers=admin_headers,
  )
  assert denied.json()['error']['code'] == 'FORBIDDEN'

  delegated = client.post(
    f'/api/v1/workflows/{workflow_id}/delegate',
    json={'delegated_to': delegatee_id, 'comment': 'on leave'},
    headers={'Authorization': f'Bearer {manager}'},
  )
  step = next(s for s in delegated.json()['data']['steps'] if s['name'] == 'Legal Review')
  assert step['status'] == 'DELEGATED'
  assert step['delegated_to'] == delegatee_id

  # The delegatee can approve the delegated step.
  ok = client.post(
    f'/api/v1/workflows/{workflow_id}/transition',
    json={'decision': 'APPROVE', 'comment': 'handled'},
    headers={'Authorization': f'Bearer {delegatee}'},
  )
  assert ok.json()['data']['current_step'] == 'Finance Review'


def test_step_escalation(authed_client):
  client, admin_headers = authed_client
  _create_user(client, admin_headers, 'manager')
  manager = _login(client, 'manager')
  contract_id = _create_contract(client, admin_headers)
  started = _start_workflow(client, admin_headers, contract_id, 'contract-approval')
  workflow_id = started['id']

  escalated = client.post(
    f'/api/v1/workflows/{workflow_id}/escalate',
    json={'comment': 'stuck for weeks'},
    headers={'Authorization': f'Bearer {manager}'},
  )
  step = next(s for s in escalated.json()['data']['steps'] if s['name'] == 'Legal Review')
  assert step['status'] == 'ESCALATED'
  assert step['escalated_at'] is not None

  # ADMIN now holds the escalation role and can decide the escalated step.
  ok = client.post(
    f'/api/v1/workflows/{workflow_id}/transition',
    json={'decision': 'APPROVE', 'comment': 'unblocked'},
    headers=admin_headers,
  )
  assert ok.json()['data']['current_step'] == 'Finance Review'


def test_escalate_overdue_sweep(authed_client):
  client, admin_headers = authed_client
  temp_def_id = 'contract-approval-timeout'
  WORKFLOW_DEFINITIONS[temp_def_id] = WorkflowDefinition(
    definition_id=temp_def_id,
    name='Timeout Workflow',
    steps=[
      WorkflowStepDefinition(
        name='Legal Review',
        assigned_role='CONTRACT_MANAGER',
        order=1,
        timeout_hours=0,
        escalation_role='ADMIN',
      ),
    ],
  )
  try:
    contract_id = _create_contract(client, admin_headers, 'Sweep Test', 'ACME')
    started = _start_workflow(client, admin_headers, contract_id, temp_def_id)
    workflow_id = started['id']

    swept = client.post('/api/v1/workflows/escalate-overdue', headers=admin_headers)
    assert swept.json()['data']['escalated'] == 1

    wf = client.get(f'/api/v1/workflows/{workflow_id}', headers=admin_headers)
    step = wf.json()['data']['steps'][0]
    assert step['status'] == 'ESCALATED'
  finally:
    WORKFLOW_DEFINITIONS.pop(temp_def_id, None)
