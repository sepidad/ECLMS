"""Default approval workflow definitions (WF-014 / SEQ-002).

The default approval workflow routes a submitted contract through
sequential review steps: Legal Review -> Finance Review -> Final Approval.
Each step is performed by a role.  New definitions can be registered
without changing the engine.

Phase 2 adds two example definitions exercising the new engine
capabilities: a parallel review workflow and a conditional workflow.
"""

from __future__ import annotations

from backend.modules.workflow.domain.workflow import WorkflowDefinition, WorkflowStepDefinition

APPROVAL_WORKFLOW_ID = 'contract-approval'
PARALLEL_APPROVAL_WORKFLOW_ID = 'contract-approval-parallel'
CONDITIONAL_APPROVAL_WORKFLOW_ID = 'contract-approval-conditional'
EXECUTIVE_APPROVAL_WORKFLOW_ID = 'contract-approval-executive'

DEFAULT_APPROVAL_WORKFLOW = WorkflowDefinition(
  definition_id=APPROVAL_WORKFLOW_ID,
  name='Contract Approval',
  steps=[
    WorkflowStepDefinition(
      name='Legal Review',
      assigned_role='CONTRACT_MANAGER',
      order=1,
      timeout_hours=24,
      escalation_role='ADMIN',
    ),
    WorkflowStepDefinition(name='Finance Review', assigned_role='CONTRACT_MANAGER', order=2),
    WorkflowStepDefinition(name='Final Approval', assigned_role='ADMIN', order=3),
  ],
)

PARALLEL_APPROVAL_WORKFLOW = WorkflowDefinition(
  definition_id=PARALLEL_APPROVAL_WORKFLOW_ID,
  name='Contract Approval with Parallel Review',
  steps=[
    WorkflowStepDefinition(name='Legal Review', assigned_role='CONTRACT_MANAGER', order=1, parallel_group_id='review'),
    WorkflowStepDefinition(name='Compliance Review', assigned_role='CONTRACT_MANAGER', order=2, parallel_group_id='review'),
    WorkflowStepDefinition(name='Final Approval', assigned_role='ADMIN', order=3),
  ],
)

CONDITIONAL_APPROVAL_WORKFLOW = WorkflowDefinition(
  definition_id=CONDITIONAL_APPROVAL_WORKFLOW_ID,
  name='Contract Approval with Conditional Step',
  steps=[
    WorkflowStepDefinition(name='Legal Review', assigned_role='CONTRACT_MANAGER', order=1),
    WorkflowStepDefinition(name='CFO Approval', assigned_role='ADMIN', order=2, condition="contract.counterparty == 'Acme'"),
    WorkflowStepDefinition(name='Final Approval', assigned_role='ADMIN', order=3),
  ],
)

EXECUTIVE_APPROVAL_WORKFLOW = WorkflowDefinition(
  definition_id=EXECUTIVE_APPROVAL_WORKFLOW_ID,
  name='Contract Executive Approval',
  steps=[
    WorkflowStepDefinition(
      name='Legal Review',
      assigned_role='CONTRACT_MANAGER',
      order=1,
      timeout_hours=24,
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

WORKFLOW_DEFINITIONS: dict[str, WorkflowDefinition] = {
  DEFAULT_APPROVAL_WORKFLOW.definition_id: DEFAULT_APPROVAL_WORKFLOW,
  PARALLEL_APPROVAL_WORKFLOW.definition_id: PARALLEL_APPROVAL_WORKFLOW,
  CONDITIONAL_APPROVAL_WORKFLOW.definition_id: CONDITIONAL_APPROVAL_WORKFLOW,
  EXECUTIVE_APPROVAL_WORKFLOW.definition_id: EXECUTIVE_APPROVAL_WORKFLOW,
}


def get_definition(definition_id: str) -> WorkflowDefinition | None:
  return WORKFLOW_DEFINITIONS.get(definition_id)
