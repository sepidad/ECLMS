"""Data Import API routes.

    POST /api/v1/import/contracts   (data.import) — CSV: title, reference_number, counterparty, content
    POST /api/v1/import/obligations (data.import) — CSV: contract_reference, description, due_date
    POST /api/v1/import/commitments (data.import) — CSV: contract_reference, description, amount, currency

Each endpoint accepts raw CSV text as the request body and returns a
summary report (total / created / failed + per-row details).
"""

from __future__ import annotations

from fastapi import APIRouter, Request

from backend.api.middleware.context import get_trace_id
from backend.api.responses import err, ok
from backend.api.security import require_permission
from backend.core.exceptions import ECLMSError

router = APIRouter(tags=['import'])


def _service(request: Request):
  return request.app.state.container.get_service('import.service')


async def _import_csv(request: Request, kind: str) -> dict:
  actor = await require_permission(request, 'data.import')
  body = await request.body()
  csv_text = body.decode('utf-8', errors='replace')
  if not csv_text.strip():
    return err('BAD_REQUEST', 'Empty CSV body', get_trace_id())
  service = _service(request)
  if kind == 'contract':
    return ok(
      await service.import_contracts(
        csv_text=csv_text,
        organization_id=actor.organization_id,
        actor_id=actor.id,
      ),
      get_trace_id(),
    )
  if kind == 'obligation':
    return ok(
      await service.import_obligations(
        csv_text=csv_text,
        organization_id=actor.organization_id,
        actor_id=actor.id,
      ),
      get_trace_id(),
    )
  if kind == 'commitment':
    return ok(
      await service.import_commitments(
        csv_text=csv_text,
        organization_id=actor.organization_id,
        actor_id=actor.id,
      ),
      get_trace_id(),
    )
  return err('BAD_REQUEST', f'Unknown import kind: {kind}', get_trace_id())


@router.post('/contracts')
async def import_contracts(request: Request):
  try:
    return await _import_csv(request, 'contract')
  except ECLMSError as exc:
    return err(exc.code, exc.message, get_trace_id(), exc.details)


@router.post('/obligations')
async def import_obligations(request: Request):
  try:
    return await _import_csv(request, 'obligation')
  except ECLMSError as exc:
    return err(exc.code, exc.message, get_trace_id(), exc.details)


@router.post('/commitments')
async def import_commitments(request: Request):
  try:
    return await _import_csv(request, 'commitment')
  except ECLMSError as exc:
    return err(exc.code, exc.message, get_trace_id(), exc.details)