# 18_Domain_Model.md

**Project:** Enterprise Contract Lifecycle Management System (ECLMS)  
**Document ID:** DM-018  
**Version:** 1.0  
**Status:** Draft
---

# 1. Purpose of This Document

This document defines the **complete domain model** of the system.

It translates conceptual definitions from `17_Core_Concepts.md` into:

- Entities
- Relationships
- Aggregates
- Domain rules
- Lifecycle behavior
- Business invariants

This is the **core engineering representation of the business domain**.

---

# 2. Domain Design Philosophy

The domain model follows:

- Domain-Driven Design (DDD-inspired structure)
- Strict separation of business logic from infrastructure
- Aggregate-based consistency boundaries
- Event-driven behavior
- Audit-first design

Aligned with:
Business Before Technology

---

# 3. Domain Structure Overview

The domain is divided into bounded contexts:

## 3.1 Core Contexts

- Identity & Access Context
- Contract Management Context
- Workflow Context
- Document Context
- Financial Context
- Obligation Context
- Audit Context
- Notification Context

Each context owns its internal model and rules.

---

# 4. Core Domain Entities

---

# 4.1 Organization Context

## Organization
Represents a legal or structural entity using the system.

Attributes:
- OrganizationId
- Name
- Type
- Status
- ParentOrganizationId

Rules:
- Can contain multiple departments
- Owns all contracts and users within scope

---

## Department
Logical subdivision of organization.

Attributes:
- DepartmentId
- Name
- OrganizationId

Rules:
- Belongs to one organization
- Can own users

---

# 4.2 Identity Context

## User
Represents a system actor.

Attributes:
- UserId
- Name
- Email
- Status
- OrganizationId

Rules:
- Must belong to exactly one organization
- Can have multiple roles

---

## Role
Defines responsibilities.

Attributes:
- RoleId
- Name
- Permissions[]

Examples:
- Admin
- Legal Reviewer
- Financial Officer
- Auditor

---

## Permission
Atomic action rights.

Attributes:
- PermissionId
- Action
- Resource

---

# 4.3 Contract Context (CORE)

## Contract (Aggregate Root)
Central business entity.

Attributes:
- ContractId
- Title
- Type
- Status
- CurrentVersionId
- WorkflowInstanceId
- OrganizationId
- CreatedBy
- CreatedAt

Rules:
- Must always have a valid workflow state
- Cannot bypass lifecycle rules
- All changes must generate audit events

---

## ContractVersion
Immutable snapshot of contract state.

Attributes:
- VersionId
- ContractId
- VersionNumber
- Content
- EffectiveDate

Rules:
- Immutable after creation
- Only latest version is active

---

## Amendment
Represents modifications.

Attributes:
- AmendmentId
- ContractId
- Reason
- Status

---

## Clause
Reusable contractual component.

Attributes:
- ClauseId
- Text
- Category

---

## Template
Predefined contract structure.

Attributes:
- TemplateId
- Name
- StructureDefinition

---

# 4.4 Workflow Context

## WorkflowDefinition
Defines lifecycle structure.

Attributes:
- WorkflowId
- Name
- Version
- States[]

---

## WorkflowState
Represents contract state.

Attributes:
- StateId
- Name
- IsFinal

Examples:
- Draft
- Review
- Approved
- Rejected
- Active

---

## WorkflowTransition
Defines movement rules.

Attributes:
- FromState
- ToState
- RequiredRoles[]
- Conditions

---

## WorkflowInstance
Runtime execution of workflow.

Attributes:
- InstanceId
- ContractId
- CurrentState
- History[]

Rules:
- One active instance per contract

---

# 4.5 Financial Context

## ContractValue
Represents monetary value.

Attributes:
- ValueId
- Amount
- Currency
- ContractId

---

## PaymentSchedule
Defines payment structure.

Attributes:
- ScheduleId
- ContractId
- Installments[]

---

## InvoiceReference
Links external financial systems.

Attributes:
- InvoiceId
- ExternalReference

---

# 4.6 Obligation Context

## Obligation
Represents enforceable responsibility.

Attributes:
- ObligationId
- ContractId
- Description
- DueDate
- Status

Rules:
- Must be tied to contract lifecycle

---

## SLA
Defines service expectations.

Attributes:
- SlaId
- Conditions
- Metrics

---

# 4.7 Document Context

## Document
Represents stored files.

Attributes:
- DocumentId
- FilePath
- Type
- Version

---

## DocumentVersion
Immutable file versions.

Attributes:
- VersionId
- DocumentId
- StorageReference

Rules:
- Immutable once stored

---

# 4.8 Audit Context

## AuditEvent (Critical Aggregate)
Immutable system record.

Attributes:
- EventId
- ActorId
- Action
- EntityType
- EntityId
- BeforeState
- AfterState
- Timestamp

Rules:
- Cannot be modified
- Cannot be deleted
- Append-only only

---

# 4.9 Notification Context

## Notification
System communication unit.

Attributes:
- NotificationId
- Type
- Recipient
- Status

---

## EscalationEvent
Triggered when rules are violated or deadlines missed.

Attributes:
- EscalationId
- TriggerCondition
- Severity

---

# 5. Aggregate Design Rules

## 5.1 Aggregate Boundaries

Each aggregate must:

- Maintain internal consistency
- Prevent cross-aggregate direct mutation
- Control its own invariants

---

## 5.2 Core Aggregates

- Contract (Primary)
- WorkflowInstance
- User
- Organization
- AuditEvent

---

# 6. Domain Invariants

## Contract Invariants

- Contract must always have a workflow state
- Contract version must be immutable
- Contract cannot skip states

## Audit Invariants

- Every change generates audit event
- Audit is immutable

## Workflow Invariants

- Only valid transitions allowed
- No direct state modification

---

# 7. Domain Events

Events represent business changes:

- ContractCreated
- ContractUpdated
- ContractApproved
- ContractRejected
- WorkflowStateChanged
- ObligationCreated
- DocumentUploaded
- AuditRecorded

---

# 8. Domain Behavior Rules

- Business logic lives inside domain
- Application layer only orchestrates
- Infrastructure never contains business rules
- All state changes go through domain methods

---

# 9. Relationship to Other Layers

- 17_Core_Concepts.md → defines meaning
- 18_Domain_Model.md → defines structure
- 19_Data_Model_Design.md → defines storage
- 20_API_Design.md → defines access

---

# 10. Closing Statement

The domain model is the **source of truth for business logic**.

All system behavior must conform to this model.