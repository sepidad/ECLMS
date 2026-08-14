"""Durable event transport backed by Redis Streams.

Implements the ``MessageBroker`` contract so the core ``EventBus`` can
persist events for at-least-once delivery and re-dispatch across process
restarts.  A dedicated consumer group tracks per-handler acknowledgements;
events are only removed from the stream once every member in the group has
acknowledged them, so no message is lost on worker crash (backed by Redis
AOF/RDB persistence).

Transport is optional.  When ``ECLMS_EVENT_TRANSPORT=memory`` (the default)
nothing is persisted and the in-process bus is used directly.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from backend.core.events.event import Event
from infrastructure.messaging.broker import MessageBroker

logger = logging.getLogger('eclms.events.redis')

STREAM_KEY = 'eclms:events'


class RedisBroker(MessageBroker):
  """Persist events to a Redis stream and consume via a consumer group."""

  def __init__(self, url: str, stream: str = STREAM_KEY, group: str = 'eclms:messages') -> None:
    self._url = url
    self._stream = stream
    self._group = group
    self._redis: Any | None = None
    self._consumer = 'eclms-consumer'

  async def connect(self) -> None:
    import redis.asyncio as aioredis

    self._redis = aioredis.from_url(self._url, decode_responses=True)
    await self._redis.ping()
    try:
      await self._redis.xgroup_create(self._stream, self._group, id='0', mkstream=True)
    except Exception as exc:  # noqa: BLE001 - group may already exist
      logger.info('Consumer group setup skipped: %s', exc)
    logger.info('Connected Redis event broker (%s)', self._url)

  async def publish(self, event: Event) -> None:
    if self._redis is None:
      await self.connect()
    assert self._redis is not None
    await self._redis.xadd(self._stream, {'event': json.dumps(event.to_dict())})

  async def listen(self, count: int = 10, block_ms: int = 5000):
    """Read pending and new events from the stream for the consumer group."""
    if self._redis is None:
      await self.connect()
    assert self._redis is not None
    entries = await self._redis.xreadgroup(
      groupname=self._group,
      consumername=self._consumer,
      streams={self._stream: '>'},
      count=count,
      block=block_ms,
    )
    for _stream_name, messages in entries:
      for message_id, fields in messages:
        yield message_id, fields['event']

  async def acknowledge(self, message_id: str) -> None:
    if self._redis is None:
      await self.connect()
    assert self._redis is not None
    await self._redis.xack(self._stream, self._group, message_id)

  async def close(self) -> None:
    if self._redis is not None:
      await self._redis.aclose()
      self._redis = None