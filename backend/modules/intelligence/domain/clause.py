"""Clause analysis domain models and rule-based parser (Phase 4 Intelligence)."""

from __future__ import annotations

from dataclasses import dataclass, field

CLAUSE_TYPE_LIABILITY = 'LIABILITY'
CLAUSE_TYPE_TERMINATION = 'TERMINATION'
CLAUSE_TYPE_INDEMNIFICATION = 'INDEMNIFICATION'
CLAUSE_TYPE_GOVERNING_LAW = 'GOVERNING_LAW'
CLAUSE_TYPE_CONFIDENTIALITY = 'CONFIDENTIALITY'
CLAUSE_TYPE_PAYMENT = 'PAYMENT'
CLAUSE_TYPE_OTHER = 'OTHER'

CLAUSE_RISK_LOW = 'LOW'
CLAUSE_RISK_MEDIUM = 'MEDIUM'
CLAUSE_RISK_HIGH = 'HIGH'


@dataclass
class ExtractedClause:
  clause_type: str
  title: str
  text: str
  risk_level: str
  is_standard: bool
  analysis_notes: str
  keywords_found: list[str] = field(default_factory=list)


@dataclass
class ClauseAnalysisResult:
  contract_id: str
  version_number: int | None
  total_clauses: int
  high_risk_clauses_count: int
  missing_recommended_types: list[str]
  clauses: list[ExtractedClause] = field(default_factory=list)
  note: str = ''
