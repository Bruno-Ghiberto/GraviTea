# Feature Specification: Architecture Decision Records (ADR)

**Feature Branch**: `004-acopio-adr`
**Created**: 2026-03-16
**Status**: Draft
**Input**: Create the Architecture Decision Records blueprint document capturing all significant architectural decisions made during the GRAVITEA acopio de granos vertical pivot.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Developer Looks Up Why a Decision Was Made (Priority: P1)

A developer (human or AI agent) encounters a design pattern in the codebase -- such as the append-only ledger for grain movements or the three-layer tenant isolation -- and needs to understand the rationale, constraints, and rejected alternatives before modifying or extending related code.

**Why this priority**: This is the primary use case for ADRs. Without accessible rationale, developers re-debate settled decisions or accidentally violate constraints, wasting time and introducing regressions.

**Independent Test**: Can be fully tested by selecting any documented decision, reading its ADR entry, and confirming the reader can answer: "Why was this chosen? What was rejected and why? What are the consequences?"

**Acceptance Scenarios**:

1. **Given** a developer encounters the append-only ledger pattern in grain movements, **When** they search the ADR document for "ledger" or "immutability", **Then** they find a self-contained ADR entry with context, decision, consequences, and rejected alternatives -- without needing to consult any other document.
2. **Given** an AI agent is tasked with modifying the merma calculation architecture, **When** it reads the relevant ADR entry, **Then** it understands that per-step merma kg values are intentionally not stored (derived from intermediates) and does not introduce stored per-step fields.
3. **Given** a developer needs to understand why Rust is used for cryptographic operations instead of Python, **When** they read the acceleration boundary ADR, **Then** they find specific criteria for when computation should move to Rust versus remain in Python.

---

### User Story 2 - Architect Evaluates Superseding a Decision (Priority: P2)

A technical architect needs to evaluate whether a previously accepted decision should be superseded due to changed requirements, new technology options, or observed limitations in production. The ADR provides the original trade-off analysis as a baseline for re-evaluation.

**Why this priority**: Projects evolve. ADRs are living documents where decisions can be superseded. The status lifecycle (Accepted -> Superseded/Deprecated) enables controlled architectural evolution without losing history.

**Independent Test**: Can be tested by selecting any accepted ADR, proposing a hypothetical change, and confirming the original context and alternatives provide sufficient baseline for re-evaluation.

**Acceptance Scenarios**:

1. **Given** the team considers switching from UUID v4 to ULID for primary keys, **When** the architect reads ADR-002 (UUID v4 strategy), **Then** they find the original rationale and trade-offs, enabling an informed comparison rather than starting from scratch.
2. **Given** a new conflict resolution strategy is needed for grain quality data, **When** the architect reads ADR-029 (conflict resolution taxonomy), **Then** they see the per-data-type mapping and rationale, allowing them to propose a targeted amendment rather than a full redesign.

---

### User Story 3 - Product Owner Reviews Architectural Constraints (Priority: P3)

The product owner needs to understand which architectural constraints limit or enable specific product features, without reading technical implementation details. The ADR document provides a navigable index of decisions with business-facing consequences.

**Why this priority**: Product decisions are constrained by architectural choices. The product owner needs to understand boundaries (e.g., "offline-first means feature X works without internet") to make informed roadmap decisions.

**Independent Test**: Can be tested by a non-technical reader navigating the ADR index, locating a decision relevant to a product feature, and understanding the business impact from the consequences section.

**Acceptance Scenarios**:

1. **Given** the product owner is planning a feature that requires real-time cross-plant grain position, **When** they read ADR-013 (Posicion Consolidada as derived view), **Then** they understand the position is computed on-demand from per-plant ledgers, which informs latency expectations for the feature.
2. **Given** the product owner asks whether tolerance tables can be customized per tenant, **When** they read ADR-010 (global vs per-tenant entities), **Then** they understand that tolerance tables are legally regulated and shared across all tenants, which is a hard constraint on any customization request.

---

### User Story 4 - New Team Member Onboards to Architecture (Priority: P3)

A new team member (developer, QA engineer, or contractor) joins the project and needs to rapidly understand the key architectural decisions and their motivations without reading 1,200+ lines of data model documentation and multiple blueprint specs.

**Why this priority**: Onboarding efficiency directly impacts team velocity. A single navigable document with all decisions indexed by category reduces ramp-up time.

**Independent Test**: Can be tested by giving the ADR document to someone unfamiliar with the project and measuring whether they can answer "what pattern is used for X and why" within 5 minutes per question.

**Acceptance Scenarios**:

1. **Given** a new developer joins the project, **When** they read the ADR index table, **Then** they can identify which categories of decisions exist and navigate directly to any decision by clicking its anchor link.
2. **Given** a QA engineer needs to understand the security architecture for test planning, **When** they read the Security Decisions category (ADRs 021-024), **Then** they understand the authentication, encryption, and validation patterns well enough to design meaningful test scenarios.

---

### Edge Cases

- What happens when two ADRs appear to contradict each other? Each ADR must be self-contained. If a decision supersedes or modifies a prior one, the "context" section must reference the original ADR and explain the relationship.
- What happens when a decision was made implicitly (no explicit discussion) but is architecturally significant? The ADR should still be written, with the context section acknowledging that the decision was implicit and reconstructing the likely rationale from available evidence (code, constitution, research documents).
- What happens when a rejected alternative later becomes viable due to new technology or requirements? The ADR status remains "Accepted" until a formal supersession. A new ADR is created with status "Proposed", referencing the original, and both coexist until the new one is accepted.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The document MUST contain a navigable ADR index table at the top, listing every ADR with its ID, title, category, status, and date.
- **FR-002**: Each ADR entry MUST include all required fields: title, status, date, context, decision, consequences (positive and negative), and alternatives considered.
- **FR-003**: ADRs MUST be organized into logical categories: Infrastructure, Data Architecture, Security, Grain Domain, Fiscal Integration, Offline & Sync, Performance, and AI/ML Readiness.
- **FR-004**: Each ADR MUST cross-reference the upstream document(s) where the decision was made, using specific section numbers (e.g., "Vision v1.0 Section 2.3", "PRD v1.0 Section 4.4", "Constitution Principle VII").
- **FR-005**: Each ADR MUST include at least one rejected alternative with explicit rejection rationale.
- **FR-006**: The document MUST capture all 7 domain decisions from the Data Model spec (D-001 through D-007) as individual ADR entries.
- **FR-007**: The document MUST trace all 11 Constitution principles (I through XI) to at least one ADR entry, demonstrating complete coverage.
- **FR-008**: The document MUST include a "How to Read This Document" section explaining the ADR format, status lifecycle (Proposed -> Accepted -> Superseded -> Deprecated), and cross-reference conventions.
- **FR-009**: The document MUST document the boundary criteria for when computation should use the performance acceleration layer versus the primary application layer.
- **FR-010**: The document MUST document the conflict resolution taxonomy with all 5 strategies mapped to specific data types: configuration (server wins), inventory levels (last write wins), transactions (additive), user data (most complete wins), document numbering (server assigns final).
- **FR-011**: The document MUST document the classification boundary for global entities (shared across all tenants) versus per-tenant entities, with rationale for each classification.
- **FR-012**: The document MUST document the dual inventory architecture: grain as continuous kg-based ledger versus discrete SKU-based inventory for agricultural inputs.
- **FR-013**: The document MUST document the offline fiscal authorization strategy (anticipated batch authorization codes for harvest-period offline operations alongside standard per-invoice authorization).
- **FR-014**: The document MUST document the weighbridge hardware integration architecture, including protocol selection rationale and fallback chain.
- **FR-015**: The document MUST document the regulatory web service integration architecture, including the authentication flow, service separation, and per-service certificate management.
- **FR-016**: The document MUST document the own-grain versus third-party-grain accounting separation, including balance-sheet versus off-balance-sheet treatment.
- **FR-017**: The document MUST document the campaign-year segregation pattern and its interaction with storage, accounting, and fiscal operations.
- **FR-018**: The document MUST document the ON DELETE behavior exception policy (default, exceptions for satellite entities, nullable assignments) with specific rationale per exception.
- **FR-019**: The document MUST contain a minimum of 30 ADR entries covering all 8 categories.
- **FR-020**: The document MUST include a decision dependency graph showing which ADRs depend on or constrain other ADRs.

### Key Entities

- **ADR Entry**: A single architectural decision record with ID, title, status, date, context, decision statement, consequences, alternatives, and upstream cross-references. Organized by category.
- **ADR Index**: A master table providing quick navigation to all ADR entries, sortable by category and status.
- **Status Lifecycle**: The progression of an ADR through states (Proposed -> Accepted -> Superseded/Deprecated), enabling controlled architectural evolution.
- **Cross-Reference Link**: A pointer from an ADR to the upstream document and section where the decision originated (Vision, PRD, Data Model, Constitution).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Every ADR entry is self-contained -- a reader can understand the decision, its rationale, and its consequences without consulting any other document.
- **SC-002**: All 11 Constitution principles (I through XI) are traceable to at least one ADR, achieving 100% coverage of foundational principles.
- **SC-003**: All 7 Data Model domain decisions (D-001 through D-007) are captured as individual ADR entries with full context preserved.
- **SC-004**: The document contains 30 or more ADR entries spanning all 8 defined categories.
- **SC-005**: Every ADR includes at least 1 rejected alternative with explicit rejection rationale, enabling future decision re-evaluation.
- **SC-006**: A new team member can locate the rationale for any specific architectural pattern within 2 minutes using the ADR index and internal navigation links.
- **SC-007**: Every ADR cross-references its upstream source with specific section numbers, enabling traceability back to the originating document.
- **SC-008**: The ADR index table links to every ADR entry via working internal document navigation.

## Assumptions

- The document is a REFERENCE, not a specification. It records and rationalizes decisions already made in Vision v1.0, PRD v1.0, Data Model v1.0, and the project Constitution.
- ADR entries are written retrospectively, formalizing decisions that were made implicitly or explicitly during the acopio vertical pivot (feature branches 001-025).
- The document follows a lightweight ADR format adapted from Michael Nygard's template, not a heavy-process governance framework.
- This is a blueprint spec (single-author document), not an implementation spec. No code changes, migrations, or tests are involved.
- The target audience includes developers, AI agents, architects, and product owners. Technical depth varies by category but business consequences are always stated.

## Dependencies

- **Depends on**: spec-01 (Vision v1.0 -- strategic decisions and Ironclad Principles), spec-02 (PRD v1.0 -- module architecture and workflow decisions), spec-03 (Data Model v1.0 -- all domain model decisions and Ironclad Principles P1-P5)
- **Blocks**: spec-05 (High-Level Design -- ADRs inform and constrain HLD choices), spec-06 (REST API Design -- ADRs constrain API patterns and data contracts)
- **References**: Project Constitution (`.specify/memory/constitution.md`), Data Model research decisions (`specs/003-acopio-data-model/research.md`)
