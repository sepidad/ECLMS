# Container View

## 1. Purpose

This document describes the major runtime containers that collectively implement ECLMS.

The Container View decomposes the system identified in the System Context into independently deployable or independently executable architectural units.

---

## 2. Scope

The Container View identifies:

- Major runtime applications
- Persistent storage
- External interfaces
- Communication pathways
- Responsibility boundaries

This document does not describe internal module implementation.

---

## 3. Architectural Overview

ECLMS is implemented using an API-First architecture with a Modular Monolith application core.

Major containers include:

- Web Application
- Backend API
- PostgreSQL Database
- File Storage
- Notification Services

Additional containers may be introduced as future architectural requirements emerge.

---

## 4. Container Responsibilities

Each container owns a clearly defined architectural responsibility.

Responsibilities shall not overlap.

Communication shall occur only through published interfaces.

---

## 5. Communication Principles

Containers communicate through stable contracts.

Direct database access between containers is prohibited.

Business rules remain within the application layer.

Infrastructure services shall not contain business logic.

---

## 6. Architectural Constraints

Container boundaries shall remain consistent with approved ADRs.

Technology selection shall never violate architectural decisions.

---

## 7. Related ADRs

- ADR-001
- ADR-002
- ADR-003
- ADR-004

---

## 8. Related Diagram

- diagrams/C2_Container.puml

---

## 9. Summary

The Container View establishes the major executable building blocks of ECLMS and defines how they collaborate while preserving architectural boundaries.