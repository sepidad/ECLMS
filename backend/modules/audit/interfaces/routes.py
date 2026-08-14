"""Audit module API routes (Constitution Article VIII)."""

from __future__ import annotations

import csv
from io import StringIO

from fastapi import APIRouter, Request
from fastapi.responses import Response

from backend.api.security import require_permission

router = APIRouter(tags=['Audit'])

CSV_COLUMNS = ('id', 'event_type', 'source_module', 'actor_id', 'entity_type', 'entity_id', 'created_at')


@router.get('')
async def list_audit_events(
  request: Request,
  limit: int = 50,
  offset: int = 0,
):
  _actor = await require_permission(request, 'user.manage')
  store = request.app.state.container.get_service('audit.store')
  events = await store.list_all(limit=max(1, min(limit, 200)), offset=max(0, offset))
  return {
    'success': True,
    'data': {
      'items': events,
      'limit': max(1, min(limit, 200)),
      'offset': max(0, offset),
    },
    'error': None,
  }


@router.get('/export.csv')
async def export_audit_csv(request: Request, limit: int = 500, offset: int = 0):
  """Return audit events as a CSV download (user.manage)."""
  await require_permission(request, 'user.manage')
  store = request.app.state.container.get_service('audit.store')
  events = await store.list_all(limit=max(1, min(limit, 5000)), offset=max(0, offset))
  buffer = StringIO()
  writer = csv.DictWriter(buffer, fieldnames=CSV_COLUMNS, extrasaction='ignore')
  writer.writeheader()
  for event in events:
    writer.writerow({column: event.get(column, '') for column in CSV_COLUMNS})
  return Response(
    content=buffer.getvalue(),
    media_type='text/csv',
    headers={'Content-Disposition': 'attachment; filename="audit_export.csv"'},
  )
