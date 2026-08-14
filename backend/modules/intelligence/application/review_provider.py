"""Review providers (Phase 4 Intelligence, AI-assisted contract review).

Two pluggable implementations mirror the storage-provider pattern:

  - ``RuleBasedReviewProvider`` — deterministic, in-process, zero external
    dependencies.  The default and always-available fallback.
  - ``LlmReviewProvider`` — calls an OpenAI-compatible ``/chat/completions``
    endpoint when ``ECLMS_AI_REVIEW_PROVIDER=llm`` and an API URL/key are
    configured.

Both produce a list of :class:`ReviewFinding` so callers are provider-agnostic.
"""

from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod

import httpx

from backend.core.logging import get_logger
from backend.modules.intelligence.domain.clause import CLAUSE_TYPE_LIABILITY, CLAUSE_TYPE_PAYMENT
from backend.modules.intelligence.domain.review import RISK_CRITICAL, RISK_HIGH, RISK_LOW, RISK_MEDIUM, ReviewFinding

logger = get_logger('eclms.intelligence.review')

_RISK_RANK = {RISK_LOW: 1, RISK_MEDIUM: 2, RISK_HIGH: 3, RISK_CRITICAL: 4}


def _worst_level(findings: list[ReviewFinding]) -> str:
  if not findings:
    return RISK_LOW
  return max(findings, key=lambda f: _RISK_RANK[f.severity]).severity


class ReviewProvider(ABC):
  name: str = ''

  @abstractmethod
  async def review(self, text: str, *, context: dict | None = None) -> list[ReviewFinding]:
    """Analyze contract text and return findings."""


class RuleBasedReviewProvider(ReviewProvider):
  name = 'rules'

  async def review(self, text: str, *, context: dict | None = None) -> list[ReviewFinding]:
    lowered = text.lower()
    findings: list[ReviewFinding] = []

    if 'unlimited liability' in lowered:
      findings.append(
        ReviewFinding(
          category=CLAUSE_TYPE_LIABILITY,
          severity=RISK_CRITICAL,
          title='Unlimited liability',
          message='The contract does not appear to cap the liability of the parties.',
          suggestion='Add an explicit aggregate liability cap (e.g. 100% of fees paid).',
        )
      )
    elif 'liability' in lowered or 'liable' in lowered:
      capped = any(w in lowered for w in ('cap', 'limited to', 'maximum liability'))
      findings.append(
        ReviewFinding(
          category=CLAUSE_TYPE_LIABILITY,
          severity=RISK_LOW if capped else RISK_MEDIUM,
          title='Liability clause',
          message=(
            'Liability is capped or limited.'
            if capped
            else 'Liability is mentioned but no explicit cap was detected.'
          ),
          suggestion='Confirm the liability cap is explicit and mutually agreed.',
        )
      )

    if any(w in lowered for w in ('indemnif', 'indemnity')):
      mutual = any(w in lowered for w in ('mutual', 'reciprocal'))
      findings.append(
        ReviewFinding(
          category='INDEMNIFICATION',
          severity=RISK_LOW if mutual else RISK_MEDIUM,
          title='Indemnification',
          message=(
            'Indemnification is mutual.' if mutual else 'One-sided indemnification may increase exposure.'
          ),
          suggestion='Negotiate mutual/reciprocal indemnification where possible.',
        )
      )

    if any(w in lowered for w in ('terminat', 'notice period', 'right to terminate')):
      # Match a countdown notice such as "7 days notice" / "14-day notice".
      # Using an adjacency-aware regex avoids flagging "net 30 days from
      # invoice" (a payment term) as a short notice period.
      notice_re = r'\b(?:7|14|30)\s*-?\s*days?\s+notice\b'
      short_notice = re.search(notice_re, lowered) is not None
      findings.append(
        ReviewFinding(
          category='TERMINATION',
          severity=RISK_MEDIUM if short_notice else RISK_LOW,
          title='Termination terms',
          message=(
            'Short termination notice period detected.'
            if short_notice
            else 'Termination provisions are present with a reasonable notice period.'
          ),
          suggestion='Ensure the notice period is sufficient for operational wind-down.',
        )
      )

    if not any(w in lowered for w in ('governing law', 'governed by', 'jurisdiction', 'laws of')):
      findings.append(
        ReviewFinding(
          category='GOVERNING_LAW',
          severity=RISK_MEDIUM,
          title='Governing law not specified',
          message='No governing law or jurisdiction clause was detected.',
          suggestion='Add a governing law and jurisdiction clause to remove legal ambiguity.',
        )
      )

    if not any(w in lowered for w in ('confidential', 'non-disclosure', 'non-disclos')):
      findings.append(
        ReviewFinding(
          category='CONFIDENTIALITY',
          severity=RISK_MEDIUM,
          title='Confidentiality not specified',
          message='No confidentiality or non-disclosure provisions were detected.',
          suggestion='Add a mutual confidentiality clause covering shared information.',
        )
      )

    if any(w in lowered for w in ('payment', 'payable', 'invoice')):
      extended = any(w in lowered for w in ('net 60', 'net-60', 'net 90', 'net-90'))
      findings.append(
        ReviewFinding(
          category=CLAUSE_TYPE_PAYMENT,
          severity=RISK_MEDIUM if extended else RISK_LOW,
          title='Payment terms',
          message=(
            'Extended payment terms increase cash-flow risk.'
            if extended
            else 'Standard payment terms are specified.'
          ),
          suggestion='Confirm payment schedule and late-payment remedies.',
        )
      )

    findings.sort(key=lambda f: _RISK_RANK[f.severity], reverse=True)
    return findings


class LlmReviewProvider(ReviewProvider):
  name = 'llm'

  def __init__(self, *, api_url: str, api_key: str, model: str, timeout_seconds: int = 30, http_client=None) -> None:
    self._api_url = api_url
    self._api_key = api_key
    self._model = model
    self._timeout = timeout_seconds
    self._http_client = http_client or httpx.AsyncClient(timeout=timeout_seconds)

  async def review(self, text: str, *, context: dict | None = None) -> list[ReviewFinding]:
    if not self._api_url:
      logger.warning('LLM review provider selected but ECLMS_LLM_API_URL is empty')
      return []

    system_prompt = (
      'You are an expert commercial contract reviewer. Analyze the contract text and return a JSON array. '
      'Each item must have exactly: category, severity ("LOW"/"MEDIUM"/"HIGH"/"CRITICAL"), title, message, suggestion. '
      'Do not include any text outside the JSON array.'
    )
    payload = {
      'model': self._model,
      'temperature': 0.2,
      'messages': [
        {'role': 'system', 'content': system_prompt},
        {'role': 'user', 'content': text[:12000]},
      ],
    }
    headers = {'Authorization': f'Bearer {self._api_key}', 'Content-Type': 'application/json'}

    try:
      response = await self._http_client.post(self._api_url, json=payload, headers=headers)
      response.raise_for_status()
      body = response.json()
      content = body['choices'][0]['message']['content']
      return self._parse_findings(content)
    except Exception as exc:  # noqa: BLE001 - provider failures degrade gracefully
      logger.warning('LLM review failed: %s', exc)
      return []

  @staticmethod
  def _parse_findings(content: str) -> list[ReviewFinding]:
    text = content.strip()
    if text.startswith('```'):
      text = re.sub(r'^```(?:json)?\s*', '', text)
      text = re.sub(r'\s*```$', '', text)
    try:
      items = json.loads(text)
    except json.JSONDecodeError:
      match = re.search(r'\[.*\]', text, re.DOTALL)
      if not match:
        return []
      items = json.loads(match.group(0))

    findings: list[ReviewFinding] = []
    for item in items if isinstance(items, list) else []:
      severity = str(item.get('severity', RISK_MEDIUM)).upper()
      if severity not in _RISK_RANK:
        severity = RISK_MEDIUM
      findings.append(
        ReviewFinding(
          category=str(item.get('category', 'GENERAL')),
          severity=severity,
          title=str(item.get('title', 'Finding')),
          message=str(item.get('message', '')),
          suggestion=str(item.get('suggestion', '')),
          provider='llm',
        )
      )
    return findings
