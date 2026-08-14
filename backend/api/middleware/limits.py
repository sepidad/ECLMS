"""API hardening middleware: rate limiting and request body-size limits.

- ``BodySizeLimitMiddleware`` rejects requests whose ``Content-Length``
  exceeds ``max_request_bytes`` with ``HTTP 413`` (no body consumption).
- ``RateLimitMiddleware`` enforces a simple fixed-window per-client-IP
  counter (honoring ``X-Forwarded-For`` behind a trusted proxy), enabling
  an explicit opt-in (``ECLMS_RATE_LIMIT_ENABLED``) so tests and local
  development are unaffected.
"""

from __future__ import annotations

import json
import threading
import time
from collections import defaultdict, deque

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

_MAX_QUEUE = 4096


class BodySizeLimitMiddleware(BaseHTTPMiddleware):
  def __init__(self, app, max_bytes: int = 0) -> None:
    super().__init__(app)
    self._max_bytes = max_bytes

  async def dispatch(self, request, call_next):
    if self._max_bytes > 0:
      content_length = request.headers.get('content-length')
      if content_length and content_length.isdigit() and int(content_length) > self._max_bytes:
        return _error_response(413, 'PAYLOAD_TOO_LARGE', f'Request body exceeds the {self._max_bytes}-byte limit')
    return await call_next(request)


class RateLimitMiddleware(BaseHTTPMiddleware):
  def __init__(self, app, *, limit: int = 100, window_seconds: int = 60, trusted_proxy: bool = False) -> None:
    super().__init__(app)
    self._limit = limit
    self._window = window_seconds
    self._trusted_proxy = trusted_proxy
    self._hits: dict[str, deque] = defaultdict(deque)
    self._lock = threading.Lock()

  async def dispatch(self, request, call_next):
    key = self._client_key(request)
    now = time.monotonic()

    with self._lock:
      window = self._hits[key]
      cutoff = now - self._window
      while window and window[0] < cutoff:
        window.popleft()
      if len(window) >= self._limit:
        retry = self._window - int(now - window[0]) if window else self._window
        return _error_response(429, 'RATE_LIMITED', f'Too many requests — retry in {max(retry, 0)}s')
      window.append(now)
      if len(self._hits) > _MAX_QUEUE:
        self._hits.clear()

    return await call_next(request)

  def _client_key(self, request) -> str:
    if self._trusted_proxy:
      forwarded = request.headers.get('x-forwarded-for')
      if forwarded:
        return forwarded.split(',')[0].strip()
    host = request.client.host if request.client else 'unknown'
    return host


def _error_response(status_code: int, code: str, message: str) -> Response:
  body = json.dumps({'success': False, 'data': None, 'error': {'code': code, 'message': message}})
  return Response(content=body, status_code=status_code, media_type='application/json')