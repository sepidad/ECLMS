"""Obligation domain entity."""

from __future__ import annotations

from datetime import UTC, datetime

from backend.core.base.entity import Entity
from backend.core.exceptions import StateTransitionError
from backend.core.utils import utc_now

OBLIGATION_STATUS_OPEN = 'OPEN'
OBLIGATION_STATUS_OVERDUE = 'OVERDUE'
OBLIGATION_STATUS_COMPLETED = 'COMPLETED'
OBLIGATION_STATUS_CANCELLED = 'CANCELLED'


class Obligation(Entity):
  """Tracks contractual obligations (payments, delivery, compliance checks).

  Args:
    contract_id: Reference to the contract this obligation belongs to.
    description: Details of what is due.
    due_date: The date this obligation is expected to be fulfilled.
    organization_id: Organization this obligation is scoped to (multi-tenancy).
    created_by: ID of the user creating the obligation.
    obligation_id: Optional ID for loading existing entities.
  """

  def __init__(
    self,
    *,
    contract_id: str,
    description: str,
    due_date: datetime,
    organization_id: str,
    created_by: str,
    obligation_id: str | None = None,
  ) -> None:
    super().__init__(obligation_id)
    self.contract_id = contract_id
    self.description = description
    self.due_date = due_date
    self.status = OBLIGATION_STATUS_OPEN
    self.organization_id = organization_id
    self.created_by = created_by
    self.completed_at: datetime | None = None

  def complete(self) -> None:
    """Mark this obligation as completed."""
    if self.status in (OBLIGATION_STATUS_COMPLETED, OBLIGATION_STATUS_CANCELLED):
      raise StateTransitionError(f'Cannot complete obligation in status {self.status}')
    self.status = OBLIGATION_STATUS_COMPLETED
    self.completed_at = utc_now()
    self.updated_at = utc_now()

  def cancel(self) -> None:
    """Mark this obligation as cancelled."""
    if self.status in (OBLIGATION_STATUS_COMPLETED, OBLIGATION_STATUS_CANCELLED):
      raise StateTransitionError(f'Cannot cancel obligation in status {self.status}')
    self.status = OBLIGATION_STATUS_CANCELLED
    self.updated_at = utc_now()

  def mark_overdue(self) -> bool:
    """Transition state to OVERDUE if the due date is in the past and it is OPEN.

    SQLite returns timezone-naive datetimes; normalize before comparing.
    Returns True if transitioned, False otherwise.
    """
    due = self.due_date
    if due.tzinfo is None:
      due = due.replace(tzinfo=datetime.now(UTC).tzinfo)
    if self.status == OBLIGATION_STATUS_OPEN and utc_now() > due:
      self.status = OBLIGATION_STATUS_OVERDUE
      self.updated_at = utc_now()
      return True
    return False
