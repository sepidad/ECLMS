"""Tests for the multi-step Executive Approval Workflow (Draft -> Legal Review -> Executive Sign-off -> Active)."""

from __future__ import annotations

import pytest

from backend.modules.workflow.domain.definitions import (
  EXECUTIVE_APPROVAL_WORKFLOW_ID,
  WORKFLOW_DEFINITIONS,
  WorkflowDefinition,
  WorkflowStepDefinition,
)
from shared.constants import CONTRACT_STATE_ACTIVE, CONTRACT_STATE_UNDER_REVIEW


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


def _create_contract(client, headers, title='Executive Workflow Test', counterparty='ACME') -> str:
  created = client.post(
    '/api/v1/contracts',
    json={'title': title, 'reference_number': 'EXEC-FLOW-1', 'counterparty': counterparty},
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


@pytest.mark.anyio
async def test_executive_approval_workflow_full_flow(authed_client):
  client, admin_headers = authed_client
  _create_user(client, admin_headers, 'manager')
  manager = _login(client, 'manager')
  
  contract_id = _create_contract(client, admin_headers)
  started = _start_workflow(client, admin_headers, contract_id, EXECUTIVE_APPROVAL_WORKFLOW_ID)
  workflow_id = started['id']

  assert started['status'] == 'RUNNING'
  assert started['current_step'] == 'Legal Review'
  assert started['current_step_role'] == 'CONTRACT_MANAGER'
  assert len(started['steps']) == 2

  # Step 1: Legal Review (approved by manager)
  ok1 = client.post(
    f'/api/v1/workflows/{workflow_id}/transition',
    json={'decision': 'APPROVE', 'step_name': 'Legal Review', 'comment': 'Legal clearance check passed.'},
    headers={'Authorization': f'Bearer {manager}'},
  )
  assert ok1.json()['success'] is True
  body = ok1.json()['data']
  assert body['current_step'] == 'Executive Sign-off'
  assert body['current_step_role'] == 'ADMIN'

  # Contract should now be UNDER_REVIEW
  contract = client.get(f'/api/v1/contracts/{contract_id}', headers=admin_headers)
  assert contract.json()['data']['state'] == CONTRACT_STATE_UNDER_REVIEW

  # Step 2: Executive Sign-off (approved by admin)
  ok2 = client.post(
    f'/api/v1/workflows/{workflow_id}/transition',
    json={'decision': 'APPROVE', 'step_name': 'Executive Sign-off', 'comment': 'Executive sign-off granted.'},
    headers=admin_headers,
  )
  assert ok2.json()['success'] is True
  assert ok2.json()['data']['status'] == 'APPROVED'

  # Contract should now be ACTIVE (Draft -> Legal Review -> Executive Sign-off -> Active completed)
  contract = client.get(f'/api/v1/contracts/{contract_id}', headers=admin_headers)
  assert contract.json()['data']['state'] == CONTRACT_STATE_ACTIVE


@pytest.mark.anyio
async def test_executive_workflow_escalation_sweep(authed_client):
  client, admin_headers = authed_client
  
  temp_def_id = 'contract-executive-timeout'
  # Register a temporary workflow with 0 hours timeout to trigger instant escalation on sweep
  WORKFLOW_DEFINITIONS[temp_def_id] = WorkflowDefinition(
    definition_id=temp_def_id,
    name='Timeout Executive Workflow',
    steps=[
      WorkflowStepDefinition(
        name='Legal Review',
        assigned_role='CONTRACT_MANAGER',
        order=1,
        timeout_hours=0,
        escalation_role='ADMIN',
      ),
      WorkflowStepDefinition(
        name='Executive Sign-off',
        assigned_role='ADMIN',
        order=2,
        timeout_hours=48,
        escalation_role='ADMIN',
      ),
    ],
  )
  try:
    contract_id = _create_contract(client, admin_headers, 'Escalate Exec Test')
    started = _start_workflow(client, admin_headers, contract_id, temp_def_id)
    workflow_id = started['id']

    # Trigger SLA escalation sweep
    swept = client.post('/api/v1/workflows/escalate-overdue', headers=admin_headers)
    assert swept.json()['data']['escalated'] == 1

    # Verify step was escalated to ADMIN
    wf = client.get(f'/api/v1/workflows/{workflow_id}', headers=admin_headers)
    step = wf.json()['data']['steps'][0]
    assert step['status'] == 'ESCALATED'
    
    # An ADMIN user should now be able to decide the escalated step
    ok = client.post(
      f'/api/v1/workflows/{workflow_id}/transition',
      json={'decision': 'APPROVE', 'step_name': 'Legal Review'},
      headers=admin_headers,
    )
    assert ok.json()['success'] is True
    assert ok.json()['data']['current_step'] == 'Executive Sign-off'
  finally:
    WORKFLOW_DEFINITIONS.pop(temp_def_id, None)
