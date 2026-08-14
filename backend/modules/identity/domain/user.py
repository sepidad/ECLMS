"""Identity domain: User aggregate.

The user aggregate carries identity attributes and credential state.
Domain rules (Constitution Article VIII) require that any change is
traceable; timestamps are captured on the aggregate root.
"""

from __future__ import annotations

from backend.core.base.entity import Entity
from backend.core.utils import utc_now


class User(Entity):
  """A system user.

  Args:
    username: Unique login name.
    email: Contact email (unique).
    full_name: Display name.
    password_hash: BCrypt hash of the password.
    is_active: Whether the account may authenticate.
    organization_id: Owning organization (required by domain invariant
        'every entity belongs to one organization').
  """

  def __init__(
    self,
    username: str,
    email: str,
    full_name: str,
    password_hash: str,
    *,
    organization_id: str,
    is_active: bool = True,
    user_id: str | None = None,
  ) -> None:
    super().__init__(user_id)
    self.username = username
    self.email = email
    self.full_name = full_name
    self.password_hash = password_hash
    self.organization_id = organization_id
    self.is_active = is_active
    self.roles: list[str] = []

  def deactivate(self) -> None:
    """Deactivate the account.  Deactivated users cannot authenticate."""
    self.is_active = False
    self.updated_at = utc_now()
