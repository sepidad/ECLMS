"""Aggregate ORM model package.

Importing this package registers every model with the declarative Base
so that Alembic autogenerate and create_all see the full schema.
"""

from infrastructure.database.models.contract_reviews import ContractReviewFeedbackModel
from infrastructure.database.models.contracts import ContractModel, ContractTemplateModel, ContractVersionModel
from infrastructure.database.models.documents_audit import (
  AuditEventModel,
  DocumentModel,
  DocumentVersionModel,
)
from infrastructure.database.models.finances import FinanceCommitmentModel, FinancePaymentModel
from infrastructure.database.models.guarantees import GuaranteeModel
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
from infrastructure.database.models.user_permission_overrides import UserPermissionOverrideModel
from infrastructure.database.models.workflow import (
  WorkflowHistoryModel,
  WorkflowInstanceModel,
  WorkflowStepModel,
)

__all__ = [
  'AuditEventModel',
  'ConnectorSyncModel',
  'ContractModel',
  'ContractReviewFeedbackModel',
  'ContractVersionModel',
  'ContractTemplateModel',
  'DocumentModel',
  'DocumentVersionModel',
  'EmailDeliveryModel',
  'FinanceCommitmentModel',
  'FinancePaymentModel',
  'GuaranteeModel',
  'NotificationModel',
  'ObligationModel',
  'OrganizationModel',
  'PermissionModel',
  'RoleModel',
  'RolePermissionModel',
  'SmsDeliveryModel',
  'UserModel',
  'UserPermissionOverrideModel',
  'UserRoleModel',
  'WebhookDeliveryModel',
  'WebhookSubscriptionModel',
  'WorkflowHistoryModel',
  'WorkflowInstanceModel',
  'WorkflowStepModel',
]
