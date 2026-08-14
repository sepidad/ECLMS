"""Central exception handling (EXEC-006 section 5.1).

Maps ECLMS exceptions to structured error responses and provides a
catch-all for unexpected errors so the API never leaks raw exceptions.
"""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from backend.api.middleware.context import get_trace_id
from backend.api.responses import err
from backend.core.exceptions import ECLMSError

logger = logging.getLogger('eclms.api')


def register_exception_handlers(app: FastAPI) -> None:
  @app.exception_handler(ECLMSError)
  async def handle_eclms_error(request: Request, exc: ECLMSError):
    logger.warning(
      'Request failed: code=%s message=%s path=%s',
      exc.code,
      exc.message,
      request.url.path,
      extra={'event_type': 'error', 'source_module': 'api'},
    )
    return JSONResponse(
      status_code=exc.http_status,
      content=err(exc.code, exc.message, get_trace_id(), exc.details),
    )

  @app.exception_handler(RequestValidationError)
  async def handle_validation_error(request: Request, exc: RequestValidationError):
    logger.warning('Request validation failed: %s', exc.errors())
    return JSONResponse(
      status_code=422,
      content=err('VALIDATION_ERROR', 'Request validation failed', get_trace_id(), {'errors': exc.errors()}),
    )

  @app.exception_handler(Exception)
  async def handle_unexpected(request: Request, exc: Exception):
    logger.exception('Unhandled error: %s', exc)
    return JSONResponse(
      status_code=500,
      content=err('INTERNAL_ERROR', 'An unexpected error occurred', get_trace_id()),
    )
