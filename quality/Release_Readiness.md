# ECLMS Release Readiness Gate

**Purpose:** Define the minimum evidence required before the current working-tree implementation is promoted from feature-complete development state to a release candidate.

This gate operationalizes the Project Constitution principles of documentation before implementation, security by design, audit by default, testing as part of development, and quality over speed.

## Gate A — Repository integrity

- [ ] All implementation files are reviewed and committed in coherent changes.
- [ ] No runtime contract files, local databases, secrets, build output, or generated artifacts are tracked.
- [ ] `git diff --check` is clean.
- [ ] The release branch has a reproducible checkout from a clean worktree.

## Gate B — Automated verification

- [ ] Backend Ruff passes.
- [ ] Full pytest suite passes from a clean environment.
- [ ] Frontend TypeScript build passes.
- [ ] Frontend lint has no actionable warnings.
- [ ] Alembic upgrade reaches one head on a fresh PostgreSQL database.
- [ ] Database downgrade/re-upgrade behavior is verified for the release migration range.

## Gate C — Business lifecycle evidence

- [ ] Contract creation, versioning, document upload/download, approval, execution, activation, and audit history pass end to end.
- [ ] Organization isolation is verified for contracts, documents, workflows, users, notifications, integrations, reporting, and intelligence.
- [ ] Obligation and payment overdue sweeps produce auditable state changes.
- [ ] Notifications, webhook retries, email/SMS delivery records, CSV import, and CSV export are verified.

## Gate D — Operational and security evidence

- [ ] Production/staging secrets fail fast when invalid.
- [ ] HTTPS, proxy headers, security headers, body-size limits, and rate limits are verified.
- [ ] Redis durable events are verified across restart/retry scenarios.
- [ ] Backup and restore are tested, not only documented.
- [ ] Health, metrics, logs, and alert thresholds are observable by operators.
- [ ] At least one real ERP/accounting connector is integrated with authentication, idempotency, retry, and reconciliation behavior.
- [ ] Digital-signature scope is either implemented or explicitly deferred by a recorded decision.

## Release decision

The release is **not ready** while any Gate A or Gate B item is open. Gate C and Gate D items may be staged only when their risk, owner, and target release are recorded.

## Current baseline

As of 2026-08-14, the project has broad feature coverage, 197 passing backend tests, clean Ruff/frontend lint, and a passing frontend build. It remains in hardening state because the implementation is largely uncommitted and enterprise connectors are still scaffolds/dry-runs.
