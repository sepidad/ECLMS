"""Response envelope helpers (EXEC-006 section 5).

Convenience constructors around the shared ApiResponse contract so API
routes and error middleware stay consistent.
"""

from __future__ import annotations

from typing import Any

from shared.contracts import failure, success


def ok(data: Any = None, trace_id: str = '') -> dict[str, Any]:
  return success(data, trace_id)


def err(code: str, message: str, trace_id: str = '', details: dict[str, Any] | None = None) -> dict[str, Any]:
  return failure(code, message, trace_id, details)
