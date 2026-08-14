"""Standard module interface (EXEC-004).

Every ECLMS module MUST implement this interface so the bootstrap
container can initialise, wire, health-check, and shut down modules in a
deterministic and framework-independent manner.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
  from backend.api.gateway import APIGateway
  from backend.bootstrap.container import ModuleContainer
  from backend.core.events.bus import EventBus


class Module(ABC):
  """Contract every module must honour.

  Lifecycle (EXEC-004 section 6):

      INIT
        -> DEPENDENCY VALIDATION
        -> SERVICE REGISTRATION
        -> ROUTE REGISTRATION
        -> EVENT REGISTRATION
        -> READY
  """

  name: str = ''
  version: str = '0.1.0'
  dependencies: tuple[str, ...] = ()

  @abstractmethod
  def initialize(self, container: ModuleContainer) -> None:
    """Load configuration, prepare internal state, validate dependencies.

    MUST NOT register routes or start background workers.
    """

  @abstractmethod
  def register_services(self, container: ModuleContainer) -> None:
    """Expose domain and application services to the container."""

  @abstractmethod
  def register_routes(self, gateway: APIGateway) -> None:
    """Register API routes through the gateway.

    No business logic is allowed in this step; it only wires routes.
    """

  @abstractmethod
  def register_events(self, bus: EventBus) -> None:
    """Subscribe to and publish module events."""

  def health_check(self) -> dict[str, Any]:
    """Return module status, dependency readiness, and subsystem health."""
    return {'name': self.name, 'version': self.version, 'status': 'ok'}

  def shutdown(self) -> None:
    """Release module resources gracefully.

    Override only when the module holds resources that must be closed.
    """
