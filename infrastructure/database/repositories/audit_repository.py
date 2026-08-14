"""SQLAlchemy-backed append-only audit store (replaces the in-memory store).

Audit records are immutable: rows are inserted, never updated or deleted
(Constitution Article VIII).
"""

from __future__ import annotations

import json
from datetime import datetime

from sqlalchemy import select

from backend.core.events import Event
from infrastructure.database.models.documents_audit import AuditEventModel
from infrastructure.database.session import get_session_factory


def _to_record(event: Event) -> AuditEventModel:
  return AuditEventModel(
    id=event.event_id,
    event_type=event.event_type,
    source_module=event.source_module,
    actor_id=event.metadata.get('actor_id'),
    entity_type=event.metadata.get('entity_type'),
    entity_id=event.metadata.get('entity_id'),
    before_state=json.dumps(event.metadata.get('before')) if event.metadata.get('before') else None,
    after_state=json.dumps(event.metadata.get('after')) if event.metadata.get('after') else None,
    payload=json.dumps(event.payload, ensure_ascii=False) if event.payload else None,
    created_at=datetime.fromisoformat(event.timestamp),
  )


class SqlAuditStore:
  async def append(self, event: Event) -> None:
    async with get_session_factory()() as session:
      session.add(_to_record(event))
      await session.commit()

  async def list_all(self, *, limit: int = 100, offset: int = 0) -> list[dict]:
    async with get_session_factory()() as session:
      stmt = (
        select(AuditEventModel)
        .order_by(AuditEventModel.created_at.desc())
        .limit(limit)
        .offset(offset)
      )
      models = (await session.execute(stmt)).scalars().all()
      return [
        {
          'id': m.id,
          'event_type': m.event_type,
          'source_module': m.source_module,
          'actor_id': m.actor_id,
          'entity_type': m.entity_type,
          'entity_id': m.entity_id,
          'created_at': m.created_at,
        }
        for m in models
      ]
