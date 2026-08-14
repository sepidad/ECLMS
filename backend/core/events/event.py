"""Event contract (EXEC-004 section 10).

Every ECLMS event MUST follow this shape:

    {
      "event_id":       "...",
      "event_type":     "...",
      "timestamp":      "...",
      "source_module":  "...",
      "payload":        {...},
      "metadata":       {...}
    }

Events are immutable, versioned, and backward compatible.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


def utc_now_iso() -> str:
  return datetime.now(UTC).isoformat()


@dataclass(frozen=True)
class Event:
  event_type: str
  source_module: str
  payload: dict[str, Any] = field(default_factory=dict)
  metadata: dict[str, Any] = field(default_factory=dict)
  event_id: str = field(default_factory=lambda: uuid.uuid4().hex)
  timestamp: str = field(default_factory=utc_now_iso)

  def to_dict(self) -> dict[str, Any]:
    return {
      'event_id': self.event_id,
      'event_type': self.event_type,
      'timestamp': self.timestamp,
      'source_module': self.source_module,
      'payload': self.payload,
      'metadata': self.metadata,
    }
