"""Workflow application service (SEQ-002 / WF-014).

Orchestrates the approval lifecycle for a contract:

    start  -> contract SUBMITTED, workflow RUNNING at step 1
    decide -> approve advances to next step; final approval transitions
              the contract to APPROVED; rejection transitions it to
              REJECTED.  Every decision is persisted to history and
              published as a domain event.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from backend.core.events import Event
from backend.core.exceptions import ConflictError, ForbiddenError, StateTransitionError
from backend.core.utils import utc_now
from backend.modules.workflow.domain.definitions import (
  APPROVAL_WORKFLOW_ID,
  EXECUTIVE_APPROVAL_WORKFLOW_ID,
  get_definition,
)
from backend.modules.workflow.domain.workflow import (
  STEP_STATUS_DELEGATED,
  STEP_STATUS_ESCALATED,
  WorkflowInstance,
  WorkflowStep,
)

if TYPE_CHECKING:
  from backend.core.events import EventBus
  from backend.modules.contracts.application.contract_service import ContractService
  from infrastructure.database.repositories.user_repository import SqlUserRepository
  from infrastructure.database.repositories.workflow_repository import SqlWorkflowRepository

from shared.constants import (
  CONTRACT_STATE_ACTIVE,
  CONTRACT_STATE_APPROVED,
  CONTRACT_STATE_EXECUTED,
  CONTRACT_STATE_REJECTED,
  CONTRACT_STATE_SUBMITTED,
  CONTRACT_STATE_UNDER_REVIEW,
)

WORKFLOW_DECISION_APPROVE = 'APPROVE'
WORKFLOW_DECISION_REJECT = 'REJECT'
WORKFLOW_DECISION_ESCALATE = 'ESCALATE'
WORKFLOW_DECISION_DELEGATE = 'DELEGATE'

# Actor used by the scheduled escalation sweep.
SYSTEM_ACTOR_ID = 'system'


def _aware(dt: datetime | None) -> datetime | None:
  """Return a timezone-aware datetime; SQLite stores naive timestamps."""
  if dt is None:
    return None
  if dt.tzinfo is None:
    return dt.replace(tzinfo=UTC)
  return dt


class WorkflowService:
  def __init__(
    self,
    repository: SqlWorkflowRepository,
    contracts: ContractService,
    users: SqlUserRepository,
    event_bus: EventBus,
  ) -> None:
    self._repository = repository
    self._contracts = contracts
    self._users = users
    self._event_bus = event_bus

  async def start(
    self,
    contract_id: str,
    started_by: str,
    *,
    organization_id: str,
    definition_id: str = APPROVAL_WORKFLOW_ID,
  ) -> WorkflowInstance:
    definition = get_definition(definition_id)
    if definition is None:
      raise ConflictError(f'Unknown workflow definition: {definition_id}')

    await self._contracts.get_contract(contract_id, organization_id=organization_id)
    running = await self._repository.find_running_for_contract(contract_id)
    if running is not None:
      raise ConflictError(f'Contract already has a running workflow: {running.id}')

    workflow = WorkflowInstance(contract_id=contract_id, definition=definition, started_by=started_by)
    await self._repository.create(workflow)

    await self._contracts.transition(contract_id, CONTRACT_STATE_SUBMITTED, organization_id=organization_id)

    await self._repository.append_history(
      workflow,
      from_state='CREATED',
      to_state='RUNNING',
      actor_id=started_by,
      reason='Workflow started',
    )
    await self._event_bus.publish(
      Event(
        event_type='workflow.started',
        source_module='workflow',
        payload={
          'workflow_id': workflow.id,
          'contract_id': contract_id,
          'definition_id': definition_id,
          'current_step': workflow.current_step.name if workflow.current_step else None,
        },
        metadata={'entity_type': 'workflow', 'entity_id': workflow.id, 'actor_id': started_by, 'organization_id': organization_id},
      )
    )
    return workflow

  async def decide(
    self,
    workflow_id: str,
    *,
    decision: str,
    actor_id: str,
    organization_id: str,
    comment: str | None = None,
    step_name: str | None = None,
  ) -> WorkflowInstance:
    workflow = await self._require_scoped_workflow(workflow_id, organization_id)
    if workflow.is_paused:
      raise StateTransitionError(
        'Workflow is paused; resume it before deciding',
        details={'workflow_id': workflow_id, 'status': workflow.status},
      )
    if not workflow.is_running:
      raise StateTransitionError(
        'Workflow is not running',
        details={'workflow_id': workflow_id, 'status': workflow.status},
      )

    contract = await self._contracts.get_contract(workflow.contract_id, organization_id=organization_id)

    step = workflow._decidable_step(step_name)
    if step is None:
      raise StateTransitionError('Workflow has no pending step', details={'workflow_id': workflow_id})

    # Authorization: the actor must hold the step's role, or be the delegatee
    # of a delegated step, or hold the escalation role of an escalated step.
    if not await self._actor_can_decide_step(actor_id, step):
      raise ForbiddenError(
        f'Step requires role {step.assigned_role}',
        details={'workflow_id': workflow_id, 'step': step.name, 'role': step.assigned_role},
      )

    if decision == WORKFLOW_DECISION_APPROVE:
      workflow.approve(actor_id, comment, contract=contract, step_name=step.name)
    elif decision == WORKFLOW_DECISION_REJECT:
      workflow.reject(actor_id, comment, step_name=step.name)
    else:
      raise ConflictError(f'Unknown decision: {decision}')

    await self._repository.save(workflow)
    await self._repository.append_history(
      workflow,
      from_state='RUNNING',
      to_state=workflow.status,
      actor_id=actor_id,
      reason=comment,
    )

    if workflow.is_approved:
      if workflow.definition_id == EXECUTIVE_APPROVAL_WORKFLOW_ID:
        await self._contracts.transition(workflow.contract_id, CONTRACT_STATE_APPROVED, organization_id=organization_id)
        await self._contracts.transition(workflow.contract_id, CONTRACT_STATE_EXECUTED, organization_id=organization_id)
        await self._contracts.transition(workflow.contract_id, CONTRACT_STATE_ACTIVE, organization_id=organization_id)
      else:
        await self._contracts.transition(workflow.contract_id, CONTRACT_STATE_APPROVED, organization_id=organization_id)
    elif workflow.is_rejected:
      # Rejection requires the contract to have reached review (state machine:
      # SUBMITTED -> UNDER_REVIEW -> REJECTED).
      if contract.state == CONTRACT_STATE_SUBMITTED:
        await self._contracts.transition(contract.id, CONTRACT_STATE_UNDER_REVIEW, organization_id=organization_id)
      await self._contracts.transition(workflow.contract_id, CONTRACT_STATE_REJECTED, organization_id=organization_id)
    elif contract.state == CONTRACT_STATE_SUBMITTED:
      # Intermediate approval: move the contract into review.
      await self._contracts.transition(contract.id, CONTRACT_STATE_UNDER_REVIEW, organization_id=organization_id)

    await self._event_bus.publish(
      Event(
        event_type='workflow.step_decided',
        source_module='workflow',
        payload={
          'workflow_id': workflow.id,
          'contract_id': workflow.contract_id,
          'step': step.name,
          'decision': decision,
          'workflow_status': workflow.status,
          'next_step': workflow.current_step.name if workflow.current_step else None,
        },
        metadata={'entity_type': 'workflow', 'entity_id': workflow.id, 'actor_id': actor_id, 'organization_id': organization_id},
      )
    )
    return workflow

  async def pause(self, workflow_id: str, *, actor_id: str, organization_id: str, reason: str) -> WorkflowInstance:
    workflow = await self._require_scoped_workflow(workflow_id, organization_id)
    workflow.pause(actor_id, reason)
    await self._repository.save(workflow)
    await self._repository.append_history(
      workflow, from_state='RUNNING', to_state='PAUSED', actor_id=actor_id, reason=reason,
    )
    await self._event_bus.publish(
      Event(
        event_type='workflow.paused',
        source_module='workflow',
        payload={'workflow_id': workflow.id, 'contract_id': workflow.contract_id, 'reason': reason},
        metadata={'entity_type': 'workflow', 'entity_id': workflow.id, 'actor_id': actor_id, 'organization_id': organization_id},
      )
    )
    return workflow

  async def resume(self, workflow_id: str, *, actor_id: str, organization_id: str) -> WorkflowInstance:
    workflow = await self._require_scoped_workflow(workflow_id, organization_id)
    workflow.resume(actor_id)
    await self._repository.save(workflow)
    await self._repository.append_history(
      workflow, from_state='PAUSED', to_state='RUNNING', actor_id=actor_id, reason='Workflow resumed',
    )
    await self._event_bus.publish(
      Event(
        event_type='workflow.resumed',
        source_module='workflow',
        payload={'workflow_id': workflow.id, 'contract_id': workflow.contract_id},
        metadata={'entity_type': 'workflow', 'entity_id': workflow.id, 'actor_id': actor_id, 'organization_id': organization_id},
      )
    )
    return workflow

  async def delegate(
    self,
    workflow_id: str,
    *,
    actor_id: str,
    organization_id: str,
    delegated_to: str,
    step_name: str | None = None,
    comment: str | None = None,
  ) -> WorkflowInstance:
    workflow = await self._require_scoped_workflow(workflow_id, organization_id)
    step = workflow._decidable_step(step_name)
    if step is None:
      raise StateTransitionError('Workflow has no pending step', details={'workflow_id': workflow_id})
    if not await self._actor_has_role(actor_id, step.assigned_role):
      raise ForbiddenError(
        f'Step requires role {step.assigned_role}',
        details={'workflow_id': workflow_id, 'step': step.name, 'role': step.assigned_role},
      )
    step.delegate(delegated_to, actor_id, comment)
    await self._repository.save(workflow)
    await self._repository.append_history(
      workflow,
      from_state='RUNNING',
      to_state=STEP_STATUS_DELEGATED,
      actor_id=actor_id,
      reason=f'Delegated to {delegated_to}',
    )
    await self._event_bus.publish(
      Event(
        event_type='workflow.step_delegated',
        source_module='workflow',
        payload={
          'workflow_id': workflow.id,
          'contract_id': workflow.contract_id,
          'step': step.name,
          'delegated_to': delegated_to,
        },
        metadata={'entity_type': 'workflow', 'entity_id': workflow.id, 'actor_id': actor_id, 'organization_id': organization_id},
      )
    )
    return workflow

  async def escalate(
    self,
    workflow_id: str,
    *,
    actor_id: str,
    organization_id: str,
    step_name: str | None = None,
    role: str | None = None,
    comment: str | None = None,
  ) -> WorkflowInstance:
    workflow = await self._require_scoped_workflow(workflow_id, organization_id)
    step = workflow._decidable_step(step_name)
    if step is None:
      raise StateTransitionError('Workflow has no pending step', details={'workflow_id': workflow_id})
    if not await self._actor_can_decide_step(actor_id, step):
      raise ForbiddenError(
        f'Step requires role {step.assigned_role}',
        details={'workflow_id': workflow_id, 'step': step.name, 'role': step.assigned_role},
      )
    target_role = role or step.escalation_role or 'ADMIN'
    step.escalate(target_role, actor_id, comment)
    await self._repository.save(workflow)
    await self._repository.append_history(
      workflow,
      from_state='RUNNING',
      to_state=STEP_STATUS_ESCALATED,
      actor_id=actor_id,
      reason=f'Escalated to {target_role}',
    )
    await self._event_bus.publish(
      Event(
        event_type='workflow.step_escalated',
        source_module='workflow',
        payload={
          'workflow_id': workflow.id,
          'contract_id': workflow.contract_id,
          'step': step.name,
          'escalation_role': target_role,
        },
        metadata={'entity_type': 'workflow', 'entity_id': workflow.id, 'actor_id': actor_id, 'organization_id': organization_id},
      )
    )
    return workflow

  async def escalate_overdue(self) -> int:
    """Escalate every active step whose SLA timeout (started_at + timeout_hours) elapsed.

    Returns the number of escalated steps.  Designed to be invoked by a
    scheduler; for Phase 2 it is also exposed as an admin endpoint.
    """
    escalated = 0
    for workflow in await self._repository.find_all_running():
      changed = False
      for step in workflow.pending_steps():
        if step.timeout_hours is None or step.escalated_at is not None:
          continue
        deadline = _aware(step.started_at) + timedelta(hours=step.timeout_hours)
        if utc_now() > deadline:
          target_role = step.escalation_role or 'ADMIN'
          step.escalate(target_role, SYSTEM_ACTOR_ID, 'SLA timeout exceeded')
          changed = True
          escalated += 1
          await self._repository.append_history(
            workflow,
            from_state='RUNNING',
            to_state=STEP_STATUS_ESCALATED,
            actor_id=SYSTEM_ACTOR_ID,
            reason=f'SLA timeout exceeded, escalated to {target_role}',
          )
      if changed:
        await self._repository.save(workflow)
    return escalated

  async def get(self, workflow_id: str, *, organization_id: str) -> WorkflowInstance:
    return await self._require_scoped_workflow(workflow_id, organization_id)

  async def list_for_organization(
    self,
    *,
    organization_id: str,
    status: str | None = None,
    limit: int = 100,
    offset: int = 0,
  ) -> list[WorkflowInstance]:
    return await self._repository.list_by_organization(
      organization_id, status=status, limit=limit, offset=offset
    )

  async def history(self, workflow_id: str, *, organization_id: str) -> list[dict]:
    await self._require_scoped_workflow(workflow_id, organization_id)
    return await self._repository.list_history(workflow_id)

  async def _require_scoped_workflow(self, workflow_id: str, organization_id: str) -> WorkflowInstance:
    """Load a workflow, verifying its contract belongs to the organization.

    A workflow whose contract lives in another org is reported as not
    found so the caller cannot infer it exists (org scoping, ADR-003).
    """
    workflow = await self._repository.require_by_id(workflow_id)
    await self._contracts.get_contract(workflow.contract_id, organization_id=organization_id)
    return workflow

  async def _actor_has_role(self, actor_id: str, role: str) -> bool:
    user = await self._users.get_by_id(actor_id)
    return user is not None and role in user.roles

  async def _actor_can_decide_step(self, actor_id: str, step: WorkflowStep) -> bool:
    """Authorize a decision on a step.

    - default: the actor must hold the step's assigned role
    - delegated step: the delegatee may also decide it
    - escalated step: holders of the escalation role may decide it
    """
    if await self._actor_has_role(actor_id, step.assigned_role):
      return True
    if step.status == STEP_STATUS_DELEGATED and step.delegated_to == actor_id:
      return True
    if step.status == STEP_STATUS_ESCALATED and step.escalation_role:
      return await self._actor_has_role(actor_id, step.escalation_role)
    return False
