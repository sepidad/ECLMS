"""Risk detection domain models and assessment engine (Phase 4 Intelligence)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

RISK_LEVEL_LOW = 'LOW'
RISK_LEVEL_MEDIUM = 'MEDIUM'
RISK_LEVEL_HIGH = 'HIGH'
RISK_LEVEL_CRITICAL = 'CRITICAL'

_SEVERITY_RANK = {'LOW': 1, 'MEDIUM': 2, 'HIGH': 3, 'CRITICAL': 4}
_LEVEL_BY_RANK = {rank: level for level, rank in _SEVERITY_RANK.items()}


@dataclass
class RiskFactor:
  category: str  # EXPIRATION, FINANCIAL, OBLIGATION, WORKFLOW_SLA
  severity: str  # LOW, MEDIUM, HIGH, CRITICAL
  score_impact: int
  code: str
  message: str
  details: dict[str, Any] = field(default_factory=dict)


@dataclass
class RiskAssessment:
  entity_type: str  # contract / organization
  entity_id: str
  overall_score: int
  risk_level: str
  risk_factors: list[RiskFactor] = field(default_factory=list)
  assessed_at: datetime = field(default_factory=lambda: datetime.now(UTC))

  @classmethod
  def calculate(cls, entity_type: str, entity_id: str, factors: list[RiskFactor]) -> RiskAssessment:
    total_score = min(100, sum(f.score_impact for f in factors))
    if total_score >= 75:
      level = RISK_LEVEL_CRITICAL
    elif total_score >= 50:
      level = RISK_LEVEL_HIGH
    elif total_score >= 25:
      level = RISK_LEVEL_MEDIUM
    else:
      level = RISK_LEVEL_LOW

    worst = max((_SEVERITY_RANK.get(f.severity, 1) for f in factors), default=1)
    worst_level = _LEVEL_BY_RANK[worst]
    if _SEVERITY_RANK[worst_level] > _SEVERITY_RANK[level]:
      level = worst_level

    return cls(
      entity_type=entity_type,
      entity_id=entity_id,
      overall_score=total_score,
      risk_level=level,
      risk_factors=factors,
    )
