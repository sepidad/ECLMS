"""Shared primitive types used across all ECLMS modules.

These types are framework-independent and intentionally minimal.
Cross-module communication must reference these types rather than
private implementations.
"""

from typing import NewType

UserId = NewType('UserId', str)
ContractId = NewType('ContractId', str)
WorkflowId = NewType('WorkflowId', str)
DocumentId = NewType('DocumentId', str)
AuditEventId = NewType('AuditEventId', str)
NotificationId = NewType('NotificationId', str)
OrganizationId = NewType('OrganizationId', str)
RoleId = NewType('RoleId', str)
PermissionId = NewType('PermissionId', str)
