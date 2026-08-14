## Session 2026-08-09 — Multi-Channel Delivery, Data Import Engine & Ops Polish

Extended the platform with end-to-end SMS notifications, external-system connectors, a CSV data import engine, and audit CSV export.

### Achievements

- **SMS Notification Channel** (`backend/modules/integration/application/sms_service.py`): pluggable `SmsProvider` ABC with `MockSmsProvider` (log) and `HttpSmsProvider` (REST + basic auth); `SmsDeliveryService` subscribes to the event bus, reuses `NotificationService.ROUTES`, resolves recipients from event `phone`/`sms_to` or `ECLMS_SMS_RECIPIENTS`, records to `sms_deliveries`; wired into `IntegrationModule`; new API `GET /api/v1/notifications/sms/deliveries`.
- **External Connectors** (`backend/modules/integration/application/connector_service.py`): pluggable `ExternalConnector` ABC with `ErpConnector` + `AccountingConnector` (dry-run when unconfigured, POST when endpoint set); `ConnectorService` registry/orchestration; `ConnectorSyncModel` records every attempt; new API `GET /api/v1/integration/connectors`, `POST .../{id}/sync`, `GET .../syncs`.
- **CSV Data Import Engine** (`backend/modules/data_import/`): new `ImportModule` with `ImportService.import_contracts` / `import_obligations` / `import_commitments` parsing CSV and delegating to domain services with per-row failure reporting; new `data.import` permission (ADMIN + CONTRACT_MANAGER); new API `POST /api/v1/import/{contracts,obligations,commitments}`.
- **Audit CSV export** (`backend/modules/audit/interfaces/routes.py`): `GET /api/v1/audit/export.csv` streams audit events as a downloadable CSV.
- **Settings**: added SMS block (`sms_enabled`, `sms_provider`, `sms_recipients`, `sms_http_*`) and connector block (`erp_endpoint`, `accounting_endpoint`) to `Settings`.
- **Frontend**: SMS Deliveries panel in the Notifications tab; Export CSV button on the Audit tab; `MessageSquare` + `Download` icons.
- **Tests**: new `tests/test_new_features.py` (14 unit) + 9 API integration tests in `tests/test_api.py`. **194 passing tests (pytest), ruff clean, `npm run build` passes**.
- **Live-verified against compose stack**: SMS + connectors + import (2 rows, events in audit) + audit CSV + ERP dry-run sync + sync history all confirmed working against containerized Postgres.

### Key Decisions

- SMS/connector/import tables (`sms_deliveries`, `connector_syncs`) are created at app startup via `Base.metadata.create_all` (same convention as the existing `email_deliveries`), keeping parity with the prior session's approach.
- Connector sync history is recorded even on dry-run so operators have an audit trail of what would have been sent.
- Row-level import failures are collected rather than aborting, giving the caller a complete correction picture.

### Next Focus

- Further roadmap I/O optimization and remaining Phase items (`docs/26_Roadmap.md`).

---

## Session 2026-08-01 — Code Bootstrap (Phase 3: Execution Foundation)

Started implementing the ECLMS codebase from the execution architecture documents.

### Achievements

- Selected the tech stack: Python 3.11 + FastAPI + SQLAlchemy (async) + PostgreSQL.
- Created the modular monolith repository layout per EXEC-002:
  - `backend/` (modules, core, api, bootstrap, config, main.py)
  - `shared/` (types, constants, contracts, utils)
  - `infrastructure/` (database, storage, messaging, email, external_clients)
- Implemented the core kernel:
  - Base `Entity`, `BaseRepository`, and `Module` interface (EXEC-004)
  - `Event`/`EventBus` with `subscribe` and `subscribe_all` (audit wildcard)
  - Exception hierarchy (domain / application / infrastructure)
  - Structured JSON logging with trace-id correlation
  - JWT + bcrypt security primitives
- Implemented the `ModuleContainer` and deterministic bootstrap sequence (EXEC-003).
- Implemented the API layer:
  - Response envelope per EXEC-006 (`success`/`data`/`error`/`trace_id`)
  - Trace-context middleware (X-Trace-Id propagation)
  - Central exception handler
  - Versioned `APIGateway` mounting module routers at `/api/v1/{module}`
- Identity module: basic authentication skeleton (login, JWT, `auth/me`), seeded dev admin.
- Contracts module: `Contract` aggregate with lifecycle state machine and `/api/v1/contracts` routes.
- Audit module: append-only audit records subscribed to all domain events.
- Scaffolded workflow, documents, notifications, integration modules.
- 22 pytest tests passing; ruff clean.

### Key Decisions

- In-memory repositories for Phase 0/1 to keep the skeleton runnable without a database; SQLAlchemy repositories replace them in Phase 1.
- Event bus is in-process; a durable transport can replace it without changing the subscriber contract.

### Next Focus

- SQLAlchemy persistence + PostgreSQL setup
- User management + RBAC/ABAC
- Document storage
- Workflow engine
- Deployment Architecture documentation

---

## Session 2026-08-01 (continued) — Phase 1 Core Contract System MVP (SQLAlchemy persistence)

Continued the Phase 1 implementation, replacing in-memory repositories with real persistence.

### Achievements

- SQLAlchemy async persistence:
  - `infrastructure/database/models/` (identity, contracts, documents_audit) registered on the declarative `Base`
  - Self-sessioning repositories in `infrastructure/database/repositories/` (user, contract, document, audit) — each operation opens its own session from the async session factory, safe at bootstrap-time construction and for concurrent requests
  - `create_schema()` for dev/test; Alembic configured (`alembic.ini`, async `env.py`, `script.py.mako`) with generated initial migration (upgrade + downgrade verified)
  - Tests run on SQLite/aiosqlite via `ECLMS_DATABASE_URL`; PostgreSQL is the production target (ADR-001)
- Contract versioning:
  - Immutable `contract_versions` snapshots created on create (v1) and update, one active version per contract, `current_version_id` written in the same transaction
  - New endpoints: `PATCH /api/v1/contracts/{id}`, `GET /api/v1/contracts/{id}/versions`
- User management + basic RBAC:
  - `UserService` (create/list users), `AuthorizationService` (`require_permission`)
  - Seeded roles (`ADMIN`, `CONTRACT_MANAGER`, `VIEWER`), static permission codes, default organization
  - Admin user seeded with the `ADMIN` role at bootstrap
  - New endpoints: `POST/GET /api/v1/identity/users`, `GET /api/v1/identity/roles` guarded by the `user.manage` permission
- Documents:
  - `DocumentService` upload flow (validate contract → store blob → hash-verify → record immutable version → publish event)
  - `LocalStorageProvider` behind the `StorageProvider` contract (`infrastructure/storage/`)
  - New endpoints: `POST /api/v1/documents/upload`, `GET /api/v1/documents/contract/{contract_id}`
- Audit: `SqlAuditStore` persists every domain event to the append-only `audit_events` table
- Removed the now-unused Phase 0 in-memory repositories
- 30 pytest tests passing (incl. new persistence/RBAC/document tests); ruff clean
- Live verification: uvicorn boot, health check, admin login, `/auth/me`, role listing against a local SQLite DB

### Key Decisions

- Repositories are self-sessioning (open their own session per operation) so they can be constructed during bootstrap before the engine exists, avoiding per-request session plumbing in the Phase 0 service wiring.
- RBAC guards enforce `user.manage` on user management endpoints; other modules will adopt route-level guards in a later increment.
- Production uses Alembic migrations; `create_schema()` (create_all) is dev/test only.

### Next Focus

- Workflow engine (approval transitions)
- Route-level RBAC/ABAC guards across all modules (org scoping)
- Deployment Architecture documentation
- PostgreSQL live run and migration verification against the real DB

---

## Session 2026-08-01 (continued) — Phase 1 Workflow Engine (Approval Transitions)

Implemented the approval workflow engine, the roadmap's #3 module priority.

### Achievements

- Domain layer:
  - `WorkflowDefinition` (immutable blueprint) vs `WorkflowInstance` (running execution) per WF-014
  - `WorkflowStep` runtime state; `WorkflowInstance.approve/reject` advance steps and record in-memory history
  - Default approval definition: Legal Review (CONTRACT_MANAGER) -> Finance Review (CONTRACT_MANAGER) -> Final Approval (ADMIN)
- Persistence (`infrastructure/database/models/workflow.py` + `SqlWorkflowRepository`):
  - `workflow_instances`, `workflow_steps` (unique per instance+step_number), `workflow_history` (immutable log)
  - Self-sessioning repository; new Alembic migration `53c331530e3d` (upgrade/downgrade verified)
- Application layer (`WorkflowService`):
  - `start` validates the definition, rejects duplicate running workflows, creates the instance, drives contract DRAFT -> SUBMITTED, publishes `workflow.started`
  - `decide` enforces per-step role authorization (RBAC via user roles), APPENDs history, publishes `workflow.step_decided`
  - Approval routing: final approval -> contract APPROVED; rejection -> contract REJECTED; intermediate steps -> contract UNDER_REVIEW
- API (`/api/v1/workflows`):
  - `POST /start`, `POST /{id}/transition`, `GET /{id}`, `GET /{id}/history`
- Added `CONTRACT_STATE_REJECTED` to shared constants.
- 5 new workflow tests (full approval, rejection, role-forbidden, duplicate conflict, post-completion decision) — 35 total passing; ruff clean.
- Live verification: boot, admin login, create contract, start workflow, read history against SQLite.

### Key Decisions

- Workflow definitions are code-registered (blueprints); instances capture the definition version at instantiation (WF-014 lifecycle consistency rule) via stored `definition_id`.
- Rejection routes the contract SUBMITTED -> UNDER_REVIEW -> REJECTED to respect the existing contract state machine.
- Per-step authorization checks the actor's roles; step role is resolved against the user repository.

### Next Focus

- Parallel / conditional approvals, escalation and delegation (Phase 2 full engine)
- Route-level RBAC/ABAC guards across all modules
- Deployment Architecture documentation
- PostgreSQL live run

---

## Session 2026-08-01 (continued) — Phase 1 RBAC Route-Level Guarding

Hardened all business module routes with shared RBAC guards (ADR-002).

### Achievements

- Added shared guards in `backend/api/security.py`:
  - `current_user_id(request)` — resolves the bearer token, raises `UnauthorizedError` (401) when missing/invalid
  - `require_permission(request, permission)` — checks the actor's permission via `AuthorizationService`, raises `ForbiddenError` (403)
- Guarded contracts routes: create/list/get/versions → `contract.read`/`contract.create`/`contract.update`/`contract.transition`
- Guarded documents routes: upload → `document.upload`; list → `document.read`
- Guarded workflow routes: start/transition → `contract.transition`; get/history → `contract.read` (per-step role check retained in the service)
- Refactored identity routes to use the shared guards (removed the duplicated local `_require_permission`); `/roles` now requires authentication
- Updated all integration tests to authenticate via a new `authed_client` fixture; added route-level RBAC tests (VIEWER denied create/update/transition/upload; allowed read-only; workflow start denied)
- 40 pytest tests passing; ruff clean

### Key Decisions

- Guards live in the API layer (`backend/api/security.py`) as the single enforcement point; modules declare the permission code per route.
- Authentication (401) and authorization (403) are distinguished: no/invalid token → UNAUTHORIZED; authenticated but missing permission → FORBIDDEN.
- The workflow service still enforces per-step role checks (separation of duties) in addition to the route-level `contract.transition` guard.

### Next Focus

- Parallel / conditional approvals (Phase 2 full engine)
- Deployment Architecture documentation

---

## Session 2026-08-01 (continued) — Organization Scoping (Multi-Tenancy, ADR-003)

### Achievements

- Tenant is now always derived from the authenticated user, never from request bodies:
  - `backend/api/security.py` resolves a full `Actor(id, organization_id)` per request; `require_permission` returns the `Actor`; added `current_organization_id`
  - Removed client-supplied `organization_id`/`owner_id` from `CreateContractRequest` and `organization_id` from `CreateUserRequest`
- Contracts fully org-scoped: create/read/update/transition/versions all check `organization_id`; `list_all` filters by org; cross-tenant access returns `NOT_FOUND` so existence is not leaked
- Documents scoped: upload and list validate the target contract belongs to the caller's org (via `ContractService.get_contract`)
- Workflows scoped: start/decide/get/history verify the workflow's contract is in the caller's org
- Identity scoped: user creation and listing operate within the caller's org (roles/permissions remain global)
- Added 4 isolation tests in `tests/test_phase1_org_scoping.py` (contracts, documents, workflows, users cross-tenant denial); 44 pytest tests passing, ruff clean
- Re-verified against live PostgreSQL: 18-step smoke test all passing (org-scoped contract + scoped list)

### Key Decisions

- Cross-tenant access is reported as `NOT_FOUND` (not `FORBIDDEN`) so callers cannot infer the existence of entities in other orgs
- Scoping is enforced at the application-service boundary (services resolve the actor org passed from the guard), keeping repositories tenant-aware via an explicit `organization_id` argument on list operations
- No schema migration needed: `contracts`/`users` already carry `organization_id`; documents and workflows scope through their owning contract
- Roles and permissions remain global; per-org role assignment is a future refinement

### Next Focus

- Parallel / conditional approvals (Phase 2 full engine)
- Deployment Architecture documentation

---

## Session 2026-08-01 (live) — PostgreSQL Live Run

### Achievements

- Started Docker Desktop (daemon was down) and provisioned PostgreSQL 16 in a container:
  - `eclms-postgres` on `localhost:5432`, user/db `eclms`, named volume `eclms-pgdata`, `--restart unless-stopped`
  - (Docker Hub pull required several retries due to transient blob EOFs)
- Ran `alembic upgrade head` against live Postgres — both migrations applied
- Started the app via uvicorn against the live DB; bootstrap seeded the default org, RBAC roles/permissions, and the dev admin (`Database health: ok`)
- Wrote and ran a 16-step live smoke test (stdlib-only client) covering:
  - Login (admin/manager/viewer), user provisioning, RBAC FORBIDDEN enforcement
  - Full contract approval workflow (Legal → Finance → Final), documents upload/list, workflow history, versioned updates
- All 16 steps passed; persistence confirmed directly in Postgres via `psql` (users/contracts/versions/documents/workflows/audit rows)
- Stopped the live server after verification

### Key Decisions

- Live run used the default settings `postgresql+asyncpg://eclms:eclms@localhost:5432/eclms` (no `.env` needed)
- API error responses arrive as HTTP 200 with `success: false` and `error.code` (EXEC-006 envelope) — smoke test asserted against the envelope, not raw HTTP status
- Workflow transition uses `decision: 'APPROVE'|'REJECT'`; history/versions return `items[]` under `data`

### Next Focus

- Organization scoping (multi-tenancy) for contracts/documents
- Parallel / conditional approvals (Phase 2 full engine)
- Deployment Architecture documentation

---

## Session 2026-08-04 — Phase 2 Workflow Engine (parallel/conditional, escalation, delegation)

### Achievements

- Domain (`backend/modules/workflow/domain/workflow.py`):
  - `WorkflowStepDefinition` extensions: `parallel_group_id`, `condition`, `timeout_hours`, `escalation_role`, `delegation_allowed`
  - `WorkflowStep` runtime state (`started_at`, `escalated_at`, `delegated_to`, `delegated_at`), `delegate()`/`escalate()`, `decide()` now accepts delegated/escalated steps; added `STEP_STATUS_SKIPPED`
  - `WorkflowInstance`: `pause()`/`resume()` (`WORKFLOW_STATUS_PAUSED`), parallel-group resolution (`pending_steps`), condition evaluation (safe `eval` against the contract), step skipping, and decide-by-`step_name`
  - `current_step`/`pending_steps` treat PENDING/DELEGATED/ESCALATED as active; skipped conditional steps are marked `SKIPPED` and the index advances past them
- Definitions: registered `contract-approval-parallel` and `contract-approval-conditional` example blueprints
- Persistence: new columns on `workflow_instances`/`workflow_steps`; Alembic migration `a1b2c3d4e5f6` (upgrade + downgrade); repository `create`/`save`/load updated; added `find_all_running()` for the SLA sweep
- Service (`WorkflowService`):
  - `decide` now passes the contract for condition evaluation, supports `step_name`, guards against deciding while paused, and authorizes delegated/escalated steps (`_actor_can_decide_step`)
  - New `pause`, `resume`, `delegate`, `escalate`, and `escalate_overdue` operations; events `workflow.paused`/`resumed`/`step_delegated`/`step_escalated`
  - `_aware()` helper normalizes naive SQLite timestamps before SLA deadline comparison
- API (`/api/v1/workflows`): `POST /{id}/pause`, `POST /{id}/resume`, `POST /{id}/delegate`, `POST /{id}/escalate` (`contract.transition`), `POST /escalate-overdue` (`user.manage`); transitions accept optional `step_name`; step serialization exposes parallel/delegation/escalation fields
- Tests: 8 new Phase 2 tests in `tests/test_phase2_workflow.py` (parallel approvals, parallel rejection, conditional skip/run, pause/resume, delegation, manual escalation, SLA sweep) — **52 pytest tests passing, ruff clean**
- Live PostgreSQL verification: started Docker, migrated `53c331530e3d -> a1b2c3d4e5f6`, confirmed columns via psql, and passed a live smoke test (parallel flow → APPROVED, pause/resume, conditional skip, escalate-overdue sweep)

### Key Decisions

- Parallel steps share a `parallel_group_id`; the group completes when all siblings are decided and rejects the workflow if any sibling rejects
- Conditional steps are skipped (marked `SKIPPED`) when their expression evaluates false; expressions are a safe `eval` on the contract object for Phase 2, to be replaced by a real expression parser in production
- Delegated steps keep their assigned role; the delegatee may decide in addition to role holders
- Escalation reassigns the step's authority to an escalation role (default `ADMIN`); `escalate_overdue` is a scheduler entry point exposed as an admin endpoint for Phase 2

### Next Focus

- Deployment Architecture documentation
- Frontend/client layer, notifications, integration modules
- Production hardening (expression parser, scheduler wiring for escalation)

## Session 2026-08-06 - Frontend, Notifications, Production Hardening

### Achievements

- Frontend UI: Vite + React + TypeScript SPA (`frontend/`), login/contracts/workflows/users tabs, port 3000 proxying `/api`; `npm run build` passes
- Notifications & webhooks module (models, migration `ebe4b66ae720`, service/repo, routes, tests) - suite grew to 53 tests
- Replaced safe `eval` with a real `simpleeval` expression parser (`ConditionEvaluator`) that rejects arbitrary/unsafe code and returns strict booleans
- Wired APScheduler `escalate_overdue` sweep into the app lifespan (gated by `ECLMS_SCHEDULER_ENABLED`)
- Added durable event transport: Redis Streams `RedisBroker` + `DurableEventBus` (at-least-once, crash recovery); default `memory` transport
- Added deps `simpleeval`, `apscheduler`, `redis`; 9 new evaluator + 3 durable-event tests
- 65 tests passing; ruff clean


### Session note (CI)

- Added GitHub Actions CI at `.github/workflows/ci.yml`: backend (ruff + pytest) and frontend (npm build) on push/PR
- Updated `DEPLOYMENT.md` verification section and `PROJECT_STATE.md`

### Session note (Docker Compose stack)

- Added Dockerfile (Python 3.11-slim, pip install -e ., alembic upgrade head then uvicorn) and .dockerignore
- Added docker-compose.yml: api (8000), db (Postgres 16, host 5433, named volume), redis (Redis 7, 6379), healthchecks
- Verified live: image builds, stack boots healthy, login/contract/conditional workflow smoke on containerized Postgres
- Verified live Redis durable transport: publish -> drain -> deliver -> ack via DurableEventBus + RedisBroker
- Updated DEPLOYMENT.md (section 6a compose stack, migration chain through ebe4b66ae720) and PROJECT_STATE.md

### Session note (Integration module - webhook delivery)

- Added organization_id to metadata on all published events (contracts, workflow, documents)
- Implemented WebhookDeliveryService in backend/modules/integration/application/webhook_service.py:
  subscribes to event bus, matches active subscriptions (exact or *), POSTs HMAC-SHA256 signed
  payloads (X-ECLMS-Signature) via httpx, records every attempt
- Added WebhookDeliveryModel + migration 6dcb594622ee (webhook_deliveries table)
- NotificationRepository.list_active_for_event; integration module wired
- Promoted httpx to runtime dependency
- 7 new tests (test_integration.py); 72 passing, ruff clean
- Live-verified on compose stack: contract.created webhook delivered with status 200 (and error path)

### Session note (Secrets & HTTPS hardening)

- Settings fail-fast: production/staging reject default or short ECLMS_JWT_SECRET
- SecurityHeadersMiddleware: nosniff, frame deny, referrer-policy, permissions-policy, HSTS behind proxy
- Caddy TLS reverse proxy in compose (Caddyfile), internal CA locally / Let's Encrypt in prod
- Dockerfile: non-root eclms user, uvicorn --proxy-headers --no-server-header
- 6 new hardening tests; 78 passing, ruff clean
- Live-verified: HTTPS login via Caddy 200 + hardening headers, all compose services healthy

### Session note (Frontend wiring for Notifications & Webhooks)

- Added Notifications & Webhooks UI tab to `frontend/src/App.tsx`
- Navbar notification badge displaying unread count with a quick-switch button
- In-app notification feed with unread highlighting and click-to-mark-read (`POST /api/v1/notifications/{id}/read`)
- Webhook subscription form (URL, event type picker, signing secret) and active subscriptions listing
- Verified against live backend; `npm run build` passes, `oxlint` clean

### Session note (Escalation Scheduler — Live E2E)

- Added SLA timeout (`timeout_hours=24`, `escalation_role='ADMIN'`) to default approval workflow's Legal Review step
- Enabled APScheduler in `docker-compose.yml` (`ECLMS_SCHEDULER_ENABLED=true`, `ECLMS_ESCALATION_INTERVAL_MINUTES=1`)
- Live verified against containerized Postgres + API:
  - Created contract and started `contract-approval` workflow
  - Backdated Legal Review step's `started_at` in Postgres beyond SLA
  - APScheduler `run_sweep` automatically triggered on schedule
  - Step transitioned to `ESCALATED`, setting `escalated_at` and `escalation_role='ADMIN'`
  - ADMIN called `/api/v1/workflows/{id}/transition` to approve the escalated step, advancing the workflow to `Finance Review`
- All 78 pytest tests pass, ruff clean

### Session note (Audit Trail API & Frontend View)

- Added `GET /api/v1/audit` endpoint in `AuditModule` (`backend/modules/audit/interfaces/routes.py`), guarded by `user.manage` permission and backed by `SqlAuditStore`
- Added "Audit Trail" tab to the frontend SPA (`frontend/src/App.tsx`), displaying immutable audit records
- Live verified against containerized API (`/api/v1/audit` returning 11 audit records); `npm run build` passes, ruff clean

### Session note (Observability & Prometheus Metrics)

- Added `MetricsMiddleware` (`backend/api/middleware/metrics.py`) tracking total requests and errors
- Added Prometheus exposition endpoint (`GET /metrics`) returning plain text metrics (`eclms_uptime_seconds`, `eclms_http_requests_total`, `eclms_http_errors_total`)
- All 79 pytest tests pass, ruff clean; live-verified against containerized API (`GET /metrics` returning valid Prometheus format)

### Session note (External Integrations — SMTP Email Delivery)

- Added SMTP settings to `Settings` (`ECLMS_EMAIL_ENABLED`, `ECLMS_SMTP_HOST`, `ECLMS_SMTP_PORT`, `ECLMS_SMTP_USER`, `ECLMS_SMTP_PASSWORD`, `ECLMS_SMTP_FROM`)
- Implemented `EmailDeliveryService` (`backend/modules/integration/application/email_service.py`) listening to domain events and dispatching notifications via `smtplib` asynchronously
- Wired into `IntegrationModule`; added 2 tests in `tests/test_email.py`
- All **81 pytest tests pass**, ruff clean

### Session note (External Integrations — S3 Object Storage Provider)

- Added `S3StorageProvider` (`infrastructure/storage/s3.py`) implementing the `StorageProvider` contract via `boto3` (AWS S3 + S3-compatible/MinIO/LocalStack); blocking calls run in thread pool via `asyncio.to_thread`
- Added `get_storage_provider()` factory selecting provider by `ECLMS_STORAGE_BACKEND`; `DocumentsModule` now uses it
- Added S3 settings (`ECLMS_STORAGE_BACKEND`, `ECLMS_S3_BUCKET`, `ECLMS_S3_REGION`, `ECLMS_S3_ENDPOINT_URL`, `ECLMS_S3_ACCESS_KEY_ID`, `ECLMS_S3_SECRET_ACCESS_KEY`); `boto3>=1.34` runtime dep
- Added 3 tests in `tests/test_storage_s3.py` (round-trip via Stubber, missing-key StorageError, factory)
- All **84 pytest tests pass**, ruff clean; live-verified document upload via factory on compose stack

### Session note (Advanced Auth — ABAC/RBAC Policies + OIDC Integration)

- Added ABAC policy engine (`backend/api/abac.py`): `Actor`, `PolicyContext`, `Policy`, `PolicyEngine`, and reusable predicates (`is_resource_owner`, `is_same_organization`, `time_between`, `action_is`, `all_of`, `any_of`). `PolicyEngine` returns `True` when no policies are registered (RBAC-only fallthrough); when policies exist it is implicit-deny with explicit `DENY` taking precedence over `ALLOW`.
- Moved the `Actor` dataclass into `backend/api/abac.py` and had `backend/api/security.py` import it, breaking the `abac` ⇄ `security` circular import.
- Extended `backend/api/security.py` with `require_abac(...)` (RBAC permission + optional ABAC evaluation) and `require_abac_only(...)` guards; both build a `PolicyContext` (actor, resource, action, environment) and evaluate the registered policy engine.
- Registered `'abac.engine'` → `PolicyEngine()` in `CommonModule.register_services`.
- Added OIDC settings to `Settings` (`ECLMS_OIDC_ENABLED`, `ECLMS_OIDC_ISSUER`, `ECLMS_OIDC_CLIENT_ID`, `ECLMS_OIDC_CLIENT_SECRET`, `ECLMS_OIDC_SCOPES`, `ECLMS_OIDC_REDIRECT_URI`, `ECLMS_OIDC_DEFAULT_ORG`).
- Added OIDC flow to `AuthService` (`backend/modules/identity/application/auth_service.py`): `oidc_authorization_url()`, `oidc_exchange_code()`, `_fetch_oidc_userinfo()`, `_upsert_oidc_user()`. New IdP users are created **inactive** (admin must activate + assign roles) with username `oidc_<sub[:8]>` and a random password, honoring `oidc_default_org`.
- Added OIDC routes in `backend/modules/identity/interfaces/routes.py`: `GET /api/v1/identity/auth/oidc/start` (redirect to IdP) and `GET /auth/oidc/callback` (exchange code → internal JWT); IdP transport errors map to `OIDC_EXCHANGE_FAILED`.
- Fixed `httpx` import (was referenced without import in routes), unused `id_token` var, redundant local imports, and the `hasattr` guard in `_upsert_oidc_user`.
- Tests: 7 new in `tests/test_abac.py` (engine semantics, predicates, no-policy fallthrough); 6 new in `tests/test_oidc.py` (auth URL, exchange happy path, insufficient claims, no access token, disabled OIDC). All **97 pytest tests pass**, ruff clean.

### Session note (Workflow & Multi-Step Approvals — Executive Sign-off)

- Added `contract-approval-executive` (`EXECUTIVE_APPROVAL_WORKFLOW_ID`) workflow definition to `backend/modules/workflow/domain/definitions.py`: **Legal Review** (CONTRACT_MANAGER, 24h SLA, escalate to ADMIN) → **Executive Sign-off** (ADMIN, 48h SLA, escalate to ADMIN). Registered in `WORKFLOW_DEFINITIONS`.
- On final approval, `WorkflowService.decide` now auto-transitions the contract through `APPROVED → EXECUTED → ACTIVE` when the workflow definition is `contract-approval-executive`; other definitions keep the existing `APPROVED` terminal state.
- The full lifecycle now matches the requested multi-step flow: **Draft → Legal Review → Executive Sign-off → Active**, with approval/rejection decisions per step and automated SLA escalation (sweep + scheduler) available to every step via `timeout_hours`/`escalation_role`.
- Added 2 tests in `tests/test_executive_workflow.py`: full executive flow (Draft→…→Active) and automated escalation sweep with admin resolution. All **103 pytest tests pass**, ruff clean.
- Live-verified on the compose stack: created contract (DRAFT) → started executive workflow (RUNNING/Legal Review) → manager approved Legal Review (contract UNDER_REVIEW) → admin approved Executive Sign-off (workflow APPROVED, contract **ACTIVE**); backdated the SLA and confirmed the sweep escalates the pending step (status ESCALATED, `escalated_at` set).

---

## Session 2026-08-07 — Obligation Tracking Module

### Achievements

- Created the `Obligations` module under `backend/modules/obligations/` following the established modular-monolith pattern (domain / application / interfaces).
- Domain (`backend/modules/obligations/domain/obligation.py`): `ContractObligation` (`PENDING`/`IN_PROGRESS`/`COMPLETED`/`OVERDUE`), `ObligationMilestone` (`PENDING`/`REACHED`), with `assign()`, `start()`, `complete()`, `mark_overdue()`, `reach_milestone()`. A timezone-guard normalizes naive SQLite datetimes before overdue comparison (`_aware`).
- Persistence: `ObligationModel` + `ObligationMilestoneModel` (`infrastructure/database/models/obligations.py`), `SqlObligationRepository`, Alembic migration `c7e8f9a0b1c2` (`obligations`).
- Service: `ObligationService` (create_obligation, add_milestone, assign, start, complete, list_for_contract, mark_overdue sweep), publishing `obligation.*` events.
- API: `/api/v1/obligations`, `/{{id}}/milestones`, `/{{id}}/assign`, `/{{id}}/start`, `/{{id}}/complete`, `/{{id}}/milestones/{mid}/reach`.
- Fixed a timezone bug where SQLite returns naive datetimes, causing `mark_overdue` overdue comparison errors.
- Restored `SqlObligationRepository` to `infrastructure/database/repositories/__init__.py` (it had been accidentally dropped during module wiring).
- Registered module/constants/permissions; tests in `tests/test_obligations.py` (7 tests). Suite grew to **110 passing tests**, ruff clean.

---

## Session 2026-08-07 (continued) — Financial Module (Commitments & Payments)

### Session log

- Created the `Finances` module under `backend/modules/finances/` (domain + infrastructure + application + interfaces).
- Domain (`backend/modules/finances/domain/finance.py`): `FinanceCommitment` (`OPEN`/`PAID`/`CANCELLED`) and `FinancePayment` (`SCHEDULED`/`PAID`/`OVERDUE`/`CANCELLED`) with `mark_paid()`, `cancel()`, `mark_overdue()`, and a timezone-aware `_aware` helper for naive SQLite datetimes.
- Persistence: `FinanceCommitmentModel` / `FinancePaymentModel` (`infrastructure/database/models/finances.py`), `SqlFinanceRepository` (save/get, `find_overdue_payments`, `list_commitments_for_contract` with `limit`/`offset`, `list_all_payments`), Alembic migration `d1e2f3a4b5c6` (`finances`).
- Service: `FinanceService` (create_commitment, create_payment, mark_paid, cancel_payment, list_commitments, list_all_commitments, list_payments, list_all_payments, sweep_overdue), publishing `finance.*` events.
- API: `/api/v1/finances/commitments`, `/commitments/{cid}/payments`, `/payments/{pid}/pay`, `/payments/{pid}/cancel`, `/sweep-overdue`, `/payments`.
- Registered module in `registry.py` + `shared/constants.py` (`MODULE_FINANCES`); added `finance.create/read/update` permissions to `seed.py` (CONTRACT_MANAGER + ADMIN, VIEWER read).
- Fixed an integration bug: `SqlFinanceRepository.get_payment_by_id` did not restore `status`/`paid_at`/timestamps from the persisted model, so a reloaded payment always defaulted to `SCHEDULED`. This caused a cancelled payment to be payable again. Restored full domain state from the model on load.
- Tests: `tests/test_finances.py` (6 tests covering schedules, paying, cancelling, sweeping overdue, and the invalid-transition guard). Suite now at **116 passing tests**, ruff clean.
- Rebuilt and restarted the compose `api` container to pick up the finance module.

### Session note (ABAC demo route + policies)

- Registered demo ABAC policy `contract-read-owner` (`backend/modules/common/__init__.py::register_demo_contract_read_policy`) on the `abac.engine` service: allows the `contract:read` action only for the contract's owner via `action_is('contract:read')` + `is_resource_owner`.
- Wired the existing demo route `GET /api/v1/contracts/{id}/abac-demo` to opt into `require_abac(request, resource=contract, action='contract:read')`, proving RBAC-granted users are still subject to ABAC denial.
- Integration tests in `tests/test_abac_route.py` (3): owner granted, non-owner VIEWER denied (`FORBIDDEN`), unauthenticated → `UNAUTHORIZED`; engine unit tests in `tests/test_abac.py` (7).
- Suite at **116 passing tests** (ABAC route tests already part of the count), ruff clean; live-verified via `/abac-demo` on the compose stack.
- Closed out the remaining roadmap Phases 0–3; next is Phase 4 (Intelligence & Optimization).

### Session note (Phase 4 start — Analytics & Reporting Module)

- New `Reporting` module (`backend/modules/reporting/`) — first slice of roadmap Phase 4 (Intelligence & Optimization, module priority #10) per `docs/26_Roadmap.md` / `docs/22_Reporting_Analytics.md`.
- `SqlReportingRepository` (`infrastructure/database/repositories/reporting_repository.py`) computes org-scoped aggregates over existing tables — **no new schema/migration**:
  - Contracts: total, by-state, active, avg lifecycle days
  - Workflows: total, by-status, avg step approval time (scoped via owning contract join)
  - Obligations: total, by-status, overdue, SLA compliance rate
  - Finances: total value, paid, payment completion rate, overdue payments, active exposure
- `ReportingService.full_report` composes an overview; `GET /api/v1/reporting/overview` guarded by new `reporting.read` permission (seeded ADMIN/CONTRACT_MANAGER/VIEWER), org-scoped (ADR-003). Reports are derived views and never mutate operational data (RPT-022).
- Registered in `registry.py` + `shared/constants.py` (`MODULE_REPORTING`) + `repositories/__init__.py` (`SqlReportingRepository`).
- Fixed `select.avg` → `func.avg` and an unused-var lint while building. Tests: `tests/test_reporting.py` (6). Suite now at **122 passing tests**, ruff clean; compose `api` container rebuilt and live-started.

### Session note (Phase 4 continue — Frontend Analytics & Reporting tab)

- Added "Analytics & Reporting" tab to the SPA (`frontend/src/App.tsx`): `BarChart3` icon import, `reporting` in the `activeTab` union, `reporting` state + `fetchReporting()` hitting `GET /api/v1/reporting/overview`, wired into the auth effect, nav entry, and a metric-card block (Contracts, Workflows, Obligations, Finances) with Refresh + loading state.
- Fixed a `fontWeight 700` typo (missing colon) in the workflow card while wiring. `npm run build` passes clean.

### Session note (Phase 4 continue — Intelligence Module: Risk, Clauses, Search, Alerts)

- New `Intelligence` module (`backend/modules/intelligence/`) implementing the four remaining Phase 4 increments as read-only, org-scoped (ADR-003) services:
  - **Risk Detection Rules Engine**: `RiskAssessment.calculate` (0-100 score + LOW/MEDIUM/HIGH/CRITICAL from summed impacts and worst factor severity); `RiskService.assess_contract_risk` (past expiry → `CONTRACT_PAST_EXPIRY` CRITICAL, expiring ≤30d → `CONTRACT_EXPIRING_SOON` HIGH, overdue obligations → `OVERDUE_OBLIGATIONS`, overdue payments → `OVERDUE_PAYMENTS`); `assess_organization_risk` portfolio overview.
  - **Clause Analysis**: rule-based typed-clause extraction (LIABILITY / TERMINATION / INDEMNIFICATION / GOVERNING_LAW / CONFIDENTIALITY / PAYMENT) from the active contract-version text with per-clause risk ratings and missing-recommended-types output.
  - **Semantic Search**: feature-hashed deterministic embeddings (no external AI API) + org-scoped `InMemoryVectorIndex`; `SemanticSearchService` lazily rebuilds per org keyed on active-version fingerprints; cosine-similarity ranking.
  - **Predictive Alerts**: `PredictiveAlertsService.generate_alerts` → `contract.expired` / `contract.expiring` / `obligation.due` / `payment.due` / `contract.high_risk` across the portfolio.
- Contracts API now accepts optional `content` on create/update (snapshotted into the immutable version) and `list_versions` returns `content` — enables text-based analysis end-to-end.
- Routes: `GET /api/v1/intelligence/risk/contracts/{id}`, `/risk/overview`, `/clauses/{id}`, `/search?q=&limit=`, `/alerts` — all guarded by new `intelligence.read` permission (seeded for ADMIN/CONTRACT_MANAGER/VIEWER).
- Fixed `seed_roles_permissions` to converge existing roles to new permission codes (previously new permissions only attached to freshly created roles), so pre-existing DBs gain `intelligence.read` on restart.
- Tests: `tests/test_intelligence.py` (17: embeddings/cosine, thresholds, vector-index scoping, auth, risk factors incl. expiry/obligations/payments, org overview, clause extraction, search ranking, predictive alerts). Suite now at **139 passing tests**, ruff clean.
- Rebuilt compose `api`; live-verified `/intelligence/risk/overview` (12 contracts assessed), `/alerts`, `/search`, and `/clauses` against containerized Postgres.

### Session note (Phase 4 continue - AI-Assisted Contract Review)

- Added a `ReviewProvider` abstraction (`backend/modules/intelligence/application/review_provider.py`) mirroring the storage-provider factory pattern:
  - `RuleBasedReviewProvider` (default, deterministic, zero deps): unlimited liability  CRITICAL; uncapped liability, one-sided indemnification, short termination notice (`7/14/30` days), missing governing law, missing confidentiality, extended payment terms (`net 60/90`) various severities.
  - `LlmReviewProvider` (optional, OpenAI-compatible `chat/completions`): constructs a JSON-array system prompt, POSTs with Bearer auth, `_parse_findings` extracts the array (tolerant of JSON fences), and degrades to `[]` on missing URL / transport / parse errors. Injectable `http_client` for tests (httpx `MockTransport`).
- `ReviewService.review_contract(contract_id, *, organization_id)` loads the active version's `content`, runs the configured provider, computes `overall_risk_level` via `_worst_level` and `high_or_critical_count` (`application/review_service.py`, `domain/review.py`).
- `IntelligenceModule` builds the provider from `ECLMS_AI_REVIEW_PROVIDER` (`rules` default, `llm` for the external provider). New settings: `ai_review_provider`, `llm_api_url`, `llm_api_key` (repr=False), `llm_model`, `llm_timeout_seconds`.
- New route: `GET /api/v1/intelligence/review/{contract_id}` guarded by `intelligence.read`.
- Tests: 7 new in `tests/test_intelligence.py` (rule-based risky/clean, empty content, LLM JSON parse, LLM endpoint call + auth header via `httpx.MockTransport`, graceful failure on 500, auth-guarded route). Suite now at **146 passing tests**, ruff clean.
- Note: the termination rule matches `'14 days'`/`'30 days'` as substrings, so a payment term like `net 30 days` can be mis-flagged as short notice. Worked around in tests; logged as a hardening follow-up.

### Session note (rebuild + frontend)

- Rebuilt the compose `api` container (`docker compose up -d --build api`, healthy) so the new `intelligence.review` service/route is live.
- Live-verified `POST /api/v1/contracts` (with `content`) + `GET /api/v1/intelligence/review/{id}` against containerized Postgres: returned `provider=rules`, `overall_risk_level=CRITICAL`, `high_or_critical_count=1`, first finding "Unlimited liability"/CRITICAL.
- Started the frontend dev server detached (`frontend/dev-server.log`); Vite ready on `http://localhost:3000/`, proxy forwarding `/api` to `localhost:8000` (FastAPI reachable through the proxy).
- Docs updated: `PROJECT_STATE.md` + `SESSION_LOG.md` (#146, AI review increment).

### Session note (Frontend Productization - Finances, Obligations, Contract Workspace)

- Added self-contained tab components in `frontend/src/components/` (each takes `headers` and manages its own data + errors/loading/empty states):
  - `FinancesTab.tsx`: commitments list with expandable payment schedules; create commitment (contract/description/amount/currency); add installment; pay/cancel payment; admin "Sweep Overdue".
  - `ObligationsTab.tsx`: obligations list with status filter and overdue highlight; create obligation (contract/description/due date); complete/cancel; admin "Sweep Overdue".
  - `ContractPanel.tsx`: contract workspace with inline edit (title/ref/counterparty/content -> `PATCH` new version), state transition, immutable versions list, document upload (multipart)/list, plus inline AI review (`/intelligence/review/{id}`) and clause analysis (`/intelligence/clauses/{id}`).
- `App.tsx`: new `Finance`/`Obligations` tabs (Wallet/ClipboardCheck icons), "Manage" button opens the panel, tab union + nav updated.
- `npm run build` passes; oxlint clean (1 pre-existing effect-dep warning).

### Session note (Backend Hardening + rules fix)

- New `backend/api/middleware/limits.py`: `BodySizeLimitMiddleware` (HTTP 413 `PAYLOAD_TOO_LARGE` on oversized `Content-Length`, no body consumption) + `RateLimitMiddleware` (in-process fixed window keyed on client IP / `X-Forwarded-For` behind trusted proxy; HTTP 429 `RATE_LIMITED`).
- Wired into `create_app` under `ECLMS_RATE_LIMIT_ENABLED` (opt-in)/`rate_limit_requests`/`rate_limit_window_seconds`/`max_request_bytes`; documented in `.env.example`.
- Fixed rules-engine short-notice false positive: termination uses adjacency regex `\b(?:7|14|30)\s*-?\s*days?\s+notice\b` so `net 30 days` payment terms no longer flag MEDIUM termination.
- Tests: `tests/test_hardening_middleware.py` (4) + `test_termination_rule_ignores_payment_day_terms`. Suite now at **151 passing tests**, ruff clean.

### Session note (Frontend & Export Polish - Download, CSV, Provider Selector, Filters)

- **Document download**: `GET /api/v1/documents/{id}/download` streams the latest version's bytes (via `DocumentService.get_content`, org-scoped) with a `Content-Disposition` filename. New `frontend/src/download.ts` `downloadAuthenticated(url, headers, filename)` drives a per-row Download button in the contract workspace.
- **CSV export**: `GET /api/v1/reporting/export.csv` concatenates contracts, obligations, payments into one CSV (`reporting.service list_all` / `list_all_payments`, limit 100000); export buttons in Analytics, Finances, and Obligations tabs.
- **Per-request review provider**: `/api/v1/intelligence/review/{id}?provider=rules|llm` via `_select_provider` + `ReviewService.review_contract(provider=)`; contract workspace gained a rules/LLM selector, plus an LLM-fallback hint when provider is LLM and no findings are returned.
- **List filters**: contracts table in `App.tsx` (search + state filter + filtered count), obligations (status + text filter), finances commitments (text filter + search box).
- **Production hardening defaults**: compose `api` now sets `ECLMS_RATE_LIMIT_ENABLED=true` (300/60s), `MAX_REQUEST_BYTES=20971520`, `ECLMS_TRUSTED_PROXY=true`; audit list clamps limit to ≤200 and offset ≥0.
- Tests: `tests/test_report_endpoints.py` (3: CSV export, document download, provider selection). Suite now at **154 passing tests**, ruff clean; `npm run build` passes.
- Rebuilt compose `api` (healthy); live-verified `GET /api/v1/reporting/export.csv` returns real rows and `?provider=rules` returns `provider:rules` against containerized Postgres (login via `POST /api/v1/identity/auth/login` admin/admin). Docs updated in `PROJECT_STATE.md` + this file.

### Session note (LLM Configuration UX & E2E Integration Smoke Test)

- **LLM Settings UX**: Created `SettingsModal.tsx` in frontend and `GET/PATCH /api/v1/config/llm-settings` endpoints in backend; accessible via "LLM Settings" button in the top navbar.
- **E2E Smoke Test**: Added `tests/test_e2e_lifecycle.py` verifying full admin login, contract creation, AI rules review, clause parsing, obligations, financial commitments, multi-step workflow transitions, and reporting CSV export.
- **Suite Status**: **155 passing tests (pytest)**, ruff clean, `npm run build` passes.

### Session note (Observability & Performance Polish - Histogram + Pagination)

- **Metrics upgrade**: `backend/api/middleware/metrics.py` now tracks `eclms_http_request_duration_seconds` (fixed buckets + `_sum`/`_count`), per-status-class counters (`eclms_http_requests_by_status{status="200"}`), and keeps existing uptime/requests/errors. Tests added in `tests/test_metrics.py`.
- **List pagination**: `GET /api/v1/contracts` and `GET /api/v1/obligations` accept `limit` (clamped to 1..200) + `offset`; contracts returns `{items, total, limit, offset}` (new `ContractRepository.count` + `ContractService.count_contracts`). Frontend contract fetch uses `?limit=200`.
- Rebuilt compose `api`; live-verified `/metrics` now emits the histogram buckets and `eclms_http_requests_by_status`. Suite now at **159 passing tests**, ruff clean, `npm run build` passes.

### Session note (Webhook Reliability - Retry with Backoff)

- `WebhookDeliveryService` now retries transient failures with exponential backoff: `_deliver_with_retries` loops up to `MAX_ATTEMPTS=3` on HTTP 429/500/502/503/504 or network errors, sleeping `min(0.5 * 2^(n-1), 8s)` between attempts, then records the final status/error once.
- Non-retryable 4xx/2xx deliver immediately; `max_attempts`/backoff are injectable for tests.
- Tests: 3 new in `tests/test_integration.py` (FakeClient gained `status_sequence`/`raise_count`); existing failure tests pinned to `max_attempts=1`. Suite now at **162 passing tests**, ruff clean; compose API rebuilt & healthy.

### Session note (DB Pool Resilience - pre-ping, recycle, pool gauges)

- Settings `database_pool_pre_ping` (True) + `database_pool_recycle` (3600s) wired into the async engine for PostgreSQL URLs in `infrastructure/database/session.py`; documented in `.env.example`.
- Added `database_pool_stats()` exposing `checked_out`/`size`/`overflow` from the SQLAlchemy pool; `/health` returns it as `database_pool` (null when engine is unpooled e.g. SQLite).
- Tests: `test_health_exposes_database_pool_stats` (relaxed overflow semantics — SQLAlchemy can report negative over-reservation). Suite now at **163 passing tests**, ruff clean; live-verified `/health` pool stats (size 10) against recomposed API.

### Session note (System Health Tab in Frontend)

- New `frontend/src/components/SystemHealthTab.tsx`: `/health` readiness panel (app/version/database, DB pool gauges from the new `database_pool` block, per-module status pills), raw Prometheus `/metrics` in a monospace terminal view, and a security-posture bullets card.
- Added a "System Health" nav tab (`id: 'system'`, Activity icon) to `App.tsx`, with the tab union extended. No backend changes.
- `npm run build` passes; live-verified `/health` (ok/ok, pool size 10) and `/api/v1/contracts` through the frontend proxy (200).

### Session note (Production Compose Profile)

- New `docker-compose.prod.yml` overlay (activated via `--profile production`): resource limits/reservations per service (api: 512M/1 CPU, db: 1024M, redis 256M + AOF persistence, keycloak 1024M + JVM caps, proxy 256M), multi-replica-ready defaults, and a switched `ECLMS_EVENT_TRANSPORT=redis` for durable multi-instance deployments.
- Compose config validates cleanly (`docker compose --profile production config`); no backend/test changes required.

### Session note (Event-Driven In-App Notifications + Mark All Read)

The in-app notification system was previously a stub (`NotificationService.handle_event` did `pass`), so domain events never surfaced in the Notifications tab. This session activated the roadmap Notification Module (#8) delivery layer:

- **Routing**: `NotificationService.ROUTES` maps domain events (`workflow.started`, `workflow.step_decided`, `workflow.paused`, `workflow.resumed`, `workflow.step_delegated`, `workflow.step_escalated`, `contract.created`, `contract.state_changed`, `document.uploaded`, `obligation.created/completed/overdue`, `finance.payment_overdue`) to subject/body templates plus an org-scoped audience of roles (ADMIN/CONTRACT_MANAGER); the acting user is always included too. `handle_event` formats templates from event payloads (with a safe fallback) and persists `channel='in_app'` notifications per recipient.
- **Repository fixes**: `Notification` list now preserves `is_read`/`created_at` when mapping rows back to domain objects (previously always surfaced as unread); new `count_unread`, `mark_all_read` (bulk update), and `SqlUserRepository.list_by_role_in_org`.
- **API**: `GET /api/v1/notifications` now includes `unread_count`; new `POST /api/v1/notifications/read-all` returns `{marked}` (guarded by `contract.read`).
- **Frontend**: Notifications tab gains a "Mark All Read" button (shown only when unread exist) that calls the new endpoint and clears the badge.
- **Tests**: 3 new in `tests/test_notifications.py` (routed event reaches the audience via the live bus; unrouted events skipped; API contract-create fires a notification then read-all clears unread).
- Suite now at **166 passing tests**, ruff clean, `npm run build` passes; compose API rebuilt & healthy; live-verified contract creation yields an unread "Contract Created" in-app notification and `read-all` resets `unread_count` to 0.

### Session note (Webhook Delivery History API + Notifications UI)

Delivery records were already persisted (`webhook_deliveries`) by the retry/backoff work but were never readable. This session surfaced them:

- **Repository**: `NotificationRepository.list_deliveries` (newest-first, `limit`/`offset`) and `delivery_summary` (`total`/`succeeded`/`failed` = status None or >=300).
- **Service**: `list_subscription_deliveries(org, sub_id, limit, offset)` with org-scoped `_require_subscription` (unknown sub -> not-found envelope).
- **API**: `GET /api/v1/notifications/webhooks/{webhook_id}/deliveries?limit&offset` (limit clamped 1..200, guarded by `user.manage`).
- **Frontend**: Notifications tab now fetches delivery history per webhook on load and shows `Deliveries: N` + red/green `Failed: M` with a per-webhook Refresh button.
- Tests: `test_webhook_deliveries_endpoint` seeds a recorded failure via the delivery service then asserts summary + item status/error + 404 envelope for an unknown sub. Suite now at **167 passing tests**, ruff clean; `npm run build` (only the pre-existing oxlint warning); compose API rebuilt & healthy; live-verified a real subscription hitting `httpbin.org/status/500` reports `total=1 failed=1 status=500`.

### Session note (Email Integration - Role-Based Delivery, History API + UI)

The email service was a stub: only 3 event types, hardcoded to `admin@eclms.local`, nothing persisted. This session turned it into a first-class integration mirroring webhook delivery:

- **Service rewrite** (`backend/modules/integration/application/email_service.py`): `EMAIL_ROUTES` reuses the notification router's templates + org-scoped role audiences; `handle_event` resolves recipients via `SqlUserRepository.list_by_role_in_org` (+ actor), formats `[ECLMS]`-prefixed subjects, sends via `smtplib` in a thread pool (mock when `smtp_host=localhost` without a user), and records every attempt; `send_email` returns `{success, error}`.
- **Persistence**: new `EmailDeliveryModel` (`email_deliveries`: org, recipient, event_type, subject, body, `status` sent/failed, error, delivered_at) in `infrastructure/database/models/integration.py`; `NotificationRepository.list_email_deliveries` (newest-first, paginated) + `email_delivery_summary` (`total`/`sent`/`failed`); org-scoped `NotificationService.list_email_deliveries`.
- **API**: `GET /api/v1/notifications/email/deliveries?limit&offset` (limit clamped 1..200, `user.manage` guard).
- **Wiring**: `IntegrationModule.register_services` injects the identity user repository + notification repository into the email service; dev compose now sets `ECLMS_EMAIL_ENABLED=true` (mock SMTP).
- **Frontend**: Notifications tab gains an "Email Deliveries" panel — total/sent/failed counts plus a recent-deliveries list (subject, recipient, event, error) with Refresh.
- **Tests**: `tests/test_email.py` rewritten (audience resolution, unrouted skip, disabled, SMTP-failure record, route coverage) + `test_email_deliveries_endpoint` (recorded failure surfaced with summary + paging). Suite now at **171 passing tests**, ruff clean; `npm run build` passes; compose API rebuilt & healthy; live-verified contract creation records `[ECLMS] Contract Created` emails as `sent` to `admin@eclms.local` and `mgr1@eclms.local` with mock SMTP log lines.
## Session 2026-08-14 — Release Hardening Started

Aligned the next project state with the Project Constitution, product vision, architecture, roadmap, and current implementation evidence.

### Achievements

- Confirmed the previous implementation state was broad but largely uncommitted on `main`.
- Confirmed the full backend suite was not hanging: the prior failure was a Windows pytest global-temp-directory permission error.
- Added `quality/Release_Readiness.md` as the explicit release gate for repository integrity, automated verification, business lifecycle evidence, and operational/security evidence.
- Added a workspace-local `tmp_path` fixture in `tests/conftest.py`, removing dependence on inaccessible global pytest temp directories.
- Added `.gitignore` rules for runtime contract storage and local SQLite databases.
- Verification: **197 pytest tests passed**, Ruff passed, `npm run lint` passed, and `npm run build` passed.

### Decision

The next state is **Phase 5 — Release Hardening**. Feature expansion is paused until the implementation can be reproduced from a clean checkout, pass the release gate, and demonstrate the operational and integration properties required by the architecture.

### Next Focus

- Consolidate the working tree into a release branch/commit sequence.
- Profile the approximately three-minute test suite and remove avoidable setup cost.
- Resolve the frontend hook warning.
- Run clean deployment, migration, backup/restore, and external-provider acceptance checks.
- Choose and implement one production-grade ERP/accounting connector; record the digital-signature decision.

---
