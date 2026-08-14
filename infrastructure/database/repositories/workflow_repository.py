"""SQLAlchemy-backed workflow repository (Phase 1).

Persists workflow instances, their steps, and the immutable history log.
Each operation opens its own session from the shared async session
factory and commits on success.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from backend.core.exceptions import NotFoundError
from backend.core.utils import new_id, utc_now
from backend.modules.workflow.domain.workflow import WorkflowDefinition, WorkflowInstance, WorkflowStep
from infrastructure.database.models.contracts import ContractModel
from infrastructure.database.models.workflow import (
  WorkflowHistoryModel,
  WorkflowInstanceModel,
  WorkflowStepModel,
)
from infrastructure.database.session import get_session_factory


def _load_steps(instance: WorkflowInstanceModel, definition: WorkflowDefinition) -> list[WorkflowStep]:
  by_number = {s.step_number: s for s in instance.steps}
  steps: list[WorkflowStep] = []
  for step_def in definition.steps:
    model = by_number.get(step_def.order)
    if model is None:
      continue
    step = WorkflowStep(step_def)
    step.status = model.status
    step.decided_by = model.decided_by
    step.comment = model.comment
    step.decided_at = model.decided_at
    step.parallel_group_id = model.parallel_group_id
    step.condition = model.condition
    step.timeout_hours = model.timeout_hours
    step.escalation_role = model.escalation_role
    step.delegation_allowed = model.delegation_allowed
    step.started_at = model.started_at
    step.escalated_at = model.escalated_at
    step.delegated_to = model.delegated_to
    step.delegated_at = model.delegated_at
    steps.append(step)
  return steps


def _to_domain(instance: WorkflowInstanceModel, definition: WorkflowDefinition) -> WorkflowInstance:
  workflow = WorkflowInstance(
    contract_id=instance.contract_id,
    definition=definition,
    started_by=instance.started_by,
    workflow_id=instance.id,
  )
  workflow.created_at = instance.created_at
  workflow.updated_at = instance.updated_at
  workflow.status = instance.status
  workflow.paused_by = instance.paused_by
  workflow.pause_reason = instance.pause_reason
  workflow.paused_at = instance.paused_at
  workflow.steps = _load_steps(instance, definition)
  workflow.current_step_index = max(0, instance.current_step_number - 1)
  workflow.history = [
    {'from': h.from_state, 'to': h.to_state, 'actor_id': h.actor_id, 'reason': h.reason, 'created_at': h.created_at}
    for h in instance.history
  ]
  return workflow


class SqlWorkflowRepository:
  async def list_by_organization(
    self,
    organization_id: str,
    *,
    status: str | None = None,
    limit: int = 100,
    offset: int = 0,
  ) -> list[WorkflowInstance]:
    """List workflows through their owning contract's organization."""
    from backend.modules.workflow.domain.definitions import get_definition

    async with get_session_factory()() as session:
      conditions = [ContractModel.organization_id == organization_id]
      if status:
        conditions.append(WorkflowInstanceModel.status == status)
      stmt = (
        select(WorkflowInstanceModel)
        .join(ContractModel, ContractModel.id == WorkflowInstanceModel.contract_id)
        .where(*conditions)
        .order_by(WorkflowInstanceModel.updated_at.desc())
        .limit(limit)
        .offset(offset)
        .options(selectinload(WorkflowInstanceModel.steps), selectinload(WorkflowInstanceModel.history))
      )
      models = (await session.execute(stmt)).scalars().all()

    workflows: list[WorkflowInstance] = []
    for model in models:
      definition = get_definition(model.definition_id)
      if definition is not None:
        workflows.append(_to_domain(model, definition))
    return workflows

  async def create(self, workflow: WorkflowInstance) -> WorkflowInstance:
    async with get_session_factory()() as session:
      session.add(
        WorkflowInstanceModel(
          id=workflow.id,
          contract_id=workflow.contract_id,
          definition_id=workflow.definition_id,
          status=workflow.status,
          current_step_number=workflow.current_step_index + 1,
          started_by=workflow.started_by,
          paused_by=workflow.paused_by,
          pause_reason=workflow.pause_reason,
          paused_at=workflow.paused_at,
          created_at=workflow.created_at,
          updated_at=workflow.updated_at,
        )
      )
      for index, step in enumerate(workflow.steps, start=1):
        session.add(
          WorkflowStepModel(
            id=new_id(),
            instance_id=workflow.id,
            step_number=index,
            name=step.name,
            assigned_role=step.assigned_role,
            status=step.status,
            parallel_group_id=step.parallel_group_id,
            condition=step.condition,
            timeout_hours=step.timeout_hours,
            escalation_role=step.escalation_role,
            delegation_allowed=step.delegation_allowed,
            started_at=step.started_at,
            escalated_at=step.escalated_at,
            delegated_to=step.delegated_to,
            delegated_at=step.delegated_at,
          )
        )
      await session.commit()
    return workflow

  async def get_by_id(self, workflow_id: str) -> WorkflowInstance | None:
    from backend.modules.workflow.domain.definitions import get_definition

    async with get_session_factory()() as session:
      stmt = (
        select(WorkflowInstanceModel)
        .where(WorkflowInstanceModel.id == workflow_id)
        .options(selectinload(WorkflowInstanceModel.steps), selectinload(WorkflowInstanceModel.history))
      )
      model = (await session.execute(stmt)).scalar_one_or_none()
      if model is None:
        return None
      definition = get_definition(model.definition_id)
      if definition is None:
        return None
      return _to_domain(model, definition)

  async def require_by_id(self, workflow_id: str) -> WorkflowInstance:
    workflow = await self.get_by_id(workflow_id)
    if workflow is None:
      raise NotFoundError(f'Workflow not found: {workflow_id}')
    return workflow

  async def save(self, workflow: WorkflowInstance) -> WorkflowInstance:
    async with get_session_factory()() as session:
      instance = await session.get(WorkflowInstanceModel, workflow.id)
      if instance is None:
        raise NotFoundError(f'Workflow not found: {workflow.id}')
      instance.status = workflow.status
      instance.current_step_number = workflow.current_step_index + 1
      instance.paused_by = workflow.paused_by
      instance.pause_reason = workflow.pause_reason
      instance.paused_at = workflow.paused_at
      instance.updated_at = utc_now()

      for index, step in enumerate(workflow.steps, start=1):
        model = next((s for s in instance.steps if s.step_number == index), None)
        if model is not None:
          model.status = step.status
          model.decided_by = step.decided_by
          model.comment = step.comment
          model.decided_at = step.decided_at
          model.parallel_group_id = step.parallel_group_id
          model.condition = step.condition
          model.timeout_hours = step.timeout_hours
          model.escalation_role = step.escalation_role
          model.delegation_allowed = step.delegation_allowed
          model.started_at = step.started_at
          model.escalated_at = step.escalated_at
          model.delegated_to = step.delegated_to
          model.delegated_at = step.delegated_at

      await session.commit()
    return workflow

  async def append_history(
    self,
    workflow: WorkflowInstance,
    *,
    from_state: str,
    to_state: str,
    actor_id: str,
    reason: str | None = None,
  ) -> None:
    async with get_session_factory()() as session:
      session.add(
        WorkflowHistoryModel(
          id=new_id(),
          instance_id=workflow.id,
          from_state=from_state,
          to_state=to_state,
          actor_id=actor_id,
          reason=reason,
          created_at=utc_now(),
        )
      )
      await session.commit()

  async def list_history(self, workflow_id: str) -> list[dict]:
    async with get_session_factory()() as session:
      stmt = (
        select(WorkflowHistoryModel)
        .where(WorkflowHistoryModel.instance_id == workflow_id)
        .order_by(WorkflowHistoryModel.created_at)
      )
      models = (await session.execute(stmt)).scalars().all()
      return [
        {
          'from_state': h.from_state,
          'to_state': h.to_state,
          'actor_id': h.actor_id,
          'reason': h.reason,
          'created_at': h.created_at,
        }
        for h in models
      ]

  async def find_running_for_contract(self, contract_id: str) -> WorkflowInstance | None:
    async with get_session_factory()() as session:
      stmt = (
        select(WorkflowInstanceModel)
        .where(WorkflowInstanceModel.contract_id == contract_id)
        .options(selectinload(WorkflowInstanceModel.steps), selectinload(WorkflowInstanceModel.history))
      )
      model = (await session.execute(stmt)).scalars().all()
    for m in model:
      if m.status == 'RUNNING':
        from backend.modules.workflow.domain.definitions import get_definition

        definition = get_definition(m.definition_id)
        if definition is not None:
          return _to_domain(m, definition)
    return None

  async def find_all_running(self) -> list[WorkflowInstance]:
    """All running workflow instances (used by the escalation sweep)."""
    from backend.modules.workflow.domain.definitions import get_definition

    async with get_session_factory()() as session:
      stmt = (
        select(WorkflowInstanceModel)
        .where(WorkflowInstanceModel.status == 'RUNNING')
        .options(selectinload(WorkflowInstanceModel.steps), selectinload(WorkflowInstanceModel.history))
      )
      models = (await session.execute(stmt)).scalars().all()
    workflows: list[WorkflowInstance] = []
    for model in models:
      definition = get_definition(model.definition_id)
      if definition is not None:
        workflows.append(_to_domain(model, definition))
    return workflows
