"""Audit module (Constitution Article VIII — Audit by Default).

Phase 0 scope: audit event model and an in-memory append-only store.
Phase 1: events are persisted to the database via the append-only
SqlAuditStore.  Phase 2 adds the full immutable audit trail system.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from backend.core.base.module import Module
from backend.core.events.event import Event

if TYPE_CHECKING:
  from backend.api.gateway import APIGateway
  from backend.bootstrap.container import ModuleContainer
  from backend.core.events import EventBus


class AuditEventRecord:
  """An immutable audit record.

  Audit records can never be modified or deleted (business rule).
  """

  def __init__(self, event: Event, *, actor_id: str | None = None) -> None:
    self.id = event.event_id
    self.event_type = event.event_type
    self.source_module = event.source_module
    self.payload = event.payload
    self.metadata = event.metadata
    self.actor_id = actor_id
    self.timestamp = event.timestamp

  def to_dict(self) -> dict[str, Any]:
    return {
      'id': self.id,
      'event_type': self.event_type,
      'source_module': self.source_module,
      'actor_id': self.actor_id,
      'timestamp': self.timestamp,
      'payload': self.payload,
    }


class AuditModule(Module):
  name = 'audit'
  version = '0.1.0'

  def initialize(self, container: ModuleContainer) -> None:
    from infrastructure.database.repositories import SqlAuditStore

    self._store = SqlAuditStore()

  def register_services(self, container: ModuleContainer) -> None:
    container.register_service('audit.store', self._store)

  def register_routes(self, gateway: APIGateway) -> None:
    from backend.modules.audit.interfaces.routes import router

    gateway.mount('audit', router)

  def register_events(self, bus: EventBus) -> None:
    """Persist every published domain event as an audit record."""

    async def record(event: Event) -> None:
      await self._store.append(event)

    bus.subscribe_all(record)
