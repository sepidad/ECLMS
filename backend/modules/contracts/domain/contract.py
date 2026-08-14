"""Contract domain: Contract aggregate and lifecycle state machine.

The lifecycle is explicit and versioned (Constitution Article IV).  A
contract cannot change state without going through a permitted
transition; no bypass is allowed.
"""

from __future__ import annotations

from datetime import datetime

from backend.core.base.entity import Entity
from backend.core.exceptions import StateTransitionError
from backend.core.utils import utc_now
from shared.constants import CONTRACT_STATE_ARCHIVED, CONTRACT_STATE_DRAFT


class Contract(Entity):
  """A business contract (the core aggregate).

  Args:
    title: Human readable contract title.
    reference_number: Organization-assigned reference.
    counterparty: The other party to the contract.
    organization_id: Owning organization.
  """

  def __init__(
    self,
    title: str,
    reference_number: str,
    counterparty: str,
    *,
    organization_id: str,
    owner_id: str,
    contract_id: str | None = None,
  ) -> None:
    super().__init__(contract_id)
    self.title = title
    self.reference_number = reference_number
    self.counterparty = counterparty
    self.organization_id = organization_id
    self.owner_id = owner_id
    self.state = CONTRACT_STATE_DRAFT
    self.effective_date: datetime | None = None
    self.expiry_date: datetime | None = None
    self.current_version_id: str | None = None

  def transition_to(self, new_state: str) -> None:
    """Validate and apply a lifecycle transition."""
    if not self._is_valid_transition(self.state, new_state):
      raise StateTransitionError(
        f'Invalid transition from {self.state} to {new_state}',
        details={'current': self.state, 'requested': new_state},
      )
    self.state = new_state
    self.updated_at = utc_now()

  @staticmethod
  def _is_valid_transition(current: str, requested: str) -> bool:
    allowed = {
      CONTRACT_STATE_DRAFT: {'SUBMITTED'},
      'SUBMITTED': {'UNDER_REVIEW'},
      'UNDER_REVIEW': {'APPROVED', 'REJECTED'},
      'APPROVED': {'EXECUTED'},
      'EXECUTED': {'ACTIVE'},
      'ACTIVE': {'AMENDED', 'EXPIRED', 'TERMINATED'},
      'REJECTED': {CONTRACT_STATE_DRAFT},
      'AMENDED': {'ACTIVE'},
      'EXPIRED': {CONTRACT_STATE_ARCHIVED},
      'TERMINATED': {CONTRACT_STATE_ARCHIVED},
    }
    return requested in allowed.get(current, set())
