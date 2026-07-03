# ADR-002 — Why Hybrid Authorization (RBAC + ABAC)

## Status
Accepted

## Date
2026-07

---

## 1. Context

ECLMS manages contracts, approvals, financial information, legal documents, and organizational workflows.

These assets require an authorization model that is both easy to administer and capable of enforcing context-sensitive business rules.

The detailed authorization model is defined in **08_Permission_Model.md**.

This ADR records the architectural decision to adopt that model as the authorization standard for the platform.

---

## 2. Decision

ECLMS adopts a hybrid authorization model combining Role-Based Access Control (RBAC) and Attribute-Based Access Control (ABAC).

---

## 3. Rationale

RBAC provides a clear and manageable mechanism for assigning permissions based on organizational roles.

ABAC complements RBAC by evaluating contextual information such as workflow state, ownership, organizational attributes, or business rules.

Neither model alone sufficiently satisfies the platform's authorization requirements.

The hybrid approach combines administrative simplicity with the flexibility required for enterprise contract workflows.

> RBAC provides structure.  
> ABAC provides intelligence.

---

## 4. Alternatives Considered

### RBAC Only

Rejected because it cannot adequately express dynamic business rules without creating excessive numbers of roles.

### ABAC Only

Rejected because it increases administrative complexity and makes authorization policies more difficult to understand and manage.

### Access Control Lists (ACL)

Rejected because they do not scale effectively across large organizations with evolving workflows and complex authorization requirements.

---

## 5. Consequences

### Positive

- Flexible authorization model
- Scalable across organizational structures
- Supports workflow-driven security decisions
- Consistent foundation for future security architecture

### Negative

- More complex than a single authorization model
- Requires disciplined governance of authorization policies

---

## 6. Alignment

This decision adopts the authorization model defined in **08_Permission_Model.md** and supports the architectural objectives established by the Project Constitution regarding security, auditability, and enterprise readiness.

---

## 7. Conclusion

A hybrid RBAC and ABAC model provides the most appropriate balance between manageability, flexibility, and long-term scalability for ECLMS and is adopted as the platform's standard authorization approach.