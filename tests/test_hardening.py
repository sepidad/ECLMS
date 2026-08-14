"""Tests for production hardening: secret validation and security headers."""

import pytest


def test_prod_rejects_default_jwt_secret(monkeypatch):
  from backend.config.settings import Settings

  monkeypatch.setenv('ECLMS_ENVIRONMENT', 'production')
  monkeypatch.setenv('ECLMS_JWT_SECRET', 'dev-only-insecure-secret-key-please-rotate-0123456789')
  with pytest.raises(ValueError, match='ECLMS_JWT_SECRET'):
    Settings()


def test_prod_rejects_short_jwt_secret(monkeypatch):
  from backend.config.settings import Settings

  monkeypatch.setenv('ECLMS_ENVIRONMENT', 'production')
  monkeypatch.setenv('ECLMS_JWT_SECRET', 'short-secret')
  with pytest.raises(ValueError, match='ECLMS_JWT_SECRET'):
    Settings()


def test_prod_accepts_strong_secret(monkeypatch):
  from backend.config.settings import Settings

  monkeypatch.setenv('ECLMS_ENVIRONMENT', 'production')
  monkeypatch.setenv('ECLMS_JWT_SECRET', 'a-very-strong-production-secret-of-sufficient-length-123')
  settings = Settings()
  assert settings.jwt_secret.startswith('a-very-strong')


def test_dev_accepts_default_secret(monkeypatch):
  from backend.config.settings import Settings

  monkeypatch.setenv('ECLMS_ENVIRONMENT', 'development')
  monkeypatch.delenv('ECLMS_JWT_SECRET', raising=False)
  settings = Settings()
  assert settings.environment == 'development'


def test_security_headers_present_on_response(authed_client):
  client, _ = authed_client
  res = client.get('/health')
  assert res.headers.get('X-Content-Type-Options') == 'nosniff'
  assert res.headers.get('X-Frame-Options') == 'DENY'
  assert res.headers.get('Referrer-Policy') == 'no-referrer'


def test_hsts_only_when_trusted_proxy(monkeypatch):
  import importlib

  from fastapi.testclient import TestClient

  monkeypatch.setenv('ECLMS_TRUSTED_PROXY', 'true')
  monkeypatch.setenv('ECLMS_DATABASE_URL', 'sqlite+aiosqlite:///:memory:')

  # The app singleton is built at import time from cached settings, so clear
  # both before constructing a fresh app.  backend.bootstrap.application must
  # be reloaded as well (its module-level app is cached in sys.modules).
  from backend.config import get_settings

  get_settings.cache_clear()
  import backend.bootstrap.application
  import backend.main

  importlib.reload(backend.bootstrap.application)
  importlib.reload(backend.main)
  app = backend.main.app
  with TestClient(app) as client:
    res = client.get('/health')
    assert res.headers.get('Strict-Transport-Security') == 'max-age=31536000; includeSubDomains'
