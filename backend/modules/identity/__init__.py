"""Identity & Access module (execution priority #1).

Phase 0 scope: basic authentication skeleton (login + current user).
Phase 1 scope: full user management and RBAC/ABAC authorization.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from backend.core.base.module import Module
from backend.modules.identity.application.auth_service import AuthService
from backend.modules.identity.application.authorization_service import AuthorizationService
from backend.modules.identity.application.user_service import UserService
from backend.modules.identity.interfaces import router

if TYPE_CHECKING:
  from backend.api.gateway import APIGateway
  from backend.bootstrap.container import ModuleContainer
  from backend.core.events import EventBus


class IdentityModule(Module):
  name = 'identity'
  version = '0.1.0'

  def initialize(self, container: ModuleContainer) -> None:
    from infrastructure.database.repositories import SqlUserRepository

    self._repositories = {'users': SqlUserRepository()}

  def register_services(self, container: ModuleContainer) -> None:
    repository = self._repositories['users']
    auth_service = AuthService(repository)
    container.register_service('identity.auth', auth_service)
    container.register_service('identity.users', repository)
    container.register_service('identity.users.service', UserService(repository))
    container.register_service('identity.authz', AuthorizationService(repository))

  def register_routes(self, gateway: APIGateway) -> None:
    gateway.mount('identity', router)

  def register_events(self, bus: EventBus) -> None:
    return None

  def health_check(self) -> dict:
    return {'name': self.name, 'version': self.version, 'status': 'ok'}
