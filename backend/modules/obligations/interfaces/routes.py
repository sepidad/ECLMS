"""Obligation API routes.

    POST   /api/v1/obligations                    (obligation.create)
    GET    /api/v1/obligations                    (obligation.read)
    GET    /api/v1/obligations/{id}               (obligation.read)
    POST   /api/v1/obligations/{id}/complete      (obligation.update)
    POST   /api/v1/obligations/{id}/cancel        (obligation.update)
    POST   /api/v1/obligations/sweep-overdue      (user.manage)
"""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from backend.api.middleware.context import get_trace_id
from backend.api.responses import err, ok
from backend.api.security import require_permission
from backend.core.exceptions import ECLMSError
from backend.modules.obligations.application.obligation_service import ObligationService

router = APIRouter(tags=['obligations'])


class CreateObligationRequest(BaseModel):
  contract_id: str = Field(min_length=1)
  description: str = Field(min_length=1, max_length=2000)
  due_date: datetime


def _service(request: Request) -> ObligationService:
  return request.app.state.container.get_service('obligations.service')


def _serialize(obligation) -> dict:
  return {
    'id': obligation.id,
    'contract_id': obligation.contract_id,
    'description': obligation.description,
    'due_date': obligation.due_date,
    'status': obligation.status,
    'organization_id': obligation.organization_id,
    'created_by': obligation.created_by,
    'completed_at': obligation.completed_at,
    'created_at': obligation.created_at,
  }


@router.post('')
async def create_obligation(payload: CreateObligationRequest, request: Request):
  try:
    actor = await require_permission(request, 'obligation.create')
    obligation = await _service(request).create(
      contract_id=payload.contract_id,
      description=payload.description,
      due_date=payload.due_date,
      organization_id=actor.organization_id,
      created_by=actor.id,
    )
  except ECLMSError as exc:
    return err(exc.code, exc.message, get_trace_id(), exc.details)
  return ok(_serialize(obligation), get_trace_id())


@router.get('')
async def list_obligations(
  request: Request,
  contract_id: str | None = None,
  status: str | None = None,
  limit: int = 100,
  offset: int = 0,
):
  try:
    actor = await require_permission(request, 'obligation.read')
    service = _service(request)
    limit = max(1, min(limit, 200))
    offset = max(0, offset)
    if contract_id:
      items = await service.list_for_contract(
        contract_id, organization_id=actor.organization_id, limit=limit, offset=offset
      )
    else:
      items = await service.list_all(
        organization_id=actor.organization_id, status=status, limit=limit, offset=offset
      )
  except ECLMSError as exc:
    return err(exc.code, exc.message, get_trace_id(), exc.details)
  return ok({'items': [_serialize(o) for o in items], 'limit': limit, 'offset': offset}, get_trace_id())


@router.post('/sweep-overdue')
async def sweep_overdue(request: Request):
  try:
    await require_permission(request, 'user.manage')
    count = await _service(request).sweep_overdue()
  except ECLMSError as exc:
    return err(exc.code, exc.message, get_trace_id(), exc.details)
  return ok({'overdue': count}, get_trace_id())


@router.get('/{obligation_id}')
async def get_obligation(obligation_id: str, request: Request):
  try:
    actor = await require_permission(request, 'obligation.read')
    obligation = await _service(request).get(
      obligation_id, organization_id=actor.organization_id
    )
  except ECLMSError as exc:
    return err(exc.code, exc.message, get_trace_id(), exc.details)
  return ok(_serialize(obligation), get_trace_id())


@router.post('/{obligation_id}/complete')
async def complete_obligation(obligation_id: str, request: Request):
  try:
    actor = await require_permission(request, 'obligation.update')
    obligation = await _service(request).complete(
      obligation_id, organization_id=actor.organization_id, actor_id=actor.id
    )
  except ECLMSError as exc:
    return err(exc.code, exc.message, get_trace_id(), exc.details)
  return ok(_serialize(obligation), get_trace_id())


@router.post('/{obligation_id}/cancel')
async def cancel_obligation(obligation_id: str, request: Request):
  try:
    actor = await require_permission(request, 'obligation.update')
    obligation = await _service(request).cancel(
      obligation_id, organization_id=actor.organization_id, actor_id=actor.id
    )
  except ECLMSError as exc:
    return err(exc.code, exc.message, get_trace_id(), exc.details)
  return ok(_serialize(obligation), get_trace_id())
