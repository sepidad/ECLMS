# Actors

**Project:** Enterprise Contract Lifecycle Management System (ECLMS)

**Document ID:** ACT-007

**Version:** 1.0

**Status:** Draft

---

# Purpose

This document identifies every external entity that interacts with the Enterprise Contract Lifecycle Management System.

Actors exist outside the system boundary and exchange information with the platform.

Actors may be human users, external systems, or automated services.

Actors do not define permissions.

Their responsibilities and privileges are defined separately within the Role and Permission Model.

---

# Actor Categories

The platform recognizes three categories of actors:

- Human Actors
- External System Actors
- Automated Actors

---

# Human Actors

Human actors represent individuals performing business activities.

Examples include:

- Contract Requester
- Contract Manager
- Legal Reviewer
- Financial Reviewer
- Technical Reviewer
- Executive Approver
- Compliance Officer
- Auditor
- System Administrator
- Read-Only User

A single individual may perform multiple roles depending on organizational policy.

---

# External System Actors

External systems communicate with ECLMS through defined interfaces.

Typical examples include:

- Identity Provider
- Email Server
- SMS Gateway
- ERP System
- Accounting System
- Procurement System
- Digital Signature Service
- Document Management System
- Business Intelligence Platform
- Artificial Intelligence Service

These systems exchange information but are not considered part of the ECLMS platform.

---

# Automated Actors

Automated actors perform scheduled or event-driven activities without direct human intervention.

Examples include:

- Notification Service
- Workflow Scheduler
- Background Processing Service
- Backup Service
- Monitoring Service
- Search Indexer
- Reporting Engine

Automation improves reliability, consistency, and operational efficiency.

---

# Actor Principles

Every actor shall:

- Have a clearly defined purpose.
- Interact through documented interfaces.
- Operate within established security boundaries.
- Produce auditable activities where applicable.

---

# Closing Statement

Actors describe who or what communicates with the platform.

They do not define authority, permissions, or responsibilities.

Those concerns are addressed separately through Roles and the Permission Model.