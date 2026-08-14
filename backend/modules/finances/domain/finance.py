"""Financial domain entities: commitment and payment."""

from __future__ import annotations

from datetime import UTC, datetime

from backend.core.base.entity import Entity
from backend.core.exceptions import StateTransitionError
from backend.core.utils import utc_now

PAYMENT_STATUS_SCHEDULED = 'SCHEDULED'
PAYMENT_STATUS_PAID = 'PAID'
PAYMENT_STATUS_OVERDUE = 'OVERDUE'
PAYMENT_STATUS_CANCELLED = 'CANCELLED'

COMMITMENT_STATUS_OPEN = 'OPEN'
COMMITMENT_STATUS_PAID = 'PAID'
COMMITMENT_STATUS_CANCELLED = 'CANCELLED'


def _aware(dt: datetime | None) -> datetime | None:
  """Normalize timezone-aware comparison; SQLite returns naive datetimes."""
  if dt is None:
    return None
  if dt.tzinfo is None:
    return dt.replace(tzinfo=UTC)
  return dt


class FinancePayment(Entity):
  """A single scheduled payment installment against a commitment."""

  def __init__(
    self,
    *,
    commitment_id: str,
    amount: float,
    due_date: datetime,
    organization_id: str,
    payment_id: str | None = None,
  ) -> None:
    super().__init__(payment_id)
    self.commitment_id = commitment_id
    self.amount = amount
    self.due_date = due_date
    self.status = PAYMENT_STATUS_SCHEDULED
    self.organization_id = organization_id
    self.paid_at: datetime | None = None

  def mark_paid(self) -> None:
    if self.status in (PAYMENT_STATUS_PAID, PAYMENT_STATUS_CANCELLED, PAYMENT_STATUS_OVERDUE):
      raise StateTransitionError(f'Cannot mark payment paid from status {self.status}')
    self.status = PAYMENT_STATUS_PAID
    self.paid_at = utc_now()
    self.updated_at = utc_now()

  def cancel(self) -> None:
    if self.status in (PAYMENT_STATUS_PAID, PAYMENT_STATUS_CANCELLED, PAYMENT_STATUS_OVERDUE):
      raise StateTransitionError(f'Cannot cancel payment in status {self.status}')
    self.status = PAYMENT_STATUS_CANCELLED
    self.updated_at = utc_now()

  def mark_overdue(self) -> bool:
    due = _aware(self.due_date) or datetime.now(UTC)
    if self.status == PAYMENT_STATUS_SCHEDULED and utc_now() > due:
      self.status = PAYMENT_STATUS_OVERDUE
      self.updated_at = utc_now()
      return True
    return False


class FinanceCommitment(Entity):
  """A financial commitment (contract value) tied to a contract."""

  def __init__(
    self,
    *,
    contract_id: str,
    description: str,
    amount: float,
    currency: str,
    organization_id: str,
    created_by: str,
    commitment_id: str | None = None,
  ) -> None:
    super().__init__(commitment_id)
    self.contract_id = contract_id
    self.description = description
    self.amount = amount
    self.currency = currency
    self.status = COMMITMENT_STATUS_OPEN
    self.organization_id = organization_id
    self.created_by = created_by

  def cancel(self) -> None:
    if self.status in (COMMITMENT_STATUS_PAID, COMMITMENT_STATUS_CANCELLED):
      raise StateTransitionError(f'Cannot cancel commitment in status {self.status}')
    self.status = COMMITMENT_STATUS_CANCELLED
    self.updated_at = utc_now()
