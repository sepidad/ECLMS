"""Base entity used by every module's domain layer.

All business entities carry a stable identifier, creation timestamp and
update timestamp so the platform can satisfy its auditability
requirements (Constitution Article VIII).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime


def utc_now() -> datetime:
  return datetime.now(UTC)


class Entity:
  """Base class for domain entities.

  Entity equality is identity-based (by id), not value-based.
  """

  def __init__(self, entity_id: str | None = None) -> None:
    self.id: str = entity_id or uuid.uuid4().hex
    self.created_at: datetime = utc_now()
    self.updated_at: datetime = utc_now()

  def __eq__(self, other: object) -> bool:
    if not isinstance(other, Entity):
      return NotImplemented
    return self.id == other.id

  def __hash__(self) -> int:
    return hash(self.id)
