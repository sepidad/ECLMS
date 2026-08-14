"""Clause Analysis Service (Phase 4 Intelligence).

Rule-based analysis of contract version text: extracts typed clauses
(liability, termination, indemnification, governing law, confidentiality,
payment), scores each clause's risk, and reports missing recommended
clause types.  Deterministic, stateless, and org-scoped through the
contracts module.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from backend.modules.intelligence.domain.clause import (
  CLAUSE_RISK_HIGH,
  CLAUSE_RISK_LOW,
  CLAUSE_RISK_MEDIUM,
  CLAUSE_TYPE_CONFIDENTIALITY,
  CLAUSE_TYPE_GOVERNING_LAW,
  CLAUSE_TYPE_INDEMNIFICATION,
  CLAUSE_TYPE_LIABILITY,
  CLAUSE_TYPE_OTHER,
  CLAUSE_TYPE_PAYMENT,
  CLAUSE_TYPE_TERMINATION,
  ClauseAnalysisResult,
  ExtractedClause,
)

if TYPE_CHECKING:
  from backend.modules.contracts.application.contract_service import ContractService

CLAUSE_RULES: dict[str, dict] = {
  CLAUSE_TYPE_LIABILITY: {
    'title': 'Liability',
    'keywords': ('liability', 'liable', 'hold harmless'),
  },
  CLAUSE_TYPE_TERMINATION: {
    'title': 'Termination',
    'keywords': ('termination', 'terminate', 'terminated', 'notice period', 'right to terminate'),
  },
  CLAUSE_TYPE_INDEMNIFICATION: {
    'title': 'Indemnification',
    'keywords': ('indemnif', 'indemnity', 'indemnify'),
  },
  CLAUSE_TYPE_GOVERNING_LAW: {
    'title': 'Governing Law',
    'keywords': ('governing law', 'governed by', 'jurisdiction', 'laws of'),
  },
  CLAUSE_TYPE_CONFIDENTIALITY: {
    'title': 'Confidentiality',
    'keywords': ('confidential', 'non-disclosure', 'non-disclos'),
  },
  CLAUSE_TYPE_PAYMENT: {
    'title': 'Payment',
    'keywords': ('payment', 'payable', 'invoice', 'net 30', 'net-30', 'net 60', 'net-60'),
  },
}

RECOMMENDED_CLAUSE_TYPES = (
  CLAUSE_TYPE_LIABILITY,
  CLAUSE_TYPE_TERMINATION,
  CLAUSE_TYPE_INDEMNIFICATION,
  CLAUSE_TYPE_GOVERNING_LAW,
  CLAUSE_TYPE_CONFIDENTIALITY,
  CLAUSE_TYPE_PAYMENT,
)


def _split_clauses(text: str) -> list[str]:
  chunks = re.split(r'\n\s*\n', text)
  return [re.sub(r'\s+', ' ', chunk).strip() for chunk in chunks if chunk.strip()]


def _classify(chunk: str) -> tuple[str, list[str]]:
  """Return (clause_type, matched_keywords) for a text chunk."""
  lowered = chunk.lower()
  best_type = CLAUSE_TYPE_OTHER
  best_hits: list[str] = []
  for clause_type, rule in CLAUSE_RULES.items():
    hits = [kw for kw in rule['keywords'] if kw in lowered]
    if len(hits) > len(best_hits):
      best_type = clause_type
      best_hits = hits
  return best_type, best_hits


def _rate_clause(clause_type: str, text: str) -> tuple[str, str]:
  """Return (risk_level, analysis_notes) for a classified clause."""
  lowered = text.lower()
  if clause_type == CLAUSE_TYPE_LIABILITY:
    if 'unlimited liability' in lowered:
      return CLAUSE_RISK_HIGH, 'Unlimited liability exposure detected'
    if any(word in lowered for word in ('cap', 'limited to', 'maximum liability')):
      return CLAUSE_RISK_LOW, 'Liability is capped or limited'
    return CLAUSE_RISK_MEDIUM, 'Liability clause present without explicit cap'

  if clause_type == CLAUSE_TYPE_TERMINATION:
    if any(word in lowered for word in ('30 days', '30-day', '14 days', '14-day', '7 days', '7-day')):
      return CLAUSE_RISK_MEDIUM, 'Short termination notice period detected'
    if any(word in lowered for word in ('60 days', '90 days', '120 days')):
      return CLAUSE_RISK_LOW, 'Adequate termination notice period'
    return CLAUSE_RISK_MEDIUM, 'Termination terms present; notice period unclear'

  if clause_type == CLAUSE_TYPE_INDEMNIFICATION:
    if any(word in lowered for word in ('mutual', 'reciprocal')):
      return CLAUSE_RISK_LOW, 'Indemnification is mutual/reciprocal'
    return CLAUSE_RISK_MEDIUM, 'One-sided indemnification may increase exposure'

  if clause_type == CLAUSE_TYPE_GOVERNING_LAW:
    return CLAUSE_RISK_LOW, 'Governing law and jurisdiction specified'

  if clause_type == CLAUSE_TYPE_CONFIDENTIALITY:
    return CLAUSE_RISK_LOW, 'Confidentiality protections specified'

  if clause_type == CLAUSE_TYPE_PAYMENT:
    if any(word in lowered for word in ('net 60', 'net-60', 'net 90', 'net-90')):
      return CLAUSE_RISK_MEDIUM, 'Extended payment terms increase cash-flow risk'
    if any(word in lowered for word in ('net 30', 'net-30', 'upon receipt', 'due on invoice')):
      return CLAUSE_RISK_LOW, 'Standard payment terms'
    return CLAUSE_RISK_MEDIUM, 'Payment terms present; schedule unclear'

  return CLAUSE_RISK_LOW, 'Miscellaneous clause; no material risk identified'


class ClauseService:
  def __init__(self, contracts: ContractService) -> None:
    self._contracts = contracts

  async def analyze_contract(self, contract_id: str, *, organization_id: str) -> ClauseAnalysisResult:
    """Analyze the active version's text of a contract."""
    contract = await self._contracts.get_contract(contract_id, organization_id=organization_id)
    versions = await self._contracts.list_versions(contract_id, organization_id=organization_id)
    active = next((v for v in versions if v.get('is_active')), None)
    text = (active or {}).get('content') or ''
    version_number = (active or {}).get('version_number')

    if not text:
      return ClauseAnalysisResult(
        contract_id=contract_id,
        version_number=version_number,
        total_clauses=0,
        high_risk_clauses_count=0,
        missing_recommended_types=list(RECOMMENDED_CLAUSE_TYPES),
        note='Contract has no analyzable text content',
      )

    found_types: set[str] = set()
    clauses: list[ExtractedClause] = []
    for chunk in _split_clauses(text):
      clause_type, hits = _classify(chunk)
      risk_level, notes = _rate_clause(clause_type, chunk)
      found_types.add(clause_type)
      clauses.append(
        ExtractedClause(
          clause_type=clause_type,
          title=CLAUSE_RULES.get(clause_type, {'title': 'General'})['title'],
          text=chunk,
          risk_level=risk_level,
          is_standard=risk_level == CLAUSE_RISK_LOW,
          analysis_notes=notes,
          keywords_found=hits,
        )
      )

    missing = [t for t in RECOMMENDED_CLAUSE_TYPES if t not in found_types]
    high_risk_count = sum(1 for c in clauses if c.risk_level == CLAUSE_RISK_HIGH)

    return ClauseAnalysisResult(
      contract_id=contract_id,
      version_number=version_number,
      total_clauses=len(clauses),
      high_risk_clauses_count=high_risk_count,
      missing_recommended_types=missing,
      clauses=clauses,
      note=f'Analyzed active version text of "{contract.title}" ({len(text)} chars)',
    )
