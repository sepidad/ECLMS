"""Unit tests for the event bus."""


from backend.core.events import Event, EventBus


async def test_publish_dispatches_to_matching_handler():
  bus = EventBus()
  received: list[Event] = []

  async def handler(event: Event) -> None:
    received.append(event)

  bus.subscribe('contract.created', handler)
  await bus.publish(Event(event_type='contract.created', source_module='contracts', payload={'id': '1'}))

  assert len(received) == 1
  assert received[0].event_type == 'contract.created'
  assert received[0].payload == {'id': '1'}


async def test_publish_ignores_non_matching_handlers():
  bus = EventBus()
  received: list[Event] = []

  async def handler(event: Event) -> None:
    received.append(event)

  bus.subscribe('contract.created', handler)
  await bus.publish(Event(event_type='other.event', source_module='audit'))

  assert received == []


async def test_subscribe_all_receives_every_event():
  bus = EventBus()
  received: list[Event] = []

  async def handler(event: Event) -> None:
    received.append(event)

  bus.subscribe_all(handler)
  await bus.publish(Event(event_type='a', source_module='m'))
  await bus.publish(Event(event_type='b', source_module='m'))

  assert [e.event_type for e in received] == ['a', 'b']


async def test_handler_failure_does_not_break_other_handlers():
  bus = EventBus()
  received: list[Event] = []

  async def bad(event: Event) -> None:
    raise RuntimeError('boom')

  async def good(event: Event) -> None:
    received.append(event)

  bus.subscribe('evt', bad)
  bus.subscribe('evt', good)
  await bus.publish(Event(event_type='evt', source_module='m'))

  assert len(received) == 1


def test_event_to_dict_contract():
  event = Event(event_type='contract.created', source_module='contracts', payload={'id': 'x'})
  data = event.to_dict()
  assert set(data.keys()) == {'event_id', 'event_type', 'timestamp', 'source_module', 'payload', 'metadata'}
