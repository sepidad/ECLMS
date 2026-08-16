# Changelog

All notable changes to ECLMS are documented here. Dates are YYYY-MM-DD.

## 2026-08-16 — Phase 6 slice 1: template-backed preparation

- New `POST /api/v1/contracts/from-template`: validates the chosen template,
  rejects unknown fields, enforces required commercial fields, and renders the
  values into the initial contract version with a schedule of commercial data.
- Contracts now record template provenance: `template_key` and structured
  field values (new columns + Alembic migration `b7c8d9e0f1a2`), returned by
  `GET /contracts/{id}` so commercial facts stay searchable and reportable.
- Frontend: "Use this template" opens a guided preparation form with dynamic
  fields, tags, and a required-guarantees reminder.
- Template library expanded to five approved templates (general service,
  procurement, construction/works, consulting, maintenance/SLA).
- Fixed a latent DOCX export crash: rich content containing a list hit
  undefined list-state variables in `add_rich_docx_content`.
- Ruff fully clean again (import sorting, stale noqa, image-error suppression);
  B008 ignored globally as a known FastAPI idiom.
- Release hardening (2026-08-15): backup/restore drill executed and recorded
  (Gate D closed), ADR-006 defers digital signatures, README/CHANGELOG/LICENSE
  added; suite grew to **209 passing tests**.

## 2026-08-14 — Release hardening & document exports

- Started Phase 5 (Release Hardening): release gate checklist
  (`quality/Release_Readiness.md`), Windows-safe pytest temp handling,
  `.gitignore` hardening; 197 tests green, ruff clean.
- Verified clean-clone build and deployment: full stack (API, PostgreSQL,
  Redis, Keycloak, Caddy) healthy with HTTPS.
- Organization Word templates: template-independent contract exports, PDF
  letterhead and footer placement, rich contract text editing with table
  selection fixes.

## 2026-08-09 — Multi-channel delivery & data import

- SMS notifications (mock and HTTP providers).
- ERP/accounting connector scaffold (dry-run mode).
- CSV data import engine: contracts, obligations, commitments.
- Audit CSV export. Suite reached 194 tests.

## 2026-08-08 — Notification delivery history

- Event-driven in-app notifications with mark-all-read.
- Webhook delivery history API and UI.
- Role-based email delivery with history API and UI.

## 2026-08-07 — Obligations, finances, reporting, intelligence

- Obligations module (tracking, alerts).
- Finances module (commitments, payments).
- Executive sign-off workflow; ABAC demo route.
- Reporting module: dashboards, CSV export, filters, pagination.
- Intelligence module: risk scoring, clause analysis, semantic search.
- AI-assisted contract review (rules + LLM providers) with settings UI and
  E2E lifecycle test.
- Frontend productization: Finances, Obligations, Contract Panel tabs.
- Hardening: rate limiting, body-size limits, latency histograms, DB pool
  gauges, webhook retry with backoff, System Health tab, production compose
  profile.

## 2026-08-06 — Frontend, notifications, CI, security

- React 19 + Vite frontend SPA.
- Notifications module: in-app, webhooks with HMAC signing.
- GitHub Actions CI (backend + frontend), Docker Compose stacks.
- Security hardening: simpleeval replaces eval, secrets validation,
  security headers, Caddy TLS.
- Durable Redis event bus; APScheduler escalation (live E2E).
- Audit API + UI; Prometheus metrics; SMTP email; S3 storage provider;
  ABAC engine; OIDC support.

## 2026-08-04 — Workflow engine expansion (Phase 2)

- Parallel approval groups, conditional steps, pause/resume, delegation.
- Escalation with SLA sweep scheduler.
- `DEPLOYMENT.md` written.

## 2026-08-01 — Core bootstrap (Phase 3)

- FastAPI modular monolith: core kernel, module container, API envelope,
  trace-id correlation, error handling.
- Identity (JWT auth), Contracts aggregate + lifecycle, Audit foundation.
- Persistence via SQLAlchemy + Alembic; contract versioning.
- RBAC with seeded roles; route-level permission guards.
- PostgreSQL live run via Docker with migrations and smoke test.
- Organization scoping (multi-tenancy).

## 2026-07-02 — Project foundation

- Documentation-first setup: specifications, ADRs, C4 architecture,
  governance, roadmaps, and repository scaffolding.
