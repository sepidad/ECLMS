"""Reporting application service (Phase 4, read-only analytics).

Coordinates aggregate queries from the reporting repository, keeping
routes thin.  All reads are org-scoped (ADR-003); computation happens
over derived aggregates that never mutate operational data.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
  from infrastructure.database.repositories.reporting_repository import SqlReportingRepository


class ReportingService:
  def __init__(self, repository: SqlReportingRepository) -> None:
    self._repository = repository

  async def contract_overview(self, *, organization_id: str) -> dict:
    by_state = await self._repository.contracts_by_state(organization_id=organization_id)
    total = await self._repository.contract_total(organization_id=organization_id)
    avg_days = await self._repository.contract_avg_lifecycle_days(organization_id=organization_id)
    return {
      'total_contracts': total,
      'by_state': by_state,
      'active': by_state.get('ACTIVE', 0),
      'avg_lifecycle_days': avg_days,
    }

  async def workflow_overview(self, *, organization_id: str) -> dict:
    return await self._repository.workflow_overview(organization_id=organization_id)

  async def obligation_overview(self, *, organization_id: str) -> dict:
    return await self._repository.obligation_overview(organization_id=organization_id)

  async def finance_overview(self, *, organization_id: str) -> dict:
    return await self._repository.finance_overview(organization_id=organization_id)

  async def full_report(self, *, organization_id: str) -> dict:
    """Aggregate all domains into a single overview report."""
    return {
      'contracts': await self.contract_overview(organization_id=organization_id),
      'workflows': await self.workflow_overview(organization_id=organization_id),
      'obligations': await self.obligation_overview(organization_id=organization_id),
      'finances': await self.finance_overview(organization_id=organization_id),
    }

  async def portfolio_trends(self, *, organization_id: str, months: int = 6) -> list[dict]:
    return await self._repository.portfolio_trends(organization_id=organization_id, months=months)
