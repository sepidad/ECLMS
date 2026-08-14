"""Identity API routes (API_CONTRACT_SPECIFICATION section 4.1).

    POST /api/v1/identity/auth/login     (public)
    GET  /api/v1/identity/auth/me        (authenticated)
    GET  /api/v1/identity/auth/oidc/start  (public) - redirect to IdP
    GET  /api/v1/identity/auth/oidc/callback (public) - OIDC callback
    POST /api/v1/identity/users          (user.manage)
    GET  /api/v1/identity/users          (user.manage)
    GET  /api/v1/identity/roles          (authenticated)

Controllers only validate requests and delegate to the application layer.
Authorization is enforced by the shared RBAC guards.
"""

from __future__ import annotations

import httpx
from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field

from backend.api.middleware.context import get_trace_id
from backend.api.responses import err, ok
from backend.api.security import current_user_id, require_permission
from backend.core.exceptions import ECLMSError
from backend.modules.identity.application.auth_service import AuthService
from backend.modules.identity.application.user_service import UserService

router = APIRouter(tags=['identity'])


class LoginRequest(BaseModel):
  username: str = Field(min_length=1)
  password: str = Field(min_length=1)


class CreateUserRequest(BaseModel):
  username: str = Field(min_length=1, max_length=100)
  email: str = Field(min_length=3, max_length=200)
  full_name: str = Field(min_length=1, max_length=200)
  password: str = Field(min_length=8, max_length=128)
  role: str | None = Field(default=None, max_length=100)


class OIDCCallbackRequest(BaseModel):
  code: str
  state: str


class RolePermissionsRequest(BaseModel):
  permissions: list[str]


def _auth(request: Request) -> AuthService:
  return request.app.state.container.get_service('identity.auth')


def _users(request: Request) -> UserService:
  return request.app.state.container.get_service('identity.users.service')


@router.post('/auth/login')
async def login(payload: LoginRequest, request: Request):
  try:
    result = await _auth(request).login(payload.username, payload.password)
  except ECLMSError as exc:
    return err(exc.code, exc.message, get_trace_id(), exc.details)
  return ok(result, get_trace_id())


@router.get('/auth/me')
async def me(request: Request):
  try:
    actor_id = await current_user_id(request)
    user = await _auth(request).resolve_user_by_id(actor_id)
  except ECLMSError as exc:
    return err(exc.code, exc.message, get_trace_id(), exc.details)
  return ok(AuthService._public(user), get_trace_id())


# OIDC endpoints
@router.get('/auth/oidc/start')
async def oidc_start(request: Request, state: str | None = None):
  """Redirect user to OIDC IdP for authentication."""
  import secrets
  state_value = state or secrets.token_urlsafe(16)
  try:
    url = _auth(request).oidc_authorization_url(state_value)
  except ECLMSError as exc:
    return err(exc.code, exc.message, get_trace_id(), exc.details)
  return RedirectResponse(url=url)


@router.get('/auth/oidc/callback')
async def oidc_callback(request: Request, code: str, state: str):
  """Handle OIDC callback from IdP, exchange code for tokens, issue internal JWT."""
  try:
    result = await _auth(request).oidc_exchange_code(code, state)
  except ECLMSError as exc:
    return err(exc.code, exc.message, get_trace_id(), exc.details)
  except httpx.HTTPError as exc:
    return err('OIDC_EXCHANGE_FAILED', f'IdP token exchange failed: {exc}', get_trace_id())
  return ok(result, get_trace_id())


@router.post('/users')
async def create_user(payload: CreateUserRequest, request: Request):
  try:
    actor = await require_permission(request, 'user.manage')
    user = await _users(request).create_user(
      **payload.model_dump(exclude_none=True),
      organization_id=actor.organization_id,
    )
  except ECLMSError as exc:
    return err(exc.code, exc.message, get_trace_id(), exc.details)
  return ok(AuthService._public(user), get_trace_id())


@router.get('/users')
async def list_users(request: Request):
  try:
    actor = await require_permission(request, 'user.manage')
    users = await _users(request).list_users(organization_id=actor.organization_id)
  except ECLMSError as exc:
    return err(exc.code, exc.message, get_trace_id(), exc.details)
  return ok(
    {
      'items': [
        {**AuthService._public(u), 'roles': u.roles, 'is_active': u.is_active} for u in users
      ]
    },
    get_trace_id(),
  )


@router.get('/roles')
async def list_roles(request: Request):
  try:
    await current_user_id(request)
    roles = await _users(request).list_roles()
    permissions = await _users(request).list_permissions()
  except ECLMSError as exc:
    return err(exc.code, exc.message, get_trace_id(), exc.details)
  return ok({'roles': roles, 'permissions': permissions}, get_trace_id())


@router.get('/roles/{role_name}/permissions')
async def role_permissions(role_name: str, request: Request):
  try:
    await require_permission(request, 'user.manage')
    service = _users(request)
    permissions = await service.role_permissions(role_name)
    all_permissions = await service.list_permissions()
  except ECLMSError as exc:
    return err(exc.code, exc.message, get_trace_id(), exc.details)
  return ok({'role': role_name, 'permissions': sorted(permissions), 'all_permissions': all_permissions}, get_trace_id())


@router.put('/roles/{role_name}/permissions')
async def replace_role_permissions(role_name: str, payload: RolePermissionsRequest, request: Request):
  try:
    await require_permission(request, 'user.manage')
    if role_name == 'ADMIN':
      raise ECLMSError('ROLE_PROTECTED', 'The ADMIN role cannot be reduced through this screen')
    if not await _users(request).replace_role_permissions(role_name, set(payload.permissions)):
      return err('NOT_FOUND', f'Role not found: {role_name}', get_trace_id())
  except ECLMSError as exc:
    return err(exc.code, exc.message, get_trace_id(), exc.details)
  return ok({'role': role_name, 'permissions': sorted(set(payload.permissions))}, get_trace_id())
