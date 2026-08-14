"""SQLAlchemy ORM models for the identity module (ADR-001: PostgreSQL).

These models persist the identity bounded context: organizations,
users, roles, and permissions.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from infrastructure.database.session import Base


class OrganizationModel(Base):
  __tablename__ = 'organizations'

  id: Mapped[str] = mapped_column(String(32), primary_key=True)
  name: Mapped[str] = mapped_column(String(200), nullable=False)
  org_type: Mapped[str] = mapped_column(String(50), nullable=False, default='default')
  status: Mapped[str] = mapped_column(String(20), nullable=False, default='active')
  parent_organization_id: Mapped[str | None] = mapped_column(String(32), ForeignKey('organizations.id'), nullable=True)
  created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
  updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

  users: Mapped[list[UserModel]] = relationship(back_populates='organization')


class UserModel(Base):
  __tablename__ = 'users'

  id: Mapped[str] = mapped_column(String(32), primary_key=True)
  username: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
  email: Mapped[str] = mapped_column(String(200), unique=True, index=True, nullable=False)
  full_name: Mapped[str] = mapped_column(String(200), nullable=False)
  password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
  is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
  status: Mapped[str] = mapped_column(String(20), nullable=False, default='active')
  organization_id: Mapped[str] = mapped_column(String(32), ForeignKey('organizations.id'), index=True, nullable=False)
  created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
  updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

  organization: Mapped[OrganizationModel] = relationship(back_populates='users')
  roles: Mapped[list[RoleModel]] = relationship(
    secondary='user_roles', back_populates='users', lazy='selectin'
  )


class RoleModel(Base):
  __tablename__ = 'roles'

  id: Mapped[str] = mapped_column(String(32), primary_key=True)
  name: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
  description: Mapped[str | None] = mapped_column(Text, nullable=True)
  created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
  updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

  users: Mapped[list[UserModel]] = relationship(
    secondary='user_roles', back_populates='roles', lazy='selectin'
  )
  permissions: Mapped[list[PermissionModel]] = relationship(
    secondary='role_permissions', back_populates='roles', lazy='selectin'
  )


class PermissionModel(Base):
  __tablename__ = 'permissions'

  id: Mapped[str] = mapped_column(String(32), primary_key=True)
  code: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
  description: Mapped[str | None] = mapped_column(Text, nullable=True)

  roles: Mapped[list[RoleModel]] = relationship(
    secondary='role_permissions', back_populates='permissions', lazy='selectin'
  )


class UserRoleModel(Base):
  __tablename__ = 'user_roles'

  user_id: Mapped[str] = mapped_column(String(32), ForeignKey('users.id'), primary_key=True)
  role_id: Mapped[str] = mapped_column(String(32), ForeignKey('roles.id'), primary_key=True)


class RolePermissionModel(Base):
  __tablename__ = 'role_permissions'

  role_id: Mapped[str] = mapped_column(String(32), ForeignKey('roles.id'), primary_key=True)
  permission_id: Mapped[str] = mapped_column(String(32), ForeignKey('permissions.id'), primary_key=True)
