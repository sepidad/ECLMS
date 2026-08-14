"""Tests for OIDC integration in AuthService (backend/modules/identity/application/auth_service.py)."""

from __future__ import annotations

from typing import ClassVar

import pytest

from backend.core.exceptions import UnauthorizedError
from backend.modules.identity.application.auth_service import AuthService


class FakeUser:
  def __init__(self, username, email, full_name, password_hash, organization_id, is_active=True):
    self.id = f'id_{username}'
    self.username = username
    self.email = email
    self.full_name = full_name
    self.password_hash = password_hash
    self.organization_id = organization_id
    self.is_active = is_active
    self.roles = []

  def deactivate(self):
    pass


class FakeUserRepository:
  def __init__(self):
    self.users = []
    self.saved = []

  async def get_by_email(self, email):
    for u in self.users:
      if u.email == email:
        return u
    return None

  async def save(self, user):
    self.saved.append(user)
    if user not in self.users:
      self.users.append(user)


class FakeResponse:
  status_code = 200

  def __init__(self, payload):
    self._payload = payload

  def json(self):
    return self._payload

  def raise_for_status(self):
    return None


class FakeClient:
  def __init__(self, responses):
    self._responses = list(responses)
    self._calls = []

  async def __aenter__(self):
    return self

  async def __aexit__(self, *exc):
    return False

  async def post(self, url, **kwargs):
    self._calls.append(('post', url, kwargs))
    return self._responses.pop(0)

  async def get(self, url, **kwargs):
    self._calls.append(('get', url, kwargs))
    return self._responses.pop(0)


class FakeSettings:
  jwt_secret = 'test-secret-that-is-at-least-thirty-two-bytes-long'
  jwt_algorithm = 'HS256'
  jwt_expire_minutes = 30
  oidc_enabled = True
  oidc_issuer = 'https://idp.example.com'
  oidc_client_id = 'client-123'
  oidc_client_secret = 'sec'
  oidc_redirect_uri = 'https://api.example.com/oidc/callback'
  oidc_scopes: ClassVar[list[str]] = ['openid', 'email', 'profile']
  oidc_default_org = 'org-default'
  oidc_internal_issuer = ''


@pytest.fixture(autouse=True)
def _clear_settings_cache():
  from backend.config import get_settings

  get_settings.cache_clear()
  yield
  get_settings.cache_clear()


def test_oidc_authorization_url(monkeypatch):
  from backend.modules.identity.application import auth_service as mod

  monkeypatch.setattr(mod, 'get_settings', lambda: FakeSettings())
  service = AuthService(FakeUserRepository())
  url = service.oidc_authorization_url('abc123')
  assert url.startswith('https://idp.example.com/protocol/openid-connect/auth?')
  assert 'client_id=client-123' in url
  assert 'scope=openid+email+profile' in url
  assert 'state=abc123' in url


def test_oidc_authorization_url_disabled(monkeypatch):
  from backend.modules.identity.application import auth_service as mod

  settings = FakeSettings()
  settings.oidc_enabled = False
  monkeypatch.setattr(mod, 'get_settings', lambda: settings)
  service = AuthService(FakeUserRepository())
  with pytest.raises(UnauthorizedError):
    service.oidc_authorization_url('state')


@pytest.mark.anyio
async def test_oidc_exchange_happy_path(monkeypatch):
  fake = FakeUserRepository()
  service = AuthService(fake)

  # Single shared client so the token-exhange POST and userinfo GET drain
  # the same response queue (userinfo_url -> token_url boundary).
  shared = FakeClient([
    FakeResponse(token_payload()),
    FakeResponse(userinfo_payload()),
  ])
  monkeypatch.setattr('backend.modules.identity.application.auth_service.httpx.AsyncClient', lambda *a, **k: shared)

  from backend.modules.identity.application import auth_service as mod

  monkeypatch.setattr(mod, 'get_settings', lambda: FakeSettings())

  result = await service.oidc_exchange_code('code', 'expiring')
  assert result['token_type'] == 'bearer'
  assert result['user']['email'] == 'user@example.com'
  assert result['user']['username'] == 'oidc_12345678'
  assert result['user']['organization_id'] == 'org-default'
  # new user is inactive by default
  assert fake.users[0].is_active is False


@pytest.mark.anyio
async def test_oidc_exchange_insufficient_claims(monkeypatch):
  service = AuthService(FakeUserRepository())

  shared = FakeClient([
    FakeResponse(token_payload()),
    FakeResponse({'sub': '12345678'}),  # no email
  ])
  monkeypatch.setattr('backend.modules.identity.application.auth_service.httpx.AsyncClient', lambda *a, **k: shared)

  with pytest.raises(UnauthorizedError):
    await service.oidc_exchange_code('code', 'expiring')


@pytest.mark.anyio
async def test_oidc_exchange_uses_internal_issuer(monkeypatch):
  settings = FakeSettings()
  settings.oidc_internal_issuer = 'http://keycloak.internal:8080/realms/eclms'
  from backend.modules.identity.application import auth_service as mod

  monkeypatch.setattr(mod, 'get_settings', lambda: settings)

  service = AuthService(FakeUserRepository())
  shared = FakeClient([
    FakeResponse(token_payload()),
    FakeResponse(userinfo_payload()),
  ])
  monkeypatch.setattr('backend.modules.identity.application.auth_service.httpx.AsyncClient', lambda *a, **k: shared)

  await service.oidc_exchange_code('code', 'state')

  post_url = next(url for method, url, _ in shared._calls if method == 'post')
  get_url = next(url for method, url, _ in shared._calls if method == 'get')
  assert post_url == 'http://keycloak.internal:8080/realms/eclms/protocol/openid-connect/token'
  assert get_url == 'http://keycloak.internal:8080/realms/eclms/protocol/openid-connect/userinfo'


@pytest.mark.anyio
async def test_oidc_exchange_disabled(monkeypatch):
  settings = FakeSettings()
  settings.oidc_enabled = False
  from backend.modules.identity.application import auth_service as mod

  monkeypatch.setattr(mod, 'get_settings', lambda: settings)
  service = AuthService(FakeUserRepository())
  with pytest.raises(UnauthorizedError):
    await service.oidc_exchange_code('code', 'state')


@pytest.mark.anyio
async def test_oidc_exchange_no_access_token(monkeypatch):
  service = AuthService(FakeUserRepository())

  shared = FakeClient([FakeResponse({})])  # no access_token, no userinfo call
  monkeypatch.setattr('backend.modules.identity.application.auth_service.httpx.AsyncClient', lambda *a, **k: shared)
  with pytest.raises(UnauthorizedError):
    await service.oidc_exchange_code('code', 'state')


# FakeResponse handled by FakeClient above


def token_payload():
  return {'access_token': 'token-1', 'id_token': 'id-token-1'}


def userinfo_payload():
  return {
    'sub': '12345678',
    'email': 'user@example.com',
    'name': 'Example User',
  }