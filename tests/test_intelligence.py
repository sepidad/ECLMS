"""Tests for the Intelligence module (Phase 4: risk, clauses, search, alerts)."""

from __future__ import annotations

from datetime import timedelta

import pytest

from backend.core.utils import utc_now
from backend.modules.intelligence.application.review_provider import RuleBasedReviewProvider
from backend.modules.intelligence.domain.risk import (
  RISK_LEVEL_CRITICAL,
  RISK_LEVEL_HIGH,
  RISK_LEVEL_LOW,
  RISK_LEVEL_MEDIUM,
  RiskAssessment,
  RiskFactor,
)
from backend.modules.intelligence.domain.semantic import (
  IndexedDocument,
  InMemoryVectorIndex,
  cosine_similarity,
  embed,
)

SAMPLE_TEXT = """This agreement sets forth the terms between the parties.

The liability of each party shall be limited to the amounts paid under this agreement.

Either party may terminate this agreement upon 60 days written notice.

Payment is due net 30 days from invoice.

This agreement shall be governed by the laws of the State of Delaware.
"""


def _svc(name: str):
  from backend.main import app

  return app.state.container.get_service(name)


@pytest.fixture
async def seeded_db():
  from infrastructure.database import create_schema, init_database

  init_database()
  await create_schema()
  yield


def _create_contract_api(client, headers, **kwargs):
  payload = {
    'title': kwargs.get('title', 'Intel Test'),
    'reference_number': kwargs.get('reference_number', 'INT-1'),
    'counterparty': 'ACME',
    'content': kwargs.get('content'),
  }
  r = client.post('/api/v1/contracts', json=payload, headers=headers)
  assert r.status_code == 200, r.text
  return r.json()['data']['id']


def test_embed_and_cosine_similarity():
  a = embed('contract liability indemnification payment terms')
  b = embed('contract liability indemnification payment terms')
  c = embed('catering service for office lunch events')
  assert cosine_similarity(a, b) > 0.99
  assert cosine_similarity(a, c) < cosine_similarity(a, b)


def test_risk_assessment_thresholds():
  def factor(impact, severity):
    return RiskFactor(category='EXPIRATION', severity=severity, score_impact=impact, code='X', message='m')

  assert RiskAssessment.calculate('contract', 'c1', [factor(10, 'LOW')]).risk_level == RISK_LEVEL_LOW
  assert RiskAssessment.calculate('contract', 'c1', [factor(30, 'MEDIUM')]).risk_level == RISK_LEVEL_MEDIUM
  assert RiskAssessment.calculate('contract', 'c1', [factor(55, 'HIGH')]).risk_level == RISK_LEVEL_HIGH
  assert RiskAssessment.calculate('contract', 'c1', [factor(80, 'CRITICAL')]).risk_level == RISK_LEVEL_CRITICAL
  assert RiskAssessment.calculate('contract', 'c1', [factor(40, 'CRITICAL')]).risk_level == RISK_LEVEL_CRITICAL


def test_risk_score_is_capped_at_100():
  assessment = RiskAssessment.calculate(
    'contract',
    'c1',
    [RiskFactor(category='X', severity='HIGH', score_impact=60, code='A', message=''),
     RiskFactor(category='Y', severity='HIGH', score_impact=60, code='B', message='')],
  )
  assert assessment.overall_score == 100


def test_vector_index_is_org_scoped():
  index = InMemoryVectorIndex()
  org_a = IndexedDocument(
    document_id='d1',
    contract_id='c1',
    title='Hardware',
    text='deliver IT hardware with payment terms',
    organization_id='org-a',
    vector=embed('deliver IT hardware with payment terms'),
  )
  org_b = IndexedDocument(
    document_id='d2',
    contract_id='c2',
    title='Catering',
    text='catering service for office events',
    organization_id='org-b',
    vector=embed('catering service for office events'),
  )
  index.upsert(org_a)
  index.upsert(org_b)
  assert index.search('hardware', organization_id='org-b') == []
  results = index.search('hardware delivery', organization_id='org-a')
  assert len(results) == 1
  assert results[0]['contract_id'] == 'c1'


def test_intelligence_requires_authentication():
  from fastapi.testclient import TestClient

  from backend.main import app

  with TestClient(app) as client:
    r = client.get('/api/v1/intelligence/risk/overview')
    assert r.json()['error']['code'] == 'UNAUTHORIZED'


def test_risk_overview_empty_org(authed_client):
  client, headers = authed_client
  r = client.get('/api/v1/intelligence/risk/overview', headers=headers)
  body = r.json()
  assert body['success'] is True
  assert body['data']['total_contracts_assessed'] == 0
  assert body['data']['average_portfolio_risk_score'] == 0.0


def test_clause_analysis_no_content(authed_client):
  client, headers = authed_client
  contract_id = _create_contract_api(client, headers)
  r = client.get(f'/api/v1/intelligence/clauses/{contract_id}', headers=headers)
  body = r.json()
  assert body['success'] is True
  data = body['data']
  assert data['total_clauses'] == 0
  assert 'no analyzable text' in data['note']
  assert 'LIABILITY' in data['missing_recommended_types']


def test_semantic_search_empty(authed_client):
  client, headers = authed_client
  r = client.get('/api/v1/intelligence/search', params={'q': 'indemnification cap'}, headers=headers)
  body = r.json()
  assert body['success'] is True
  assert body['data']['results'] == []


def test_predictive_alerts_empty(authed_client):
  client, headers = authed_client
  r = client.get('/api/v1/intelligence/alerts', headers=headers)
  body = r.json()
  assert body['success'] is True
  assert body['data']['total'] == 0


async def test_contract_past_expiry_is_critical(seeded_db):
  contracts = _svc('contracts.service')
  contract = await contracts.create_contract(
    title='Expired',
    reference_number='EX-1',
    counterparty='ACME',
    organization_id='org-default',
    owner_id='u1',
  )
  contract.expiry_date = utc_now() - timedelta(days=5)
  from infrastructure.database.repositories import SqlContractRepository

  repo = SqlContractRepository()
  await repo.save(contract)

  risks = _svc('intelligence.risk')
  assessment = await risks.assess_contract_risk(contract.id, organization_id='org-default')
  codes = [f.code for f in assessment.risk_factors]
  assert 'CONTRACT_PAST_EXPIRY' in codes
  assert assessment.risk_level == RISK_LEVEL_CRITICAL


async def test_contract_expiring_soon_is_high(seeded_db):
  contracts = _svc('contracts.service')
  contract = await contracts.create_contract(
    title='Expiring Soon',
    reference_number='EX-2',
    counterparty='ACME',
    organization_id='org-default',
    owner_id='u1',
  )
  contract.expiry_date = utc_now() + timedelta(days=15)
  from infrastructure.database.repositories import SqlContractRepository

  repo = SqlContractRepository()
  await repo.save(contract)

  risks = _svc('intelligence.risk')
  assessment = await risks.assess_contract_risk(contract.id, organization_id='org-default')
  codes = [f.code for f in assessment.risk_factors]
  assert 'CONTRACT_EXPIRING_SOON' in codes
  assert assessment.risk_level == RISK_LEVEL_HIGH


async def test_overdue_obligations_add_risk(seeded_db):
  contracts = _svc('contracts.service')
  contract = await contracts.create_contract(
    title='Deliverables',
    reference_number='OB-1',
    counterparty='ACME',
    organization_id='org-default',
    owner_id='u1',
  )
  obligations = _svc('obligations.service')
  await obligations.create(
    contract_id=contract.id,
    description='Ship widgets',
    due_date=utc_now() - timedelta(days=3),
    organization_id='org-default',
    created_by='u1',
  )
  await obligations.sweep_overdue()

  risks = _svc('intelligence.risk')
  assessment = await risks.assess_contract_risk(contract.id, organization_id='org-default')
  codes = [f.code for f in assessment.risk_factors]
  assert 'OVERDUE_OBLIGATIONS' in codes


async def test_overdue_payments_add_risk(seeded_db):
  contracts = _svc('contracts.service')
  contract = await contracts.create_contract(
    title='Finance Risk',
    reference_number='FN-1',
    counterparty='ACME',
    organization_id='org-default',
    owner_id='u1',
  )
  finances = _svc('finances.service')
  commitment = await finances.create_commitment(
    contract_id=contract.id,
    description='License',
    amount=5000.0,
    currency='USD',
    organization_id='org-default',
    created_by='u1',
  )
  await finances.create_payment(
    commitment_id=commitment.id,
    amount=5000.0,
    due_date=utc_now() - timedelta(days=2),
    organization_id='org-default',
  )
  await finances.sweep_overdue()

  risks = _svc('intelligence.risk')
  assessment = await risks.assess_contract_risk(contract.id, organization_id='org-default')
  codes = [f.code for f in assessment.risk_factors]
  assert 'OVERDUE_PAYMENTS' in codes


async def test_organization_risk_overview(seeded_db):
  contracts = _svc('contracts.service')
  for i in range(2):
    contract = await contracts.create_contract(
      title=f'Portfolio {i}',
      reference_number=f'PF-{i}',
      counterparty='ACME',
      organization_id='org-default',
      owner_id='u1',
    )
    contract.expiry_date = utc_now() - timedelta(days=1)
    from infrastructure.database.repositories import SqlContractRepository

    repo = SqlContractRepository()
    await repo.save(contract)

  risks = _svc('intelligence.risk')
  report = await risks.assess_organization_risk(organization_id='org-default')
  assert report['total_contracts_assessed'] == 2
  assert report['high_or_critical_risk_contracts'] == 2


async def test_clause_analysis_extracts_types(seeded_db):
  contracts = _svc('contracts.service')
  contract = await contracts.create_contract(
    title='Legal',
    reference_number='CL-1',
    counterparty='ACME',
    organization_id='org-default',
    owner_id='u1',
    content=SAMPLE_TEXT,
  )
  clauses = _svc('intelligence.clauses')
  result = await clauses.analyze_contract(contract.id, organization_id='org-default')
  types = {c.clause_type for c in result.clauses}
  assert 'LIABILITY' in types
  assert 'TERMINATION' in types
  assert 'PAYMENT' in types
  assert 'GOVERNING_LAW' in types
  assert 'INDEMNIFICATION' in result.missing_recommended_types
  assert 'CONFIDENTIALITY' in result.missing_recommended_types
  assert result.high_risk_clauses_count == 0


async def test_semantic_search_ranks_relevant_first(seeded_db):
  contracts = _svc('contracts.service')
  await contracts.create_contract(
    title='Hardware',
    reference_number='SR-1',
    counterparty='ACME',
    organization_id='org-default',
    owner_id='u1',
    content='The supplier shall deliver IT hardware with payment due net 30 days.',
  )
  await contracts.create_contract(
    title='Catering',
    reference_number='SR-2',
    counterparty='ACME',
    organization_id='org-default',
    owner_id='u1',
    content='The vendor provides catering services for office events and meetings.',
  )

  search = _svc('intelligence.search')
  results = await search.search('hardware delivery and payment terms', organization_id='org-default')
  assert results[0]['title'] == 'Hardware'
  assert results[0]['similarity_score'] > 0.0


async def test_predictive_alerts_detect_expiry(seeded_db):
  contracts = _svc('contracts.service')
  contract = await contracts.create_contract(
    title='About To Expire',
    reference_number='AL-1',
    counterparty='ACME',
    organization_id='org-default',
    owner_id='u1',
  )
  contract.expiry_date = utc_now() + timedelta(days=3)
  from infrastructure.database.repositories import SqlContractRepository

  repo = SqlContractRepository()
  await repo.save(contract)

  alerts = _svc('intelligence.alerts')
  items = await alerts.generate_alerts(organization_id='org-default')
  types = {a['alert_type'] for a in items}
  assert 'contract.expiring' in types
  assert any(a['severity'] == 'HIGH' for a in items if a['alert_type'] == 'contract.expiring')


# --- AI-assisted contract review ---

RISKY_TEXT = """This agreement sets forth the terms between the parties.

The parties shall have unlimited liability and shall include all losses.

Either party may terminate this agreement upon 14 days written notice.

Payment is due net 60 days from invoice.
"""

CLEAN_TEXT = """This agreement sets forth the terms between the parties.

The liability of each party shall be limited to the amounts paid and capped at one million dollars.

It is hereby agreed that the parties shall mutually indemnify each other.

Either party may terminate this agreement upon 90 days written notice.

Payment is due net 10 days from invoice.

This agreement shall be governed by the laws of the State of Delaware.

The parties shall keep all shared information confidential.
"""


async def test_rule_based_review_detects_risks(seeded_db):
  contracts = _svc('contracts.service')
  contract = await contracts.create_contract(
    title='Risky Review',
    reference_number='RV-1',
    counterparty='ACME',
    organization_id='org-default',
    owner_id='u1',
    content=RISKY_TEXT,
  )
  review = _svc('intelligence.review')
  result = await review.review_contract(contract.id, organization_id='org-default')
  assert result.provider == 'rules'
  assert result.overall_risk_level == 'CRITICAL'
  titles = {f.title for f in result.findings}
  assert 'Unlimited liability' in titles
  assert result.high_or_critical_count >= 1


async def test_rule_based_review_clean_contract(seeded_db):
  contracts = _svc('contracts.service')
  contract = await contracts.create_contract(
    title='Clean Review',
    reference_number='RV-2',
    counterparty='ACME',
    organization_id='org-default',
    owner_id='u1',
    content=CLEAN_TEXT,
  )
  review = _svc('intelligence.review')
  result = await review.review_contract(contract.id, organization_id='org-default')
  assert result.overall_risk_level == 'LOW'
  assert result.findings[0].severity == 'LOW'


async def test_review_no_content(seeded_db):
  contracts = _svc('contracts.service')
  contract = await contracts.create_contract(
    title='Empty Review',
    reference_number='RV-3',
    counterparty='ACME',
    organization_id='org-default',
    owner_id='u1',
  )
  review = _svc('intelligence.review')
  result = await review.review_contract(contract.id, organization_id='org-default')
  assert result.findings == []
  assert result.overall_risk_level == 'LOW'


def test_llm_provider_parses_response():
  from backend.modules.intelligence.application.review_provider import LlmReviewProvider

  payload = '```json\n[{"category": "LIABILITY", "severity": "HIGH", "title": "T", "message": "M", "suggestion": "S"}]\n```'
  findings = LlmReviewProvider._parse_findings(payload)
  assert len(findings) == 1
  assert findings[0].provider == 'llm'
  assert findings[0].severity == 'HIGH'


async def test_llm_provider_calls_endpoint():
  import httpx

  from backend.modules.intelligence.application.review_provider import LlmReviewProvider

  def handler(request):
    assert request.headers['Authorization'] == 'Bearer test-key'
    body = {
      'choices': [
        {
          'message': {
            'content': (
              '[{"category": "PAYMENT", "severity": "MEDIUM", "title": "Net 60", '
              '"message": "long terms", "suggestion": "shorten"}]'
            )
          }
        }
      ]
    }
    return httpx.Response(200, json=body)

  client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
  provider = LlmReviewProvider(
    api_url='http://llm.local/v1/chat/completions',
    api_key='test-key',
    model='test-model',
    http_client=client,
  )
  findings = await provider.review('Payment is due net 60 days.')
  assert len(findings) == 1
  assert findings[0].severity == 'MEDIUM'
  assert findings[0].title == 'Net 60'


async def test_llm_provider_degrades_gracefully_on_error():
  import httpx

  from backend.modules.intelligence.application.review_provider import LlmReviewProvider

  def handler(request):
    return httpx.Response(500)

  client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
  provider = LlmReviewProvider(
    api_url='http://llm.local/v1/chat/completions',
    api_key='test-key',
    model='test-model',
    http_client=client,
  )
  findings = await provider.review('Some text.')
  assert findings == []


async def test_review_route_requires_auth():
  from fastapi.testclient import TestClient

  from backend.main import app

  with TestClient(app) as client:
    r = client.get('/api/v1/intelligence/review/00000000000000000000000000000000')
    assert r.json()['error']['code'] == 'UNAUTHORIZED'


async def test_termination_rule_ignores_payment_day_terms():
  """'net 30 days' in a payment clause must not trigger short-notice."""
  text = (
    'Payment is due net 30 days from invoice.\n\n'
    'Either party may terminate this agreement upon 60 days notice.'
  )
  provider = RuleBasedReviewProvider()
  findings = await provider.review(text)
  termination = next((f for f in findings if f.category == 'TERMINATION'), None)
  assert termination is not None
  assert termination.severity == 'LOW'
