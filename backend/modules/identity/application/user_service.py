"""User management application service (Phase 1 RBAC).

Provides user administration use cases (create, list, role assignment).
Authorization checks are performed by the RBAC middleware against the
permission codes held by the caller's roles.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from backend.core.exceptions import ConflictError, NotFoundError
from backend.modules.identity.application.auth_service import hash_password
from backend.modules.identity.domain.user import User

if TYPE_CHECKING:
  from infrastructure.database.repositories.user_repository import SqlUserRepository


class UserService:
  def __init__(self, repository: SqlUserRepository) -> None:
    self._repository = repository

  async def create_user(
    self,
    *,
    username: str,
    email: str,
    full_name: str,
    password: str,
    organization_id: str = 'org-default',
    role: str | None = None,
  ) -> User:
    existing = await self._repository.get_by_username(username)
    if existing is not None:
      raise ConflictError(f'Username already exists: {username}')
    if await self._repository.get_by_email(email) is not None:
      raise ConflictError(f'Email already exists: {email}')

    user = User(
      username=username,
      email=email,
      full_name=full_name,
      password_hash=hash_password(password),
      organization_id=organization_id,
    )
    await self._repository.save(user)

    if role is not None:
      role_row = await self._repository.get_role_by_name(role)
      if role_row is None:
        raise NotFoundError(f'Role not found: {role}')
      await self._repository.assign_role(user.id, role_row['id'])
    return user

  async def list_users(self, *, organization_id: str, limit: int = 100, offset: int = 0) -> list[User]:
    return await self._repository.list_all(organization_id=organization_id, limit=limit, offset=offset)

  async def list_roles(self) -> list[dict]:
    return await self._repository.list_roles()

  async def list_permissions(self) -> list[dict]:
    return await self._repository.list_permissions()
