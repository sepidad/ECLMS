"""Domain-level exceptions (MODULE_INTERFACE_SPECIFICATION section 11).

All module exceptions must be structured, traceable, and handled by the
central exception middleware.
"""

from __future__ import annotations

from backend.core.exceptions.base import ECLMSError


class DomainError(ECLMSError):
  """Base error for business-rule violations within a bounded context."""

  code = 'DOMAIN_ERROR'
  http_status = 422
