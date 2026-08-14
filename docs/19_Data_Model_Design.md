# 19_Data_Model_Design.md

**Project:** Enterprise Contract Lifecycle Management System (ECLMS)  
**Document ID:** DATA-019  
**Version:** 1.0  
**Status:** Draft
---

# 1. Purpose of This Document

This document defines the **logical and physical data model** of the system.

It translates the domain model into:

- Database structure
- Data relationships
- Indexing strategy (conceptual)
- Storage separation rules
- Audit storage design
- Reporting data strategy

It does NOT define SQL syntax or implementation-specific schema.

---

# 2. Data Architecture Philosophy

The system follows these principles:

- Data is a strategic asset
- Audit data is immutable
- Operational and analytical data are separated
- Domain model drives data structure
- Data integrity is enforced at design level
- No silent data mutation in critical entities

Aligned with:
Data as a Strategic Asset :contentReference[oaicite:0]{index=0}

---

# 3. Data Layer Overview

The system uses a multi-store logical architecture:

## 3.1 Operational Store
- Active system data
- Contracts
- Users
- Workflows
- Documents metadata

## 3.2 Audit Store (Append-only)
- Immutable event log
- System traceability
- Compliance history

## 3.3 Reporting Store
- Aggregated data
- Precomputed analytics
- KPI structures

## 3.4 Document Store
- Binary files
- External storage references

---

# 4. Core Data Principles

- Every entity has a unique identifier
- Every change generates an audit record
- No destructive overwrite of critical business data
- Versioning is mandatory for contracts and documents
- Referential integrity is enforced at domain level

---

# 5. Core Data Entities Mapping

---

# 5.1 Organization Data Model

Table: Organization

Fields:
- OrganizationId (PK)
- Name
- Type
- Status
- ParentOrganizationId (FK)

Relationships:
- One-to-many with Departments
- One-to-many with Users
- One-to-many with Contracts

---

# 5.2 User Data Model

Table: User

Fields:
- UserId (PK)
- Name
- Email
- Status
- OrganizationId (FK)

Relationships:
- Many-to-many with Roles
- One-to-many with AuditEvents

---

# 5.3 Contract Data Model (CORE)

Table: Contract

Fields:
- ContractId (PK)
- Title
- Type
- Status
- OrganizationId (FK)
- CurrentVersionId (FK)
- WorkflowInstanceId (FK)
- CreatedBy
- CreatedAt

Rules:
- Must always reference active workflow
- Must always reference valid version

---

Table: ContractVersion

Fields:
- VersionId (PK)
- ContractId (FK)
- VersionNumber
- ContentBlob
- EffectiveDate
- IsActive

Rules:
- Immutable after creation
- Only one active version per contract

---

# 5.4 Workflow Data Model

Table: WorkflowInstance

Fields:
- InstanceId (PK)
- ContractId (FK)
- CurrentState
- WorkflowDefinitionId
- Status

---

Table: WorkflowHistory

Fields:
- HistoryId (PK)
- InstanceId (FK)
- FromState
- ToState
- ActorId
- Timestamp
- Reason

---

# 5.5 Financial Data Model

Table: ContractValue

Fields:
- ValueId (PK)
- ContractId (FK)
- Amount
- Currency

---

Table: PaymentSchedule

Fields:
- ScheduleId (PK)
- ContractId (FK)
- InstallmentNumber
- Amount
- DueDate
- Status

---

# 5.6 Obligation Data Model

Table: Obligation

Fields:
- ObligationId (PK)
- ContractId (FK)
- Description
- DueDate
- Status

---

# 5.7 Document Data Model

Table: Document

Fields:
- DocumentId (PK)
- ContractId (FK)
- Type
- StorageReference
- CreatedAt

---

Table: DocumentVersion

Fields:
- VersionId (PK)
- DocumentId (FK)
- StoragePath
- Hash
- CreatedAt

Rules:
- Immutable storage
- Hash-based integrity verification

---

# 5.8 Audit Data Model (CRITICAL)

Table: AuditEvent

Fields:
- EventId (PK)
- ActorId
- EntityType
- EntityId
- Action
- BeforeState (JSON)
- AfterState (JSON)
- Timestamp

Rules:
- Append-only
- Never updated
- Never deleted
- Fully traceable

---

# 6. Relationships Model

Core relationships:

- Organization → Users, Contracts
- Contract → Versions, Workflow, Documents, Obligations
- WorkflowInstance → History
- User → Roles → Permissions
- Contract → AuditEvents

---

# 7. Indexing Strategy (Conceptual)

Indexes must support:

- Contract lookup by status
- Contract lookup by organization
- Workflow state queries
- Audit tracing by entity
- Financial aggregation queries

Key indexes:

- Contract(OrganizationId, Status)
- WorkflowInstance(CurrentState)
- AuditEvent(EntityId, Timestamp)
- Document(ContractId)

---

# 8. Data Integrity Rules

- No orphan contracts
- No invalid workflow state
- No missing audit trail
- No unversioned contract updates
- Referential integrity enforced at domain level

---

# 9. Versioning Strategy

Versioned entities:

- Contracts
- Documents
- Workflows

Rules:
- Old versions remain immutable
- New versions do not overwrite old data
- Version history is always preserved

---

# 10. Audit Data Strategy

Audit system is:

- Fully append-only
- Independent storage layer
- Indexed by entity and time
- Immutable by design

Audit captures:
- Who
- What
- When
- Before state
- After state

---

# 11. Reporting Data Model

Reporting layer is separate from operational data.

It uses:

- Precomputed aggregates
- Time-based snapshots
- Contract summaries
- Financial rollups

Examples:

- Monthly contract activity
- Approval duration metrics
- Financial exposure reports

---

# 12. Data Lifecycle Rules

- Active data → Operational store
- Historical data → Archived storage
- Audit data → Permanent storage
- Reporting data → Recomputed periodically

---

# 13. Multi-Tenancy Consideration (Future)

System is designed for:

- Organization isolation
- Shared infrastructure
- Logical separation via OrganizationId

---

# 14. Relationship to Other Layers

- 17_Core_Concepts → defines meaning
- 18_Domain_Model → defines structure
- 19_Data_Model → defines storage
- 20_API_Design → exposes access layer

---

# 15. Closing Statement

The data model ensures that:

- Business integrity is preserved
- Auditability is guaranteed
- System scaling is possible
- Reporting is efficient
- Long-term evolution is supported