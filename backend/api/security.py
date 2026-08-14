"""Shared API authorization guards (RBAC + ABAC, ADR-002) + org scoping (ADR-003).

Reusable guards so every module enforces authentication, permission, and
organization-scope checks consistently.  Guards raise ECLMSError subclasses
which the central error handler maps to the response envelope:

    UnauthorizedError (401)  - missing/invalid bearer token
    ForbiddenError    (403)  - authenticated but missing permission

The tenant is always derived from the authenticated user, never from
request bodies (org scoping, ADR-003).  The JWT carries the org claim,
and every guard resolves the user once per request.

Usage:

    @router.post('/contracts')
    async def create_contract(payload: CreateContractRequest, request: Request):
      actor = await require_permission(request, 'contract.create')
      ...  # actor.id, actor.organization_id
"""

from __future__ import annotations

from fastapi import Request

from backend.api.abac import Actor, PolicyContext, PolicyEngine
from backend.core.exceptions import ForbiddenError, UnauthorizedError

__all__ = [
  'Actor',
  'current_actor',
  'current_organization_id',
  'current_user_id',
  'require_abac',
  'require_abac_only',
  'require_permission',
]


async def current_actor(request: Request) -> Actor:
  """Resolve and return the authenticated user (id + organization).

  Raises UnauthorizedError when no valid bearer token is present.
  """
  token = request.headers.get('Authorization', '')
  if not token.lower().startswith('bearer '):
    raise UnauthorizedError('Missing bearer token')
  auth = request.app.state.container.get_service('identity.auth')
  user = await auth.resolve_user(token[7:])
  return Actor(id=user.id, organization_id=user.organization_id)


async def current_user_id(request: Request) -> str:
  """Resolve and return the authenticated user id."""
  return (await current_actor(request)).id


async def current_organization_id(request: Request) -> str:
  """Resolve and return the authenticated user's organization id."""
  return (await current_actor(request)).organization_id


async def require_permission(request: Request, permission: str) -> Actor:
  """Return the actor, raising Unauthorized/Forbidden as appropriate."""
  actor = await current_actor(request)
  authz = request.app.state.container.get_service('identity.authz')
  await authz.require_permission(actor.id, permission)
  return actor


def _get_policy_engine(request: Request) -> PolicyEngine:
  return request.app.state.container.get_service('abac.engine')


async def require_abac(
  request: Request,
  permission: str | None = None,
  *,
  resource: object | None = None,
  action: str | None = None,
) -> Actor:
  """Authorize using RBAC permission and optional ABAC policies.

  - If ``permission`` is given, RBAC check is performed first.
  - ABAC policy engine is evaluated with context (actor, resource, action).
  - With no registered policies, ABAC is a no-op (RBAC-only).
  """
  actor = await current_actor(request)

  if permission:
    authz = request.app.state.container.get_service('identity.authz')
    await authz.require_permission(actor.id, permission)

  engine = _get_policy_engine(request)
  if engine._policies:
    ctx = PolicyContext(
      actor=actor,
      resource=resource,
      action=action,
      environment={
        'client_ip': request.client.host if request.client else None,
        'user_agent': request.headers.get('user-agent'),
      },
    )
    if not engine.evaluate(ctx):
      raise ForbiddenError('Access denied by ABAC policy')

  return actor


async def require_abac_only(
  request: Request,
  *,
  resource: object | None = None,
  action: str | None = None,
) -> Actor:
  """Authorize using ABAC policies only (no RBAC permission check)."""
  return await require_abac(request, permission=None, resource=resource, action=action)
