"""Aggregate ORM model package.

Importing this package registers every model with the declarative Base
so that Alembic autogenerate and create_all see the full schema.
"""

from infrastructure.database.models.contracts import ContractModel, ContractVersionModel
from infrastructure.database.models.documents_audit import (
  AuditEventModel,
  DocumentModel,
  DocumentVersionModel,
)
from infrastructure.database.models.finances import FinanceCommitmentModel, FinancePaymentModel
from infrastructure.database.models.identity import (
  OrganizationModel,
  PermissionModel,
  RoleModel,
  RolePermissionModel,
  UserModel,
  UserRoleModel,
)
from infrastructure.database.models.integration import (
  ConnectorSyncModel,
  EmailDeliveryModel,
  SmsDeliveryModel,
  WebhookDeliveryModel,
)
from infrastructure.database.models.notifications import (
  NotificationModel,
  WebhookSubscriptionModel,
)
from infrastructure.database.models.obligations import ObligationModel
from infrastructure.database.models.workflow import (
  WorkflowHistoryModel,
  WorkflowInstanceModel,
  WorkflowStepModel,
)

__all__ = [
  'AuditEventModel',
  'ConnectorSyncModel',
  'ContractModel',
  'ContractVersionModel',
  'DocumentModel',
  'DocumentVersionModel',
  'EmailDeliveryModel',
  'FinanceCommitmentModel',
  'FinancePaymentModel',
  'NotificationModel',
  'ObligationModel',
  'OrganizationModel',
  'PermissionModel',
  'RoleModel',
  'RolePermissionModel',
  'SmsDeliveryModel',
  'UserModel',
  'UserRoleModel',
  'WebhookDeliveryModel',
  'WebhookSubscriptionModel',
  'WorkflowHistoryModel',
  'WorkflowInstanceModel',
  'WorkflowStepModel',
]
