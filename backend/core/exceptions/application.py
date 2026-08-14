"""Application-layer exceptions."""

from __future__ import annotations

from backend.core.exceptions.base import ECLMSError


class ApplicationError(ECLMSError):
  """Base error for use-case orchestration failures."""

  code = 'APPLICATION_ERROR'
  http_status = 500


class NotFoundError(ApplicationError):
  code = 'NOT_FOUND'
  http_status = 404


class ConflictError(ApplicationError):
  code = 'CONFLICT'
  http_status = 409


class ValidationError(ApplicationError):
  code = 'VALIDATION_ERROR'
  http_status = 422


class UnauthorizedError(ApplicationError):
  code = 'UNAUTHORIZED'
  http_status = 401


class ForbiddenError(ApplicationError):
  code = 'FORBIDDEN'
  http_status = 403


class StateTransitionError(ApplicationError):
  code = 'INVALID_STATE_TRANSITION'
  http_status = 409
