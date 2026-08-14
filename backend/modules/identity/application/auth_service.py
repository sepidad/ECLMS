"""Authentication service (sequence/10_User_Authentication.md).

Coordinates login and user-context resolution.  Phase 0 uses JWT tokens
signed with the configured secret; external IdP/OAuth flows are added in
Phase 1/Phase 3.
"""

from __future__ import annotations

import secrets
from datetime import UTC, datetime, timedelta
from urllib.parse import urlencode

import bcrypt
import httpx

from backend.config import get_settings
from backend.core.exceptions import UnauthorizedError
from backend.core.security.tokens import create_jwt, decode_jwt
from backend.modules.identity.domain.user import User


def hash_password(password: str) -> str:
  return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def verify_password(password: str, password_hash: str) -> bool:
  try:
    return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))
  except ValueError:
    return False


class AuthService:
  """Issues and validates JWT sessions."""

  def __init__(self, user_repository) -> None:
    self._users = user_repository

  async def authenticate(self, username: str, password: str) -> User:
    user = await self._users.get_by_username(username)
    if user is None or not user.is_active:
      raise UnauthorizedError('Invalid credentials')
    if not verify_password(password, user.password_hash):
      raise UnauthorizedError('Invalid credentials')
    return user

  async def login(self, username: str, password: str) -> dict:
    settings = get_settings()
    user = await self.authenticate(username, password)
    token = self._create_token(user, settings)
    return {'access_token': token, 'token_type': 'bearer', 'user': self._public(user)}

  def _create_token(self, user: User, settings) -> str:
    now = datetime.now(UTC)
    payload = {
      'sub': user.id,
      'username': user.username,
      'org': user.organization_id,
      'iat': now,
      'exp': now + timedelta(minutes=settings.jwt_expire_minutes),
    }
    return create_jwt(payload, settings.jwt_secret, settings.jwt_algorithm)

  async def resolve_user(self, token: str) -> User:
    settings = get_settings()
    try:
      payload = decode_jwt(token, settings.jwt_secret, (settings.jwt_algorithm,))
    except Exception as exc:
      raise UnauthorizedError('Invalid or expired token') from exc
    return await self.resolve_user_by_id(payload.get('sub', ''))

  async def resolve_user_by_id(self, user_id: str) -> User:
    user = await self._users.get_by_id(user_id)
    if user is None or not user.is_active:
      raise UnauthorizedError('User no longer active')
    return user

  # OIDC methods
  def oidc_authorization_url(self, state: str, nonce: str | None = None) -> str:
    """Build the OIDC authorization URL for redirecting the user to the IdP."""
    settings = get_settings()
    if not settings.oidc_enabled:
      raise UnauthorizedError('OIDC is not enabled')
    params = {
      'response_type': 'code',
      'client_id': settings.oidc_client_id,
      'redirect_uri': settings.oidc_redirect_uri,
      'scope': ' '.join(settings.oidc_scopes),
      'state': state,
    }
    if nonce:
      params['nonce'] = nonce
    return f'{settings.oidc_issuer.rstrip("/")}/protocol/openid-connect/auth?{urlencode(params)}'

  def _internal_issuer(self, settings) -> str:
    """Base issuer for server-to-server calls (falls back to the public issuer)."""
    return (settings.oidc_internal_issuer or settings.oidc_issuer).rstrip('/')

  async def oidc_exchange_code(self, code: str, state: str) -> dict:
    """Exchange authorization code for tokens and return user info + internal JWT."""
    settings = get_settings()
    if not settings.oidc_enabled:
      raise UnauthorizedError('OIDC is not enabled')

    token_url = f'{self._internal_issuer(settings)}/protocol/openid-connect/token'
    data = {
      'grant_type': 'authorization_code',
      'code': code,
      'redirect_uri': settings.oidc_redirect_uri,
      'client_id': settings.oidc_client_id,
      'client_secret': settings.oidc_client_secret,
    }
    async with httpx.AsyncClient(timeout=10.0) as client:
      resp = await client.post(token_url, data=data)
      resp.raise_for_status()
      tokens = resp.json()

    access_token = tokens.get('access_token')
    if not access_token:
      raise UnauthorizedError('No access token returned from IdP')

    # Fetch user info from IdP
    userinfo = await self._fetch_oidc_userinfo(access_token, settings)
    return await self._upsert_oidc_user(userinfo, settings)

  async def _fetch_oidc_userinfo(self, access_token: str, settings) -> dict:
    userinfo_url = f'{self._internal_issuer(settings)}/protocol/openid-connect/userinfo'
    async with httpx.AsyncClient(timeout=10.0) as client:
      resp = await client.get(
        userinfo_url,
        headers={'Authorization': f'Bearer {access_token}'},
      )
      resp.raise_for_status()
      return resp.json()

  async def _upsert_oidc_user(self, userinfo: dict, settings) -> dict:
    """Find or create local user from OIDC claims, issue internal JWT."""
    email = userinfo.get('email')
    sub = userinfo.get('sub')
    if not email or not sub:
      raise UnauthorizedError('Insufficient claims from IdP')

    # Try to find existing user by email
    user = await self._users.get_by_email(email)
    if user is None:
      # Create new user (inactive by default; admin must activate / assign role)
      user = User(
        username=f'oidc_{sub[:8]}',
        email=email,
        full_name=userinfo.get('name', email.split('@')[0]),
        password_hash=hash_password(secrets.token_urlsafe(32)),
        organization_id=settings.oidc_default_org,
        is_active=False,  # require admin activation
      )
      await self._users.save(user)

    # Issue internal JWT
    token = self._create_token(user, settings)
    return {'access_token': token, 'token_type': 'bearer', 'user': self._public(user)}

  @staticmethod
  def _public(user: User) -> dict:
    return {
      'id': user.id,
      'username': user.username,
      'email': user.email,
      'full_name': user.full_name,
      'organization_id': user.organization_id,
    }
