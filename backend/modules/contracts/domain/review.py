"""Independent reviewer feedback for the official contract version."""

from __future__ import annotations

from dataclasses import dataclass

from backend.core.utils import new_id, utc_now


@dataclass
class ReviewFeedback:
  contract_id: str
  version_id: str
  reviewer_id: str
  reviewer_role: str
  kind: str
  body: str
  proposed_text: str | None = None
  id: str = ''
  status: str = 'OPEN'
  created_at: object = None

  def __post_init__(self) -> None:
    self.id = self.id or new_id()
    self.created_at = self.created_at or utc_now()
