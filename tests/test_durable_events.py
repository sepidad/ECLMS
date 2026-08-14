"""Tests for the durable event transport (Redis-backed, at-least-once).

Uses an in-memory fake broker so the durable semantics can be verified
without a running Redis server.
"""

from __future__ import annotations

import asyncio
import json

import pytest

from backend.core.events import DurableEventBus, Event
from infrastructure.messaging.broker import MessageBroker


class FakeBroker(MessageBroker):
  """In-memory broker recording published and acknowledged messages."""

  def __init__(self) -> None:
    self.messages: list[tuple[str, str]] = []
    self.consumed: list[str] = []
    self.acknowledged: list[str] = []
    self.connected = False
    self.closed = False
    self.deliver = True
    self.fail_delivery = 0

  async def connect(self) -> None:
    self.connected = True

  async def publish(self, event: Event) -> None:
    self.messages.append((event.event_id, json.dumps(event.to_dict())))

  async def listen(self, count=1, block_ms=None):
    if not self.deliver:
      return
    for message_id, raw in self.messages:
      if message_id not in self.consumed:
        self.consumed.append(message_id)
        if self.fail_delivery > 0:
          self.fail_delivery -= 1
          raise RuntimeError('delivery failed')
        yield message_id, raw

  async def acknowledge(self, message_id: str) -> None:
    self.acknowledged.append(message_id)

  async def close(self) -> None:
    self.closed = True


async def _record(received: list[Event], event: Event) -> None:
  received.append(event)


@pytest.mark.asyncio
async def test_event_reaches_subscriber_after_persist_and_drain():
  broker = FakeBroker()
  bus = DurableEventBus(broker)
  received: list[Event] = []
  bus.subscribe('test.event', lambda e: _record(received, e))

  await bus.start()
  await bus.publish(Event(event_type='test.event', source_module='test', payload={'a': 1}))
  await asyncio.sleep(0.1)
  await bus.stop()

  assert broker.connected is True
  assert broker.closed is True
  # Published to the broker exactly once and drained/acked once.
  assert len(broker.messages) == 1
  assert received, 'subscriber never ran'
  assert received[0].event_type == 'test.event'
  assert received[0].payload == {'a': 1}
  assert broker.acknowledged == [broker.messages[0][0]]


@pytest.mark.asyncio
async def test_message_persisted_even_when_no_subscriber():
  broker = FakeBroker()
  bus = DurableEventBus(broker)
  await bus.start()
  # No subscriber registered; event should still be durable (persisted).
  await bus.publish(Event(event_type='test.event', source_module='test'))
  await asyncio.sleep(0.05)
  await bus.stop()

  assert len(broker.messages) == 1
  # No subscribers means the message is still durable; drain acks it.
  assert broker.acknowledged == [broker.messages[0][0]]


@pytest.mark.asyncio
async def test_memory_bus_does_not_use_broker():
  from backend.core.events import EventBus

  bus = EventBus()
  out: list[str] = []

  async def handler(event: Event) -> None:
    out.append(event.event_type)

  bus.subscribe('x', handler)
  await bus.publish(Event(event_type='x', source_module='t'))
  assert out == ['x']