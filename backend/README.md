# ECLMS Backend

Enterprise Contract Lifecycle Management System — Modular Monolith (Python + FastAPI + SQLAlchemy).

## Layout

    backend/
      core/           Shared kernel: base entities, events, exceptions, security, utils, logging
      config/         Runtime configuration (pydantic-settings, ECLMS_* env)
      api/            Gateway, middleware, versioning, response envelope
      bootstrap/      Module container + application factory (deterministic startup)
      modules/        Bounded contexts (identity, contracts, workflow, documents, audit, ...)
      main.py         uvicorn entrypoint

    shared/           Cross-cutting types, constants, contracts, utils
    infrastructure/   Database, storage, messaging, email provider contracts

## Module interface (EXEC-004)

Every module implements: `initialize`, `register_services`, `register_routes`,
`register_events`, `health_check`, `shutdown`.

## Running (development)

    python -m venv .venv
    .\.venv\Scripts\Activate.ps1
    pip install -e ".[dev]"
    uvicorn backend.main:app --reload

Health check: http://127.0.0.1:8000/health

## Authentication skeleton (Phase 0)

Seeded dev user: `admin` / `admin`.

    POST /api/v1/identity/auth/login   {"username": "admin", "password": "admin"}
    GET  /api/v1/identity/auth/me      Authorization: Bearer <token>

## Contract MVP (Phase 1)

    POST /api/v1/contracts
    GET  /api/v1/contracts/{id}
    POST /api/v1/contracts/{id}/transition   {"new_state": "SUBMITTED"}

## Response envelope (EXEC-006)

All endpoints return `{success, data, error, trace_id}`.  Trace id is echoed
back in the `X-Trace-Id` response header and propagated through logs.
