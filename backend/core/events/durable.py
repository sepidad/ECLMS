"""Durable event bus.

Composes the in-memory ``EventBus`` with a ``MessageBroker`` so every
published event is persisted before local handlers run.  A background
drain task re-dispatches persisted events that were not yet handled
(crash recovery) and acknowledges them.  This provides at-least-once
delivery without changing the subscriber contract.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from backend.core.events.bus import EventBus
from backend.core.events.event import Event
from infrastructure.messaging.broker import MessageBroker

logger = logging.getLogger('eclms.events')

DEFAULT_DRAIN_INTERVAL = 5.0
DEFAULT_BATCH_SIZE = 100


class DurableEventBus(EventBus):
  """Persist events to a broker and dispatch to local in-process handlers."""

  def __init__(
    self,
    broker: MessageBroker,
    drain_interval: float = DEFAULT_DRAIN_INTERVAL,
    batch_size: int = DEFAULT_BATCH_SIZE,
  ) -> None:
    super().__init__()
    self._broker = broker
    self._drain_interval = drain_interval
    self._batch_size = batch_size
    self._drain_task: asyncio.Task | None = None
    self._started = False

  async def publish(self, event: Event) -> None:
    await self._broker.publish(event)
    logger.info('Published event %s to broker', event.event_type)

  async def start(self) -> None:
    """Connect the broker and start the crash-recovery drain task."""
    await self._broker.connect()
    self._drain_task = asyncio.create_task(self._drain_loop())
    self._started = True
    logger.info('Durable event bus started')

  async def stop(self) -> None:
    if self._drain_task is not None:
      self._drain_task.cancel()
      try:
        await self._drain_task
      except asyncio.CancelledError:
        pass
    await self._broker.close()
    self._started = False

  def _event_from_json(self, raw: str) -> Event:
    data: dict[str, Any] = json.loads(raw)
    return Event(
      event_type=data['event_type'],
      source_module=data['source_module'],
      payload=data.get('payload', {}),
      metadata=data.get('metadata', {}),
      event_id=data['event_id'],
      timestamp=data.get('timestamp', ''),
    )

  async def _drain_loop(self) -> None:
    while True:
      try:
        async for message_id, raw in self._broker.listen(count=self._batch_size):
          try:
            event = self._event_from_json(raw)
            await self._dispatch(event)
            await self._broker.acknowledge(message_id)
          except Exception:
            logger.exception('Failed to process persisted event %s', message_id)
        await asyncio.sleep(self._drain_interval)
      except asyncio.CancelledError:
        raise
      except Exception:
        logger.exception('Drain loop error; retrying')
        await asyncio.sleep(self._drain_interval)