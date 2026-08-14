"""Infrastructure-layer exceptions."""

from __future__ import annotations

from backend.core.exceptions.base import ECLMSError


class InfrastructureError(ECLMSError):
  """Base error for infrastructure and external service failures."""

  code = 'INFRASTRUCTURE_ERROR'
  http_status = 503


class DatabaseError(InfrastructureError):
  code = 'DATABASE_ERROR'


class StorageError(InfrastructureError):
  code = 'STORAGE_ERROR'


class ExternalServiceError(InfrastructureError):
  code = 'EXTERNAL_SERVICE_ERROR'
