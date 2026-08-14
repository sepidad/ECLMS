"""Common module: cross-cutting helpers shared by modules.

Holds shared domain primitives and utilities.  It is the first module to
load and has no business responsibilities of its own.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from backend.api.abac import Policy, PolicyEngine, action_is, all_of, is_resource_owner
from backend.core.base.module import Module

if TYPE_CHECKING:
  from backend.api.gateway import APIGateway
  from backend.bootstrap.container import ModuleContainer
  from backend.core.events import EventBus


def register_demo_contract_read_policy(policy_engine: PolicyEngine) -> None:
  """Demo ABAC policy: a user may read a contract only if they own it.

  This only affects routes that opt in via ``require_abac`` with the matching
  action string ('contract:read'), so all existing RBAC-guarded routes are
  unaffected.
  """
  policy_engine.add_policy(
    Policy(
      name='contract-read-owner',
      predicate=all_of(action_is('contract:read'), is_resource_owner),
      description='Users may read a contract only if they own it.',
      effect='allow',
    )
  )


class CommonModule(Module):
  name = 'common'
  version = '0.1.0'

  def initialize(self, container: ModuleContainer) -> None:
    return None

  def register_services(self, container: ModuleContainer) -> None:
    engine = PolicyEngine()
    register_demo_contract_read_policy(engine)
    container.register_service('abac.engine', engine)

  def register_routes(self, gateway: APIGateway) -> None:
    return None

  def register_events(self, bus: EventBus) -> None:
    return None
