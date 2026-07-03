# C4 Architecture Documentation

## Purpose

This directory contains the architectural views of the Enterprise Contract Lifecycle Management System (ECLMS) using the C4 Model.

The purpose of these documents is to describe the system architecture at multiple levels of abstraction, providing a consistent and structured understanding of the platform for architects, developers, reviewers, and future contributors.

The C4 documentation does not replace the Project Constitution, Vision, Product Principles, Requirements, or Architecture Decision Records (ADRs). Instead, it transforms those architectural decisions into a coherent representation of the system.

---

# Role Within the Repository

The architecture documentation occupies the layer between architectural decisions and implementation.

The documentation hierarchy of the project is:

```
Project Constitution
        ↓
Vision
        ↓
Product Principles
        ↓
Business & System Requirements
        ↓
Architecture Decision Records (ADR)
        ↓
C4 Architecture Documentation
        ↓
Architecture Diagrams
        ↓
Implementation
```

Each layer builds upon the layers above it.

No document within this directory may contradict an approved ADR or any upstream architectural document.

---

# Scope

The C4 documentation describes the architecture of ECLMS from three progressively detailed viewpoints.

The documented levels are:

- System Context
- Container View
- Component View

The Code level defined by the original C4 methodology is intentionally excluded from the repository because implementation details are represented by the source code itself.

---

# Objectives

The objectives of the C4 documentation are to:

- Describe the architecture at multiple abstraction levels.
- Define clear architectural boundaries.
- Improve communication between stakeholders.
- Support architectural consistency.
- Reduce ambiguity during implementation.
- Preserve architectural knowledge independently of individual contributors.
- Provide a stable reference for future architectural evolution.

---

# C4 Documents

## 01_System_Context.md

Describes ECLMS as a single enterprise system.

Defines:

- System boundary
- Primary actors
- External systems
- High-level interactions
- Architectural scope

This document answers:

> What is ECLMS and how does it interact with its environment?

---

## 02_Container_View.md

Describes the major runtime containers that collectively implement ECLMS.

Defines:

- Application containers
- Databases
- External services
- Communication paths
- Container responsibilities

This document answers:

> How is the system organized into executable building blocks?

---

## 03_Component_View.md

Describes the internal business architecture of the primary application container.

Defines:

- Business components
- Responsibilities
- Dependencies
- Component interaction principles

This document answers:

> How is the application internally organized?

---

# Relationship with Architecture Decision Records

Architecture Decision Records define **why** architectural decisions were made.

The C4 documentation defines **what the resulting architecture looks like**.

Examples include:

| Architecture Decision | Architectural Representation |
|------------------------|------------------------------|
| ADR-001 — Why PostgreSQL | PostgreSQL appears as the primary persistence container. |
| ADR-002 — Why Hybrid Authorization | Security boundaries and authorization responsibilities appear within the architecture. |
| ADR-003 — Why API First | External consumers interact through published APIs. |
| ADR-004 — Why Modular Monolith First | Business components are organized as modules within a single application. |

The C4 documents shall never redefine or justify architectural decisions already recorded in ADRs.

---

# Relationship with Architecture Diagrams

The Markdown documents provide the authoritative textual description of the architecture.

Visual diagrams are maintained separately under:

```
architecture/diagrams/
```

Each C4 document has a corresponding architectural diagram.

The documents explain the architecture.

The diagrams visualize the architecture.

Neither replaces the other.

---

# Architectural Principles

Every C4 document shall adhere to the following principles:

- Architecture before implementation.
- Business before technology.
- Enterprise-first thinking.
- Security by design.
- Auditability by default.
- API-first architecture.
- Modular boundaries.
- Separation of concerns.
- Single responsibility.
- Technology independence whenever practical.

---

# Documentation Rules

All C4 documents shall:

- Describe architecture rather than implementation.
- Avoid framework-specific details.
- Avoid programming language details.
- Avoid database schema definitions.
- Avoid implementation algorithms.
- Remain consistent with approved ADRs.
- Use terminology defined elsewhere in the repository.
- Preserve architectural stability over time.

---

# Reading Order

Readers unfamiliar with the project should review the documents in the following order:

1. Project Constitution
2. Vision
3. Product Principles
4. Functional Requirements
5. Non-Functional Requirements
6. Architecture Decision Records (ADR)
7. C4 Architecture Documentation
8. Architecture Diagrams

Following this sequence ensures that architectural decisions are understood before examining their implementation.

---

# Future Evolution

As ECLMS evolves, additional architectural views may be introduced.

Examples include:

- Deployment Architecture
- Integration Architecture
- Security Architecture
- Sequence Diagrams
- Infrastructure Views

These documents complement the C4 model but do not replace it.

---

# Summary

The C4 Architecture Documentation provides the canonical architectural description of ECLMS.

Together with the Project Constitution, Vision, Product Principles, Requirements, and Architecture Decision Records, it forms the architectural foundation upon which the system is implemented, maintained, and evolved.

The architecture documented here should remain stable, understandable, and maintainable throughout the lifetime of the project.