"""SQLAlchemy-backed user repository (replaces the in-memory store).

Each operation opens its own session from the shared async session
factory, so repositories are safe to construct at bootstrap time (before
the database engine exists) and safe to use from concurrent requests.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from backend.modules.identity.domain.user import User
from infrastructure.database.models.identity import (
  PermissionModel,
  RoleModel,
  RolePermissionModel,
  UserModel,
  UserRoleModel,
)
from infrastructure.database.session import get_session_factory


def _to_domain(model: UserModel) -> User:
  user = User(
    username=model.username,
    email=model.email,
    full_name=model.full_name,
    password_hash=model.password_hash,
    organization_id=model.organization_id,
    is_active=model.is_active,
    user_id=model.id,
  )
  user.created_at = model.created_at
  user.updated_at = model.updated_at
  user.roles = [role.name for role in model.roles]
  return user


class SqlUserRepository:
  async def get_by_username(self, username: str) -> User | None:
    async with get_session_factory()() as session:
      stmt = select(UserModel).where(UserModel.username == username).options(selectinload(UserModel.roles))
      model = (await session.execute(stmt)).scalar_one_or_none()
      return _to_domain(model) if model else None

  async def get_by_id(self, user_id: str) -> User | None:
    async with get_session_factory()() as session:
      stmt = select(UserModel).where(UserModel.id == user_id).options(selectinload(UserModel.roles))
      model = (await session.execute(stmt)).scalar_one_or_none()
      return _to_domain(model) if model else None

  async def get_by_email(self, email: str) -> User | None:
    async with get_session_factory()() as session:
      stmt = select(UserModel).where(UserModel.email == email).options(selectinload(UserModel.roles))
      model = (await session.execute(stmt)).scalar_one_or_none()
      return _to_domain(model) if model else None

  async def save(self, user: User) -> User:
    async with get_session_factory()() as session:
      existing = await session.get(UserModel, user.id)
      if existing is None:
        session.add(
          UserModel(
            id=user.id,
            username=user.username,
            email=user.email,
            full_name=user.full_name,
            password_hash=user.password_hash,
            is_active=user.is_active,
            status='active',
            organization_id=user.organization_id,
            created_at=user.created_at,
            updated_at=user.updated_at,
          )
        )
      else:
        existing.username = user.username
        existing.email = user.email
        existing.full_name = user.full_name
        existing.password_hash = user.password_hash
        existing.is_active = user.is_active
        existing.updated_at = user.updated_at
      await session.commit()
    return user

  async def list_all(self, *, organization_id: str, limit: int = 100, offset: int = 0) -> list[User]:
    async with get_session_factory()() as session:
      stmt = (
        select(UserModel)
        .where(UserModel.organization_id == organization_id)
        .order_by(UserModel.created_at)
        .limit(limit)
        .offset(offset)
      )
      models = (await session.execute(stmt)).scalars().all()
      return [_to_domain(m) for m in models]

  async def list_by_role_in_org(self, organization_id: str, role: str) -> list[User]:
    """Return active users in an organization that hold the given role."""
    async with get_session_factory()() as session:
      stmt = (
        select(UserModel)
        .join(UserRoleModel, UserRoleModel.user_id == UserModel.id)
        .join(RoleModel, RoleModel.id == UserRoleModel.role_id)
        .where(
          UserModel.organization_id == organization_id,
          RoleModel.name == role,
          UserModel.is_active.is_(True),
        )
        .options(selectinload(UserModel.roles))
      )
      models = (await session.execute(stmt)).scalars().all()
      return [_to_domain(m) for m in models]

  async def assign_role(self, user_id: str, role_id: str) -> None:
    async with get_session_factory()() as session:
      link = UserRoleModel(user_id=user_id, role_id=role_id)
      session.add(link)
      await session.commit()

  async def list_roles(self) -> list[dict]:
    async with get_session_factory()() as session:
      stmt = select(RoleModel).order_by(RoleModel.name)
      models = (await session.execute(stmt)).scalars().all()
      return [{'id': r.id, 'name': r.name, 'description': r.description} for r in models]

  async def list_permissions(self) -> list[dict]:
    async with get_session_factory()() as session:
      stmt = select(PermissionModel).order_by(PermissionModel.code)
      models = (await session.execute(stmt)).scalars().all()
      return [{'id': p.id, 'code': p.code, 'description': p.description} for p in models]

  async def role_permissions(self, role_name: str) -> set[str]:
    async with get_session_factory()() as session:
      stmt = select(RoleModel).where(RoleModel.name == role_name).options(selectinload(RoleModel.permissions))
      role = (await session.execute(stmt)).scalar_one_or_none()
      return {permission.code for permission in role.permissions} if role else set()

  async def replace_role_permissions(self, role_name: str, permissions: set[str]) -> bool:
    async with get_session_factory()() as session:
      role = (await session.execute(select(RoleModel).where(RoleModel.name == role_name))).scalar_one_or_none()
      if role is None:
        return False
      await session.execute(RolePermissionModel.__table__.delete().where(RolePermissionModel.role_id == role.id))
      valid = (await session.execute(select(PermissionModel).where(PermissionModel.code.in_(permissions)))).scalars().all()
      for permission in valid:
        session.add(RolePermissionModel(role_id=role.id, permission_id=permission.id))
      await session.commit()
      return True

  async def get_role_by_name(self, name: str) -> dict | None:
    async with get_session_factory()() as session:
      stmt = select(RoleModel).where(RoleModel.name == name)
      model = (await session.execute(stmt)).scalar_one_or_none()
      if model is None:
        return None
      return {'id': model.id, 'name': model.name, 'description': model.description}

  async def permissions_for_user(self, user_id: str) -> set[str]:
    """Return the set of permission codes granted to a user via their roles."""
    async with get_session_factory()() as session:
      stmt = (
        select(UserModel)
        .where(UserModel.id == user_id)
        .options(selectinload(UserModel.roles).selectinload(RoleModel.permissions))
      )
      model = (await session.execute(stmt)).scalar_one_or_none()
      if model is None:
        return set()
      return {permission.code for role in model.roles for permission in role.permissions}
