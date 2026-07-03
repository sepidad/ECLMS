# Contract Amendment Sequence

**Document ID:** SEQ-004

---

# Purpose

Defines controlled modification of existing contracts.

---

# Trigger

Approved amendment request.

---

# Main Flow

1. Amendment initiated.
2. Existing contract locked.
3. Amendment version created.
4. Workflow executed.
5. Approval completed.
6. New version activated.
7. Previous version preserved.
8. Audit completed.

---

# Business Rules

- Original contract is never overwritten.
- Version history remains immutable.

---

# Related Diagram

diagrams/04_Contract_Amendment.puml