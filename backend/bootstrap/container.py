"""Module container (BACKEND_BOOTSTRAP_ARCHITECTURE.md section 4).

Composes modules into a running application.  The container owns module
lifecycle: initialize, service registration, route registration, event
registration, health checks, and shutdown.
"""

from __future__ import annotations

import logging
from typing import Any

from backend.core.base.module import Module

logger = logging.getLogger('eclms.bootstrap')


class ModuleContainer:
  """Owns module instances and shared service bindings."""

  def __init__(self) -> None:
    self._modules: dict[str, Module] = {}
    self._services: dict[str, Any] = {}
    self._initialized: list[str] = []

  def register(self, module: Module) -> None:
    if module.name in self._modules:
      raise ValueError(f'Duplicate module: {module.name}')
    self._modules[module.name] = module

  def get_module(self, name: str) -> Module:
    return self._modules[name]

  def modules(self) -> list[Module]:
    return list(self._modules.values())

  def register_service(self, key: str, service: Any) -> None:
    self._services[key] = service

  def get_service(self, key: str) -> Any:
    return self._services[key]

  def initialize(self) -> None:
    """Initialize modules in registration order with dependency validation."""
    for module in self.modules():
      for dep in module.dependencies:
        if dep not in self._modules:
          raise RuntimeError(f'Module {module.name} requires missing dependency: {dep}')
      logger.info('Initializing module %s', module.name)
      module.initialize(self)
      self._initialized.append(module.name)

  def register_all_services(self) -> None:
    for name in self._initialized:
      self._modules[name].register_services(self)

  def register_all_events(self) -> None:
    for name in self._initialized:
      self._modules[name].register_events(self.get_service('event_bus'))

  def health_checks(self) -> dict[str, Any]:
    return {name: self._modules[name].health_check() for name in self._modules}

  def shutdown_all(self) -> None:
    for name in reversed(self._initialized):
      logger.info('Shutting down module %s', name)
      self._modules[name].shutdown()
