"""Module registry.

Returns module instances in the documented load order
(BACKEND_BOOTSTRAP_ARCHITECTURE.md section 3 step 3):

    identity -> contracts -> workflow -> documents -> audit
        -> notifications -> integration
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
  from backend.core.base.module import Module


def get_modules() -> list[Module]:
  """Instantiate and return all ECLMS modules in dependency order."""
  from backend.modules.audit import AuditModule
  from backend.modules.common import CommonModule
  from backend.modules.contracts import ContractsModule
  from backend.modules.data_import import ImportModule
  from backend.modules.documents import DocumentsModule
  from backend.modules.finances import FinancesModule
  from backend.modules.identity import IdentityModule
  from backend.modules.integration import IntegrationModule
  from backend.modules.intelligence import IntelligenceModule
  from backend.modules.notifications import NotificationsModule
  from backend.modules.obligations import ObligationsModule
  from backend.modules.reporting import ReportingModule
  from backend.modules.workflow import WorkflowModule

  return [
    CommonModule(),
    IdentityModule(),
    ContractsModule(),
    WorkflowModule(),
    DocumentsModule(),
    FinancesModule(),
    ObligationsModule(),
    ImportModule(),
    ReportingModule(),
    IntelligenceModule(),
    AuditModule(),
    NotificationsModule(),
    IntegrationModule(),
  ]
