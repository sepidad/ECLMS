"""External system connectors (ERP / accounting / webhook I/O) scaffold.

Phase 3 roadmap item: connect the system to external enterprise
ecosystems.  Connectors expose a pluggable ``ExternalConnector`` contract
(organized by gateway architecture).  When an endpoint is unconfigured a
sync is a ``dry_run`` that records the attempt (for auditability) without
transmitting anything; when an endpoint is set the connector POSTs the
org-scoped payload and records the outcome.

Every sync attempt is recorded in ``connector_syncs`` (organization,
connector, status, detail, executed_at).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

import httpx
from sqlalchemy import select

from backend.core.logging import get_logger
from backend.core.utils import new_id, utc_now
from infrastructure.database.models.integration import ConnectorSyncModel
from infrastructure.database.session import get_session_factory

logger = get_logger('eclms.integration.connectors')


class ExternalConnector(ABC):
  """Contract a connector with an external system must honour."""

  id: str = ''
  display_name: str = ''

  @abstractmethod
  async def sync(self, *, organization_id: str, endpoint: str) -> dict[str, Any]:
    """Push org-scoped data to ``endpoint`` (or a dry-run when empty).

    Returns a result dict with ``sent`` (int) and ``errors`` (list).
    """


class ErpConnector(ExternalConnector):
  """Synchronizes contracts & commitments with an ERP system."""

  id = 'erp'
  display_name = 'ERP (contracts & commitments)'

  def __init__(self, client: httpx.AsyncClient | None = None) -> None:
    self._client = client or httpx.AsyncClient(timeout=10.0)

  async def sync(self, *, organization_id: str, endpoint: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = payload or {'organization_id': organization_id, 'kind': 'erp_sync', 'contracts': [], 'commitments': []}
    if not endpoint:
      return {'dry_run': True, 'sent': 0, 'preview': payload}
    try:
      response = await self._client.post(endpoint, json=payload)
      response.raise_for_status()
      return {'dry_run': False, 'sent': 1, 'status_code': response.status_code, 'mapped_records': _count_records(payload)}
    except httpx.HTTPError as exc:
      return {'dry_run': False, 'sent': 0, 'errors': [str(exc)]}


class AccountingConnector(ExternalConnector):
  """Synchronizes payments & commitments with an accounting system."""

  id = 'accounting'
  display_name = 'Accounting (payments & commitments)'

  def __init__(self, client: httpx.AsyncClient | None = None) -> None:
    self._client = client or httpx.AsyncClient(timeout=10.0)

  async def sync(self, *, organization_id: str, endpoint: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = payload or {'organization_id': organization_id, 'kind': 'accounting_sync', 'commitments': [], 'payments': []}
    if not endpoint:
      return {'dry_run': True, 'sent': 0, 'preview': payload}
    try:
      response = await self._client.post(endpoint, json=payload)
      response.raise_for_status()
      return {'dry_run': False, 'sent': 1, 'status_code': response.status_code, 'mapped_records': _count_records(payload)}
    except httpx.HTTPError as exc:
      return {'dry_run': False, 'sent': 0, 'errors': [str(exc)]}


def _count_records(payload: dict[str, Any]) -> int:
  return sum(len(value) for key, value in payload.items() if key != 'organization_id' and isinstance(value, list))


def default_connectors() -> list[ExternalConnector]:
  return [ErpConnector(), AccountingConnector()]


class ConnectorService:
  """Registry + orchestration for external system connectors."""

  def __init__(self, settings, connectors: list[ExternalConnector] | None = None, contracts=None, finances=None) -> None:
    self._settings = settings
    self._contracts = contracts
    self._finances = finances
    self._connectors = {c.id: c for c in (connectors or default_connectors())}
    self._endpoints = {
      'erp': settings.erp_endpoint,
      'accounting': settings.accounting_endpoint,
    }

  def list_connectors(self) -> list[dict[str, Any]]:
    return [
      {
        'id': connector.id,
        'display_name': connector.display_name,
        'configured': bool(self._endpoints.get(connector.id)),
        'endpoint': self._endpoints.get(connector.id) or '',
      }
      for connector in self._connectors.values()
    ]

  async def sync(self, connector_id: str, *, organization_id: str) -> dict[str, Any]:
    connector = self._connectors.get(connector_id)
    if connector is None:
      raise KeyError(connector_id)
    endpoint = self._endpoints.get(connector_id) or ''
    payload = await self._build_payload(connector_id, organization_id)
    result = await connector.sync(organization_id=organization_id, endpoint=endpoint, payload=payload)
    await self._record_sync(
      connector_id=connector_id,
      organization_id=organization_id,
      detail=result,
    )
    return result

  async def _build_payload(self, connector_id: str, organization_id: str) -> dict[str, Any]:
    """Map ECLMS entities into stable, organization-scoped connector records."""
    payload: dict[str, Any] = {'organization_id': organization_id, 'kind': f'{connector_id}_sync'}
    if self._contracts:
      contracts = await self._contracts.list_contracts(organization_id=organization_id, limit=100000)
      payload['contracts'] = [
        {
          'id': item.id,
          'reference_number': item.reference_number,
          'title': item.title,
          'counterparty': item.counterparty,
          'state': item.state,
        }
        for item in contracts
      ]
    if self._finances and connector_id == 'erp':
      commitments = await self._finances.list_all_commitments(organization_id=organization_id)
      payload['commitments'] = [
        {'id': item.id, 'contract_id': item.contract_id, 'description': item.description, 'amount': item.amount, 'currency': item.currency, 'status': item.status}
        for item in commitments
      ]
    if self._finances and connector_id == 'accounting':
      commitments = await self._finances.list_all_commitments(organization_id=organization_id)
      payments = await self._finances.list_all_payments(organization_id=organization_id)
      payload['commitments'] = [
        {'id': item.id, 'contract_id': item.contract_id, 'description': item.description, 'amount': item.amount, 'currency': item.currency, 'status': item.status}
        for item in commitments
      ]
      payload['payments'] = [
        {'id': item.id, 'commitment_id': item.commitment_id, 'amount': item.amount, 'due_date': item.due_date.isoformat() if item.due_date else None, 'status': item.status}
        for item in payments
      ]
    return payload

  async def _record_sync(
    self,
    *,
    connector_id: str,
    organization_id: str,
    detail: dict[str, Any],
  ) -> str:
    sync_id = new_id()
    async with get_session_factory()() as session:
      session.add(
        ConnectorSyncModel(
          id=sync_id,
          organization_id=organization_id,
          connector_id=connector_id,
          status='failed' if detail.get('errors') else 'ok',
          detail=detail,
          executed_at=utc_now(),
        )
      )
      await session.commit()
    return sync_id

  async def list_syncs(
    self,
    organization_id: str,
    *,
    limit: int = 100,
    offset: int = 0,
  ) -> list[dict[str, Any]]:
    async with get_session_factory()() as session:
      stmt = (
        select(ConnectorSyncModel)
        .where(ConnectorSyncModel.organization_id == organization_id)
        .order_by(ConnectorSyncModel.executed_at.desc())
        .limit(limit)
        .offset(offset)
      )
      rows = (await session.execute(stmt)).scalars().all()
      return [
        {
          'id': row.id,
          'connector_id': row.connector_id,
          'status': row.status,
          'detail': row.detail,
          'executed_at': row.executed_at,
        }
        for row in rows
      ]
