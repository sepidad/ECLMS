"""Application bootstrap (BACKEND_BOOTSTRAP_ARCHITECTURE.md).

Implements the deterministic startup sequence:

    1. Core initialization (logging, config, exceptions)
    2. Infrastructure layer (database)
    3. Domain module loading (in dependency order)
    4. API layer initialization (gateway, middleware, versioning)
    5. Event system activation
    6. System health validation

Module wiring happens at app-construction time so routes are available
before the event loop starts; the lifespan context owns only
infrastructure lifecycle (database connect/dispose).
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend.api.gateway import APIGateway
from backend.api.middleware.errors import register_exception_handlers
from backend.api.middleware.limits import BodySizeLimitMiddleware, RateLimitMiddleware
from backend.api.middleware.metrics import MetricsMiddleware, render_metrics
from backend.api.middleware.security import SecurityHeadersMiddleware
from backend.api.middleware.trace import TraceContextMiddleware
from backend.bootstrap.container import ModuleContainer
from backend.config import get_settings
from backend.core.events import DurableEventBus, EventBus
from backend.core.logging import configure_logging, get_logger
from backend.modules.registry import get_modules
from infrastructure.database import (
  check_database_health,
  create_schema,
  database_pool_stats,
  dispose_database,
  init_database,
)
from infrastructure.messaging import RedisBroker

logger = get_logger('eclms.bootstrap')


def _build_event_bus(settings) -> DurableEventBus | EventBus:
  """Select the event bus based on configured transport.

  ``memory`` (default) uses the in-process bus.  ``redis`` persists every
  event to a Redis stream for at-least-once delivery and crash recovery.
  """
  if settings.event_transport == 'redis':
    broker = RedisBroker(
      url=settings.redis_url,
      stream=settings.redis_event_stream,
      group=settings.redis_consumer_group,
    )
    logger.info('Event transport: durable (Redis)')
    return DurableEventBus(broker)
  logger.info('Event transport: memory')
  return EventBus()


def _start_scheduler(container: ModuleContainer, settings) -> Any:
  """Start the escalation sweep scheduler when enabled.

  Uses APScheduler's AsyncIOScheduler on the current (uvicorn) event
  loop.  Disabled by default so tests and simple deployments do not
  spawn background jobs.
  """
  if not settings.scheduler_enabled:
    return None
  try:
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    from apscheduler.triggers.interval import IntervalTrigger
  except ImportError:
    logger.warning('APScheduler not installed; escalation sweep scheduler disabled')
    return None

  service = container.get_service('workflow.service')
  scheduler = AsyncIOScheduler()

  async def run_sweep() -> None:
    try:
      await service.escalate_overdue()
    except Exception:
      logger.exception('Escalation sweep failed')

  scheduler.add_job(
    run_sweep,
    trigger=IntervalTrigger(minutes=settings.escalation_interval_minutes),
    id='workflow-escalation-sweep',
    replace_existing=True,
    max_instances=1,
    coalesce=True,
  )
  scheduler.start()
  logger.info('Started escalation sweep scheduler (every %s min)', settings.escalation_interval_minutes)
  return scheduler


async def _seed_dev_admin() -> None:
  """Create the development admin account if it does not exist.

  Also seeds the default roles/permissions (RBAC) and assigns the ADMIN
  role to the admin user.  Production deployments must replace this with
  real provisioning.
  """
  from backend.modules.identity.application.auth_service import hash_password
  from backend.modules.identity.domain.user import User
  from infrastructure.database.repositories import SqlUserRepository
  from infrastructure.database.seed import assign_role, seed_roles_permissions

  await seed_roles_permissions()

  repository = SqlUserRepository()
  if await repository.get_by_username('admin') is None:
    admin = User(
      username='admin',
      email='admin@eclms.local',
      full_name='System Administrator',
      password_hash=hash_password('admin'),
      organization_id='org-default',
    )
    await repository.save(admin)
    await assign_role(admin.id, 'ADMIN')
    logger.info('Seeded development admin user')


def create_app() -> FastAPI:
  """Build and wire the ECLMS application."""
  settings = get_settings()
  configure_logging(settings.log_level, json_output=settings.json_logs)

  # 1. Core initialization
  container = ModuleContainer()
  event_bus = _build_event_bus(settings)
  container.register_service('event_bus', event_bus)
  container.register_service('settings', settings)

  # 3. Domain module loading (in dependency order)
  for module in get_modules():
    container.register(module)
  container.initialize()
  container.register_all_services()

  # 2/6. Infrastructure lifecycle
  @asynccontextmanager
  async def lifespan(application: FastAPI):
    logger.info('Starting %s v%s (%s)', settings.app_name, settings.app_version, settings.environment)
    init_database()
    db_ok = await check_database_health()
    if db_ok:
      await create_schema()
      await _seed_dev_admin()
    logger.info('Database health: %s', 'ok' if db_ok else 'unavailable')
    if isinstance(event_bus, DurableEventBus):
      await event_bus.start()
    scheduler = _start_scheduler(container, settings)
    yield
    if scheduler is not None:
      scheduler.shutdown(wait=False)
    if isinstance(event_bus, DurableEventBus):
      await event_bus.stop()
    logger.info('Shutting down %s', settings.app_name)
    container.shutdown_all()
    await dispose_database()

  # 4. API layer initialization
  app = FastAPI(title=settings.app_name, version=settings.app_version, lifespan=lifespan)
  app.add_middleware(MetricsMiddleware)
  app.add_middleware(TraceContextMiddleware)
  app.add_middleware(SecurityHeadersMiddleware, trusted_proxy=settings.trusted_proxy)
  if settings.rate_limit_enabled:
    app.add_middleware(
      RateLimitMiddleware,
      limit=settings.rate_limit_requests,
      window_seconds=settings.rate_limit_window_seconds,
      trusted_proxy=settings.trusted_proxy,
    )
  if settings.max_request_bytes > 0:
    app.add_middleware(BodySizeLimitMiddleware, max_bytes=settings.max_request_bytes)
  app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
  )
  register_exception_handlers(app)

  gateway = APIGateway(app)
  for module in container.modules():
    gateway.register_module(module)
    gateway.add_health(module)
  gateway.activate()

  # 5. Event system activation
  container.register_all_events()

  app.state.container = container
  app.state.event_bus = event_bus

  @app.get('/health')
  async def health():
    return {
      'status': 'ok',
      'app': settings.app_name,
      'version': settings.app_version,
      'database': 'ok' if await check_database_health() else 'unavailable',
      'database_pool': database_pool_stats(),
      'modules': container.health_checks(),
    }

  @app.get('/metrics', response_class=Response)
  async def metrics():
    from fastapi.responses import PlainTextResponse
    return PlainTextResponse(render_metrics())

  class LLMSettingsUpdate(BaseModel):
    llm_api_url: str | None = None
    llm_api_key: str | None = None
    llm_model: str | None = None
    llm_timeout_seconds: int | None = None

  @app.get('/api/v1/config/llm-settings')
  async def get_llm_settings(request: Request):
    from backend.api.middleware.context import get_trace_id
    from backend.api.responses import ok
    return ok({
      'llm_api_url': settings.llm_api_url,
      'llm_api_key': settings.llm_api_key,
      'llm_model': settings.llm_model,
      'llm_timeout_seconds': settings.llm_timeout_seconds
    }, get_trace_id())

  @app.patch('/api/v1/config/llm-settings')
  async def update_llm_settings(request: Request, payload: LLMSettingsUpdate):
    from backend.api.middleware.context import get_trace_id
    from backend.api.responses import ok
    if payload.llm_api_url is not None:
      settings.llm_api_url = payload.llm_api_url
    if payload.llm_api_key is not None:
      settings.llm_api_key = payload.llm_api_key
    if payload.llm_model is not None:
      settings.llm_model = payload.llm_model
    if payload.llm_timeout_seconds is not None:
      settings.llm_timeout_seconds = payload.llm_timeout_seconds
    return ok({
      'llm_api_url': settings.llm_api_url,
      'llm_model': settings.llm_model,
      'llm_timeout_seconds': settings.llm_timeout_seconds
    }, get_trace_id())

  return app


app = create_app()
