"""SQLAlchemy-backed reporting repository (Phase 4, read-only analytics).

Produces aggregated, read-optimized statistics over existing operational
data (contracts, workflows, finances, obligations).  Reporting never
mutates source data (RPT-022 section 2), just reads and aggregates.

Every query is org-scoped (ADR-003).  Workflow scoping is derived through
the owning contract's organization_id.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import func, select

from infrastructure.database.models.contracts import ContractModel
from infrastructure.database.models.finances import (
  FinanceCommitmentModel,
  FinancePaymentModel,
)
from infrastructure.database.models.obligations import ObligationModel
from infrastructure.database.models.workflow import WorkflowInstanceModel, WorkflowStepModel
from infrastructure.database.session import get_session_factory


class SqlReportingRepository:
  """Aggregate queries for contract/workflow/finance/obligation analytics."""

  async def contracts_by_state(self, *, organization_id: str) -> dict[str, int]:
    async with get_session_factory()() as session:
      stmt = (
        select(ContractModel.state, func.count())
        .where(ContractModel.organization_id == organization_id)
        .group_by(ContractModel.state)
      )
      return {state: count for state, count in (await session.execute(stmt)).all()}

  async def contract_total(self, *, organization_id: str) -> int:
    async with get_session_factory()() as session:
      stmt = select(func.count()).select_from(ContractModel).where(
        ContractModel.organization_id == organization_id
      )
      return (await session.scalar(stmt)) or 0

  async def contract_avg_lifecycle_days(self, *, organization_id: str) -> float | None:
    async with get_session_factory()() as session:
      stmt = (
        select(func.count())
        .select_from(ContractModel)
        .where(ContractModel.organization_id == organization_id)
      )
      total = (await session.scalar(stmt)) or 0
      if total == 0:
        return None
      # Average age of all contracts (created_at -> now).
      stmt = (
        select(func.avg(func.extract('epoch', func.now() - ContractModel.created_at)))
        .where(ContractModel.organization_id == organization_id)
      )
      seconds = (await session.scalar(stmt)) or 0
      return round(float(seconds) / 86400.0, 2)

  async def workflow_overview(self, *, organization_id: str) -> dict:
    async with get_session_factory()() as session:
      # Total workflows scoped via the owning contract's org.
      total_stmt = (
        select(func.count())
        .select_from(WorkflowInstanceModel)
        .join(ContractModel, ContractModel.id == WorkflowInstanceModel.contract_id)
        .where(ContractModel.organization_id == organization_id)
      )
      total = (await session.scalar(total_stmt)) or 0

      by_status_stmt = (
        select(WorkflowInstanceModel.status, func.count())
        .join(ContractModel, ContractModel.id == WorkflowInstanceModel.contract_id)
        .where(ContractModel.organization_id == organization_id)
        .group_by(WorkflowInstanceModel.status)
      )
      by_status = {
        status: count for status, count in (await session.execute(by_status_stmt)).all()
      }

      # Average step approval time (decided_at - started_at) for decided steps.
      avg_stmt = (
        select(func.avg(
          func.extract(
            'epoch',
            WorkflowStepModel.decided_at - WorkflowStepModel.started_at,
          )
        ))
        .join(
          WorkflowInstanceModel,
          WorkflowInstanceModel.id == WorkflowStepModel.instance_id,
        )
        .join(ContractModel, ContractModel.id == WorkflowInstanceModel.contract_id)
        .where(
          ContractModel.organization_id == organization_id,
          WorkflowStepModel.decided_at.isnot(None),
          WorkflowStepModel.started_at.isnot(None),
        )
      )
      avg_seconds = (await session.scalar(avg_stmt)) or 0

      return {
        'total_workflows': total,
        'by_status': by_status,
        'avg_step_days': round(float(avg_seconds) / 86400.0, 2),
      }

  async def obligation_overview(self, *, organization_id: str) -> dict:
    async with get_session_factory()() as session:
      by_status_stmt = (
        select(ObligationModel.status, func.count())
        .where(ObligationModel.organization_id == organization_id)
        .group_by(ObligationModel.status)
      )
      by_status = {
        status: count for status, count in (await session.execute(by_status_stmt)).all()
      }
      total = sum(by_status.values())

      # SLA compliance: completed obligations that finished on/before due date.
      sla_stmt = (
        select(func.count())
        .select_from(ObligationModel)
        .where(
          ObligationModel.organization_id == organization_id,
          ObligationModel.status == 'COMPLETED',
          ObligationModel.completed_at.isnot(None),
          ObligationModel.completed_at <= ObligationModel.due_date,
        )
      )
      on_time = (await session.scalar(sla_stmt)) or 0
      completed = by_status.get('COMPLETED', 0)

      return {
        'total_obligations': total,
        'by_status': by_status,
        'overdue': by_status.get('OVERDUE', 0),
        'sla_compliance_rate': round(on_time / completed, 2) if completed else None,
      }

  async def finance_overview(self, *, organization_id: str) -> dict:
    async with get_session_factory()() as session:
      total_value = (await session.scalar(
        select(func.coalesce(func.sum(FinancePaymentModel.amount), 0.0)).where(
          FinancePaymentModel.organization_id == organization_id,
          FinancePaymentModel.status != 'CANCELLED',
        )
      )) or 0.0

      paid = (await session.scalar(
        select(func.coalesce(func.sum(FinancePaymentModel.amount), 0.0)).where(
          FinancePaymentModel.organization_id == organization_id,
          FinancePaymentModel.status == 'PAID',
        )
      )) or 0.0

      total_payments = (await session.scalar(
        select(func.count())
        .select_from(FinancePaymentModel)
        .where(FinancePaymentModel.organization_id == organization_id)
      )) or 0

      overdue_payments = (await session.scalar(
        select(func.count())
        .select_from(FinancePaymentModel)
        .where(
          FinancePaymentModel.organization_id == organization_id,
          FinancePaymentModel.status == 'OVERDUE',
        )
      )) or 0

      active_exposure = (await session.scalar(
        select(func.coalesce(func.sum(FinanceCommitmentModel.amount), 0.0)).where(
          FinanceCommitmentModel.organization_id == organization_id,
          FinanceCommitmentModel.status == 'OPEN',
        )
      )) or 0.0

      return {
        'total_value': round(float(total_value), 2),
        'paid': round(float(paid), 2),
        'payment_completion_rate': round(float(paid) / float(total_value), 2) if total_value else None,
        'total_payments': total_payments,
        'overdue_payments': overdue_payments,
        'active_exposure': round(float(active_exposure), 2),
      }

  async def portfolio_trends(self, *, organization_id: str, months: int = 6) -> list[dict]:
    """Return month buckets for the portfolio command center.

    Bucketing is deliberately done in Python rather than with a database-
    specific date function so the same reporting contract works on SQLite,
    PostgreSQL, and the test database.
    """
    months = max(3, min(months, 24))
    now = datetime.now(UTC)
    first_month = now.month - months + 1
    start_year = now.year + (first_month - 1) // 12
    start_month = (first_month - 1) % 12 + 1

    def month_key(value: datetime) -> str:
      return f'{value.year:04d}-{value.month:02d}'

    keys: list[str] = []
    year, month = start_year, start_month
    for _ in range(months):
      keys.append(f'{year:04d}-{month:02d}')
      month += 1
      if month == 13:
        year += 1
        month = 1

    async with get_session_factory()() as session:
      contract_rows = (await session.execute(
        select(ContractModel.created_at).where(ContractModel.organization_id == organization_id)
      )).scalars().all()
      payment_rows = (await session.execute(
        select(FinancePaymentModel.due_date, FinancePaymentModel.amount, FinancePaymentModel.status)
        .where(FinancePaymentModel.organization_id == organization_id)
      )).all()
      obligation_rows = (await session.execute(
        select(ObligationModel.due_date, ObligationModel.status)
        .where(ObligationModel.organization_id == organization_id)
      )).all()

    buckets = {
      key: {
        'month': key,
        'contracts_created': 0,
        'payments_scheduled': 0,
        'payments_paid': 0,
        'obligations_due': 0,
      }
      for key in keys
    }
    for created_at in contract_rows:
      bucket = buckets.get(month_key(created_at))
      if bucket:
        bucket['contracts_created'] += 1
    for due_date, amount, status in payment_rows:
      bucket = buckets.get(month_key(due_date))
      if bucket:
        bucket['payments_scheduled'] += round(float(amount or 0), 2)
        if status == 'PAID':
          bucket['payments_paid'] += round(float(amount or 0), 2)
    for due_date, status in obligation_rows:
      bucket = buckets.get(month_key(due_date))
      if bucket and status != 'CANCELLED':
        bucket['obligations_due'] += 1
    return list(buckets.values())
