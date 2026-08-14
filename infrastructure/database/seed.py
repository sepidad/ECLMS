"""Development seed data (roles, permissions, default organization).

Production deployments must replace this with real provisioning.  The
admin account is assigned the ADMIN role which carries every permission.
"""

from __future__ import annotations

from backend.core.utils import utc_now
from infrastructure.database.models.identity import (
  OrganizationModel,
  PermissionModel,
  RoleModel,
  RolePermissionModel,
  UserRoleModel,
)
from infrastructure.database.session import get_session_factory

#: Static permission codes used by the application and RBAC middleware.
PERMISSIONS = {
  'contract.create': 'Create contracts',
  'contract.read': 'Read contracts',
  'contract.update': 'Update contracts',
  'contract.transition': 'Change contract lifecycle state',
  'document.upload': 'Upload contract documents',
  'document.read': 'Read contract documents',
  'obligation.create': 'Create contractual obligations',
  'obligation.read': 'Read contractual obligations',
  'obligation.update': 'Complete or cancel obligations',
  'finance.create': 'Create financial commitments and payments',
  'finance.read': 'Read financial commitments and payments',
  'finance.update': 'Mark payments paid or cancel them',
  'reporting.read': 'Read analytics and reporting overviews',
  'intelligence.read': 'Run risk, clause, search, and alert analysis',
  'user.manage': 'Manage users and roles',
  'data.import': 'Import contracts, obligations and finances from CSV',
}

ROLES = {
  'ADMIN': ('Full system access', set(PERMISSIONS)),
  'CONTRACT_MANAGER': (
    'Manage contracts',
    {
      'contract.create',
      'contract.read',
      'contract.update',
      'contract.transition',
      'document.upload',
      'document.read',
      'obligation.create',
      'obligation.read',
      'obligation.update',
      'finance.create',
      'finance.read',
      'finance.update',
      'reporting.read',
      'intelligence.read',
      'data.import',
    },
  ),
  'VIEWER': ('Read-only access', {'contract.read', 'document.read', 'obligation.read', 'finance.read', 'reporting.read', 'intelligence.read'}),
}


async def seed_roles_permissions() -> None:
  """Create/refresh default roles, permissions, and the default organization.

  Idempotent: existing roles are converged to the current permission
  definitions so newly added permission codes attach to existing roles.
  """
  async with get_session_factory()() as session:
    org = await session.get(OrganizationModel, 'org-default')
    if org is None:
      session.add(
        OrganizationModel(
          id='org-default',
          name='Default Organization',
          org_type='default',
          status='active',
          created_at=utc_now(),
          updated_at=utc_now(),
        )
      )

    for code, description in PERMISSIONS.items():
      perm = await session.get(PermissionModel, code)
      if perm is None:
        session.add(PermissionModel(id=code, code=code, description=description))

    for name, (description, perms) in ROLES.items():
      role = await session.get(RoleModel, name)
      if role is None:
        role = RoleModel(
          id=name,
          name=name,
          description=description,
          created_at=utc_now(),
          updated_at=utc_now(),
        )
        session.add(role)
        await session.flush()
      for code in perms:
        link = await session.get(RolePermissionModel, (role.id, code))
        if link is None:
          session.add(RolePermissionModel(role_id=role.id, permission_id=code))

    await session.commit()


async def assign_role(user_id: str, role_name: str) -> None:
  """Assign a role to a user (idempotent)."""
  async with get_session_factory()() as session:
    role = await session.get(RoleModel, role_name)
    if role is None:
      return
    link = UserRoleModel(user_id=user_id, role_id=role.id)
    session.add(link)
    await session.commit()
