"""Predictive Alerts Service (Phase 4 Intelligence).

Derives forward-looking alerts from contract expirations, open
obligations, scheduled payments, and portfolio risk scores.  Alerts are
computed on demand; the same signals feed the batch sweep worker.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, timedelta
from typing import TYPE_CHECKING

from backend.core.utils import utc_now
from backend.modules.intelligence.domain.risk import RISK_LEVEL_CRITICAL, RISK_LEVEL_HIGH
from shared.constants import CONTRACT_STATE_ARCHIVED, CONTRACT_STATE_EXPIRED, CONTRACT_STATE_TERMINATED

if TYPE_CHECKING:
  from backend.modules.contracts.application.contract_service import ContractService
  from backend.modules.finances.application.finance_service import FinanceService
  from backend.modules.intelligence.application.risk_service import RiskService
  from backend.modules.obligations.application.obligation_service import ObligationService

NON_ACTIVE_STATES = {CONTRACT_STATE_EXPIRED, CONTRACT_STATE_TERMINATED, CONTRACT_STATE_ARCHIVED}
DEFAULT_HORIZON_DAYS = 30
DUE_SOON_HORIZON_DAYS = 7

_SEVERITY_RANK = {'LOW': 1, 'MEDIUM': 2, 'HIGH': 3, 'CRITICAL': 4}


@dataclass
class AlertItem:
  alert_type: str  # contract.expiring / contract.expired / obligation.due / payment.due / contract.high_risk
  severity: str  # LOW / MEDIUM / HIGH / CRITICAL
  message: str
  contract_id: str | None = None
  entity_id: str | None = None
  entity_type: str | None = None
  details: dict = field(default_factory=dict)


class PredictiveAlertsService:
  def __init__(
    self,
    contracts: ContractService,
    obligations: ObligationService | None = None,
    finances: FinanceService | None = None,
    risks: RiskService | None = None,
  ) -> None:
    self._contracts = contracts
    self._obligations = obligations
    self._finances = finances
    self._risks = risks

  @staticmethod
  def _aware(dt) -> None:
    return dt.replace(tzinfo=UTC) if dt is not None and dt.tzinfo is None else dt

  async def generate_alerts(self, *, organization_id: str, horizon_days: int = DEFAULT_HORIZON_DAYS) -> list[dict]:
    """Generate forward-looking alerts for the whole organization portfolio."""
    alerts: list[AlertItem] = []
    now = utc_now()
    horizon = now + timedelta(days=horizon_days)

    contracts = await self._contracts.list_contracts(organization_id=organization_id)
    for contract in contracts:
      if contract.expiry_date:
        expiry = self._aware(contract.expiry_date)
        if expiry < now and contract.state not in NON_ACTIVE_STATES:
          alerts.append(
            AlertItem(
              alert_type='contract.expired',
              severity='CRITICAL',
              message=f'Contract "{contract.title}" passed its expiry date',
              contract_id=contract.id,
              entity_type='contract',
              entity_id=contract.id,
              details={'expiry_date': expiry.isoformat()},
            )
          )
        elif now <= expiry <= horizon and contract.state not in NON_ACTIVE_STATES:
          days_left = (expiry - now).days
          alerts.append(
            AlertItem(
              alert_type='contract.expiring',
              severity='HIGH' if days_left <= DUE_SOON_HORIZON_DAYS else 'MEDIUM',
              message=f'Contract "{contract.title}" expires in {days_left} day(s)',
              contract_id=contract.id,
              entity_type='contract',
              entity_id=contract.id,
              details={'expiry_date': expiry.isoformat(), 'days_remaining': days_left},
            )
          )

    if self._obligations:
      open_obligations = await self._obligations.list_all(organization_id=organization_id, status='OPEN')
      for obligation in open_obligations:
        due = self._aware(obligation.due_date)
        if now <= due <= now + timedelta(days=DUE_SOON_HORIZON_DAYS):
          days_left = (due - now).days
          alerts.append(
            AlertItem(
              alert_type='obligation.due',
              severity='MEDIUM',
              message=f'Obligation due in {days_left} day(s): {obligation.description[:80]}',
              contract_id=obligation.contract_id,
              entity_type='obligation',
              entity_id=obligation.id,
              details={'due_date': due.isoformat(), 'days_remaining': days_left},
            )
          )

    if self._finances:
      scheduled = await self._finances.list_all_payments(organization_id=organization_id, status='SCHEDULED')
      for payment in scheduled:
        due = self._aware(payment.due_date)
        if now <= due <= now + timedelta(days=DUE_SOON_HORIZON_DAYS):
          days_left = (due - now).days
          alerts.append(
            AlertItem(
              alert_type='payment.due',
              severity='MEDIUM',
              message=f'Payment of {payment.amount:.2f} due in {days_left} day(s)',
              entity_type='payment',
              entity_id=payment.id,
              details={'due_date': due.isoformat(), 'days_remaining': days_left, 'amount': payment.amount},
            )
          )

    if self._risks:
      for contract in contracts:
        assessment = await self._risks.assess_contract_risk(contract.id, organization_id=organization_id)
        if assessment.risk_level in (RISK_LEVEL_HIGH, RISK_LEVEL_CRITICAL):
          alerts.append(
            AlertItem(
              alert_type='contract.high_risk',
              severity=assessment.risk_level,
              message=(
                f'Contract "{contract.title}" risk level {assessment.risk_level} '
                f'(score {assessment.overall_score})'
              ),
              contract_id=contract.id,
              entity_type='contract',
              entity_id=contract.id,
              details={'risk_score': assessment.overall_score, 'risk_factors': len(assessment.risk_factors)},
            )
          )

    alerts.sort(key=lambda a: _SEVERITY_RANK.get(a.severity, 0), reverse=True)
    return [item.__dict__ for item in alerts]
