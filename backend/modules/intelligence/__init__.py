"""Intelligence module (Phase 4, roadmap priority #10 - Intelligence layer).

Provides risk detection, clause analysis, semantic search, predictive
alerts, and AI-assisted contract review over contracts, obligations,
finances, and workflows.  Everything is read-only and org-scoped
(ADR-003); nothing here mutates operational data.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from backend.core.base.module import Module
from backend.modules.intelligence.application.clause_service import ClauseService
from backend.modules.intelligence.application.predictive_service import PredictiveAlertsService
from backend.modules.intelligence.application.review_provider import (
  LlmReviewProvider,
  RuleBasedReviewProvider,
)
from backend.modules.intelligence.application.review_service import ReviewService
from backend.modules.intelligence.application.risk_service import RiskService
from backend.modules.intelligence.application.semantic_service import SemanticSearchService
from backend.modules.intelligence.interfaces import router

if TYPE_CHECKING:
  from backend.api.gateway import APIGateway
  from backend.bootstrap.container import ModuleContainer
  from backend.core.events import EventBus


class IntelligenceModule(Module):
  name = 'intelligence'
  version = '0.1.0'
  dependencies = ('contracts', 'finances', 'obligations')

  def initialize(self, container: ModuleContainer) -> None:
    self._risk_service: RiskService | None = None
    self._clause_service: ClauseService | None = None
    self._search_service: SemanticSearchService | None = None
    self._alerts_service: PredictiveAlertsService | None = None
    self._review_service: ReviewService | None = None

  def register_services(self, container: ModuleContainer) -> None:
    contracts = container.get_service('contracts.service')
    finances = container.get_service('finances.service')
    obligations = container.get_service('obligations.service')
    settings = container.get_service('settings')

    risk_service = RiskService(contracts, finances=finances, obligations=obligations)
    clause_service = ClauseService(contracts)
    search_service = SemanticSearchService(contracts)
    alerts_service = PredictiveAlertsService(
      contracts, obligations=obligations, finances=finances, risks=risk_service
    )

    if settings.ai_review_provider.lower() == 'llm':
      provider = LlmReviewProvider(
        api_url=settings.llm_api_url,
        api_key=settings.llm_api_key,
        model=settings.llm_model,
        timeout_seconds=settings.llm_timeout_seconds,
      )
    else:
      provider = RuleBasedReviewProvider()
    review_service = ReviewService(contracts, provider)

    self._risk_service = risk_service
    self._clause_service = clause_service
    self._search_service = search_service
    self._alerts_service = alerts_service
    self._review_service = review_service

    container.register_service('intelligence.risk', risk_service)
    container.register_service('intelligence.clauses', clause_service)
    container.register_service('intelligence.search', search_service)
    container.register_service('intelligence.alerts', alerts_service)
    container.register_service('intelligence.review', review_service)

  def register_routes(self, gateway: APIGateway) -> None:
    gateway.mount('intelligence', router)

  def register_events(self, bus: EventBus) -> None:
    return None
