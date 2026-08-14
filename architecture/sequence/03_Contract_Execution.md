# Contract Execution Sequence

**Document ID:** SEQ-003

---

# Purpose

Defines transition from Approved to Active.

---

# Trigger

Final approval completed.

---

# Participants

Workflow Engine

Contract Management

Notification

Audit

External Systems

---

# Main Flow

1. Final approval verified.
2. Contract activated.
3. Effective date established.
4. Obligations activated.
5. Related guarantees activated.
6. Audit recorded.
7. Notifications published.

---

# Business Rules

- Only approved contracts may become active.
- Effective dates are immutable after activation unless amended.

---

# Security

Activation requires authorization.

---

# Audit

Activation shall always be recorded.

---

# Related Diagram

diagrams/03_Contract_Execution.puml