# ECLMS — Enterprise Contract Lifecycle Management System

> **Proprietary and confidential.** This repository and its contents are for
> internal use only. All rights reserved.

A modular-monolith platform for the full contract lifecycle: drafting from
templates, structured review and approval workflows, obligations and financial
commitments, AI-assisted risk review, and complete audit trails — built for
on-premises deployment with cloud-compatible storage.

## Highlights

- **Contract lifecycle** — contracts with versioning, templates (including
  organization Word templates), guarantees, review feedback, and document
  export to DOCX/PDF.
- **Workflow engine** — serial and parallel approval steps, conditional steps,
  pause/resume, delegation, escalation with SLA sweeps, executive sign-off.
- **Access control** — RBAC (admin / contract manager / viewer roles),
  ABAC policies, organization scoping (multi-tenancy), and optional OIDC
  single sign-on (Keycloak, Auth0, Dex, Okta).
- **Obligations & finances** — obligation tracking, financial commitments,
  payments, and guarantee monitoring.
- **Intelligence** — clause analysis, risk scoring, semantic search, and
  AI-assisted contract review (rule engine plus configurable LLM providers).
- **Notifications** — in-app notifications, webhooks (HMAC-signed with retry
  and backoff), SMTP email, and SMS delivery.
- **Audit & reporting** — append-only audit events with CSV export,
  dashboards and report endpoints, Prometheus metrics.
- **Data import** — CSV import for contracts, obligations, and commitments;
  audit CSV export.

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.11, FastAPI, Pydantic v2, SQLAlchemy 2 (async), Alembic |
| Database | PostgreSQL 16 (asyncpg), Redis 7 (durable event bus) |
| Frontend | React 19, TypeScript, Vite |
| Auth | JWT + bcrypt, RBAC/ABAC, OIDC (Keycloak) |
| Storage | Local filesystem or S3-compatible object storage |
| Runtime | Docker Compose (dev + prod), Caddy TLS reverse proxy, GitHub Actions CI |

## Quick Start (Docker Compose)

```bash
docker compose up --build
```

This starts five services:

| Service | URL / Port | Notes |
|---|---|---|
| API | http://localhost:8000 (`/health`, `/api/v1/...`) | Seeded dev user `admin` / `admin` |
| PostgreSQL | localhost:5433 | Volume `eclms-compose-pgdata` |
| Redis | localhost:6379 | Volume `eclms-compose-redisdata` |
| Keycloak | http://localhost:8080 | Demo realm `eclms` (`admin` / `admin`) |
| Proxy (frontend) | http://localhost | Serves the built SPA, proxies `/api` |

Production-style stack: `docker compose -f docker-compose.prod.yml up --build`
(see `DEPLOYMENT.md`).

## Quick Start (Development)

Backend:

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -e ".[dev]"
uvicorn backend.main:app --reload
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

Configuration is environment-driven (`ECLMS_*` variables, Pydantic settings).
See `.env.example` for every key and `DEPLOYMENT.md` for the full reference.

## Tests & Lint

```bash
pytest              # 200+ tests (backend modules + integration suite)
ruff check .        # Python lint
cd frontend && npm run lint && npm run build   # frontend lint + build
```

CI runs both backend and frontend jobs on every push (`.github/workflows/ci.yml`).

## Project Layout

```
backend/
  core/           Shared kernel: entities, events, exceptions, security, logging
  config/         Runtime configuration (pydantic-settings)
  api/            Gateway, middleware, security, ABAC, versioning
  bootstrap/      Application factory + module container
  modules/        Bounded contexts: identity, contracts, workflow, documents,
                  finances, obligations, import, reporting, intelligence,
                  audit, notifications, integration
frontend/         React 19 + Vite SPA
infrastructure/   Database, storage, messaging provider contracts
shared/           Cross-cutting types and utilities
deploy/           Keycloak realm, proxy config
docs/             Specifications and design documents
architecture/     ADRs, C4 model, sequence diagrams
```

## Documentation

- `DEPLOYMENT.md` — runtime topology, environment reference, operations
- `PROJECT_STATE.md` — phase-by-phase implementation status
- `SESSION_LOG.md` — detailed development history
- `docs/` — module specifications and the product roadmap
- `quality/Release_Readiness.md` — release gate checklist
