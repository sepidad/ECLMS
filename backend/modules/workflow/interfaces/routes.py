"""Workflow API routes (API_CONTRACT_SPECIFICATION section 7.2).

    POST /api/v1/workflows/start              (contract.transition)
    POST /api/v1/workflows/{id}/transition    (contract.transition)
    POST /api/v1/workflows/{id}/pause         (contract.transition)
    POST /api/v1/workflows/{id}/resume        (contract.transition)
    POST /api/v1/workflows/{id}/delegate      (contract.transition)
    POST /api/v1/workflows/{id}/escalate      (contract.transition)
    POST /api/v1/workflows/escalate-overdue   (user.manage)
    GET  /api/v1/workflows/{id}               (contract.read)
    GET  /api/v1/workflows/{id}/history       (contract.read)

Controllers only validate and delegate to the application layer.
Authorization is enforced by the shared RBAC guards.
"""

from __future__ import annotations

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from backend.api.middleware.context import get_trace_id
from backend.api.responses import err, ok
from backend.api.security import require_permission
from backend.core.exceptions import ECLMSError
from backend.modules.workflow.application.workflow_service import (
  WORKFLOW_DECISION_APPROVE,
  WORKFLOW_DECISION_REJECT,
  WorkflowService,
)

router = APIRouter(tags=['workflows'])


class StartWorkflowRequest(BaseModel):
  contract_id: str = Field(min_length=1)
  definition_id: str | None = Field(default=None, max_length=100)


class TransitionRequest(BaseModel):
  decision: str = Field(pattern=f'^{WORKFLOW_DECISION_APPROVE}$|^{WORKFLOW_DECISION_REJECT}$')
  step_name: str | None = Field(default=None, max_length=200)
  comment: str | None = Field(default=None, max_length=2000)


class PauseRequest(BaseModel):
  reason: str = Field(min_length=1, max_length=1000)


class DelegateRequest(BaseModel):
  delegated_to: str = Field(min_length=1, max_length=100)
  step_name: str | None = Field(default=None, max_length=200)
  comment: str | None = Field(default=None, max_length=2000)


class EscalateRequest(BaseModel):
  role: str | None = Field(default=None, max_length=100)
  step_name: str | None = Field(default=None, max_length=200)
  comment: str | None = Field(default=None, max_length=2000)


def _service(request: Request) -> WorkflowService:
  return request.app.state.container.get_service('workflow.service')


@router.post('/start')
async def start_workflow(payload: StartWorkflowRequest, request: Request):
  try:
    actor = await require_permission(request, 'contract.transition')
    service = _service(request)
    workflow = await service.start(
      payload.contract_id,
      started_by=actor.id,
      organization_id=actor.organization_id,
      definition_id=payload.definition_id or 'contract-approval',
    )
  except ECLMSError as exc:
    return err(exc.code, exc.message, get_trace_id(), exc.details)
  return ok(_serialize(workflow), get_trace_id())


@router.get('')
async def list_workflows(
  request: Request,
  status: str | None = None,
  limit: int = 100,
  offset: int = 0,
):
  try:
    actor = await require_permission(request, 'contract.read')
    workflows = await _service(request).list_for_organization(
      organization_id=actor.organization_id,
      status=status,
      limit=max(1, min(limit, 200)),
      offset=max(offset, 0),
    )
  except ECLMSError as exc:
    return err(exc.code, exc.message, get_trace_id(), exc.details)
  return ok({'items': [_serialize(workflow) for workflow in workflows]}, get_trace_id())


@router.post('/{workflow_id}/transition')
async def transition(workflow_id: str, payload: TransitionRequest, request: Request):
  try:
    actor = await require_permission(request, 'contract.transition')
    service = _service(request)
    workflow = await service.decide(
      workflow_id,
      decision=payload.decision,
      actor_id=actor.id,
      comment=payload.comment,
      step_name=payload.step_name,
      organization_id=actor.organization_id,
    )
  except ECLMSError as exc:
    return err(exc.code, exc.message, get_trace_id(), exc.details)
  return ok(_serialize(workflow), get_trace_id())


@router.post('/{workflow_id}/pause')
async def pause_workflow(workflow_id: str, payload: PauseRequest, request: Request):
  try:
    actor = await require_permission(request, 'contract.transition')
    workflow = await _service(request).pause(
      workflow_id, actor_id=actor.id, organization_id=actor.organization_id, reason=payload.reason,
    )
  except ECLMSError as exc:
    return err(exc.code, exc.message, get_trace_id(), exc.details)
  return ok(_serialize(workflow), get_trace_id())


@router.post('/{workflow_id}/resume')
async def resume_workflow(workflow_id: str, request: Request):
  try:
    actor = await require_permission(request, 'contract.transition')
    workflow = await _service(request).resume(
      workflow_id, actor_id=actor.id, organization_id=actor.organization_id,
    )
  except ECLMSError as exc:
    return err(exc.code, exc.message, get_trace_id(), exc.details)
  return ok(_serialize(workflow), get_trace_id())


@router.post('/{workflow_id}/delegate')
async def delegate_step(workflow_id: str, payload: DelegateRequest, request: Request):
  try:
    actor = await require_permission(request, 'contract.transition')
    workflow = await _service(request).delegate(
      workflow_id,
      actor_id=actor.id,
      organization_id=actor.organization_id,
      delegated_to=payload.delegated_to,
      step_name=payload.step_name,
      comment=payload.comment,
    )
  except ECLMSError as exc:
    return err(exc.code, exc.message, get_trace_id(), exc.details)
  return ok(_serialize(workflow), get_trace_id())


@router.post('/{workflow_id}/escalate')
async def escalate_step(workflow_id: str, payload: EscalateRequest, request: Request):
  try:
    actor = await require_permission(request, 'contract.transition')
    workflow = await _service(request).escalate(
      workflow_id,
      actor_id=actor.id,
      organization_id=actor.organization_id,
      step_name=payload.step_name,
      role=payload.role,
      comment=payload.comment,
    )
  except ECLMSError as exc:
    return err(exc.code, exc.message, get_trace_id(), exc.details)
  return ok(_serialize(workflow), get_trace_id())


@router.post('/escalate-overdue')
async def escalate_overdue(request: Request):
  try:
    await require_permission(request, 'user.manage')
    count = await _service(request).escalate_overdue()
  except ECLMSError as exc:
    return err(exc.code, exc.message, get_trace_id(), exc.details)
  return ok({'escalated': count}, get_trace_id())


@router.get('/{workflow_id}')
async def get_workflow(workflow_id: str, request: Request):
  try:
    actor = await require_permission(request, 'contract.read')
    workflow = await _service(request).get(workflow_id, organization_id=actor.organization_id)
  except ECLMSError as exc:
    return err(exc.code, exc.message, get_trace_id(), exc.details)
  return ok(_serialize(workflow), get_trace_id())


@router.get('/{workflow_id}/history')
async def get_history(workflow_id: str, request: Request):
  try:
    actor = await require_permission(request, 'contract.read')
    items = await _service(request).history(workflow_id, organization_id=actor.organization_id)
  except ECLMSError as exc:
    return err(exc.code, exc.message, get_trace_id(), exc.details)
  return ok({'items': items}, get_trace_id())


def _serialize(workflow) -> dict:
  current = workflow.current_step
  return {
    'id': workflow.id,
    'contract_id': workflow.contract_id,
    'definition_id': workflow.definition_id,
    'status': workflow.status,
    'current_step_number': workflow.current_step_index + 1 if workflow.steps else None,
    'current_step': current.name if current else None,
    'current_step_role': current.assigned_role if current else None,
    'steps': [
      {
        'name': s.name,
        'assigned_role': s.assigned_role,
        'status': s.status,
        'parallel_group_id': s.parallel_group_id,
        'delegated_to': s.delegated_to,
        'escalated_at': s.escalated_at,
        'started_at': s.started_at,
        'timeout_hours': s.timeout_hours,
        'escalation_role': s.escalation_role,
        'decided_by': s.decided_by,
        'comment': s.comment,
      }
      for s in workflow.steps
    ],
  }
