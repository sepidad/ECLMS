# ECLMS Deployment Architecture (Implementation)

**Document ID:** DEP-001
**Status:** Implemented (matching the current codebase)
**Related:** `architecture/deployment/` (conceptual package), ADR-001 (PostgreSQL), ADR-004 (Modular Monolith), ADR-005 (On-premises first, cloud-compatible)

---

## 1. Purpose

This document describes how the **implemented** ECLMS system is deployed and
operated.  The `architecture/deployment/` package defines the conceptual,
technology-independent deployment architecture; this document records the
concrete, verified implementation and the operational procedures that
accompany it.

The system is a **modular monolith** (ADR-004): a single FastAPI application
process hosts all modules (identity, contracts, documents, workflow, audit,
notifications, integration), backed by PostgreSQL (ADR-001) and a pluggable
file storage provider.

---

## 2. Runtime Topology

```
Clients (browser / API consumers)
        │  HTTPS
        ▼
Reverse Proxy / Load Balancer (optional in dev)
        │
        ▼
┌──────────────────────────────┐
│  Application Server           │
│  uvicorn  backend.main:app    │
│  (Modular Monolith)           │
│   - REST API  /api/v1         │
│   - Business logic / workflow │
│   - RBAC authorization        │
│   - Event bus (in-process)    │
└──────────────┬───────────────┘
               │
       ┌───────┴───────┐
       ▼               ▼
 PostgreSQL         File Storage
 (transactions,      (documents,
  workflow state,     contract files)
  audit, history)
```

Deployment responsibilities:

| Component | Role |
|---|---|
| Application server | One deployable process; hosts all modules, the workflow engine, RBAC, validation, audit. Stateless except for in-process event bus (no sticky sessions required). |
| PostgreSQL | System of record: contracts, versions, users, roles/permissions, workflows, history, audit events, documents metadata. |
| File storage | Immutable document blobs behind the `StorageProvider` contract (`LocalStorageProvider` today). |

There is no separate background-worker process yet; the workflow SLA-escalation
sweep (`POST /api/v1/workflows/escalate-overdue`) is a scheduler entry point
intended to run on a timer.

---

## 3. Environment Configuration

All configuration is environment-driven via the `ECLMS_` prefix (Pydantic
`BaseSettings`, `backend/config/settings.py`).  A `.env` file may supply
values; the committed `.env.example` documents the keys.

| Variable | Default | Purpose |
|---|---|---|
| `ECLMS_ENVIRONMENT` | `development` | Runtime environment label |
| `ECLMS_LOG_LEVEL` | `INFO` | Log verbosity |
| `ECLMS_JSON_LOGS` | `true` | Structured JSON log output |
| `ECLMS_JWT_SECRET` | dev-only value (must rotate) | Token signing secret |
| `ECLMS_JWT_EXPIRE_MINUTES` | `60` | Token lifetime |
| `ECLMS_DATABASE_URL` | `postgresql+asyncpg://eclms:eclms@localhost:5432/eclms` | Async SQLAlchemy DSN |
| `ECLMS_DATABASE_ECHO` | `false` | SQL echo |
| `ECLMS_DATABASE_POOL_SIZE` | `10` | Asyncpg pool size |
| `ECLMS_DATABASE_MAX_OVERFLOW` | `20` | Pool overflow |
| `ECLMS_STORAGE_ROOT` | `./var/storage` | Document blob root |
| `ECLMS_STORAGE_BACKEND` | `local` | Storage provider: `local` filesystem or `s3` object storage |
| `ECLMS_S3_BUCKET` / `ECLMS_S3_REGION` / `ECLMS_S3_ENDPOINT_URL` / `ECLMS_S3_ACCESS_KEY_ID` / `ECLMS_S3_SECRET_ACCESS_KEY` | — | S3 bucket, region, optional endpoint URL, and credentials (MinIO/LocalStack/AWS) |
| `ECLMS_EMAIL_ENABLED` | `false` | Enable outbound SMTP email |
| `ECLMS_SMTP_HOST` / `ECLMS_SMTP_PORT` / `ECLMS_SMTP_USER` / `ECLMS_SMTP_PASSWORD` / `ECLMS_SMTP_FROM` | `localhost` / `587` / empty / empty / `eclms@eclms.local` | SMTP server and sender config |
| `ECLMS_OIDC_ENABLED` | `false` | Enable OIDC external IdP login |
| `ECLMS_OIDC_ISSUER` / `ECLMS_OIDC_CLIENT_ID` / `ECLMS_OIDC_CLIENT_SECRET` | empty | OIDC provider issuer URL, client id, and secret |
| `ECLMS_OIDC_SCOPES` | `openid,email,profile` | Comma-separated OIDC scopes string |
| `ECLMS_OIDC_REDIRECT_URI` | empty | OIDC callback redirect URI |
| `ECLMS_OIDC_DEFAULT_ORG` | `org-default` | Organization assigned to new OIDC users |
| `ECLMS_CORS_ORIGINS` | `*` | CORS allow-list |
| `ECLMS_TRUSTED_PROXY` | `false` | Honor `X-Forwarded-*` + emit HSTS (true only behind TLS reverse proxy) |

**Security:** secrets must never be committed.  In development the JWT secret
is an explicit insecure default; production must supply a strong secret
(secret store or environment injection).

---

## 4. Database Provisioning

PostgreSQL runs in Docker for development:

```
docker run -d --name eclms-postgres \
  -e POSTGRES_USER=eclms -e POSTGRES_PASSWORD=eclms -e POSTGRES_DB=eclms \
  -p 5432:5432 -v eclms-pgdata:/var/lib/postgresql/data \
  --restart unless-stopped postgres:16
```

Start/stop:

```
docker start eclms-postgres
docker stop eclms-postgres
```

The named volume `eclms-pgdata` preserves data across container restarts.

---

## 5. Schema Management (Alembic)

Schema changes use **one reversible Alembic migration per logical change**.
Apply migrations against the live database:

```
& .venv/Scripts/python.exe -m alembic upgrade head
```

Rollback a single migration:

```
& .venv/Scripts/python.exe -m alembic downgrade -1
```

Current chain (head): `b789652b8c89` (initial schema) →
`53c331530e3d` (workflow tables) → `a1b2c3d4e5f6` (Phase 2 workflow fields) →
`ebe4b66ae720` (notifications/webhooks) → `6dcb594622ee` (webhook deliveries).

`infrastructure/database/session.create_schema()` is **dev/test only**
(`Base.metadata.create_all`); it does not migrate existing tables and must
never replace Alembic in production.

---

## 6. Running the Application

Start the API server (development):

```
& .venv/Scripts/python.exe -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

Bootstrap sequence (see `backend/bootstrap/application.py`):

1. Configure logging from settings.
2. Build the module container and register services/events.
3. On startup: connect to the database, run `create_schema()` (dev),
   seed default roles/permissions, the default organization, and the
   development admin account (`admin` / `admin`) if absent.
4. Mount module routers under `/api/v1` and activate health endpoints.

**Seeding is development-only.**  Production replaces it with real user and
organization provisioning.

### 6a. Docker Compose Stack

A `docker-compose.yml` runs the full stack: API (built from the `Dockerfile`),
PostgreSQL 16, and Redis 7 (for the durable event transport):

```
docker compose up -d --build
```

| Service | Container | Host port | Role |
|---|---|---|---|
| `api` | `eclms-compose-api` | `8000` | ECLMS modular monolith (uvicorn), runs `alembic upgrade head` on start |
| `db` | `eclms-compose-postgres` | `5433` | PostgreSQL 16 (named volume `eclms-compose-pgdata`); host `5432` is kept free for the standalone dev container |
| `redis` | `eclms-compose-redis` | `6379` | Redis 7 (named volume `eclms-compose-redisdata`) for `ECLMS_EVENT_TRANSPORT=redis` |
| `proxy` | `eclms-compose-proxy` | `443`/`80` | Caddy reverse proxy terminating TLS (internal CA locally; Let's Encrypt in production) |

Health: `docker compose ps` shows all three `healthy`; `GET http://localhost:8000/health`
returns `database: ok`.

The API defaults to the in-process transport (`ECLMS_EVENT_TRANSPORT=memory`).
The escalation scheduler is enabled in `docker-compose.yml` (`ECLMS_SCHEDULER_ENABLED: 'true'`,
`ECLMS_ESCALATION_INTERVAL_MINUTES: '1'`).
To enable the durable Redis transport, override in `docker-compose.yml`:

```
ECLMS_EVENT_TRANSPORT: redis
```

Stop/teardown:

```
docker compose down        # stop and remove containers
docker compose down -v     # also remove volumes
```

The standalone development database (`eclms-postgres` on host port `5432`,
section 4) and the compose database (`eclms-compose-postgres` on `5433`) are
independent; use whichever matches your workflow.

---

## 7. Health Checks and Observability

| Endpoint | Purpose |
|---|---|
| `GET /health` | Global health: app name/version, database reachability (`ok`/`unavailable`), per-module health checks. |
| `GET /api/v1/{module}/health` | Per-module health check. |
| `GET /api/v1/identity/roles` | Auth + role/permission listing. |

Logging is structured JSON with a `trace_id` correlated per request
(`X-Trace-Id` propagation).  Every domain event is persisted to the append-only
`audit_events` table, giving an auditable event stream independent of
application logs.

---

## 8. API Surface

All business APIs live under `/api/v1` and use the EXEC-006 response envelope:
HTTP 200 with `success: true|false`, `data`, `error` (with `code`), `trace_id`.
Errors are **not** returned as HTTP 4xx/5xx statuses from business endpoints.

| Module | Routes | Guard |
|---|---|---|
| identity | `POST /auth/login`, `GET /auth/me`, `POST|GET /users`, `GET /roles` | `user.manage` on user mgmt |
| contracts | `POST /contracts`, `GET /contracts`, `GET/PATCH /contracts/{id}`, `POST /contracts/{id}/transition`, `GET /contracts/{id}/versions` | `contract.create/read/update/transition` |
| documents | `POST /documents/upload`, `GET /documents/contract/{contract_id}` | `document.upload/read` |
| workflow | `POST /workflows/start`, `POST /workflows/{id}/transition`, `pause`, `resume`, `delegate`, `escalate`, `POST /workflows/escalate-overdue`, `GET /workflows/{id}`, `GET /workflows/{id}/history` | `contract.transition` / `contract.read` / `user.manage` |
| notifications | `GET /notifications`, `POST /notifications/{id}/read`, `POST|GET /notifications/webhooks` | `contract.read` / `user.manage` |

Webhook delivery: the integration module subscribes to the in-process event bus
and forwards matching events (exact event type or `*`) to each active
subscription, signing the JSON body with HMAC-SHA256
(`X-ECLMS-Signature` = hex of `HMAC-SHA256(secret, body)`). Every attempt is
recorded in `webhook_deliveries` (status code / error).

All cross-tenant access is scoped to the authenticated user's organization and
returns `NOT_FOUND` for entities in other orgs (ADR-003).

---

## 9. File Storage

Document blobs are stored under `ECLMS_STORAGE_ROOT` via
`infrastructure/storage/LocalStorageProvider`, behind the pluggable
`StorageProvider` contract.  Swapping in an object store requires no business
logic changes.  Files are hash-verified on upload; metadata lives in
PostgreSQL while content lives on disk.

---

## 10. Backup and Recovery

- **Database:** `pg_dump` against the `eclms-postgres` container, or snapshot
  the `eclms-pgdata` volume.  Restore via `pg_restore`/`psql`.
- **Files:** mirror `ECLMS_STORAGE_ROOT`; documents are immutable versions, so
  restore is idempotent.
- **Recovery order:** restore database → restore files → apply remaining
  migrations → start application → verify `/health` reports database `ok`.

The conceptual `architecture/deployment/06_Backup_Strategy.md` defines the
retention and verification policy targets.

---

## 11. Security Posture

- TLS termination at the Caddy reverse proxy (`Caddyfile`); the application
  serves HTTP on the compose network only and honours `X-Forwarded-*` via
  uvicorn `--proxy-headers` (`ECLMS_TRUSTED_PROXY=true`).
- Local development uses Caddy's internal CA (self-signed); production points
  the Caddyfile at a public hostname and Caddy issues/renews Let's Encrypt
  certificates automatically.
- Hardening response headers set by `SecurityHeadersMiddleware`:
  `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`,
  `Referrer-Policy: no-referrer`, `Permissions-Policy`, and
  `Strict-Transport-Security` when behind TLS.
- Secret validation fails fast: `ECLMS_JWT_SECRET` must be a 32+ character,
  non-default value when `ECLMS_ENVIRONMENT` is `production`/`staging`
  (`backend/config/settings.py`).
- PostgreSQL is private and not exposed to client networks.
- Secrets via environment/secret store; never in the repository.
- JWT bearer authentication; RBAC route guards per module.
- Per-step role authorization inside the workflow engine (separation of
  duties beyond the route guard).
- Audit trail is append-only and recorded in the database.
- The default `ADMIN`/`CONTRACT_MANAGER`/`VIEWER` roles and dev admin account
  must be replaced in production provisioning.

---

## 12. Scaling Path

The implementation matches `architecture/deployment/01_Deployment_Architecture.md`
scaling phases without application changes:

| Phase | Deployment |
|---|---|
| 1 (current) | Single application server + single PostgreSQL (Docker) |
| 2 | Separate reverse proxy, application server, database |
| 3 | Multiple application instances behind a load balancer (stateless app) |
| 4 | Enterprise: HA PostgreSQL, object storage, distributed caching, DR |

The application is stateless (no in-memory session state; JWT auth), so
horizontal scaling does not require sticky sessions.  The in-process event bus
and background-job entry points are the two components to externalize
(durable transport, dedicated scheduler) when scaling beyond a single process.

---

## 13. Verification

The deployment is continuously verified three ways:

1. **CI pipeline** (`.github/workflows/ci.yml`) — on every push/PR to `main`/`master`:
   - Backend job: `pip install -e ".[dev]"`, `ruff check`, `pytest tests/` (SQLite per test via conftest)
   - Frontend job: `npm ci` + `npm run build` in `frontend/`
2. **Test suite** — 65+ pytest tests against a fresh SQLite database per test
   (`tests/`), ruff-clean. Scheduler and Redis transport stay off in CI
   (`ECLMS_SCHEDULER_ENABLED=false`, `ECLMS_EVENT_TRANSPORT=memory`).
3. **Live smoke test** — against the real PostgreSQL container: provisioning,
   RBAC, full approval workflow, parallel/conditional workflows, escalation
   sweep, document upload, history, versioned updates, org scoping.

---

## 14. Traceability

| Artifact | Relationship |
|---|---|
| ADR-001 | PostgreSQL as the system of record. |
| ADR-004 | Modular monolith deployed as a single process. |
| ADR-005 | On-premises-first with cloud-compatible abstractions (storage provider, env config). |
| `architecture/deployment/` | Conceptual deployment architecture this document realizes. |
| `backend/bootstrap/application.py` | Concrete bootstrap sequence. |
| `infrastructure/database/` | Connection, models, migrations, repositories. |
| `.env.example` | Documented runtime configuration. |
