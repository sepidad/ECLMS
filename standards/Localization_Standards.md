# Localization Standards

**Project:** Enterprise Contract Lifecycle Management System (ECLMS)

**Document ID:** STD-LOC-001

**Version:** 2.0

**Status:** Draft

---

# Purpose

This document defines the localization principles and standards for the Enterprise Contract Lifecycle Management System (ECLMS).

Localization ensures that the system can present information in multiple languages while maintaining a single, consistent business and technical architecture.

---

# Localization Philosophy

The ECLMS follows an **English-first engineering model** with **localized user experiences**.

The project distinguishes between the language used to build the system and the language used to operate the system.

### Engineering Language

English is the canonical language for:

* Source code
* Database schema
* APIs
* Configuration
* Internal documentation
* Technical documentation
* Architecture documents
* Log messages
* Error identifiers
* Test cases
* Repository artifacts

Using a single engineering language improves maintainability, collaboration, tooling compatibility, and long-term sustainability.

### User Language

The application shall present information in the language selected by the user.

The initial release shall support:

* English
* Persian (فارسی)

Future languages shall be added without modifying business logic.

---

# Separation of Concerns

Business logic shall never depend on presentation language.

The system shall separate:

* Business logic
* User interface text
* Validation messages
* Notifications
* Reports
* Email templates
* Help content

All user-facing text shall be externalized into localization resources.

---

# Supported Languages

Initial release:

| Language        | Status    |
| --------------- | --------- |
| English         | Supported |
| Persian (فارسی) | Supported |

The architecture shall permit additional languages through configuration rather than application redesign.

---

# User Interface Requirements

The application shall support:

* English (Left-to-Right)
* Persian (Right-to-Left)

The interface shall correctly adapt:

* Layout direction
* Navigation
* Alignment
* Icons where appropriate
* Text rendering
* Input controls

Switching languages shall not require restarting the application.

---

# Regional Formatting

Localization shall support language-specific formatting for:

* Dates: هجری شمسی
* Time :  برای فارسی  دیفالت تهران 
* Numbers
* Currency: 
* Percentages

Business data shall remain language-independent.

---

# Translation Standards

Translations shall be:

* Consistent
* Professionally reviewed
* Context-aware
* Version controlled
* Traceable

Machine-generated translations shall not be considered authoritative without review.

---

# Technical Standards

The system shall:

* Store all text using Unicode (UTF-8 or equivalent)
* Avoid hard-coded user-visible strings
* Support resource-based localization
* Support dynamic language switching
* Separate localization resources from business logic

---

# Future Expansion

Localization architecture shall support additional languages without requiring:

* Database redesign
* Business rule changes
* Workflow changes
* API redesign

Adding a new language should primarily involve providing new localization resources.

---

# Guiding Principle

**English is the language of engineering.**

**Persian is the primary language of business operation.**

The architecture shall ensure that software implementation remains internationally maintainable while providing a native experience for Persian-speaking users.
