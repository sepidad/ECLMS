"""Risk Service (Phase 4 Intelligence).

Evaluates contracts and organizational portfolios against multi-dimensional
risk rules: contract expirations, financial payment overruns, obligation
defaults, and workflow SLA escalations.
"""

from __future__ import annotations

from datetime import UTC, timedelta
from typing import TYPE_CHECKING

from backend.core.utils import utc_now
from backend.modules.intelligence.domain.risk import (
  RISK_LEVEL_CRITICAL,
  RISK_LEVEL_HIGH,
  RiskAssessment,
  RiskFactor,
)
from shared.constants import CONTRACT_STATE_ARCHIVED, CONTRACT_STATE_EXPIRED, CONTRACT_STATE_TERMINATED

if TYPE_CHECKING:
  from backend.modules.contracts.application.contract_service import ContractService
  from backend.modules.finances.application.finance_service import FinanceService
  from backend.modules.obligations.application.obligation_service import ObligationService

NON_EXPOSED_CONTRACT_STATES = {CONTRACT_STATE_EXPIRED, CONTRACT_STATE_TERMINATED, CONTRACT_STATE_ARCHIVED}


class RiskService:
  def __init__(
    self,
    contracts: ContractService,
    finances: FinanceService | None = None,
    obligations: ObligationService | None = None,
  ) -> None:
    self._contracts = contracts
    self._finances = finances
    self._obligations = obligations

  async def assess_contract_risk(self, contract_id: str, *, organization_id: str) -> RiskAssessment:
    """Evaluate all risk factors for a specific contract."""
    contract = await self._contracts.get_contract(contract_id, organization_id=organization_id)
    factors: list[RiskFactor] = []
    now = utc_now()

    # 1. Expiration Risk
    if contract.expiry_date:
      exp = contract.expiry_date
      if exp.tzinfo is None:
        exp = exp.replace(tzinfo=UTC)

      if exp < now and contract.state not in NON_EXPOSED_CONTRACT_STATES:
        factors.append(
          RiskFactor(
            category='EXPIRATION',
            severity=RISK_LEVEL_CRITICAL,
            score_impact=40,
            code='CONTRACT_PAST_EXPIRY',
            message=f'Contract passed expiry date ({exp.strftime("%Y-%m-%d")}) while active',
            details={'expiry_date': exp.isoformat(), 'state': contract.state},
          )
        )
      elif exp <= now + timedelta(days=30) and contract.state not in NON_EXPOSED_CONTRACT_STATES:
        days_left = max(0, (exp - now).days)
        factors.append(
          RiskFactor(
            category='EXPIRATION',
            severity=RISK_LEVEL_HIGH,
            score_impact=25,
            code='CONTRACT_EXPIRING_SOON',
            message=f'Contract expires in {days_left} day(s)',
            details={'expiry_date': exp.isoformat(), 'days_remaining': days_left},
          )
        )

    # 2. Obligation Risk
    if self._obligations:
      obligations = await self._obligations.list_for_contract(contract_id, organization_id=organization_id)
      overdue = [o for o in obligations if o.status == 'OVERDUE']
      if overdue:
        factors.append(
          RiskFactor(
            category='OBLIGATION',
            severity=RISK_LEVEL_HIGH,
            score_impact=30,
            code='OVERDUE_OBLIGATIONS',
            message=f'Contract has {len(overdue)} overdue obligation(s)',
            details={'overdue_count': len(overdue)},
          )
        )

    # 3. Financial Payment Risk
    if self._finances:
      commitments = await self._finances.list_commitments(contract_id, organization_id=organization_id)
      overdue_payments = 0
      for commitment in commitments:
        payments = await self._finances.list_payments(commitment.id, organization_id=organization_id)
        overdue_payments += sum(1 for p in payments if p.status == 'OVERDUE')
      if overdue_payments > 0:
        factors.append(
          RiskFactor(
            category='FINANCIAL',
            severity=RISK_LEVEL_HIGH,
            score_impact=30,
            code='OVERDUE_PAYMENTS',
            message=f'Contract has {overdue_payments} overdue payment installment(s)',
            details={'overdue_payments': overdue_payments},
          )
        )

    return RiskAssessment.calculate('contract', contract_id, factors)

  async def assess_organization_risk(self, *, organization_id: str) -> dict:
    """Evaluate aggregate portfolio risk across the entire organization."""
    contracts = await self._contracts.list_contracts(organization_id=organization_id)
    contract_assessments: list[dict] = []

    for contract in contracts:
      assessment = await self.assess_contract_risk(contract.id, organization_id=organization_id)
      contract_assessments.append(
        {
          'contract_id': contract.id,
          'title': contract.title,
          'state': contract.state,
          'overall_score': assessment.overall_score,
          'risk_level': assessment.risk_level,
          'risk_factors_count': len(assessment.risk_factors),
        }
      )

    high_risk_count = sum(
      1 for a in contract_assessments if a['risk_level'] in (RISK_LEVEL_HIGH, RISK_LEVEL_CRITICAL)
    )
    avg_score = (
      round(sum(a['overall_score'] for a in contract_assessments) / len(contract_assessments), 1)
      if contract_assessments
      else 0.0
    )

    return {
      'organization_id': organization_id,
      'total_contracts_assessed': len(contract_assessments),
      'high_or_critical_risk_contracts': high_risk_count,
      'average_portfolio_risk_score': avg_score,
      'contracts': contract_assessments,
    }
