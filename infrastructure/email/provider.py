"""Email provider contract (integration/05_Email_Integration.md).

Email is a side-effect, never a business action.  The provider contract
keeps the notification module independent of the concrete email backend.
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class EmailProvider(ABC):
  """Contract for sending emails."""

  @abstractmethod
  async def send(
    self,
    *,
    to: list[str],
    subject: str,
    body: str,
    html: str | None = None,
  ) -> None:
    raise NotImplementedError
