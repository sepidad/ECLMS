# ECLMS Release Readiness Gate

**Purpose:** Define the minimum evidence required before the current working-tree implementation is promoted from feature-complete development state to a release candidate.

This gate operationalizes the Project Constitution principles of documentation before implementation, security by design, audit by default, testing as part of development, and quality over speed.

## Gate A — Repository integrity

- [x] The implementation is committed in a clean `main` baseline (`79de4a2`).
- [x] No runtime contract files, local databases, secrets, build output, or generated artifacts are tracked.
- [x] `git diff --check` is clean after the current hardening change is committed.
- [x] The pushed repository was cloned into a fresh checkout and matched commit `79de4a2` with a clean status.

## Gate B — Automated verification

- [x] Backend Ruff passes.
- [x] Full pytest suite passes from a clean checkout: 197 tests passed.
- [x] Frontend TypeScript build passes from the clean checkout.
- [x] Frontend lint has no actionable warnings.
- [x] Alembic upgrade reaches one head on the PostgreSQL Compose database during API startup.
- [ ] Database downgrade/re-upgrade behavior is verified for the release migration range.

## Gate C — Business lifecycle evidence

- [ ] Contract creation, versioning, document upload/download, approval, execution, activation, and audit history pass end to end.
- [ ] Organization isolation is verified for contracts, documents, workflows, users, notifications, integrations, reporting, and intelligence.
- [ ] Obligation and payment overdue sweeps produce auditable state changes.
- [ ] Notifications, webhook retries, email/SMS delivery records, CSV import, and CSV export are verified.

## Gate D — Operational and security evidence

- [ ] Production/staging secrets fail fast when invalid.
- [x] HTTPS through Caddy, proxy headers, security headers, body-size limits, and rate limits are configured/verified; local HTTPS uses the configured `localhost` hostname.
- [ ] Redis durable events are verified across restart/retry scenarios.
- [x] Backup and restore are tested, not only documented. (2026-08-15 drill: `pg_dump` custom-format backup of the live Compose database, restore into a scratch database, row counts matched baseline exactly, application booted against the restored database with `/health` ok and all 13 modules ok, admin login succeeded. Evidence retained at `var/backups/eclms-backup-20260815.dump`; see DEPLOYMENT.md §10.)
- [ ] Health, metrics, logs, and alert thresholds are observable by operators.
- [ ] At least one real ERP/accounting connector is integrated with authentication, idempotency, retry, and reconciliation behavior.
- [x] Digital-signature scope is either implemented or explicitly deferred by a recorded decision. (ADR-006, accepted 2026-08-15: deferred for the initial release; future support as a provider-based integration in the Integration module.)

## Release decision

The release is **not ready** while any Gate A or Gate B item is open. Gate C and Gate D items may be staged only when their risk, owner, and target release are recorded.

## Current baseline

As of 2026-08-14, the project has a clean pushed baseline, a reproducible clean checkout, 197 passing backend tests, clean Ruff/frontend lint, and a passing frontend build. Both Compose files validate, the production API image builds, all five development services report healthy, `/health` and `/metrics` return 200, and `https://localhost/health` returns 200 with HSTS. Remaining release gates are backup/restore evidence, full external-provider acceptance, one production-grade ERP/accounting connector, and the digital-signature decision.
