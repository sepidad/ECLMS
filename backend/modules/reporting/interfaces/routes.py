"""Reporting API routes (Phase 4, read-only analytics).

    GET   /api/v1/reporting/overview            (reporting.read)
    GET   /api/v1/reporting/export.csv        (reporting.read)

All endpoints are read-only, org-scoped, and guarded by RBAC.
"""

from __future__ import annotations

import csv
import io

from fastapi import APIRouter, Query, Request
from fastapi.responses import Response

from backend.api.middleware.context import get_trace_id
from backend.api.responses import err, ok
from backend.api.security import require_permission
from backend.core.exceptions import ECLMSError
from backend.modules.reporting.application.reporting_service import ReportingService

router = APIRouter(tags=['reporting'])


def _service(request: Request) -> ReportingService:
  return request.app.state.container.get_service('reporting.service')


@router.get('/overview')
async def get_report_overview(request: Request):
  """Return aggregated analytics across contracts, workflows, obligations, finances."""
  try:
    actor = await require_permission(request, 'reporting.read')
    report = await _service(request).full_report(organization_id=actor.organization_id)
  except ECLMSError as exc:
    return err(exc.code, exc.message, get_trace_id(), exc.details)
  return ok(report, get_trace_id())


@router.get('/trends')
async def get_report_trends(request: Request, months: int = Query(default=6, ge=3, le=24)):
  """Return org-scoped monthly portfolio and payment trend buckets."""
  try:
    actor = await require_permission(request, 'reporting.read')
    trends = await _service(request).portfolio_trends(
      organization_id=actor.organization_id,
      months=months,
    )
  except ECLMSError as exc:
    return err(exc.code, exc.message, get_trace_id(), exc.details)
  return ok({'months': trends}, get_trace_id())


@router.get('/export.csv')
async def export_report(request: Request):
  """Download an org-scoped CSV snapshot of contracts, obligations, and payments."""
  try:
    actor = await require_permission(request, 'reporting.read')
    container = request.app.state.container

    contracts = await container.get_service('contracts.service').list_contracts(
      organization_id=actor.organization_id, limit=100000
    )
    obligations = await container.get_service('obligations.service').list_all(
      organization_id=actor.organization_id, limit=100000
    )
    payments = await container.get_service('finances.service').list_all_payments(
      organization_id=actor.organization_id, limit=100000
    )
  except ECLMSError as exc:
    return err(exc.code, exc.message, get_trace_id(), exc.details)

  buf = io.StringIO()
  writer = csv.writer(buf)

  writer.writerow(['# ECLMS contract portfolio export'])
  writer.writerow(['contract_id', 'title', 'reference_number', 'counterparty', 'state', 'created_at'])
  for c in contracts:
    writer.writerow([
      c.id,
      c.title,
      c.reference_number,
      c.counterparty,
      c.state,
      c.created_at.isoformat() if c.created_at else '',
    ])
  writer.writerow([])

  writer.writerow(['# Obligations'])
  writer.writerow(['obligation_id', 'contract_id', 'description', 'due_date', 'status'])
  for o in obligations:
    writer.writerow([
      o.id,
      o.contract_id,
      o.description,
      o.due_date.isoformat() if o.due_date else '',
      o.status,
    ])
  writer.writerow([])

  writer.writerow(['# Payment schedule'])
  writer.writerow(['payment_id', 'commitment_id', 'amount', 'due_date', 'status'])
  for p in payments:
    writer.writerow([
      p.id,
      p.commitment_id,
      p.amount,
      p.due_date.isoformat() if p.due_date else '',
      p.status,
    ])

  return Response(
    content=buf.getvalue(),
    media_type='text/csv',
    headers={'Content-Disposition': 'attachment; filename="eclms-report.csv"'},
  )
