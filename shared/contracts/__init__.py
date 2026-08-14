"""Shared API contracts (EXEC-006).

Defines the standard response envelope and error shape that every
ECLMS endpoint must honour:

    {
      "success": true,
      "data": {},
      "error": null,
      "trace_id": "string"
    }

    {
      "success": false,
      "data": null,
      "error": { "code": "...", "message": "..." },
      "trace_id": "string"
    }
"""

from __future__ import annotations

from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar('T')


class ApiError(BaseModel):
  code: str
  message: str
  details: dict[str, Any] | None = None


class ApiResponse(BaseModel, Generic[T]):
  success: bool
  data: T | None = None
  error: ApiError | None = None
  trace_id: str = Field(default_factory=lambda: '')


def success(data: Any = None, trace_id: str = '') -> dict[str, Any]:
  return {'success': True, 'data': data, 'error': None, 'trace_id': trace_id}


def failure(code: str, message: str, trace_id: str = '', details: dict[str, Any] | None = None) -> dict[str, Any]:
  error = {'code': code, 'message': message}
  if details:
    error['details'] = details
  return {'success': False, 'data': None, 'error': error, 'trace_id': trace_id}


class PaginatedResult(BaseModel, Generic[T]):
  items: list[T] = []
  total: int = 0
  page: int = 1
  page_size: int = 20
