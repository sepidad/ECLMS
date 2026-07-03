# Notification Flow Sequence

**Document ID:** SEQ-009

---

# Purpose

Defines generation and delivery of business notifications.

---

# Trigger

Business event.

---

# Main Flow

1. Event published.
2. Notification policy evaluated.
3. Recipients determined.
4. Channels selected.
5. Notification delivered.
6. Delivery status recorded.

---

# Rules

Notification failure shall not invalidate completed business transactions.

---

# Related Diagram

diagrams/09_Notification_Flow.puml