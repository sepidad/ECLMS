"""Messaging infrastructure.

Phase 0 exposes a provider contract.  The in-memory implementation
bridges to the core EventBus; a durable broker may be added later.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from backend.core.events.event import Event


class MessageBroker(ABC):
  """Contract for message transport providers."""

  @abstractmethod
  async def publish(self, event: Event) -> None:
    raise NotImplementedError

  @abstractmethod
  async def connect(self) -> None:
    raise NotImplementedError

  @abstractmethod
  async def close(self) -> None:
    raise NotImplementedError
