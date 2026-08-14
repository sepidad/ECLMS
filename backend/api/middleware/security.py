"""Security headers middleware.

Adds hardening headers to every response:
  - X-Content-Type-Options: nosniff
  - X-Frame-Options: DENY
  - Referrer-Policy: no-referrer
  - Strict-Transport-Security (only when behind TLS, i.e. ECLMS_TRUSTED_PROXY)
  - Permissions-Policy: no feature that the app does not use

The API itself serves HTTP; TLS is terminated at the reverse proxy.
"""

from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

SECURITY_HEADERS = {
  'X-Content-Type-Options': 'nosniff',
  'X-Frame-Options': 'DENY',
  'Referrer-Policy': 'no-referrer',
  'Permissions-Policy': 'geolocation=(), microphone=(), camera=()',
}


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
  def __init__(self, app, *, trusted_proxy: bool = False) -> None:
    super().__init__(app)
    self._trusted_proxy = trusted_proxy

  async def dispatch(self, request: Request, call_next):
    response = await call_next(request)
    for name, value in SECURITY_HEADERS.items():
      response.headers.setdefault(name, value)
    if self._trusted_proxy and not response.headers.get('Strict-Transport-Security'):
      response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    return response
