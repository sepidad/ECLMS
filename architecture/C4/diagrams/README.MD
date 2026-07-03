# Architecture Diagrams (C4 Visual Layer)

## 1. Purpose

This directory contains the visual representation of the Enterprise Contract Lifecycle Management System (ECLMS) architecture using PlantUML-based C4 diagrams.

These diagrams are the **visual counterpart** to the C4 documentation located in `architecture/C4/`.

---

## 2. Role in the Architecture

The architecture of ECLMS is defined in multiple layers:

```
Constitution
    ↓
Vision
    ↓
Product Principles
    ↓
Requirements
    ↓
ADRs
    ↓
C4 Documentation (What the system is)
    ↓
Diagrams (How it looks visually)
    ↓
Implementation
```

Diagrams do NOT define architecture.

They visualize architecture defined elsewhere.

---

## 3. Diagram Set

The system architecture is represented through three primary C4 views:

### 01 — System Context
Represents the system boundary and external actors.

### 02 — Container View
Represents major runtime containers and their interactions.

### 03 — Component View
Represents internal modular structure of the backend application.

---

## 4. Conventions

All diagrams must follow these rules:

- Use consistent naming aligned with C4 documentation
- Reflect approved ADR decisions
- Avoid implementation-specific details
- Avoid framework or library references
- Maintain technology independence at architectural level
- Use consistent styling via `styles.puml`

---

## 5. Styling

All diagrams must include:

```
!include styles.puml
```

This ensures consistency in:

- colors
- layout
- typography
- visual hierarchy

---

## 6. Relationship with C4 Documentation

| C4 Document | Diagram |
|------------|--------|
| System Context | 01_System_Context.puml |
| Container View | 02_Container_View.puml |
| Component View | 03_Component_View.puml |

Markdown documents define architecture.  
Diagrams visualize it.

---

## 7. Maintenance Rules

- Diagrams must be updated whenever ADRs change architecture.
- Diagrams must remain consistent with C4 documentation.
- No diagram may introduce new architectural concepts.

---

## 8. Summary

This directory provides the **visual architectural truth** of ECLMS.

It is a derived artifact from ADRs and C4 documentation and must never contradict upstream architectural sources.