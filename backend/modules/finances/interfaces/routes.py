"""Finance API routes.

    POST   /api/v1/finances/commitments                (finance.create)
    GET    /api/v1/finances/commitments?contract_id=   (finance.read)
    POST   /api/v1/finances/commitments/{id}/payments  (finance.create)
    GET    /api/v1/finances/commitments/{id}/payments  (finance.read)
    POST   /api/v1/finances/payments/{id}/pay          (finance.update)
    POST   /api/v1/finances/payments/{id}/cancel       (finance.update)
    POST   /api/v1/finances/sweep-overdue              (user.manage)
    GET    /api/v1/finances/payments?status=           (finance.read)
"""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from backend.api.middleware.context import get_trace_id
from backend.api.responses import err, ok
from backend.api.security import require_permission
from backend.core.exceptions import ECLMSError
from backend.modules.finances.application.finance_service import FinanceService

router = APIRouter(tags=['finances'])


class CreateCommitmentRequest(BaseModel):
  contract_id: str = Field(min_length=1)
  description: str = Field(min_length=1, max_length=500)
  amount: float = Field(gt=0)
  currency: str = Field(default='USD', min_length=3, max_length=3)


class CreatePaymentRequest(BaseModel):
  amount: float = Field(gt=0)
  due_date: datetime


def _service(request: Request) -> FinanceService:
  return request.app.state.container.get_service('finances.service')


def _serialize_commitment(c) -> dict:
  return {
    'id': c.id,
    'contract_id': c.contract_id,
    'description': c.description,
    'amount': c.amount,
    'currency': c.currency,
    'status': c.status,
    'organization_id': c.organization_id,
    'created_by': c.created_by,
    'created_at': c.created_at,
  }


def _serialize_payment(p) -> dict:
  return {
    'id': p.id,
    'commitment_id': p.commitment_id,
    'amount': p.amount,
    'due_date': p.due_date,
    'status': p.status,
    'organization_id': p.organization_id,
    'paid_at': p.paid_at,
    'created_at': p.created_at,
  }


@router.post('/commitments')
async def create_commitment(payload: CreateCommitmentRequest, request: Request):
  try:
    actor = await require_permission(request, 'finance.create')
    service = _service(request)
    commitment = await service.create_commitment(
      contract_id=payload.contract_id,
      description=payload.description,
      amount=payload.amount,
      currency=payload.currency,
      organization_id=actor.organization_id,
      created_by=actor.id,
    )
  except ECLMSError as exc:
    return err(exc.code, exc.message, get_trace_id(), exc.details)
  return ok(_serialize_commitment(commitment), get_trace_id())


@router.get('/commitments')
async def list_commitments(
  request: Request,
  contract_id: str | None = None,
  limit: int = 100,
  offset: int = 0,
):
  try:
    actor = await require_permission(request, 'finance.read')
    service = _service(request)
    if contract_id:
      items = await service.list_commitments(
        contract_id, organization_id=actor.organization_id, limit=limit, offset=offset
      )
    else:
      items = await service.list_all_commitments(
        organization_id=actor.organization_id, limit=limit, offset=offset
      )
  except ECLMSError as exc:
    return err(exc.code, exc.message, get_trace_id(), exc.details)
  return ok({'items': [_serialize_commitment(c) for c in items]}, get_trace_id())


@router.post('/commitments/{commitment_id}/payments')
async def create_payment(commitment_id: str, payload: CreatePaymentRequest, request: Request):
  try:
    actor = await require_permission(request, 'finance.create')
    service = _service(request)
    payment = await service.create_payment(
      commitment_id=commitment_id,
      amount=payload.amount,
      due_date=payload.due_date,
      organization_id=actor.organization_id,
    )
  except ECLMSError as exc:
    return err(exc.code, exc.message, get_trace_id(), exc.details)
  return ok(_serialize_payment(payment), get_trace_id())


@router.get('/commitments/{commitment_id}/payments')
async def list_payments(
  commitment_id: str,
  request: Request,
  limit: int = 100,
  offset: int = 0,
):
  try:
    actor = await require_permission(request, 'finance.read')
    service = _service(request)
    items = await service.list_payments(
      commitment_id, organization_id=actor.organization_id, limit=limit, offset=offset
    )
  except ECLMSError as exc:
    return err(exc.code, exc.message, get_trace_id(), exc.details)
  return ok({'items': [_serialize_payment(p) for p in items]}, get_trace_id())


@router.post('/payments/{payment_id}/pay')
async def pay_payment(payment_id: str, request: Request):
  try:
    actor = await require_permission(request, 'finance.update')
    service = _service(request)
    payment = await service.mark_paid(
      payment_id, organization_id=actor.organization_id, actor_id=actor.id
    )
  except ECLMSError as exc:
    return err(exc.code, exc.message, get_trace_id(), exc.details)
  return ok(_serialize_payment(payment), get_trace_id())


@router.post('/payments/{payment_id}/cancel')
async def cancel_payment(payment_id: str, request: Request):
  try:
    actor = await require_permission(request, 'finance.update')
    service = _service(request)
    payment = await service.cancel_payment(
      payment_id, organization_id=actor.organization_id, actor_id=actor.id
    )
  except ECLMSError as exc:
    return err(exc.code, exc.message, get_trace_id(), exc.details)
  return ok(_serialize_payment(payment), get_trace_id())


@router.post('/sweep-overdue')
async def sweep_overdue(request: Request):
  try:
    await require_permission(request, 'user.manage')
    count = await _service(request).sweep_overdue()
  except ECLMSError as exc:
    return err(exc.code, exc.message, get_trace_id(), exc.details)
  return ok({'overdue': count}, get_trace_id())


@router.get('/payments')
async def list_all_payments(
  request: Request,
  status: str | None = None,
  limit: int = 100,
  offset: int = 0,
):
  try:
    actor = await require_permission(request, 'finance.read')
    service = _service(request)
    items = await service.list_all_payments(
      organization_id=actor.organization_id, status=status, limit=limit, offset=offset
    )
  except ECLMSError as exc:
    return err(exc.code, exc.message, get_trace_id(), exc.details)
  return ok({'items': [_serialize_payment(p) for p in items]}, get_trace_id())