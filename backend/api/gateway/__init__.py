"""API Gateway (integration/03_API_Gateway_Architecture.md).

The gateway is the single entry point for client access.  It mounts
versioned module routers directly onto the application so every public
endpoint lives under /api/v1/{module}.  Direct module access from
outside is forbidden.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import APIRouter, FastAPI

from backend.api.versioning import api_prefix

if TYPE_CHECKING:
  from backend.core.base.module import Module


class APIGateway:
  """Owns the versioned route tree and mounts module routers."""

  def __init__(self, app: FastAPI) -> None:
    self._app = app
    self._modules: dict[str, Module] = {}

  def register_module(self, module: Module) -> None:
    """Register a module and let it mount its routes under its prefix."""
    self._modules[module.name] = module
    module.register_routes(self)

  def mount(self, prefix: str, router: APIRouter) -> None:
    """Mount a module router under /api/v1/{prefix}."""
    self._app.include_router(router, prefix=f'{api_prefix()}/{prefix}')

  def add_health(self, module: Module) -> None:
    """Expose each module's health check under /api/v1/{module}/health."""
    router = APIRouter(tags=[module.name])

    @router.get('/health')
    async def health():
      return module.health_check()

    self.mount(module.name, router)

  def activate(self) -> None:
    """Finalize the gateway.  Mounting is eager, so this is a no-op."""
    return
