"""CSV data import engine.

Bulk-imports contracts, obligations and financial commitments from a CSV
text payload.  Each row is parsed, validated against the domain service,
and recorded as either created or failed (with a human-readable reason).
The result is a per-kind summary suitable for an import report.

Row-level failures do not abort the import — every row is attempted so
the caller gets a complete picture of what succeeded and what needs
correction.
"""

from __future__ import annotations

import csv
from datetime import datetime
from io import StringIO
from typing import Any

from backend.core.logging import get_logger
from backend.modules.contracts.application.contract_service import ContractService
from backend.modules.finances.application.finance_service import FinanceService
from backend.modules.obligations.application.obligation_service import ObligationService

logger = get_logger('eclms.import')

CONTRACT_HEADERS = ('title', 'reference_number', 'counterparty', 'content')
OBLIGATION_HEADERS = ('contract_reference', 'description', 'due_date')
COMMITMENT_HEADERS = ('contract_reference', 'description', 'amount', 'currency')


class ImportService:
  """Parse CSV text and bulk-create domain entities."""

  def __init__(
    self,
    contracts: ContractService,
    obligations: ObligationService,
    finances: FinanceService,
  ) -> None:
    self._contracts = contracts
    self._obligations = obligations
    self._finances = finances

  async def import_contracts(
    self,
    *,
    csv_text: str,
    organization_id: str,
    actor_id: str,
  ) -> dict[str, Any]:
    return await self._import_csv(
      csv_text=csv_text,
      headers=CONTRACT_HEADERS,
      organization_id=organization_id,
      actor_id=actor_id,
      kind='contract',
      row_handler=self._create_contract,
    )

  async def import_obligations(
    self,
    *,
    csv_text: str,
    organization_id: str,
    actor_id: str,
  ) -> dict[str, Any]:
    return await self._import_csv(
      csv_text=csv_text,
      headers=OBLIGATION_HEADERS,
      organization_id=organization_id,
      actor_id=actor_id,
      kind='obligation',
      row_handler=self._create_obligation,
    )

  async def import_commitments(
    self,
    *,
    csv_text: str,
    organization_id: str,
    actor_id: str,
  ) -> dict[str, Any]:
    return await self._import_csv(
      csv_text=csv_text,
      headers=COMMITMENT_HEADERS,
      organization_id=organization_id,
      actor_id=actor_id,
      kind='commitment',
      row_handler=self._create_commitment,
    )

  async def _import_csv(
    self,
    *,
    csv_text: str,
    headers: tuple[str, ...],
    organization_id: str,
    actor_id: str,
    kind: str,
    row_handler,
  ) -> dict[str, Any]:
    reader = csv.DictReader(StringIO(csv_text))
    created: list[dict[str, Any]] = []
    failed: list[dict[str, Any]] = []
    total = 0
    for row_number, row in enumerate(reader, start=2):
      total += 1
      try:
        entity = await row_handler(
          row=row,
          headers=headers,
          organization_id=organization_id,
          actor_id=actor_id,
        )
        created.append({'row': row_number, 'id': entity.id})
      except Exception as exc:  # noqa: BLE001 - surface row-level failure in report
        failed.append({'row': row_number, 'reason': str(exc), 'data': dict(row)})
        logger.warning('Import row %d (%s) failed: %s', row_number, kind, exc)
    return {
      'kind': kind,
      'total': total,
      'created': len(created),
      'failed': len(failed),
      'created_items': created,
      'failed_items': failed,
    }

  @staticmethod
  def _require(row: dict[str, str], header: str) -> str:
    value = (row.get(header) or '').strip()
    if not value:
      raise ValueError(f'Missing required column: {header}')
    return value

  async def _create_contract(self, *, row, headers, organization_id, actor_id):
    del headers
    return await self._contracts.create_contract(
      title=self._require(row, 'title'),
      reference_number=self._require(row, 'reference_number'),
      counterparty=self._require(row, 'counterparty'),
      content=row.get('content'),
      organization_id=organization_id,
      owner_id=actor_id,
    )

  async def _create_obligation(self, *, row, headers, organization_id, actor_id):
    del headers
    contract_ref = self._require(row, 'contract_reference')
    due_date_raw = self._require(row, 'due_date')
    try:
      due_date = datetime.fromisoformat(due_date_raw)
    except ValueError as exc:
      raise ValueError(f'Invalid due_date (expected ISO 8601): {due_date_raw}') from exc
    return await self._obligations.create(
      contract_id=contract_ref,
      description=self._require(row, 'description'),
      due_date=due_date,
      organization_id=organization_id,
      created_by=actor_id,
    )

  async def _create_commitment(self, *, row, headers, organization_id, actor_id):
    del headers
    contract_ref = self._require(row, 'contract_reference')
    amount_raw = self._require(row, 'amount')
    try:
      amount = float(amount_raw)
    except ValueError as exc:
      raise ValueError(f'Invalid amount: {amount_raw}') from exc
    return await self._finances.create_commitment(
      contract_id=contract_ref,
      description=self._require(row, 'description'),
      amount=amount,
      currency=(row.get('currency') or 'USD').strip() or 'USD',
      organization_id=organization_id,
      created_by=actor_id,
    )