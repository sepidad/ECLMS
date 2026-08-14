"""Integration connector API routes.

    GET    /api/v1/integration/connectors               (user.manage)
    POST   /api/v1/integration/connectors/{id}/sync     (user.manage)
    GET    /api/v1/integration/connectors/syncs         (user.manage)

Mounted by the Integration module directly onto the gateway.
"""

from __future__ import annotations

from fastapi import APIRouter, Request

from backend.api.middleware.context import get_trace_id
from backend.api.responses import err, ok
from backend.api.security import require_permission
from backend.core.exceptions import ECLMSError

router = APIRouter(tags=['integration'])


def _connectors(request: Request):
  return request.app.state.container.get_service('integration.connectors')


@router.get('/connectors')
async def list_connectors(request: Request):
  try:
    await require_permission(request, 'user.manage')
    connectors = _connectors(request).list_connectors()
  except ECLMSError as exc:
    return err(exc.code, exc.message, get_trace_id(), exc.details)
  return ok({'items': connectors}, get_trace_id())


@router.post('/connectors/{connector_id}/sync')
async def sync_connector(connector_id: str, request: Request):
  try:
    actor = await require_permission(request, 'user.manage')
    result = await _connectors(request).sync(
      connector_id, organization_id=actor.organization_id,
    )
  except KeyError:
    return err('NOT_FOUND', f'Unknown connector: {connector_id}', get_trace_id())
  except ECLMSError as exc:
    return err(exc.code, exc.message, get_trace_id(), exc.details)
  return ok({'connector_id': connector_id, **result}, get_trace_id())


@router.get('/connectors/syncs')
async def list_connector_syncs(request: Request, limit: int = 50, offset: int = 0):
  try:
    actor = await require_permission(request, 'user.manage')
    limit = max(1, min(limit, 200))
    offset = max(offset, 0)
    items = await _connectors(request).list_syncs(
      actor.organization_id, limit=limit, offset=offset,
    )
  except ECLMSError as exc:
    return err(exc.code, exc.message, get_trace_id(), exc.details)
  return ok({'items': items, 'limit': limit, 'offset': offset}, get_trace_id())


def register_connector_routes(gateway) -> None:
  gateway.mount('integration', router)