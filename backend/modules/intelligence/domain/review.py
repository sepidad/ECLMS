"""Contract review domain models (Phase 4 Intelligence, AI-assisted review)."""

from __future__ import annotations

from dataclasses import dataclass, field

RISK_LOW = 'LOW'
RISK_MEDIUM = 'MEDIUM'
RISK_HIGH = 'HIGH'
RISK_CRITICAL = 'CRITICAL'


@dataclass
class ReviewFinding:
  """A single observed risk / opportunity in a contract text.

  ``provider`` records whether it came from the deterministic rules engine
  or an external language model, preserving traceability (audit invariance).
  """

  category: str
  severity: str  # LOW / MEDIUM / HIGH / CRITICAL
  title: str
  message: str
  suggestion: str
  provider: str = 'rules'


@dataclass
class ContractReviewResult:
  """Aggregated result of a contract review pass."""

  contract_id: str
  version_number: int | None
  provider: str
  overall_risk_level: str
  findings: list[ReviewFinding] = field(default_factory=list)

  @property
  def high_or_critical_count(self) -> int:
    return sum(1 for f in self.findings if f.severity in (RISK_HIGH, RISK_CRITICAL))