"""Tests for API hardening middleware (rate limiting + body-size limits)."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.api.middleware.limits import BodySizeLimitMiddleware, RateLimitMiddleware


def _client(max_bytes: int = 0, limit: int = 100, window: int = 60) -> TestClient:
  app = FastAPI()

  @app.get('/ping')
  async def ping():
    return {'pong': True}

  @app.post('/echo')
  async def echo():
    return {'ok': True}

  if max_bytes > 0:
    app.add_middleware(BodySizeLimitMiddleware, max_bytes=max_bytes)
  if limit < 1_000_000:
    app.add_middleware(RateLimitMiddleware, limit=limit, window_seconds=window)
  return TestClient(app)


def test_body_size_limit_rejects_large_payload():
  client = _client(max_bytes=100)
  resp = client.post('/echo', content=b'x' * 1000)
  assert resp.status_code == 413
  body = resp.json()
  assert body['error']['code'] == 'PAYLOAD_TOO_LARGE'


def test_body_size_limit_allows_small_payload():
  client = _client(max_bytes=100)
  resp = client.post('/echo', content=b'ok')
  assert resp.status_code == 200
  assert resp.json()['ok'] is True


def test_body_size_limit_disabled_by_default():
  client = _client(max_bytes=0)
  resp = client.post('/echo', content=b'x' * 10_000)
  assert resp.status_code == 200


def test_rate_limit_returns_429_after_threshold():
  client = _client(limit=3, window=60)
  statuses = [client.get('/ping').status_code for _ in range(5)]
  assert statuses[:3] == [200, 200, 200]
  assert statuses[3] == 429
  assert statuses[4] == 429
  assert client.get('/ping').json()['error']['code'] == 'RATE_LIMITED'