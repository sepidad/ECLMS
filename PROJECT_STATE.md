## Current Phase

### ✅ Phase 1 — Project Documentation
Completed

### ✅ Phase 2 — Architecture Foundation
Completed

Includes:

- Architecture Decision Records
- C4 Architecture
- Behavioral Architecture (Sequence)
- PlantUML Architecture Framework

### ✅ Phase 3 — Execution Foundation (Code Bootstrap)
Completed (2026-08-01)

Includes:

- Tech stack decision: Python 3.11 + FastAPI + SQLAlchemy (async) + PostgreSQL
- Modular monolith repository layout (`backend/`, `shared/`, `infrastructure/`)
- Core kernel: base entity/repository/module, events, exceptions, security, utils, logging
- Module interface per EXEC-004 (initialize/register_services/register_routes/register_events/health_check/shutdown)
- Module container + deterministic bootstrap sequence (EXEC-003)
- API layer: response envelope (EXEC-006), trace-id middleware, central error handler, versioned gateway
- Identity module: basic auth skeleton (login, JWT, current user) — Phase 0/1 scope
- Contracts module: Contract aggregate + lifecycle state machine + API — Phase 1 scope
- Audit module: append-only event subscription foundation
- 22 passing tests (pytest), ruff clean

### ✅ Phase 1 — Core Contract System MVP (persistence)
In progress (2026-08-01) — SQLAlchemy persistence layer implemented

Includes:

- SQLAlchemy async persistence replacing the Phase 0 in-memory repositories
  - `infrastructure/database/models/` (identity, contracts, documents+audit) registered on the declarative `Base`
  - `infrastructure/database/repositories/` self-sessioning repositories (user, contract, document, audit)
  - `create_schema()` for dev/test; Alembic migrations (one reversible migration per logical change) with a generated initial schema migration
  - SQLite (`aiosqlite`) used for tests via `ECLMS_DATABASE_URL`; PostgreSQL remains the production target (ADR-001)
- Contract versioning: immutable `contract_versions` snapshots, one active version per contract, `current_version_id` on the aggregate
  - New API: `PATCH /api/v1/contracts/{id}` (versioned update), `GET /api/v1/contracts/{id}/versions`
- User management + basic RBAC:
  - `UserService` (create/list users), `AuthorizationService` (permission checks)
  - Seeded roles (`ADMIN`, `CONTRACT_MANAGER`, `VIEWER`), permissions, default organization
  - New API: `POST/GET /api/v1/identity/users`, `GET /api/v1/identity/roles` (guarded by `user.manage`)
- Documents: hash-verified immutable document versions + `LocalStorageProvider` (pluggable `StorageProvider` contract)
  - New API: `POST /api/v1/documents/upload`, `GET /api/v1/documents/contract/{contract_id}`
- Audit events persisted to the DB (`audit_events` append-only table) via `SqlAuditStore`
- Workflow engine (Phase 1 minimal approval transitions):
  - `WorkflowDefinition` (immutable blueprint) / `WorkflowInstance` (running execution) distinction per WF-014
  - Default approval workflow: Legal Review (CONTRACT_MANAGER) -> Finance Review (CONTRACT_MANAGER) -> Final Approval (ADMIN)
  - Start drives contract DRAFT -> SUBMITTED; step approvals move through review; final approval -> APPROVED; rejection -> REJECTED
  - Per-step role-based authorization (RBAC), immutable `workflow_history` log, `workflow.started`/`workflow.step_decided` events
  - New API: `POST /api/v1/workflows/start`, `POST /api/v1/workflows/{id}/transition`, `GET /api/v1/workflows/{id}`, `GET /api/v1/workflows/{id}/history`
- 35 passing tests (pytest), ruff clean

### ✅ Phase 1 — RBAC Route-Level Guarding (ADR-002)
Completed (2026-08-01)

- Shared authorization guards in `backend/api/security.py`:
  - `current_user_id` (authn → 401 Unauthorized)
  - `require_permission` (authz → 403 Forbidden)
- Route-level permission enforcement across all business modules:
  - Contracts: `contract.create` / `contract.read` / `contract.update` / `contract.transition`
  - Documents: `document.upload` / `document.read`
  - Workflows: `contract.transition` (start/decide) / `contract.read` (get/history)
  - Identity: `user.manage` on user management; auth required for `/roles`
- Refactored identity routes onto the shared guards (removed duplicated `_require_permission`)
- All tests updated to authenticate as the seeded admin; added route-level RBAC tests (VIEWER denied create/update/transition/upload; allowed read)
- 40 passing tests (pytest), ruff clean

### ✅ PostgreSQL Live Run
Completed (2026-08-01)

- Provisioned PostgreSQL 16 via Docker (`eclms-postgres` container, port 5432, user/db `eclms`, named volume `eclms-pgdata`)
- Applied Alembic migrations to live Postgres: `b789652b8c89` (initial schema) → `53c331530e3d` (workflow tables)
- Started the application against the live database; bootstrap seeded default organization, roles/permissions, and the dev admin
- Verified with a 16-step live smoke test (all passing):
  - Admin login, user provisioning (CONTRACT_MANAGER / VIEWER), RBAC enforcement (FORBIDDEN on restricted actions)
  - Contract lifecycle: create DRAFT → workflow start → Legal/Finance approval (manager) → final approval (admin) → APPROVED
  - Document upload + read-only listing, workflow history, versioned updates (v1 → v2)
- Confirmed persistence directly in Postgres: 3 users, 10 contracts, 13 versions, 3 documents, 8 workflows, 19 workflow history rows, 50 audit events
- NOTE: API returns errors via HTTP 200 envelope with `success: false` + `error.code` (EXEC-006 convention)

### ✅ Phase 1 — Organization Scoping (Multi-Tenancy, ADR-003)
Completed (2026-08-01)

- Tenant is always derived from the authenticated user (JWT `org` claim / `user.organization_id`), never from request bodies
- `backend/api/security.py` now resolves a full `Actor(id, organization_id)`; `require_permission` returns it; removed client-supplied `organization_id`/`owner_id` from `CreateContractRequest` and `organization_id` from `CreateUserRequest`
- Contracts: create/read/update/transition/versions all scoped by `organization_id`; `list_contracts` filters by org; cross-tenant access returns `NOT_FOUND` (existence not leaked)
- Documents: upload/list require the target contract to belong to the caller's org
- Workflows: start/decide/get/history verify the workflow's contract is in the caller's org
- Identity: user creation/listing scoped to the caller's org; roles/permissions remain global
- 4 new isolation tests (contracts/documents/workflows/users) — 44 passing tests (pytest), ruff clean
- Verified against live PostgreSQL: 18-step smoke test all passing (includes org-scoped contract + list)

### ✅ Phase 2 — Workflow Engine Expansion (parallel/conditional, escalation, delegation)
Completed (2026-08-04)

- **Domain** (`backend/modules/workflow/domain/workflow.py`):
  - `WorkflowStepDefinition` extensions: `parallel_group_id`, `condition`, `timeout_hours`, `escalation_role`, `delegation_allowed`
  - `WorkflowStep` runtime state: `started_at`, `escalated_at`, `delegated_to`, `delegated_at`, plus `delegate()` / `escalate()`; `decide()` now accepts delegated/escalated steps
  - `WorkflowInstance`: `pause()` / `resume()` (`PAUSED` status), parallel-group resolution (`pending_steps`, `_all_parallel_steps_decided`, `_advance_past_parallel_group`), condition evaluation via safe `eval` on the contract, `SKIPPED` step status for false conditions, decide-by-step-name (`step_name`) for parallel decisions
  - New statuses: `WORKFLOW_STATUS_PAUSED`, `STEP_STATUS_ESCALATED`/`DELEGATED`/`SKIPPED`
- **Definitions**: added `contract-approval-parallel` (Legal + Compliance in parallel, then Final Approval) and `contract-approval-conditional` (CFO Approval runs only when `contract.counterparty == 'Acme'`)
- **Persistence**: new columns on `workflow_instances` (`paused_by`, `pause_reason`, `paused_at`) and `workflow_steps` (`parallel_group_id`, `condition`, `timeout_hours`, `escalation_role`, `delegation_allowed`, `started_at`, `escalated_at`, `delegated_to`, `delegated_at`); Alembic migration `a1b2c3d4e5f6` applied to live Postgres; repository `create`/`save`/load updated, added `find_all_running()` for the escalation sweep
- **Service**: `decide` passes the contract for condition evaluation, supports `step_name`, enforces paused-state guard, and authorizes delegated/escalated steps (`_actor_can_decide_step`); new `pause`, `resume`, `delegate`, `escalate`, and `escalate_overdue` (SLA sweep) operations with `workflow.paused`/`resumed`/`step_delegated`/`step_escalated` events
- **API**: `POST /{id}/pause`, `POST /{id}/resume`, `POST /{id}/delegate`, `POST /{id}/escalate` (all `contract.transition`), `POST /escalate-overdue` (`user.manage`); transition requests accept optional `step_name`
- **Tests**: 8 new Phase 2 tests (parallel approvals, parallel rejection, conditional skip/run, pause/resume, delegation, manual escalation, SLA sweep) — **52 passing tests (pytest), ruff clean**
- Verified against live PostgreSQL: parallel flow → APPROVED, pause/resume, conditional skip, and `escalate-overdue` sweep all pass

### ✅ Deployment Architecture (Implementation)
Completed (2026-08-04)

- Wrote `DEPLOYMENT.md` — the implementation-focused deployment document for the actual codebase (complements the conceptual `architecture/deployment/` package):
  - Runtime topology: modular monolith (FastAPI/uvicorn single process) + PostgreSQL + pluggable file storage
  - Environment configuration table (`ECLMS_*` vars), Docker PostgreSQL provisioning, Alembic migration chain, run commands
  - Health checks (`/health`, per-module), API surface and RBAC guards, file storage, backup/recovery order, security posture, scaling path (Phases 1–4), and verification (52 tests + live smoke test)
  - Traceability to ADR-001/004/005 and the conceptual deployment architecture

### ✅ Frontend UI (React/Vite client)
Completed (2026-08-06)

- Scaffolded `frontend/` with Vite + React + TypeScript (React 19, Vite 8, lucide-react icons)
- Full SPA dashboard in `src/App.tsx`: login (admin/admin), contracts, workflows/approvals, users/RBAC
- Dev server on port 3000 proxying `/api` to `localhost:8000` (`vite.config.ts`)
- `npm run build` passes

### ✅ Notifications & Webhook Integrations
Completed (2026-08-06)

- `NotificationModel` / `WebhookSubscriptionModel` in `infrastructure/database/models/notifications.py`
- Alembic migration `ebe4b66ae720` (notifications/webhooks)
- `NotificationRepository` + `NotificationService` (`application/notification_service.py`), route guards via shared auth
- API: `GET /api/v1/notifications`, `POST /{id}/read`, webhook subscribe/list; module wired via `gateway.mount('notifications', ...)`
- Test added; suite grew to 53 passing tests (pytest), ruff clean

### ✅ Production Hardening (expression parser, scheduler, durable events)
Completed (2026-08-06)

- **Safe expression parser**: replaced the Phase 2 `eval` for conditional steps with `simpleeval` via `backend/modules/workflow/domain/condition_evaluator.py` (`ConditionEvaluator.evaluate`, `ConditionEvaluationError`); verified it rejects arbitrary code (`__import__`, `open`) and returns strict booleans; `_evaluate_condition` treats evaluation errors as "skip"
- **Escalation scheduler**: APScheduler `AsyncIOScheduler` wired into the app lifespan calling `WorkflowService.escalate_overdue` on an interval; controlled by `ECLMS_SCHEDULER_ENABLED` (default off) and `ECLMS_ESCALATION_INTERVAL_MINUTES`; clean shutdown in lifespan
- **Durable event transport**: `infrastructure/messaging/redis_broker.py` implements the `MessageBroker` ABC via Redis Streams + consumer group (at-least-once, crash recovery); `backend/core/events/durable.py` `DurableEventBus` persists then drains/acks; selected by `ECLMS_EVENT_TRANSPORT=redis` (default `memory`), `ECLMS_REDIS_URL`
- Deps added: `simpleeval`, `apscheduler`, `redis`
- **65 passing tests (pytest), ruff clean**

### ✅ CI Pipeline (GitHub Actions)
Completed (2026-08-06)

- `.github/workflows/ci.yml` on push/PR to `main`/`master`
- Backend job: Python 3.11, `pip install -e ".[dev]"`, `ruff check`, `pytest tests/` (SQLite via conftest; scheduler/Redis off)
- Frontend job: Node 20, `npm ci`, `npm run build`
- Documented in `DEPLOYMENT.md` §13

### ✅ Docker Compose Stack (API + Postgres + Redis)
Completed (2026-08-06)

- `Dockerfile` (Python 3.11-slim, `pip install -e .`, runs `alembic upgrade head` then uvicorn) + `.dockerignore`
- `docker-compose.yml`: `api` (port 8000, build from repo), `db` (Postgres 16, host port 5433, named volume), `redis` (Redis 7, port 6379); healthchecks on all services
- Image builds clean; full stack boots healthy; live smoke verified:
  - Login, create contract, start conditional workflow (RUNNING, Legal/Finance/Final steps) against containerized Postgres
  - Redis durable transport live test: publish → drain → deliver → ack via `DurableEventBus` + `RedisBroker`
- Documented in `DEPLOYMENT.md` §6a; migration chain updated through `ebe4b66ae720`

### ✅ Integration Module — Webhook Delivery
Completed (2026-08-06)

- Events now carry `organization_id` in metadata (all publishers: contracts, workflow, documents) — ADR-003 compliant, enables org-scoped delivery
- `backend/modules/integration/application/webhook_service.py`: `WebhookDeliveryService` subscribes to the event bus (`subscribe_all`), matches active subscriptions by event type (exact or `*`), POSTs HMAC-SHA256-signed payloads (`X-ECLMS-Signature` header) via `httpx`, and records every attempt
- `WebhookDeliveryModel` + migration `6dcb594622ee` (`webhook_deliveries` table: org, subscription, event type, url, status_code, error, delivered_at)
- `NotificationRepository.list_active_for_event` added; integration module wired in `register_services`/`register_events`
- `httpx` promoted to a runtime dependency
- Tests: 7 new in `tests/test_integration.py` (HMAC signing, matching, wildcard, org-scoping, failure recording, disabled) — **72 passing tests (pytest), ruff clean**
- Verified live against the compose stack: subscribed `contract.created` webhook → created contract → delivery recorded with `status_code 200` (plus error path with connection refused)

### ✅ Production Hardening — Secrets & HTTPS
Completed (2026-08-06)

- **Secrets validation**: `Settings` rejects the default/dev JWT secret and any secret < 32 chars when `ECLMS_ENVIRONMENT` is `production`/`staging` (fails fast at boot); `DEV_SECRET_MARKER` constant
- **Security headers middleware** (`backend/api/middleware/security.py`): `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: no-referrer`, `Permissions-Policy`, plus `Strict-Transport-Security` when `ECLMS_TRUSTED_PROXY=true`; wired into `create_app`
- **TLS reverse proxy**: Caddy service in compose (`Caddyfile`) terminating TLS on 443; internal CA for local dev, Let's Encrypt path for production; uvicorn `--proxy-headers --no-server-header`; app runs as non-root `eclms` user in the image
- Tests: 6 new in `tests/test_hardening.py` (prod secret rejection, dev acceptance, headers, HSTS behind proxy) — **78 passing tests (pytest), ruff clean**
- Live-verified on compose stack: HTTPS login through Caddy returns 200, HSTS + hardening headers present, all 4 services healthy

### ✅ Frontend Wiring for Notifications & Webhooks
Completed (2026-08-06)

- UI tab "Notifications & Webhooks" in `frontend/src/App.tsx` (Navbar badge with unread count + dedicated tab button)
- In-app notifications feed with unread highlight, channel tag, and click-to-mark-read (`POST /api/v1/notifications/{id}/read`)
- Webhook subscription form (URL, event type dropdown, signing secret) + active webhooks list (`POST/GET /api/v1/notifications/webhooks`)
- Live verified against running backend; `npm run build` passes, `oxlint` clean

### ✅ Escalation Scheduler — Live E2E
Completed (2026-08-06)

- Default approval workflow Legal Review step updated with a 24-hour SLA (`timeout_hours=24`, `escalation_role='ADMIN'`)
- APScheduler configured in `docker-compose.yml` (`ECLMS_SCHEDULER_ENABLED=true`, `ECLMS_ESCALATION_INTERVAL_MINUTES=1`)
- Live verified against containerized Postgres + API:
  - Created contract + started `contract-approval` workflow (step: Legal Review, status: `PENDING`)
  - Backdated step `started_at` in Postgres beyond SLA
  - APScheduler automatically ran `escalate_overdue()` sweep on schedule
  - Step status transitioned to `ESCALATED`, `escalated_at` set, `escalation_role='ADMIN'` assigned
  - ADMIN called `/api/v1/workflows/{id}/transition` to approve the escalated step; workflow advanced to `Finance Review`
- All 78 tests pass (pytest), ruff clean

### ✅ Audit Trail API & Frontend View
Completed (2026-08-06)

- Added `GET /api/v1/audit` endpoint in `AuditModule` (`backend/modules/audit/interfaces/routes.py`), guarded by `user.manage` permission and backed by `SqlAuditStore`
- Added "Audit Trail" tab to the frontend SPA (`frontend/src/App.tsx`), displaying immutable event records (timestamp, event type, module, entity, actor ID)
- Live verified against containerized API (`/api/v1/audit` returning 11 append-only audit events); `npm run build` passes, ruff clean

### ✅ Observability & Prometheus Metrics
Completed (2026-08-06)

- Added `MetricsMiddleware` (`backend/api/middleware/metrics.py`) tracking total HTTP requests and error counts
- Added Prometheus exposition endpoint (`GET /metrics`) returning plain text metrics (`eclms_uptime_seconds`, `eclms_http_requests_total`, `eclms_http_errors_total`)
- Live verified against containerized API (`GET /metrics` returning valid Prometheus format); all 79 pytest tests pass, ruff clean

### ✅ External Integrations — SMTP Email Delivery
Completed (2026-08-06)

- Added SMTP settings to `Settings` (`ECLMS_EMAIL_ENABLED`, `ECLMS_SMTP_HOST`, `ECLMS_SMTP_PORT`, `ECLMS_SMTP_USER`, `ECLMS_SMTP_PASSWORD`, `ECLMS_SMTP_FROM`)
- Implemented `EmailDeliveryService` (`backend/modules/integration/application/email_service.py`) listening to domain events (`workflow.step_escalated`, etc.) and dispatching emails asynchronously via `smtplib` (with mock/local development fallback)
- Wired into `IntegrationModule` and verified with 2 new tests in `tests/test_email.py` — **81 passing tests (pytest), ruff clean**

### ✅ External Integrations — S3 Object Storage Provider
Completed (2026-08-06)

- Added `S3StorageProvider` (`infrastructure/storage/s3.py`) implementing the `StorageProvider` contract via `boto3` (works with AWS S3 and S3-compatible services like MinIO / LocalStack; blocking calls run in a thread pool via `asyncio.to_thread`)
- Added `get_storage_provider()` factory (`infrastructure/storage/__init__.py`) selecting `S3StorageProvider` or `LocalStorageProvider` based on `ECLMS_STORAGE_BACKEND` (default `local`)
- Added S3 settings to `Settings` (`ECLMS_STORAGE_BACKEND`, `ECLMS_S3_BUCKET`, `ECLMS_S3_REGION`, `ECLMS_S3_ENDPOINT_URL`, `ECLMS_S3_ACCESS_KEY_ID`, `ECLMS_S3_SECRET_ACCESS_KEY`)
- `DocumentsModule` now uses the factory; `boto3>=1.34` promoted to a runtime dependency
- Tests: 3 new in `tests/test_storage_s3.py` (round-trip, missing-key error, factory) — **84 passing tests (pytest), ruff clean**
- Live verified: document upload still works via the factory (local backend) on the compose stack

### ✅ Advanced Auth — ABAC/RBAC Policies + OIDC Integration
Completed (2026-08-06)

- Added ABAC policy engine (`backend/api/abac.py`): `Actor`, `PolicyContext`, `Policy`, `PolicyEngine`, and predicates (`is_resource_owner`, `is_same_organization`, `time_between`, `action_is`, `all_of`, `any_of`). Semantics: no registered policies → RBAC-only fallthrough (evaluate returns `True`); with policies → implicit deny, explicit `DENY` overrides `ALLOW`.
- Moved `Actor` into `abac.py` and made `security.py` import it, resolving the `abac` ⇄ `security` circular import.
- Extended `backend/api/security.py` with `require_abac(...)` and `require_abac_only(...)` guards that evaluate ABAC policies over a `PolicyContext` (actor, resource, action, environment) after the RBAC check.
- Registered `'abac.engine'` → `PolicyEngine()` in `CommonModule.register_services`.
- Added OIDC settings to `Settings` and the OIDC authorization-code flow to `AuthService` (`oidc_authorization_url`, `oidc_exchange_code`, `_fetch_oidc_userinfo`, `_upsert_oidc_user`). New IdP users are created inactive (admin activation required) and scoped to `oidc_default_org`.
- Added OIDC routes: `GET /api/v1/identity/auth/oidc/start` and `GET /auth/oidc/callback`; transport failures → `OIDC_EXCHANGE_FAILED`.
- Tests: 7 new in `tests/test_abac.py`, 6 new in `tests/test_oidc.py` — **97 passing tests (pytest), ruff clean**.
- Updated `.env.example` with storage, SMTP, and OIDC variables.

### ✅ Workflow & Multi-Step Approvals — Executive Sign-off
Completed (2026-08-07)

- Added `contract-approval-executive` workflow definition (`Legal Review` → `Executive Sign-off`), registered in `WORKFLOW_DEFINITIONS` (`backend/modules/workflow/domain/definitions.py`).
- `WorkflowService.decide` auto-transitions the contract `APPROVED → EXECUTED → ACTIVE` on final approval for this definition, delivering the full **Draft → Legal Review → Executive Sign-off → Active** lifecycle.
- Every step carries an SLA (`timeout_hours`) + escalation role, driven by the existing automated escalation sweep / APScheduler.
- Tests: 2 new in `tests/test_executive_workflow.py` (full flow + escalation sweep) — **103 passing tests (pytest), ruff clean**.
- Live-verified on the compose stack end-to-end including automated SLA escalation.

### ✅ Obligation Tracking Module
Completed (2026-08-07)

- New `Obligations` module (`backend/modules/obligations/`): `ContractObligation` (`PENDING`/`IN_PROGRESS`/`COMPLETED`/`OVERDUE`) and `ObligationMilestone` (`PENDING`/`REACHED`), with assign/start/complete/reach-milestone/overdue-sweep operations.
- Persistence: `ObligationModel`/`ObligationMilestoneModel`, `SqlObligationRepository`, migration `c7e8f9a0b1c2`; timezone-aware overdue comparison (naive-SQLite guard).
- API: `/api/v1/obligations`, `/{id}/milestones`, `/{id}/assign`, `/{id}/start`, `/{id}/complete`, `/{id}/milestones/{mid}/reach`.
- Registered module/constants/permissions; 7 tests in `tests/test_obligations.py` — **110 passing tests (pytest), ruff clean**.

### ✅ Financial Module — Commitments & Payment Schedules
Completed (2026-08-07)

- New `Finances` module (`backend/modules/finances/`): `FinanceCommitment` (`OPEN`/`PAID`/`CANCELLED`) and `FinancePayment` (`SCHEDULED`/`PAID`/`OVERDUE`/`CANCELLED`) with `mark_paid`/`cancel`/`mark_overdue` and a `sweep_overdue` operation.
- Persistence: `FinanceCommitmentModel`/`FinancePaymentModel`, `SqlFinanceRepository`, migration `d1e2f3a4b5c6`; Pydantic validation on request payloads.
- API: `/api/v1/finances/commitments`, `/commitments/{cid}/payments`, `/payments/{pid}/pay`, `/payments/{pid}/cancel`, `/sweep-overdue`, `/payments`.
- Permissions `finance.create/read/update` seeded (CONTRACT_MANAGER + ADMIN, VIEWER read); domain events `finance.*`; invalid state transitions return `INVALID_STATE_TRANSITION`.
- Fixed `SqlFinanceRepository.get_payment_by_id` to restore status/timestamps on load (prevented paying a cancelled payment).
- Tests: `tests/test_finances.py` (6 tests) — **116 passing tests (pytest), ruff clean**; compose `api` container rebuilt and live-started.

### ✅ ABAC Demo Route + Policies (Engine wired end-to-end)
Completed (2026-08-07)

- Demo policy `contract-read-owner` registered on the `abac.engine` service in `CommonModule.register_services` (`backend/modules/common/__init__.py`): allows the `contract:read` action only for the contract's owner (`action_is('contract:read')` + `is_resource_owner`).
- Demo route `GET /api/v1/contracts/{id}/abac-demo` (`backend/modules/contracts/interfaces/routes.py`) opts into `require_abac(request, resource=contract, action='contract:read')`, proving an RBAC-granted user can still be denied when the ABAC policy disallows the action.
- Integration tests in `tests/test_abac_route.py` (3): owner granted, non-owner VIEWER denied (`FORBIDDEN`), unauthenticated → `UNAUTHORIZED`. Engine unit tests in `tests/test_abac.py` (7).
- **116 passing tests (pytest), ruff clean**, live-verified against the compose stack via `/abac-demo`.

### ✅ Phase 4 — Analytics & Reporting Module (Intelligence Layer start)
Completed (2026-08-07)

- New `Reporting` module (`backend/modules/reporting/`), the first slice of roadmap Phase 4 (Intelligence & Optimization, module priority #10) per `docs/26_Roadmap.md` and `docs/22_Reporting_Analytics.md`.
- Read-only aggregation layer (`SqlReportingRepository` in `infrastructure/database/repositories/reporting_repository.py`) computing org-scoped analytics over existing tables (no new schema/migration):
  - **Contracts**: total, by-state distribution, active count, average lifecycle days
  - **Workflows**: total, by-status distribution, average step approval time (org-scoped through the owning contract)
  - **Obligations**: total, by-status, overdue count, SLA compliance rate
  - **Finances**: total value, paid amount, payment completion rate, overdue payments, active exposure
- `ReportingService` composes a single overview; API `GET /api/v1/reporting/overview` guarded by new `reporting.read` permission (seeded for ADMIN/CONTRACT_MANAGER/VIEWER), org-scoped (ADR-003).
- Reports are derived views (RPT-022): never mutate operational data.
- Tests: `tests/test_reporting.py` (6) — **122 passing tests (pytest), ruff clean**; compose `api` container rebuilt and live-started.

### ✅ Phase 4 — Intelligence Module (Risk, Clauses, Search, Alerts)
Completed (2026-08-07)

- New `Intelligence` module (`backend/modules/intelligence/`) delivering the remaining Phase 4 increments: risk detection, clause analysis, semantic search, and predictive alerts. Read-only and org-scoped (ADR-003).
- **Risk Detection Rules Engine** (`domain/risk.py`, `application/risk_service.py`):
  - `RiskAssessment.calculate` → 0-100 score + level (LOW/MEDIUM/HIGH/CRITICAL), derived from the summed factor impacts and the most severe factor.
  - `RiskService.assess_contract_risk` evaluates: past-expiry active contracts (`CONTRACT_PAST_EXPIRY`), expiring within 30 days (`CONTRACT_EXPIRING_SOON`), overdue obligations (`OVERDUE_OBLIGATIONS`), overdue payment installments (`OVERDUE_PAYMENTS`).
  - `RiskService.assess_organization_risk` → portfolio overview (total assessed, high/critical count, average score, per-contract detail).
- **Clause Analysis** (`domain/clause.py`, `application/clause_service.py`): rule-based parser over active contract-version text, extracting typed clauses (LIABILITY, TERMINATION, INDEMNIFICATION, GOVERNING_LAW, CONFIDENTIALITY, PAYMENT) with per-clause risk rating and a missing-recommended-clauses list.
- **Semantic Search** (`domain/semantic.py`, `application/semantic_service.py`): deterministic feature-hashed embeddings (no external AI API) + org-scoped in-memory vector index; lazy per-org rebuild keyed on active-version fingerprints; ranked by cosine similarity.
- **Predictive Alerts** (`application/predictive_service.py`): forward-looking alerts for `contract.expired`, `contract.expiring`, `obligation.due`, `payment.due`, `contract.high_risk` across the portfolio.
- Contracts API now accepts optional `content` on create/update so version text is snapshot and analyzable; `list_versions` exposes `content`.
- Seeding is now convergent: existing roles gain newly added permission codes (fixes roles created before new permissions).
- API: `GET /api/v1/intelligence/risk/contracts/{id}`, `/risk/overview`, `/clauses/{id}`, `/search?q=`, `/alerts` — all guarded by new `intelligence.read` permission.
- Tests: `tests/test_intelligence.py` (17) — **139 passing tests (pytest), ruff clean**; compose `api` container rebuilt, live-verified all five endpoints against containerized Postgres.

### ✅ Phase 4 — AI-Assisted Contract Review (provider abstraction)
Completed (2026-08-07)

- New `ReviewProvider` abstraction (`backend/modules/intelligence/application/review_provider.py`) mirroring the storage-provider factory pattern, with two pluggable implementations:
  - `RuleBasedReviewProvider` (default, deterministic, zero deps): flags unlimited liability (CRITICAL), uncapped liability, one-sided indemnification, short termination notice (`7/14/30` days), missing governing law, missing confidentiality, and extended payment terms (`net 60/90`).
  - `LlmReviewProvider` (optional, OpenAI-compatible `/chat/completions`): parses a JSON array of findings from the response, degrades gracefully to `[]` on missing URL, transport, or parse errors.
- `ReviewService` (`application/review_service.py`): loads the active version's `content`, runs the provider, computes `overall_risk_level` via `_worst_level` and `high_or_critical_count`.
- `domain/review.py`: `ReviewFinding` (category, severity, title, message, suggestion, provider) and `ContractReviewResult`.
- `IntelligenceModule` selects the provider from `ECLMS_AI_REVIEW_PROVIDER` (default `rules`); when `llm`, wires `ECLMS_LLM_API_URL`/`_KEY`/`_MODEL`/`_TIMEOUT`. New settings: `ai_review_provider`, `llm_api_url`, `llm_api_key` (repr=False), `llm_model`, `llm_timeout_seconds`.
- New API: `GET /api/v1/intelligence/review/{contract_id}` guarded by `intelligence.read`.
- Tests: 7 new in `tests/test_intelligence.py` (rule-based risk/clean, empty content, LLM response parsing, LLM endpoint call via `httpx.MockTransport`, graceful failure, auth-guarded route) — **146 passing tests (pytest), ruff clean**.

### ✅ Frontend Productization — Finances, Obligations & Contract Workspace
Completed (2026-08-07)

- New self-contained tab components in `frontend/src/components/` (each receives `headers` and manages its own data):
  - `FinancesTab.tsx` — commitments list (expandable payment schedules), create commitment (contract, description, amount, currency), add payment installment, mark paid / cancel payment, admin "Sweep Overdue".
  - `ObligationsTab.tsx` — obligation list with status filter, create obligation (contract, description, due date), complete / cancel, admin "Sweep Overdue", overdue highlight.
  - `ContractPanel.tsx` — full contract workspace: metadata view + inline edit (title/reference/counterparty/content → versioned PATCH), state transition select, immutable versions list with content-length, document upload (multipart, doc_type) + document list, **AI contract review** (`/intelligence/review/{id}`) and **clause analysis** (`/intelligence/clauses/{id}`) inline.
- `App.tsx`: added `Finance` and `Obligations` tabs to nav (Wallet / ClipboardCheck icons), "Manage" button per contract row opens `ContractPanel`, tabs wired into `main`; tab union extended.
- Empty/loading/error banners and inline messages across all new components.
- `npm run build` (tsc + vite) passes; oxlint clean (1 pre-existing warning).

### ✅ Backend Hardening — Rate Limiting & Body-Size Limits
Completed (2026-08-07)

- New `backend/api/middleware/limits.py`: `BodySizeLimitMiddleware` (HTTP 413 `PAYLOAD_TOO_LARGE` when `Content-Length` exceeds `max_request_bytes`, without consuming the body) and `RateLimitMiddleware` (in-process fixed-window counter keyed on client IP, honoring `X-Forwarded-For` behind a trusted proxy; HTTP 429 `RATE_LIMITED`).
- Wired into `create_app` behind settings: `ECLMS_RATE_LIMIT_ENABLED` (opt-in, default off), `rate_limit_requests` (100), `rate_limit_window_seconds` (60), `max_request_bytes` (0 = unlimited). Documented in `.env.example`.
- Tests: `tests/test_hardening_middleware.py` (4: 413 on large payload, small payload passes, disabled default, 429 after threshold) — **150 passing tests**.

### ✅ Rules-Engine Fix — Short-Notice False Positive
Completed (2026-08-07)

- Termination short-notice detection now uses an adjacency-aware regex (`\b(?:7|14|30)\s*-?\s*days?\s+notice\b`) instead of a substring check, so `"net 30 days from invoice"` in a payment clause no longer flags a MEDIUM short-notice finding.
- Regression test `test_termination_rule_ignores_payment_day_terms` in `tests/test_intelligence.py` — **151 passing tests (pytest), ruff clean**.

### ✅ Frontend & Export Polish — Download, CSV Export, Review Provider Selector, List Filters
Completed (2026-08-07)

- **Document download**: new `GET /api/v1/documents/{id}/download` streams the current version's bytes with a `Content-Disposition` filename; `frontend/src/download.ts` `downloadAuthenticated` helper drives a per-row Download button in the contract workspace.
- **CSV export**: `GET /api/v1/reporting/export.csv` returns contracts, obligations, and payments as a single CSV via the reporting service (`list_all` / `list_all_payments`); "Download CSV" / "Export CSV" buttons wired in the Analytics, Finances, and Obligations tabs.
- **Per-request review provider**: `GET /api/v1/intelligence/review/{id}?provider=rules|llm` selects the reviewer; the contract workspace has a rules/LLM selector, with an LLM-fallback hint when no findings come back.
- **List filters**: Client-side search (title/ref/counterparty/state for contracts; description/status/contract for obligations & commitments), contract state filter and active-state select, plus commitment/obligation text filters and an Export CSV button.
- **Production hardening defaults**: compose `api` enables `ECLMS_RATE_LIMIT_ENABLED=true` (300 req/60s), `MAX_REQUEST_BYTES=20971520`, `ECLMS_TRUSTED_PROXY=true`; audit pagination caps at 200 rows / non-negative offset.
- **Tests**: 3 new in `tests/test_report_endpoints.py` (CSV export, download, provider) — **154 passing tests (pytest), ruff clean, `npm run build` passes**, all live-verified against the recomposed container (CSV rows + `?provider=rules`).

### ✅ LLM Review Polish & E2E Lifecycle Smoke Test
Completed (2026-08-07)

- **LLM Configuration Modal & Runtime Endpoints**: Added `SettingsModal.tsx` in the frontend (accessible via navbar "LLM Settings") allowing configuration of LLM API URL, API key, model, and timeout seconds at runtime; backed by new runtime configuration endpoints (`GET/PATCH /api/v1/config/llm-settings`).
- **End-to-End Lifecycle Smoke Test**: Added `tests/test_e2e_lifecycle.py` verifying login, contract creation, AI review rules analysis, clause parsing, obligation creation, financial commitment creation, multi-step state transitions, and reporting CSV export in a single integrated test flow.
- **Suite Status**: **155 passing tests (pytest), ruff clean, `npm run build` passes**.

### ✅ Observability & Performance Polish — Latency Histogram, Pagination
Completed (2026-08-07)

- **Prometheus latency histogram**: `/metrics` now exposes `eclms_http_request_duration_seconds` (fixed buckets + sum/count), `eclms_http_requests_by_status{status="2xx/3xx/4xx/5xx"}`, alongside existing uptime/requests/errors counters.
- **Pagination for list endpoints**: `GET /api/v1/contracts` and `GET /api/v1/obligations` now accept `limit` (clamped ≤200) and `offset`; contracts list returns `{items, total, limit, offset}`; finance lists already supported pagination. Frontend fetches up to the 200-row cap to keep full-portfolio views working.
- **Tests**: 2 metrics tests + 2 pagination tests (clamp + slicing) — **159 passing tests (pytest), ruff clean, `npm run build` passes**; live-verified `/metrics` histogram/status counters against the recomposed container.

### ✅ Webhook Reliability — Retry with Exponential Backoff
Completed (2026-08-07)

- `WebhookDeliveryService._deliver_with_retries` retries transient failures (HTTP 429/500/502/503/504 and network errors) with exponential backoff (default base 0.5s → cap 8s, `MAX_ATTEMPTS=3`), recording the final status/error after attempts are exhausted.
- Non-retryable 4xx/2xx responses deliver immediately without retries.
- Tests: 3 new (transient-500-then-success, network-error-retries, non-retryable-no-retry); existing failure tests pinned to `max_attempts=1`. Suite now at **162 passing tests (pytest), ruff clean**; compose API rebuilt & healthy.

### ✅ DB Pool Resilience & Observability — pre-ping, recycle, pool gauges
Completed (2026-08-07)

- New settings `ECLMS_DATABASE_POOL_PRE_PING` (default on) and `ECLMS_DATABASE_POOL_RECYCLE` (3600s) wired into the async engine for PostgreSQL, hardening the pool against dropped connections/restarts and stale idle sockets (documented in `.env.example`).
- `/health` now reports `database_pool: {checked_out, size, overflow}` gauges via `database_pool_stats()` so operators can watch pool utilization; returns null when not a pooled engine.
- Tests: `test_health_exposes_database_pool_stats` — **163 passing tests (pytest), ruff clean**; live-verified `/health` pool stats against the recomposed container.

### ✅ Frontend System Health Tab — readiness, modules, metrics
Completed (2026-08-07)

- New `SystemHealthTab.tsx` renders live `/health` (app/version/database/DB pool gauges/module status pills), raw Prometheus `/metrics` in a dark terminal view, and a security-posture summary; reached via the new "System Health" nav tab in `App.tsx`.
- No backend changes required — reads the existing `/health` + `/metrics` endpoints through the dev/proxy.
- `npm run build` passes; live-verified `/health` (status ok, db ok, pool size 10) and the contracts API through the frontend proxy.

### ✅ Production Compose Profile — Resource Limits, Redis Transport, Scaling Readiness
Completed (2026-08-07)

- New `docker-compose.prod.yml` overlay (activated with `--profile production`): resource limits/reservations for api/db/redis/keycloak/proxy, multi-replica-ready defaults, and `ECLMS_EVENT_TRANSPORT=redis` for durable multi-instance deployments.
- Production-ready settings surfaced in the overlay: `pool_pre_ping=true`, `pool_recycle=3600`, and JVM/tuning hints for Keycloak (`KC_PROXY=edge`, memory caps).
- Compose config validates cleanly (`docker compose --profile production config`), `npm run build` passes.

### ✅ Event-Driven In-App Notifications + Mark-All-Read
Completed (2026-08-08)

- `NotificationService.handle_event` now routes domain events to in-app notifications via the `ROUTES` template table (workflow start/decision/pause/resume/delegate/escalate, contract create/state-change, document upload, obligation create/complete/overdue, payment overdue) targeted at org-scoped ADMIN/CONTRACT_MANAGER audiences plus the actor.
- Fixed `is_read`/`created_at` round-tripping in notification mapping; new `count_unread` + `mark_all_read`; `SqlUserRepository.list_by_role_in_org`.
- New API: `POST /api/v1/notifications/read-all` (+ `unread_count` on the list); Notifications tab "Mark All Read" button, unread badge driven by API state.
- Tests: 3 new in `tests/test_notifications.py` — suite now at **166 passing tests (pytest), ruff clean**; `npm run build` passes; compose API rebuilt & healthy; live-verified contract creation → unread notification and read-all reset.

### ✅ Webhook Delivery History API + Notifications UI
Completed (2026-08-08)

- `NotificationRepository.list_deliveries` (newest-first, paginated) + `delivery_summary` (`total`/`succeeded`/`failed`); org-scoped `NotificationService.list_subscription_deliveries` with not-found envelope for unknown subscriptions.
- New API: `GET /api/v1/notifications/webhooks/{id}/deliveries?limit&offset` (limit clamped 1..200, `user.manage` guard).
- Frontend Notifications tab shows per-webhook `Deliveries: N` + `Failed: M` counts (red/green) with a Refresh button, fetched automatically on load.
- Tests: `test_webhook_deliveries_endpoint` — suite now at **167 passing tests (pytest), ruff clean**; `npm run build` passes; compose API rebuilt & healthy; live-verified a subscription to `httpbin.org/status/500` reports `total=1 failed=1 status=500`.

### ✅ Email Integration — Role-Based Delivery, History API + UI
Completed (2026-08-08)

- `EmailDeliveryService` rewritten from the 3-event stub into a full integration: `EMAIL_ROUTES` reuses the notification router templates/audiences, resolves org-scoped recipients by role via `SqlUserRepository.list_by_role_in_org` (+ actor), sends via `smtplib` in a thread pool (mock when `smtp_host=localhost` with no user), and records every attempt.
- `EmailDeliveryModel` (`email_deliveries` table: org, recipient, event_type, subject, body, status `sent`/`failed`, error, delivered_at) added to `infrastructure/database/models/integration.py`; `NotificationRepository.list_email_deliveries` (newest-first, paginated) + `email_delivery_summary` (`total`/`sent`/`failed`); org-scoped `NotificationService.list_email_deliveries`.
- New API: `GET /api/v1/notifications/email/deliveries?limit&offset` (limit clamped 1..200, `user.manage` guard).
- `IntegrationModule.register_services` now injects the user repository + notification repository into the email service; dev compose enables `ECLMS_EMAIL_ENABLED=true` (mock SMTP).
- Frontend Notifications tab gains an "Email Deliveries" panel: total/sent/failed counts + recent deliveries list (subject, recipient, event, error) with a Refresh button.
- Tests: `tests/test_email.py` rewritten (audience resolution, unrouted skip, disabled, SMTP-failure record, routes) + `test_email_deliveries_endpoint` — suite now at **171 passing tests (pytest), ruff clean**; `npm run build` passes; compose API rebuilt & healthy; live-verified contract creation → emails recorded as `sent` to `admin@eclms.local` + `mgr1@eclms.local` with mock SMTP log lines.

### ✅ Multi-Channel Delivery & Data Import Engine (SMS, Connectors, CSV Import)
Completed (2026-08-09)

- **SMS Notification Channel** (`backend/modules/integration/application/sms_service.py`):
  - Pluggable `SmsProvider` ABC with `MockSmsProvider` (dev/log) and `HttpSmsProvider` (generic REST w/ basic auth).
  - `SmsDeliveryService` subscribes to the event bus, reuses `NotificationService.ROUTES`, resolves recipients from event payload `phone`/`sms_to` or configured `ECLMS_SMS_RECIPIENTS`, records every attempt to `sms_deliveries` (org, recipient, phone, event, body, status `sent`/`failed`, error).
  - `build_sms_provider(settings)` factory selects `mock`/`http` from `ECLMS_SMS_PROVIDER`.
  - New settings: `ECLMS_SMS_ENABLED`, `ECLMS_SMS_PROVIDER`, `ECLMS_SMS_RECIPIENTS`, `ECLMS_SMS_HTTP_URL`, `ECLMS_SMS_HTTP_USERNAME`, `ECLMS_SMS_HTTP_PASSWORD`.
  - Wired into `IntegrationModule.register_services`/`register_events`.
  - New API: `GET /api/v1/notifications/sms/deliveries?limit&offset` (limit clamped 1..200, `user.manage` guard).
  - Repository: `NotificationRepository.list_sms_deliveries` + `sms_delivery_summary`.

- **External Connectors Scaffold (ERP / Accounting)** (`backend/modules/integration/application/connector_service.py`):
  - Pluggable `ExternalConnector` ABC with `ErpConnector` (contracts & commitments) and `AccountingConnector` (payments & commitments), each dry-runs when `ECLMS_ERP_ENDPOINT`/`ECLMS_ACCOUNTING_ENDPOINT` is unset.
  - `ConnectorService` registry + orchestration; `ConnectorSyncModel` (`connector_syncs` table) records every sync attempt.
  - New API: `GET /api/v1/integration/connectors` (registry), `POST /api/v1/integration/connectors/{id}/sync` (dry-run or POST), `GET /api/v1/integration/connectors/syncs` (history).

- **CSV Data Import Engine** (`backend/modules/data_import/`):
  - New `ImportModule` (depends on contracts/obligations/finances) with `ImportService.import_contracts` / `import_obligations` / `import_commitments` parsing CSV text and delegating to the domain services; row-level failures recorded per-row in a summary report (total/created/failed).
  - CSV contracts: `title, reference_number, counterparty, content`; obligations: `contract_reference, description, due_date` (ISO 8601); commitments: `contract_reference, description, amount, currency`.
  - New API: `POST /api/v1/import/contracts`, `/import/obligations`, `/import/commitments` (raw CSV body, `data.import` guard, empty body → `BAD_REQUEST`).
  - New permission `data.import` seeded for ADMIN + CONTRACT_MANAGER.

- **Ops Polish — Audit CSV Export**:
  - New `GET /api/v1/audit/export.csv?limit` (`user.manage`) streams audit events as a downloadable CSV (`Content-Disposition: attachment; filename="audit_export.csv"`).

- **Frontend**:
  - Notifications tab: SMS Deliveries panel (total/sent/failed + per-delivery card: phone, body, event, error) alongside the existing Email panel; Refresh buttons for both; unified "Refresh" button on the tab.
  - Audit tab: "Export CSV" button streams the new `/audit/export.csv` endpoint via `downloadAuthenticated`.
  - New lucide icons: `MessageSquare` (SMS), `Download` (export).

- **Tests**: `tests/test_new_features.py` (14 unit: SMS dispatch/skip/disabled/failure, import CSV + row-failure + empty, connector dry-run/sync/registry) + 9 new API integration tests in `tests/test_api.py` (SMS auth+envelope, import auth+CSV+empty, connectors auth+list+unknown, audit CSV). **194 passing tests (pytest), ruff clean, `npm run build` passes**.

- **Live-verified against compose stack** (Postgres 16, API rebuilt & healthy): SMS deliveries envelope, connectors list (`erp`, `accounting`), import contracts (2 rows created, events appear in audit), audit CSV export (`text/csv`, `contract.created` row present), ERP sync dry-run + history recording.

### 🔄 Phase 5 — Release Hardening (started 2026-08-14)

The project has entered release-hardening rather than feature expansion. This phase converts the broad implementation completed through 2026-08-09 into a reproducible, auditable release candidate.

Completed in the first hardening slice:

- Added `quality/Release_Readiness.md` with repository, automated verification, business lifecycle, operational, and security gates.
- Added a workspace-local pytest `tmp_path` fixture so Windows test runs do not depend on stale or inaccessible global pytest temp directories.
- Added `.gitignore` protection for runtime contract storage and local SQLite databases.
- Verified **197 pytest tests passing**, Ruff clean, `npm run lint` clean, and `npm run build` passing.

Completed in the second hardening slice:

- Cloned the pushed repository into a clean checkout at `79de4a2`; clean status and frontend dependency/build verification passed.
- Full backend suite passed from the clean checkout: **197 tests**.
- Docker Compose development and production configurations validated.
- Built and started the Compose stack successfully; API, PostgreSQL, Redis, Keycloak, and Caddy all reported healthy.
- Verified direct API `/health` and `/metrics` plus Caddy `https://localhost/health` (HTTP 200 with HSTS).
- Hardened `.dockerignore` and `.gitignore` so nested test caches and temporary validation clones cannot contaminate build/repository contexts; pushed as `eb79ea8`.

Completed in the third hardening slice (2026-08-15):

- Consolidated the working tree into a clean commit series and pushed to origin (main in sync).
- Added the project README, CHANGELOG, and a proprietary LICENSE notice.
- Recorded the digital-signature scope decision as ADR-006 (explicit deferral; future provider-based integration) — Gate D item closed.
- Executed the backup/restore drill end to end against the live Compose database: `pg_dump` backup, restore into a scratch database with identical row counts, application boot against the restored database (`/health` ok, all 13 modules ok), and admin login verified. Evidence recorded in `quality/Release_Readiness.md` and `DEPLOYMENT.md` §10 — Gate D item closed.
- Fixed a latent DOCX export crash (`add_rich_docx_content` used list-state variables before assignment) and restored a fully clean Ruff run.

Current blockers for release readiness:

- ERP/accounting connectors remain scaffolded/dry-run integrations.
- Real external-provider acceptance tests remain to be demonstrated.

Next focus:

- Complete external-provider acceptance checks and the production-grade connector.

### 🔄 Phase 6 — Contract Manager Workflow (in progress)

- Added `docs/28_Contract_Manager_Workflow.md` as the implementation specification derived from the contract workflow design document.
- The first user journey is now explicitly manager-led: template → structured draft → parallel legal/finance review → manager merge → value/risk approval → execution → guarantee monitoring.
- Template library expanded to five approved templates (general service, procurement, construction/works, consulting, maintenance/SLA) with structured fields, locked/optional clauses, required guarantees, and per-role review SLAs.
- **Slice 1 complete (2026-08-15): template-backed contract preparation.**
  - `POST /api/v1/contracts/from-template` validates the template and its required commercial fields (unknown keys rejected), stores `template_key` + structured field values on the contract (Alembic migration `b7c8d9e0f1a2`), and renders the values into the initial contract version alongside a commercial-data schedule.
  - `GET /api/v1/contracts/{id}` now returns template provenance and field data.
  - Frontend "Use this template" opens a guided preparation form with dynamic fields and a required-guarantees reminder.
  - Seven new tests (validation, API lifecycle, RBAC denial); suite at **209 passing**; Ruff clean; frontend lint + build pass.
- Remaining Phase 6 slices: configurable review assignments with SLA tracking, value/risk approval routing, guarantee register states and alerts (partially present), Persian localization after workflow acceptance.
