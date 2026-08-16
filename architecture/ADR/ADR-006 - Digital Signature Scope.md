# ADR-006 — Digital Signatures: Deferred Scope with Provider-Based Future Integration

**Project:** Enterprise Contract Lifecycle Management System (ECLMS)

**Document ID:** ADR-006

**Title:** Digital-Signature Scope — Explicit Deferral for the Initial Release

**Status:** Accepted

**Date:** 2026-08-15

---

# Context

ECLMS records contract execution today through the approval workflow engine
(executive sign-off), hash-verified document versions, and the append-only
audit event trail.

Target organizations (government agencies, municipalities, hospitals,
financial institutions, and large private enterprises — see ADR-005) operate
under different legal regimes for electronic signatures:

- Some jurisdictions and organizations accept simple/spoken-for electronic
  approval records with a complete audit trail.
- Others require advanced or qualified electronic signatures (e.g., eIDAS
  AdES/QES in the EU, or specific national trust-service providers).
- Some already operate a central signing platform that ECLMS would need to
  integrate with rather than replace.

Digital-signature products and trust services are also a commercial
integration surface: DocuSign, Adobe Acrobat Sign, national trust-service
providers, and on-premises signing appliances.

The release-readiness gate (`quality/Release_Readiness.md`, Gate D) requires
that digital-signature scope is either implemented or explicitly deferred by a
recorded decision.

# Problem

Committing to a signature integration now would mean choosing a vendor and a
legal profile before any customer requirement fixes them. That choice cannot
be made correctly in the abstract: it depends on the customer's jurisdiction,
existing signing infrastructure, and procurement constraints.

Deferring silently, on the other hand, leaves a release-blocking question open
and risks implicit assumptions leaking into the contract execution model.

# Decision

Digital-signature integration is **explicitly deferred** for the initial
release. It is out of scope for Phase 5 and Phase 6.

For the initial release:

1. Contract execution is recorded through the existing workflow approval
   (including executive sign-off), document content hashes, and audit events.
   This is the system of record for *who approved what, when*.
2. The API and data model must not take any design step that assumes a
   specific signature vendor or legal profile.

When signature support is scheduled (a later phase), it will be implemented as
an **external provider integration** behind the Integration module's provider
contract (the same pattern as email/SMS/storage providers): pluggable,
configurable per deployment, and invisible to core contract logic.

Triggers for scheduling the integration:

- A customer or prospect requires legally binding advanced/qualified
  signatures.
- A target market/regulatory requirement (e.g., eIDAS QES) blocks adoption.
- An organization mandates its central signing platform for all contract
  execution.

# Rationale

- Keeps the release gate decision auditable instead of implicit.
- Avoids premature vendor commitment with no requirement to anchor it.
- The provider-contract pattern (already proven for storage, email, SMS, and
  LLM review) makes later integration additive rather than structural.
- Existing hash-verified documents plus audit events already provide
  tamper-evidence for the approval record.

# Consequences

## Positive

- Release gate unblocked by a recorded, reviewable decision.
- No vendor lock-in; integration cost deferred until requirements are real.
- Later integration follows an established architectural pattern.

## Negative

- Contracts executed in the initial release are not legally e-signed by
  ECLMS itself; organizations requiring QES/AdES must run their external
  signing process alongside until the integration lands.
- Marketing to signature-regulated buyers is weaker until then.

# Alternatives Considered

## Integrate a SaaS Signature Vendor Now

Rejected: picks a vendor and legal profile without a customer requirement;
adds an external dependency to an on-premises-first product (ADR-005).

## Build Internal Signing (Key Management, Certificates)

Rejected: high cost and liability (trust-service territory), far outside the
product's core competency, and unnecessary for the target release.

## Silent Deferral (No Decision Recorded)

Rejected: leaves the release gate open and invites inconsistent assumptions
in the execution model.

# Related ADRs

- ADR-004 — Modular Monolith First (provider contracts live in modules)
- ADR-005 — On-Premises First with Cloud Compatibility (external SaaS
  dependency concerns)

# Review

Revisit this decision when any trigger listed under *Decision* occurs, or at
the latest when the first production deployment to a signature-regulated
organization is planned.

# Status

Accepted — 2026-08-15
