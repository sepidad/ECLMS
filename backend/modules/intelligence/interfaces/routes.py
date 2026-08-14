"""Intelligence API routes (Phase 4).

    GET  /api/v1/intelligence/risk/contracts/{contract_id}   (intelligence.read)
    GET  /api/v1/intelligence/risk/overview                 (intelligence.read)
    GET  /api/v1/intelligence/clauses/{contract_id}         (intelligence.read)
    GET  /api/v1/intelligence/search                        (intelligence.read)
    GET  /api/v1/intelligence/alerts                        (intelligence.read)
    GET  /api/v1/intelligence/review/{contract_id}          (intelligence.read)

All endpoints are read-only, org-scoped, and guarded by RBAC.
"""

from __future__ import annotations

from fastapi import APIRouter, Request

from backend.api.middleware.context import get_trace_id
from backend.api.responses import err, ok
from backend.api.security import require_permission
from backend.core.exceptions import ECLMSError

router = APIRouter(tags=['intelligence'])


def _service(request: Request, key: str):
  return request.app.state.container.get_service(key)


@router.get('/review/{contract_id}')
async def review_contract(request: Request, contract_id: str, provider: str | None = None):
  """Run AI-assisted review on a contract's active version text.

  ``provider`` optionally overrides the configured reviewer: ``rules``
  (deterministic) or ``llm`` (external model).  When omitted, the
  configured default is used.
  """
  try:
    actor = await require_permission(request, 'intelligence.read')
    review_service = _service(request, 'intelligence.review')
    selected = _select_provider(request, provider) if provider else None
    result = await review_service.review_contract(
      contract_id, organization_id=actor.organization_id, provider=selected
    )
  except ECLMSError as exc:
    return err(exc.code, exc.message, get_trace_id(), exc.details)
  return ok(
    {
      'contract_id': result.contract_id,
      'version_number': result.version_number,
      'provider': result.provider,
      'overall_risk_level': result.overall_risk_level,
      'high_or_critical_count': result.high_or_critical_count,
      'findings': [f.__dict__ for f in result.findings],
    },
    get_trace_id(),
  )


def _select_provider(request: Request, provider: str):
  """Build a review provider on demand for a per-request override."""
  from backend.config import get_settings
  from backend.modules.intelligence.application.review_provider import (
    LlmReviewProvider,
    RuleBasedReviewProvider,
  )

  settings = get_settings()
  if provider == 'llm':
    return LlmReviewProvider(
      api_url=settings.llm_api_url,
      api_key=settings.llm_api_key,
      model=settings.llm_model,
      timeout_seconds=settings.llm_timeout_seconds,
    )
  return RuleBasedReviewProvider()


@router.get('/risk/contracts/{contract_id}')
async def assess_contract_risk(request: Request, contract_id: str):
  """Return the multi-dimensional risk profile for a single contract."""
  try:
    actor = await require_permission(request, 'intelligence.read')
    assessment = await _service(request, 'intelligence.risk').assess_contract_risk(
      contract_id, organization_id=actor.organization_id
    )
  except ECLMSError as exc:
    return err(exc.code, exc.message, get_trace_id(), exc.details)
  return ok(assessment.__dict__, get_trace_id())


@router.get('/risk/overview')
async def assess_organization_risk(request: Request):
  """Return the aggregate portfolio risk profile for the organization."""
  try:
    actor = await require_permission(request, 'intelligence.read')
    report = await _service(request, 'intelligence.risk').assess_organization_risk(
      organization_id=actor.organization_id
    )
  except ECLMSError as exc:
    return err(exc.code, exc.message, get_trace_id(), exc.details)
  return ok(report, get_trace_id())


@router.get('/clauses/{contract_id}')
async def analyze_clauses(request: Request, contract_id: str):
  """Return typed-clause analysis for a contract's active version text."""
  try:
    actor = await require_permission(request, 'intelligence.read')
    result = await _service(request, 'intelligence.clauses').analyze_contract(
      contract_id, organization_id=actor.organization_id
    )
  except ECLMSError as exc:
    return err(exc.code, exc.message, get_trace_id(), exc.details)
  return ok(result.__dict__, get_trace_id())


@router.get('/search')
async def semantic_search(request: Request, q: str, limit: int = 10):
  """Return contracts ranked by semantic similarity to the query text."""
  try:
    actor = await require_permission(request, 'intelligence.read')
    results = await _service(request, 'intelligence.search').search(
      q, organization_id=actor.organization_id, limit=max(1, min(limit, 50))
    )
  except ECLMSError as exc:
    return err(exc.code, exc.message, get_trace_id(), exc.details)
  return ok({'query': q, 'results': results}, get_trace_id())


@router.get('/alerts')
async def predictive_alerts(request: Request, horizon_days: int = 30):
  """Return forward-looking alerts for the organization portfolio."""
  try:
    actor = await require_permission(request, 'intelligence.read')
    alerts = await _service(request, 'intelligence.alerts').generate_alerts(
      organization_id=actor.organization_id, horizon_days=max(1, min(horizon_days, 365))
    )
  except ECLMSError as exc:
    return err(exc.code, exc.message, get_trace_id(), exc.details)
  return ok({'alerts': alerts, 'total': len(alerts)}, get_trace_id())
