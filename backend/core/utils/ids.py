"""Shared utility helpers for the backend kernel."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime


def new_id() -> str:
  """Generate a new unique identifier."""
  return uuid.uuid4().hex


def utc_now() -> datetime:
  """Return the current UTC datetime."""
  return datetime.now(UTC)


def utc_now_iso() -> str:
  """Return the current UTC datetime as an ISO 8601 string."""
  return utc_now().isoformat()
