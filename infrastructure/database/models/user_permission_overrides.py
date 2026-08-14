from __future__ import annotations

from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from infrastructure.database.session import Base


class UserPermissionOverrideModel(Base):
  __tablename__ = 'user_permission_overrides'
  user_id: Mapped[str] = mapped_column(String(32), ForeignKey('users.id'), primary_key=True)
  permission_id: Mapped[str] = mapped_column(String(100), ForeignKey('permissions.id'), primary_key=True)
  enabled: Mapped[bool] = mapped_column(Boolean, nullable=False)
