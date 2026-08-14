"""Authorization service (Phase 1 RBAC).

Checks whether an authenticated user holds the required permission code
through one of their roles.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from backend.core.exceptions import ForbiddenError

if TYPE_CHECKING:
  from infrastructure.database.repositories.user_repository import SqlUserRepository


class AuthorizationService:
  def __init__(self, user_repository: SqlUserRepository) -> None:
    self._users = user_repository

  async def require_permission(self, user_id: str, permission: str) -> None:
    """Raise ForbiddenError unless the user holds the permission."""
    permissions = await self._users.permissions_for_user(user_id)
    if permission not in permissions:
      raise ForbiddenError(f'Missing permission: {permission}')

  async def permissions_for(self, user_id: str) -> set[str]:
    return await self._users.permissions_for_user(user_id)
