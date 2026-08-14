"""In-memory event bus.

Provides the internal publish/subscribe mechanism used by modules for
decoupled communication (EXEC-004 section 7.2).  The bus is intentionally
synchronous for the MVP; a durable transport may replace it in the
integration layer without changing the subscriber contract.
"""

from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from collections.abc import Awaitable, Callable

from backend.core.events.event import Event

logger = logging.getLogger('eclms.events')

Handler = Callable[[Event], Awaitable[None]]


class EventBus:
  def __init__(self) -> None:
    self._handlers: dict[str, list[Handler]] = defaultdict(list)
    self._wildcard: list[Handler] = []

  def subscribe(self, event_type: str, handler: Handler) -> None:
    self._handlers[event_type].append(handler)

  def subscribe_all(self, handler: Handler) -> None:
    """Subscribe to every published event (used by the audit module)."""
    self._wildcard.append(handler)

  def unsubscribe(self, event_type: str, handler: Handler) -> None:
    if handler in self._handlers.get(event_type, []):
      self._handlers[event_type].remove(handler)

  async def publish(self, event: Event) -> None:
    await self._dispatch(event)

  async def _dispatch(self, event: Event) -> None:
    handlers = list(self._handlers.get(event.event_type, [])) + list(self._wildcard)
    if not handlers:
      logger.debug('No subscribers for event %s', event.event_type)
      return
    logger.info('Publishing event %s (%d handler(s))', event.event_type, len(handlers))
    results = await asyncio.gather(*(h(event) for h in handlers), return_exceptions=True)
    for result in results:
      if isinstance(result, BaseException):
        logger.exception('Event handler failed for %s', event.event_type, exc_info=result)
