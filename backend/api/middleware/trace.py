"""Trace id middleware.

Assigns a correlation id to every request.  The id is accepted from the
X-Trace-Id header when present, otherwise generated, and echoed back in
the response header.
"""

from __future__ import annotations

import contextvars

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from backend.api.middleware.context import get_trace_id, reset_trace_id, set_trace_id


class TraceContextMiddleware(BaseHTTPMiddleware):
  async def dispatch(self, request: Request, call_next):
    incoming = request.headers.get('X-Trace-Id', '')
    token: contextvars.Token = set_trace_id(incoming)
    trace_id = get_trace_id()
    try:
      response = await call_next(request)
    finally:
      reset_trace_id(token)
    response.headers['X-Trace-Id'] = trace_id
    return response
