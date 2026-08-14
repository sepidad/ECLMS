"""Base exception for the ECLMS platform.

Every error that crosses an architectural boundary should derive from
this hierarchy so the central error middleware can produce a structured
response (EXEC-006 section 5.1).
"""

from __future__ import annotations

from typing import Any


class ECLMSError(Exception):
  """Root error type for the platform.

  Attributes:
    code: Stable machine-readable error code returned to callers.
    http_status: HTTP status mapped to this error.
    message: Human readable message.
    details: Optional structured payload attached to the error.
    cause: Optional underlying exception for traceability.
  """

  code = 'ECLMS_ERROR'
  http_status = 500
  message = 'An unexpected error occurred'

  def __init__(
    self,
    message: str | None = None,
    *,
    details: dict[str, Any] | None = None,
    cause: Exception | None = None,
  ) -> None:
    self.message = message or self.message
    self.details = details
    self.cause = cause
    super().__init__(self.message)
