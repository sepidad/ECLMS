"""Contract API routes (API_CONTRACT_SPECIFICATION section 4.2).

    POST   /api/v1/contracts                       (contract.create)
    GET    /api/v1/contracts                       (contract.read)
    GET    /api/v1/contracts/{id}                  (contract.read)
    PATCH  /api/v1/contracts/{id}                  (contract.update)
    GET    /api/v1/contracts/{id}/versions         (contract.read)
    POST   /api/v1/contracts/{id}/transition       (contract.transition)

Controllers only validate and delegate to the application layer.
Authorization is enforced by the shared RBAC guards.
"""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from backend.api.middleware.context import get_trace_id
from backend.api.responses import err, ok
from backend.api.security import require_abac, require_permission
from backend.core.exceptions import ECLMSError
from backend.modules.contracts.application.contract_service import ContractService
from backend.modules.contracts.domain.template import list_templates
from backend.modules.contracts.domain.structure import normalize_structure, numbered_structure, render_structure

router = APIRouter(tags=['contracts'])


class CreateContractRequest(BaseModel):
  title: str = Field(min_length=1, max_length=300)
  reference_number: str = Field(min_length=1, max_length=64)
  counterparty: str = Field(min_length=1, max_length=200)
  content: str | None = Field(default=None, max_length=200_000)
  structure: list[dict] | None = None


class UpdateContractRequest(BaseModel):
  title: str | None = Field(default=None, min_length=1, max_length=300)
  reference_number: str | None = Field(default=None, min_length=1, max_length=64)
  counterparty: str | None = Field(default=None, min_length=1, max_length=200)
  content: str | None = Field(default=None, max_length=200_000)
  structure: list[dict] | None = None


class TransitionRequest(BaseModel):
  new_state: str = Field(min_length=1)


class FeedbackRequest(BaseModel):
  version_id: str = Field(min_length=1)
  reviewer_role: str = Field(pattern='^(LEGAL|FINANCE)$')
  kind: str = Field(pattern='^(COMMENT|SUGGESTION|REJECTION)$')
  body: str = Field(min_length=1, max_length=10000)
  proposed_text: str | None = Field(default=None, max_length=200000)


class FeedbackDecisionRequest(BaseModel):
  status: str = Field(pattern='^(ACCEPTED|REJECTED)$')


class FeedbackMergeRequest(BaseModel):
  new_content: str = Field(min_length=1, max_length=200000)


class GuaranteeRequest(BaseModel):
  guarantee_type: str
  direction: str
  amount: float = Field(gt=0)
  currency: str = Field(min_length=1, max_length=8)
  issuer: str = Field(min_length=1, max_length=200)
  beneficiary: str = Field(min_length=1, max_length=200)
  serial_number: str = Field(min_length=1, max_length=100)
  valid_from: date
  expires_on: date


def _service(request: Request) -> ContractService:
  return request.app.state.container.get_service('contracts.service')


def _review_service(request: Request):
  return request.app.state.container.get_service('contracts.review.service')


def _guarantee_service(request: Request):
  return request.app.state.container.get_service('contracts.guarantee.service')


@router.get('/templates')
async def get_contract_templates(request: Request):
  """Return the approved Phase 6 template library for contract preparation."""
  try:
    await require_permission(request, 'contract.read')
  except ECLMSError as exc:
    return err(exc.code, exc.message, get_trace_id(), exc.details)
  return ok({'items': list_templates()}, get_trace_id())


@router.post('')
async def create_contract(payload: CreateContractRequest, request: Request):
  try:
    actor = await require_permission(request, 'contract.create')
    service = _service(request)
    create = payload.model_dump(exclude_none=True)
    if payload.structure is not None:
      normalized = normalize_structure(payload.structure)
      create['structure'] = normalized
      create['content'] = render_structure(normalized)
    contract = await service.create_contract(
      **create,
      organization_id=actor.organization_id,
      owner_id=actor.id,
    )
  except ECLMSError as exc:
    return err(exc.code, exc.message, get_trace_id(), exc.details)
  return ok({'id': contract.id, 'state': contract.state}, get_trace_id())


@router.get('')
async def list_contracts(request: Request, limit: int = 100, offset: int = 0):
  try:
    actor = await require_permission(request, 'contract.read')
    service = _service(request)
    limit = max(1, min(limit, 200))
    offset = max(0, offset)
    items = await service.list_contracts(organization_id=actor.organization_id, limit=limit, offset=offset)
    total = await service.count_contracts(organization_id=actor.organization_id)
  except ECLMSError as exc:
    return err(exc.code, exc.message, get_trace_id(), exc.details)
  return ok(
    {
      'items': [{'id': c.id, 'title': c.title, 'state': c.state, 'reference_number': c.reference_number} for c in items],
      'total': total,
      'limit': limit,
      'offset': offset,
    },
    get_trace_id(),
  )


@router.get('/{contract_id}')
async def get_contract(contract_id: str, request: Request):
  try:
    actor = await require_permission(request, 'contract.read')
    service = _service(request)
    contract = await service.get_contract(contract_id, organization_id=actor.organization_id)
  except ECLMSError as exc:
    return err(exc.code, exc.message, get_trace_id(), exc.details)
  return ok(
    {
      'id': contract.id,
      'title': contract.title,
      'reference_number': contract.reference_number,
      'counterparty': contract.counterparty,
      'state': contract.state,
      'organization_id': contract.organization_id,
      'owner_id': contract.owner_id,
    },
    get_trace_id(),
  )


@router.get('/{contract_id}/feedback')
async def list_feedback(contract_id: str, request: Request):
  try:
    actor = await require_permission(request, 'contract.read')
    items = await _review_service(request).list_feedback(contract_id, actor.organization_id)
  except ECLMSError as exc:
    return err(exc.code, exc.message, get_trace_id(), exc.details)
  return ok({'items': items}, get_trace_id())


@router.get('/guarantees/warnings')
async def guarantee_warnings(request: Request, days: int = 30):
  try:
    actor = await require_permission(request, 'contract.read')
    items = await _guarantee_service(request).warnings(actor.organization_id, max(1, min(days, 365)))
  except ECLMSError as exc:
    return err(exc.code, exc.message, get_trace_id(), exc.details)
  return ok({'items': items}, get_trace_id())


@router.get('/{contract_id}/guarantees')
async def list_guarantees(contract_id: str, request: Request):
  try:
    actor = await require_permission(request, 'contract.read')
    items = await _guarantee_service(request).list(contract_id, actor.organization_id)
  except ECLMSError as exc:
    return err(exc.code, exc.message, get_trace_id(), exc.details)
  return ok({'items': items}, get_trace_id())


@router.post('/{contract_id}/guarantees')
async def create_guarantee(contract_id: str, payload: GuaranteeRequest, request: Request):
  try:
    actor = await require_permission(request, 'contract.update')
    item = await _guarantee_service(request).create(contract_id=contract_id, organization_id=actor.organization_id, **payload.model_dump())
  except ECLMSError as exc:
    return err(exc.code, exc.message, get_trace_id(), exc.details)
  return ok({'id': item.id, 'state': item.state}, get_trace_id())


@router.post('/{contract_id}/feedback')
async def add_feedback(contract_id: str, payload: FeedbackRequest, request: Request):
  try:
    actor = await require_permission(request, 'contract.update')
    item = await _review_service(request).add_feedback(
      contract_id=contract_id, reviewer_id=actor.id, organization_id=actor.organization_id,
      **payload.model_dump(),
    )
  except ECLMSError as exc:
    return err(exc.code, exc.message, get_trace_id(), exc.details)
  return ok({'id': item.id, 'status': item.status}, get_trace_id())


@router.post('/feedback/{feedback_id}/decision')
async def decide_feedback(feedback_id: str, payload: FeedbackDecisionRequest, request: Request):
  try:
    await require_permission(request, 'contract.update')
    await _review_service(request).decide(feedback_id, payload.status)
  except ECLMSError as exc:
    return err(exc.code, exc.message, get_trace_id(), exc.details)
  return ok({'id': feedback_id, 'status': payload.status}, get_trace_id())


@router.post('/{contract_id}/feedback/{feedback_id}/merge')
async def merge_feedback(contract_id: str, feedback_id: str, payload: FeedbackMergeRequest, request: Request):
  try:
    actor = await require_permission(request, 'contract.update')
    contract = await _review_service(request).merge(
      contract_id=contract_id,
      feedback_id=feedback_id,
      new_content=payload.new_content,
      organization_id=actor.organization_id,
    )
  except ECLMSError as exc:
    return err(exc.code, exc.message, get_trace_id(), exc.details)
  return ok({'id': contract.id, 'state': contract.state, 'version_id': contract.current_version_id}, get_trace_id())


@router.patch('/{contract_id}')
async def update_contract(contract_id: str, payload: UpdateContractRequest, request: Request):
  try:
    actor = await require_permission(request, 'contract.update')
    service = _service(request)
    update = payload.model_dump(exclude_none=True)
    if payload.structure is not None:
      normalized = normalize_structure(payload.structure)
      _, _, _ = numbered_structure(normalized)
      update['structure'] = normalized
      update['content'] = render_structure(normalized)
    contract = await service.update_contract(
      contract_id,
      **update,
      organization_id=actor.organization_id,
    )
  except ECLMSError as exc:
    return err(exc.code, exc.message, get_trace_id(), exc.details)
  return ok({'id': contract.id, 'state': contract.state}, get_trace_id())


@router.get('/{contract_id}/versions')
async def list_versions(contract_id: str, request: Request):
  try:
    actor = await require_permission(request, 'contract.read')
    service = _service(request)
    versions = await service.list_versions(contract_id, organization_id=actor.organization_id)
  except ECLMSError as exc:
    return err(exc.code, exc.message, get_trace_id(), exc.details)
  return ok({'items': versions}, get_trace_id())


@router.post('/{contract_id}/transition')
async def transition(contract_id: str, payload: TransitionRequest, request: Request):
  try:
    actor = await require_permission(request, 'contract.transition')
    service = _service(request)
    contract = await service.transition(contract_id, payload.new_state, organization_id=actor.organization_id)
  except ECLMSError as exc:
    return err(exc.code, exc.message, get_trace_id(), exc.details)
  return ok({'id': contract.id, 'state': contract.state}, get_trace_id())


@router.get('/{contract_id}/abac-demo')
async def read_contract_abac(contract_id: str, request: Request):
  """Demo route guarding access with an ABAC policy (require_abac).

  Unlike the ordinary ``GET /contracts/{id}`` (RBAC + org scope only), this
  route evaluates the ABAC engine against the loaded contract as the
  resource.  The registered demo policy allows the read action only for the
  contract's owner, so a collaborator holding ``contract.read`` is denied
  unless they own the contract.
  """
  try:
    actor = await require_permission(request, 'contract.read')
    service = _service(request)
    contract = await service.get_contract(contract_id, organization_id=actor.organization_id)
    await require_abac(request, resource=contract, action='contract:read')
    result = {
      'id': contract.id,
      'title': contract.title,
      'state': contract.state,
      'owner_id': contract.owner_id,
    }
  except ECLMSError as exc:
    return err(exc.code, exc.message, get_trace_id(), exc.details)
  return ok({'contract': result, 'access': 'granted_by_abac'}, get_trace_id())
