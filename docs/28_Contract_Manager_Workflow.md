# Phase 6 — Contract Manager Workflow

## Purpose

This document is the implementation specification for the first user-facing contract workflow, based on `workflow-قرارداد.docx`.

## Primary user

The Contract Manager creates and manages contracts, selects reusable templates, completes missing commercial information, sends contracts for review, merges feedback, tracks approvals, and monitors guarantees. Administrators retain unrestricted configuration and administrative control.

## First-release lifecycle

```text
Draft → Review → Manager merge → Approval → Execute → Active → Monitor
```

Legal and Finance review in parallel by default. A reviewer never edits the official contract version. Each reviewer receives an independent review assignment and may submit comments, suggested text, or a rejection reason. Only the Contract Manager may accept or reject suggestions and create the next official version.

## Template requirements

An approved template version contains structured fields, locked clauses, editable optional clauses, required documents, default reviewers, review SLAs, approval routing rules, and mandatory guarantee types. Contract values are stored as data as well as rendered into the document so they remain searchable and reportable.

## Phase 1 guarantee types

- Bid bond
- Advance-payment guarantee
- Performance guarantee
- Insurance guarantee

The guarantee register must store amount, currency, percentage, issuer, beneficiary, serial number, issue date, validity dates, direction, attachment, release condition, and state. Received guarantees need expiry warnings; issued guarantees need release-right reminders.

## Role landing pages

- Contract Manager: workflow queue, drafts, merge tasks, approvals, and guarantee warnings.
- Legal Advisor: assigned legal review tasks and SLA status.
- Finance Head: assigned financial review tasks plus aggregate guarantee warnings.
- Administrator: users, roles, templates, thresholds, SLAs, clauses, and system configuration.

## Acceptance scenario

The first vertical slice is complete when a manager creates a contract from a template, legal and finance submit independent feedback, the manager accepts/rejects feedback into a new version, and the contract proceeds through approval without changing reviewer ownership of the official document.

## Implementation order

1. Template library and structured contract fields.
2. Independent legal/finance review assignments, comments, and suggested edits.
3. Manager merge and version creation.
4. Configurable value/risk approval routing.
5. Guarantee register, expiry alerts, renewal, release, and claim states.
6. English UI first; Persian localization follows after workflow acceptance.
