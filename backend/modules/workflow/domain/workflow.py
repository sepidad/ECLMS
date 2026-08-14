"""Workflow domain: approval workflow definition and instance.

Implements the workflow blueprint/instance distinction from WF-014:
a definition is the immutable blueprint; an instance is a running
execution for a specific contract, executing the definition version
active at instantiation time.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from backend.core.base.entity import Entity
from backend.core.exceptions import StateTransitionError
from backend.core.utils import utc_now
from backend.modules.workflow.domain.condition_evaluator import ConditionEvaluator

WORKFLOW_STATUS_RUNNING = 'RUNNING'
WORKFLOW_STATUS_APPROVED = 'APPROVED'
WORKFLOW_STATUS_REJECTED = 'REJECTED'
WORKFLOW_STATUS_CANCELLED = 'CANCELLED'
WORKFLOW_STATUS_PAUSED = 'PAUSED'

STEP_STATUS_PENDING = 'PENDING'
STEP_STATUS_APPROVED = 'APPROVED'
STEP_STATUS_REJECTED = 'REJECTED'
STEP_STATUS_ESCALATED = 'ESCALATED'
STEP_STATUS_DELEGATED = 'DELEGATED'
STEP_STATUS_SKIPPED = 'SKIPPED'

# A step awaiting a decision (regardless of being delegated or escalated).
STEP_STATUS_ACTIVE = (STEP_STATUS_PENDING, STEP_STATUS_DELEGATED, STEP_STATUS_ESCALATED)

WORKFLOW_DECISION_APPROVE = 'APPROVE'
WORKFLOW_DECISION_REJECT = 'REJECT'
WORKFLOW_DECISION_ESCALATE = 'ESCALATE'
WORKFLOW_DECISION_DELEGATE = 'DELEGATE'


@dataclass(frozen=True)
class WorkflowStepDefinition:
  """A single approval step in a workflow blueprint."""

  name: str
  assigned_role: str
  order: int = 0
  # Phase 2 extensions
  parallel_group_id: str | None = None       # Steps with same group_id run in parallel
  condition: str | None = None               # Expression like "contract.value > 100000"
  timeout_hours: int | None = None           # Step SLA timeout
  escalation_role: str | None = None         # Who to escalate to on timeout
  delegation_allowed: bool = True            # Whether this step can be delegated


@dataclass(frozen=True)
class WorkflowDefinition:
  """Immutable workflow blueprint (WF-014)."""

  definition_id: str
  name: str
  steps: list[WorkflowStepDefinition] = field(default_factory=list)

  def __post_init__(self) -> None:
    ordered = sorted(self.steps, key=lambda s: s.order)
    object.__setattr__(self, 'steps', ordered)


class WorkflowStep:
  """Runtime state of one approval step."""

  def __init__(self, definition: WorkflowStepDefinition) -> None:
    self.name = definition.name
    self.assigned_role = definition.assigned_role
    self.status = STEP_STATUS_PENDING
    self.decided_by: str | None = None
    self.comment: str | None = None
    self.decided_at = None
    # Phase 2 runtime state
    self.parallel_group_id = definition.parallel_group_id
    self.condition = definition.condition
    self.timeout_hours = definition.timeout_hours
    self.escalation_role = definition.escalation_role
    self.delegation_allowed = definition.delegation_allowed
    self.started_at = utc_now()
    self.escalated_at: datetime | None = None
    self.delegated_to: str | None = None
    self.delegated_at: datetime | None = None

  def decide(self, decision: str, actor_id: str, comment: str | None = None) -> None:
    if self.status not in STEP_STATUS_ACTIVE:
      raise StateTransitionError('Step already decided', details={'step': self.name, 'status': self.status})
    self.status = decision
    self.decided_by = actor_id
    self.comment = comment
    self.decided_at = utc_now()

  def delegate(self, delegated_to: str, actor_id: str, comment: str | None = None) -> None:
    """Reassign this pending step to another user (delegation).

    Delegation is only allowed while the step is pending, and only if the
    step definition permits it.  The step keeps its assigned_role for
    authorization, so the delegated-to user must still hold that role.
    """
    if self.status != STEP_STATUS_PENDING:
      raise StateTransitionError('Cannot delegate a decided step', details={'step': self.name, 'status': self.status})
    if not self.delegation_allowed:
      raise StateTransitionError('Delegation not allowed for this step', details={'step': self.name})
    self.delegated_to = delegated_to
    self.delegated_at = utc_now()
    self.status = STEP_STATUS_DELEGATED
    self.decided_by = actor_id
    self.comment = comment

  def escalate(self, escalation_role: str, actor_id: str, comment: str | None = None) -> None:
    """Escalate a pending step to a higher role (e.g. on SLA timeout)."""
    if self.status not in (STEP_STATUS_PENDING, STEP_STATUS_DELEGATED):
      raise StateTransitionError('Cannot escalate a decided step', details={'step': self.name, 'status': self.status})
    self.escalated_at = utc_now()
    self.escalation_role = escalation_role
    self.status = STEP_STATUS_ESCALATED
    self.decided_by = actor_id
    self.comment = comment


class WorkflowInstance(Entity):
  """A running approval workflow for one contract."""

  def __init__(
    self,
    *,
    contract_id: str,
    definition: WorkflowDefinition,
    started_by: str,
    workflow_id: str | None = None,
  ) -> None:
    super().__init__(workflow_id)
    self.contract_id = contract_id
    self.definition_id = definition.definition_id
    self.definition_name = definition.name
    self.status = WORKFLOW_STATUS_RUNNING
    self.started_by = started_by
    self.steps: list[WorkflowStep] = [WorkflowStep(s) for s in definition.steps]
    self.current_step_index = 0
    self.history: list[dict[str, Any]] = []
    self._conditions = ConditionEvaluator()
    # Phase 2: pause state
    self.paused_at: datetime | None = None
    self.paused_by: str | None = None
    self.pause_reason: str | None = None

  @property
  def current_step(self) -> WorkflowStep | None:
    """The next active step from the current index (works within parallel groups)."""
    for step in self.steps[self.current_step_index:]:
      if step.status in STEP_STATUS_ACTIVE:
        return step
    return None

  def pending_steps(self) -> list[WorkflowStep]:
    """All steps currently eligible for a decision (parallel siblings included)."""
    pending = [s for s in self.steps if s.status in STEP_STATUS_ACTIVE]
    if not pending:
      return []
    if pending[0].parallel_group_id:
      return [s for s in pending if s.parallel_group_id == pending[0].parallel_group_id]
    return [pending[0]]

  def _decidable_step(self, step_name: str | None) -> WorkflowStep | None:
    if step_name is None:
      return self.current_step
    for step in self.pending_steps():
      if step.name == step_name:
        return step
    return None

  @property
  def is_paused(self) -> bool:
    return self.status == WORKFLOW_STATUS_PAUSED

  def pause(self, actor_id: str, reason: str) -> None:
    if self.status != WORKFLOW_STATUS_RUNNING:
      raise StateTransitionError('Only a running workflow can be paused', details={'status': self.status})
    self.status = WORKFLOW_STATUS_PAUSED
    self.paused_at = utc_now()
    self.paused_by = actor_id
    self.pause_reason = reason
    self.history.append({'from': 'RUNNING', 'to': 'PAUSED', 'actor_id': actor_id, 'reason': reason})

  def resume(self, actor_id: str) -> None:
    if self.status != WORKFLOW_STATUS_PAUSED:
      raise StateTransitionError('Only a paused workflow can be resumed', details={'status': self.status})
    self.status = WORKFLOW_STATUS_RUNNING
    self.paused_at = None
    self.paused_by = None
    self.pause_reason = None
    self.history.append({'from': 'PAUSED', 'to': 'RUNNING', 'actor_id': actor_id, 'reason': 'Workflow resumed'})

  def _all_parallel_steps_decided(self, group_id: str) -> bool:
    group_steps = [s for s in self.steps if s.parallel_group_id == group_id]
    return all(s.status in (STEP_STATUS_APPROVED, STEP_STATUS_REJECTED) for s in group_steps)
  def _any_parallel_step_rejected(self, group_id: str) -> bool:
    group_steps = [s for s in self.steps if s.parallel_group_id == group_id]
    return any(s.status == STEP_STATUS_REJECTED for s in group_steps)

  def _advance_past_parallel_group(self, group_id: str) -> None:
    """Move current_step_index past all steps in the given parallel group."""
    while self.current_step_index < len(self.steps):
      step = self.steps[self.current_step_index]
      if step.parallel_group_id != group_id:
        break
      self.current_step_index += 1

  def _evaluate_condition(self, step: WorkflowStep, contract: Any) -> bool:
    """Evaluate a step's condition expression against the contract.

    Uses the production ``ConditionEvaluator`` (safe AST evaluation, no
    arbitrary code execution).  A condition that fails to parse or does not
    produce a boolean is treated as not-runnable (step is skipped).
    """
    try:
      return self._conditions.evaluate(step.condition, contract)
    except Exception:  # noqa: BLE001 - condition failure must never crash the workflow
      # Invalid/unrunnable condition → treat as False (skip step).
      return False

  def _should_skip_step(self, step: WorkflowStep, contract: Any) -> bool:
    """Determine if a step should be skipped based on condition and parallel group state."""
    if not self._evaluate_condition(step, contract):
      return True
    # If step is in a parallel group and group already decided, skip
    return bool(step.parallel_group_id and self._all_parallel_steps_decided(step.parallel_group_id))

  def _find_next_pending_step(self, contract: Any) -> WorkflowStep | None:
    """Find the next step that should run, skipping conditional/parallel steps.

    Steps whose condition evaluates to false are marked SKIPPED and
    ``current_step_index`` advances past them so ``current_step`` always
    reflects the step that actually needs a decision.
    """
    i = self.current_step_index
    while i < len(self.steps):
      step = self.steps[i]
      if step.status in STEP_STATUS_ACTIVE and not self._should_skip_step(step, contract):
        self.current_step_index = i
        return step
      if step.status in STEP_STATUS_ACTIVE and self._should_skip_step(step, contract):
        step.status = STEP_STATUS_SKIPPED
      i += 1
    return None

  def approve(
    self,
    actor_id: str,
    comment: str | None = None,
    contract: Any = None,
    step_name: str | None = None,
  ) -> None:
    step = self._decidable_step(step_name)
    if step is None:
      raise StateTransitionError('Workflow has no pending step', details={'status': self.status})
    step.decide(STEP_STATUS_APPROVED, actor_id, comment)
    self.history.append({'from': self.status, 'to': 'STEP_APPROVED', 'actor_id': actor_id, 'reason': comment})

    # Handle parallel groups
    if step.parallel_group_id:
      if self._any_parallel_step_rejected(step.parallel_group_id):
        self.status = WORKFLOW_STATUS_REJECTED
        self.history.append({'from': 'STEP_APPROVED', 'to': WORKFLOW_STATUS_REJECTED, 'actor_id': actor_id, 'reason': 'Parallel step rejected'})
      elif self._all_parallel_steps_decided(step.parallel_group_id):
        self._advance_past_parallel_group(step.parallel_group_id)
        next_step = self._find_next_pending_step(contract)
        if next_step is None:
          self.status = WORKFLOW_STATUS_APPROVED
          self.history.append({'from': 'STEP_APPROVED', 'to': WORKFLOW_STATUS_APPROVED, 'actor_id': actor_id, 'reason': comment})
    else:
      # Linear step
      self.current_step_index += 1
      next_step = self._find_next_pending_step(contract)
      if next_step is None:
        self.status = WORKFLOW_STATUS_APPROVED
        self.history.append({'from': 'STEP_APPROVED', 'to': WORKFLOW_STATUS_APPROVED, 'actor_id': actor_id, 'reason': comment})

  def reject(self, actor_id: str, comment: str | None = None, step_name: str | None = None) -> None:
    step = self._decidable_step(step_name)
    if step is None:
      raise StateTransitionError('Workflow has no pending step', details={'status': self.status})
    step.decide(STEP_STATUS_REJECTED, actor_id, comment)
    self.status = WORKFLOW_STATUS_REJECTED
    self.history.append({'from': 'PENDING', 'to': WORKFLOW_STATUS_REJECTED, 'actor_id': actor_id, 'reason': comment})

  @property
  def is_approved(self) -> bool:
    return self.status == WORKFLOW_STATUS_APPROVED

  @property
  def is_rejected(self) -> bool:
    return self.status == WORKFLOW_STATUS_REJECTED

  @property
  def is_running(self) -> bool:
    return self.status == WORKFLOW_STATUS_RUNNING
