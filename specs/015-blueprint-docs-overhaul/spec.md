# Feature Specification: Project Blueprint Documentation Overhaul

**Feature Branch**: `015-blueprint-docs-overhaul`
**Created**: 2026-02-21
**Status**: Draft
**Input**: Update 9 existing Project Blueprint documents and create 3 new documents to restore the documentation suite as the single source of truth for the GRAVITEA-ERP project, reflecting the system as built through Feature 014 (February 2026).

## Clarifications

### Session 2026-02-21

- Q: How should quality metrics (test count, coverage, endpoints) be verified during document updates? → A: Run `scripts/run-tests-external.sh`, read persisted `.summary` files from `Docs/Tests/` for authoritative metrics.
- Q: What diagram format should be used in blueprint documents? → A: Mermaid (rendered in GitHub/Notion, AI-maintainable).
- Q: Should the spec include an explicit list of ADR topics? → A: Yes, seed list of 14 ADR topics added to US-7.
- Q: What is the primary local development setup path for the onboarding guide? → A: Docker Compose only (docker compose up, seed_all, run tests via Docker).
- Q: What level of detail for the planned GCP production architecture? → A: Document known service mappings and known gaps from spec 011 analysis; mark undecided items as "TBD". Starter reference, not comprehensive migration plan.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Accurate Module Status Across All Documents (Priority: P1)

A developer (human or AI agent) reads any blueprint document and finds module status information that matches the actual codebase. Documents that previously showed "0%" or "Pending" for completed modules now show "Complete" with accurate capability summaries.

**Why this priority**: Stale module status is the single biggest documentation failure. Six modules are complete but multiple documents show them at 0% or Pending. This causes developers to make wrong assumptions about what exists and AI agents to re-implement completed functionality.

**Independent Test**: Can be verified by reading any document's module status table and cross-checking each entry against the corresponding Django app directory in the codebase.

**Acceptance Scenarios**:

1. **Given** the Product Vision document previously listed VENTAS at 0% and ARCA at 0%, **When** the document is updated, **Then** both modules show "Complete" with accurate capability summaries matching the implemented code.
2. **Given** the HLD previously listed Frontend Electron at 0%, **When** the document is updated, **Then** the Frontend section describes the Next.js 16 prototype as the current development frontend and Electron as the planned production target.
3. **Given** multiple documents contain module status tables (Product Vision, HLD, LLD, Development Workflow), **When** all are updated, **Then** the module status is consistent across every document — no contradictions between documents.
4. **Given** the Tenant Customization framework (Feature 014) is not mentioned in any document, **When** documents are updated, **Then** at least the HLD, LLD, and Data Model include the tenant customization layer.
5. **Given** COMPRAS is partially implemented and REPORTES is not started, **When** documents are updated, **Then** these modules are clearly marked "Partial" and "Not started" respectively — not conflated with completed modules.

---

### User Story 2 - Accurate Quality Metrics (Priority: P1)

A developer reads any document that cites test counts, coverage percentages, or endpoint counts and finds numbers that match the actual codebase state.

**Why this priority**: Multiple documents cite wildly different metrics (433 tests, 1471 tests) when the actual count is 2201+. Incorrect metrics undermine trust in all documentation and cause AI agents to miscalibrate their testing expectations.

**Independent Test**: Can be verified by running `pytest --co -q` to count tests, `pytest --cov` for coverage, and counting OpenAPI endpoints, then comparing against every document that cites these figures.

**Acceptance Scenarios**:

1. **Given** the Development Workflow document cites "433 tests, 82% coverage", **When** the document is updated, **Then** it shows the current verified test count and coverage percentage.
2. **Given** the LLD cites "1471 tests, 64 endpoints", **When** the document is updated, **Then** it shows the current verified test count and endpoint count.
3. **Given** multiple documents cite the same metric (e.g., test count), **When** all are updated, **Then** the same figure appears everywhere (no document has a different number for the same metric).
4. **Given** the REST API Design lists ~30 planned endpoints, **When** the document is updated, **Then** it references the actual OpenAPI spec files as the authoritative source for endpoint details.

---

### User Story 3 - Updated REST API Documentation (Priority: P1)

A developer looking for API endpoint information finds the REST API Design document pointing to authoritative OpenAPI specifications and accurately describing the implemented API surface.

**Why this priority**: The REST API Design is currently a skeleton labeled "En Diseno" with ~30 planned endpoints, while 100+ endpoints are live with generated OpenAPI specs. This is the highest-gap document and the most frequently consulted by frontend developers and AI agents.

**Independent Test**: Can be verified by comparing every endpoint listed in the document against the OpenAPI YAML files in `api/openapi/` and confirming no implemented endpoints are missing.

**Acceptance Scenarios**:

1. **Given** the REST API Design currently shows "En Diseno" status, **When** the document is updated, **Then** it reflects "Active" status with accurate endpoint coverage per module.
2. **Given** 6 OpenAPI YAML files exist in `api/openapi/`, **When** the document is updated, **Then** it references these files as the authoritative endpoint source and explains how they are generated.
3. **Given** the Facturacion module has no API section in the current document, **When** the document is updated, **Then** the ARCA/WSFEv1 endpoints are documented with their authentication and lifecycle patterns.
4. **Given** Problem+JSON (RFC 9457) error format is implemented, **When** the document is updated, **Then** the error handling section describes the actual error format with examples.
5. **Given** the document previously listed Ventas with 8 planned endpoints, **When** the document is updated, **Then** Ventas shows all implemented endpoints (orders, payments, customers, invoicing).

---

### User Story 4 - Complete Data Model Documentation (Priority: P1)

A developer consulting the Data Model document finds entity-relationship descriptions for all implemented modules, not just the original three.

**Why this priority**: The Data Model is at version 0.1 and missing entire modules (Facturacion, Ventas, Tenant Customization). Developers designing new features or writing migrations need accurate entity knowledge to avoid breaking existing relationships.

**Independent Test**: Can be verified by listing all Django models across `apps/` and confirming each appears in the Data Model document with correct relationships.

**Acceptance Scenarios**:

1. **Given** the Data Model is missing Facturacion entities, **When** the document is updated, **Then** Comprobante, ComprobanteItem, ArCaCredential, PuntoDeVenta, and CAEA models are documented with their relationships.
2. **Given** the Data Model is missing Ventas entities, **When** the document is updated, **Then** Order, OrderItem, Payment, and Customer models are documented with their relationships.
3. **Given** the Data Model is missing Tenant Customization entities, **When** the document is updated, **Then** TenantFieldDefinition, TenantModuleConfig, and BusinessTemplate models are documented, with BusinessTemplate explicitly noted as system-wide (not tenant-bound).
4. **Given** entity-relationship diagrams exist in the document, **When** the document is updated, **Then** diagrams include all implemented entities and their foreign key relationships.
5. **Given** the version is 0.1, **When** the document is updated, **Then** the version is incremented to reflect the scope of changes.

---

### User Story 5 - Realistic Roadmap with MVP Target (Priority: P2)

A stakeholder reads the Roadmap and understands what has been completed, what remains for MVP, and the target timeline.

**Why this priority**: The current Roadmap uses the original Q4 2025 - Q3 2026 timeline with no connection to actual progress. The MVP target of May 1, 2026 is not documented. Without a realistic roadmap, resource allocation and prioritization decisions are uninformed.

**Independent Test**: Can be verified by checking that every item marked "Complete" in the Roadmap corresponds to a merged feature branch, and every "Remaining" item maps to a concrete deliverable.

**Acceptance Scenarios**:

1. **Given** the Roadmap shows the original 4-phase Q4-Q3 timeline, **When** the document is updated, **Then** it reflects actual completion dates for features 001-014 and the MVP May 1, 2026 target.
2. **Given** multiple features are complete (AUTH, INVENTARIO, VENTAS, FACTURACION, SYNC, Observability, Frontend Prototype, Tenant Customization), **When** the roadmap is updated, **Then** each appears with its branch name, description, and completion status.
3. **Given** remaining MVP work exists (COMPRAS, REPORTES, Electron packaging, GCP deployment, CI/CD), **When** the roadmap is updated, **Then** each remaining item is listed as a discrete deliverable with clear scope.
4. **Given** some planned items may not be needed for MVP, **When** the roadmap is updated, **Then** "MVP Required" vs "Post-MVP" labels clearly distinguish what must ship by May 1 from what can follow.

---

### User Story 6 - Developer Onboarding Guide (Priority: P2)

A new developer (human or AI agent) reads a single onboarding document and can go from zero to productive — understanding the architecture, setting up the environment, navigating the codebase, and following development conventions.

**Why this priority**: No such document exists today. New developers must piece together information from 9+ documents, none of which are current. This wastes onboarding time and leads to convention violations that require rework.

**Independent Test**: Can be verified by having a person unfamiliar with the project follow the guide step-by-step and confirming they can: clone the repo, start Docker services, run tests, and locate key code files within 30 minutes of reading.

**Acceptance Scenarios**:

1. **Given** no onboarding guide exists, **When** the document is created, **Then** it contains all required sections: Architecture Overview, Environment Setup, Module Map, Spec-Driven Development, Key Conventions, Directory Structure, Running Tests, Feature Status Dashboard, AI Agent Context.
2. **Given** a developer follows the Environment Setup section, **When** they execute each step, **Then** they have a running local environment via Docker Compose (`docker compose up`, `seed_all`, tests passing via `docker compose exec web pytest`). The WSL venv is NOT part of the onboarding path — it is an AI agent workaround only.
3. **Given** the Module Map section, **When** a developer reads it, **Then** they can identify which Django app owns each business domain and its implementation status.
4. **Given** the Key Conventions section, **When** a developer creates a new model, **Then** they know to use TenantBoundModel, follow the immutable ledger pattern for financial data, and use Problem+JSON for errors.
5. **Given** the AI Agent Context section, **When** an AI agent reads it, **Then** it understands CLAUDE.md, skill auto-invocation triggers, and Serena memory usage.

---

### User Story 7 - Architecture Decision Records (Priority: P2)

A developer investigating why a technical decision was made can look up the ADR and find the context, alternatives considered, and rationale — preventing re-debate of settled decisions.

**Why this priority**: Multiple significant architectural decisions have been made (web-first development, JSONB customization, defense-in-depth) without formal documentation. Knowledge of why decisions were made lives only in Serena memories and chat transcripts, making it fragile and inaccessible.

**Independent Test**: Can be verified by reading each ADR entry and confirming the stated decision matches the actual implementation in the codebase.

**Acceptance Scenarios**:

1. **Given** no ADR document exists, **When** the document is created, **Then** it contains at least 14 ADR entries covering the major architectural decisions made through Feature 014.
2. **Given** each ADR entry, **When** read by a developer, **Then** it includes: date, status, context (why the decision was needed), decision (what was chosen), alternatives considered, and consequences.
3. **Given** ADR-001 (Web-first development with deferred Electron), **When** a developer reads it, **Then** they understand why Next.js is used during development and when/why Electron will replace it.
4. **Given** ADR-003 (Defense-in-Depth tenant isolation), **When** a developer reads it, **Then** they understand the three layers (Manager + RLS + IDOR) and why all three are necessary.
5. **Given** a future developer wants to change a settled decision, **When** they consult the ADR, **Then** they can see the original rationale and alternatives before proposing a change.

**ADR Seed List** (minimum 10 required, implementing agent may add more):

| ADR # | Topic | Key Decision |
|-------|-------|-------------|
| ADR-001 | Web-first development, deferred Electron | Next.js for dev phase; Electron is production target |
| ADR-002 | Single Django monolith over microservices | One modular monolith with app-per-domain, not separate services |
| ADR-003 | Defense-in-Depth tenant isolation | Three layers: TenantBoundManager + PostgreSQL RLS + IDOR validation |
| ADR-004 | RS256 JWT with custom claims | Asymmetric signing over HS256; tenant/role/branch in claims |
| ADR-005 | Immutable ledger for financial data | Append-only StockMovement and authorized Comprobantes; no UPDATE/DELETE |
| ADR-006 | AES-256-GCM field-level encryption | PII encrypted at field level with HMAC-SHA256 blind indexes for search |
| ADR-007 | Argon2 password hashing | Argon2id over bcrypt for memory-hard resistance |
| ADR-008 | JSONB tenant customization over EAV | Shopify-like pattern: metadata table + JSONB custom_data column |
| ADR-009 | Problem+JSON error format (RFC 9457) | Structured error responses over ad-hoc JSON error bodies |
| ADR-010 | Docker Compose consolidation with profiles | Single root docker-compose.yml with profiles over multiple files |
| ADR-011 | Offline-first sync with server-side conflict resolution | Server authoritative; PendingOperation queue on client |
| ADR-012 | Spec-driven development workflow | speckit commands (specify → plan → tasks → implement) |
| ADR-013 | External test runner for AI agents | scripts/run-tests-external.sh for 96% token savings |
| ADR-014 | AI agent skills architecture | CLAUDE.md + skills/ directory with auto-invoke triggers |

---

### User Story 8 - Deployment & Infrastructure Guide (Priority: P3)

A developer or DevOps engineer reads the deployment guide and understands both the current local development infrastructure and the planned production GCP infrastructure, including the migration path between them.

**Why this priority**: Infrastructure documentation exists scattered across Docker files and chat transcripts. Consolidating it into one document is important but less urgent than fixing actively misleading content in existing documents. The production deployment is a future milestone.

**Independent Test**: Can be verified by confirming the Local Development section matches the actual `docker-compose.yml` services and profiles, and the Production Target section covers all planned GCP services.

**Acceptance Scenarios**:

1. **Given** no deployment guide exists, **When** the document is created, **Then** it contains three sections: Local Development (current), Production Target (planned), and Migration Path.
2. **Given** the Local Development section, **When** compared to `docker-compose.yml`, **Then** every service, profile, port mapping, and healthcheck is accurately documented.
3. **Given** the Production Target section, **When** read by a DevOps engineer, **Then** they see a service mapping table (Docker service → GCP service) with known gaps from the spec 011 cloud-sql-readiness analysis, and undecided items clearly marked "TBD".
4. **Given** the Migration Path section, **When** read by a developer, **Then** they understand the known migration considerations (from spec 011 analysis) without speculative detail. Items not yet studied are listed as "TBD — requires further analysis".

---

### User Story 9 - Cross-Reference Integrity (Priority: P3)

A developer following a reference from one document to another finds accurate, consistent information at the destination — no contradictions, broken references, or outdated cross-references.

**Why this priority**: With 12 documents (9 updated + 3 new), cross-references become a significant consistency risk. However, this is naturally addressed as each document is updated individually and only needs explicit verification at the end.

**Independent Test**: Can be verified by searching all documents for phrases like "see [Document]", "refer to", "as described in" and checking that each referenced section exists and contains consistent information.

**Acceptance Scenarios**:

1. **Given** multiple documents reference each other's module status, **When** all documents are updated, **Then** module status tables are identical or explicitly explain any different granularity.
2. **Given** the HLD references the Data Model for entity details, **When** both are updated, **Then** the referenced entities actually appear in the Data Model.
3. **Given** test count appears in multiple documents, **When** all are updated, **Then** the same verified figure appears everywhere.
4. **Given** a reference points to "see Roadmap for timeline", **When** the Roadmap is updated, **Then** the referenced timeline information exists and is accurate.

---

### User Story 10 - PRD and HLD Reflect Dual-Environment Reality (Priority: P2)

A developer reading the PRD or HLD understands the dual-environment strategy: Next.js web frontend for current development, Electron desktop app for production deployment — without confusion about which is current vs planned.

**Why this priority**: The PRD and HLD currently describe Electron and Cloud Run as the primary architecture, which is the production target but not the current development reality. Developers joining now would be confused to find a Next.js app instead. Clear "current vs planned" distinction prevents wasted effort on wrong assumptions.

**Independent Test**: Can be verified by reading the architecture sections of PRD and HLD and confirming they clearly label which components are "Implemented (current)" and which are "Planned (production target)".

**Acceptance Scenarios**:

1. **Given** the PRD describes Electron as the primary frontend, **When** the document is updated, **Then** it distinguishes between the Next.js 16 development frontend (implemented) and the Electron production frontend (planned).
2. **Given** the HLD architecture diagram shows Cloud Run + Electron + Cloud SQL, **When** the document is updated, **Then** the diagram shows both the current Docker Compose setup AND the planned GCP architecture, clearly labeled.
3. **Given** the SRS lists "Must use Electron" as a design constraint, **When** the document is updated, **Then** it clarifies that Electron is a production constraint while Next.js is the development implementation.
4. **Given** the offline-first capability described in the PRD relies on Electron + SQLite, **When** the document is updated, **Then** it clarifies the current state (backend sync endpoints ready) and planned state (Electron + SQLite for offline storage).

---

### Edge Cases

- What happens if a metric cannot be verified because the environment is not running? Run `scripts/run-tests-external.sh` to generate results, then cite the `.summary` file and verification date. If the script cannot run, use the most recent `.summary` file in `Docs/Tests/` and note the date of that run.
- What happens when a document references a feature that is partially complete? Use explicit status markers: "Complete", "Partial (describe what's missing)", "Planned", "Deferred".
- How are documents in Spanish handled? Preserve the existing language of each document. Do not translate Spanish documents to English or vice versa.
- What happens if the OpenAPI specs are out of date relative to the code? Flag this as a finding rather than propagating potentially stale information.
- What happens if two existing documents have contradictory information? The codebase is the source of truth. Update both documents to match the code, note the discrepancy was resolved, and move on.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Every updated document MUST contain an accurate `Last Updated: YYYY-MM-DD` header reflecting when the update was applied.
- **FR-002**: Every module status table MUST distinguish "Complete", "Partial", "Planned", and "Not started" using consistent terminology across all documents.
- **FR-003**: Every quality metric (test count, coverage, endpoint count) MUST be verified by running `scripts/run-tests-external.sh` and reading the persisted `.summary` files from `Docs/Tests/`. The verification date and source command MUST be cited alongside the metric.
- **FR-004**: The REST API Design document MUST reference the OpenAPI YAML files in `api/openapi/` as the authoritative endpoint source.
- **FR-005**: The Data Model document MUST include entity-relationship information for all implemented Django models.
- **FR-006**: The Roadmap MUST show the MVP May 1, 2026 target date with clear "Complete", "MVP Required", and "Post-MVP" categorization.
- **FR-007**: The Developer Onboarding Guide MUST enable a new developer to go from zero to a running local environment within 30 minutes of reading.
- **FR-008**: The ADR document MUST contain at least the 14 entries from the ADR Seed List (US-7) with consistent format (Date, Status, Context, Decision, Alternatives, Consequences). Additional entries may be added.
- **FR-009**: The Deployment Guide MUST document both the current Docker Compose setup and the planned GCP production infrastructure.
- **FR-010**: Cross-references between documents MUST point to sections that exist and contain accurate information.
- **FR-011**: No document MUST describe a feature as "Complete" unless the corresponding code exists in the codebase.
- **FR-012**: No document MUST omit a feature that is implemented in the codebase.
- **FR-013**: All diagrams MUST use Mermaid format (renderable in GitHub/Notion). Diagrams MUST reflect the actual architecture, not aspirational designs. Diagrams showing planned architecture MUST be explicitly labeled "Planned". Existing ASCII diagrams SHOULD be converted to Mermaid during the update.
- **FR-014**: Documents MUST preserve their existing language (English or Spanish). The update process MUST NOT change a document's language.
- **FR-015**: Documents MUST preserve their existing structure where possible. New sections may be added but existing section order MUST NOT be reorganized unless the structure is fundamentally broken.

### Key Entities *(documentation-specific)*

- **Blueprint Document**: A Markdown file in `Docs/Project Blueprint/` serving as a project reference document. Each has a title, purpose, sections, and version/date metadata.
- **Module Status Entry**: A row in a module status table showing a Django app's implementation state (Complete, Partial, Planned, Not started) with capability summary.
- **Quality Metric**: A verified quantitative measure (test count, coverage percentage, endpoint count) that appears in one or more documents and must be consistent everywhere.
- **Architecture Decision Record**: A structured entry documenting a technical decision with context, alternatives, rationale, and consequences.
- **Cross-Reference**: A link or mention in one document pointing to content in another document.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All 9 existing documents are updated with accurate February 2026 state — zero entries showing "0%" or "Pending" for completed modules.
- **SC-002**: 3 new documents are created (Onboarding Guide, ADR, Deployment Guide) with all required sections as defined in their user stories.
- **SC-003**: Every quality metric cited in any document matches the verified codebase state (tolerance: metrics verified within the same work session).
- **SC-004**: Cross-reference integrity: every "see Document X" reference points to a section that exists and contains consistent information (zero broken or contradictory references).
- **SC-005**: Module status consistency: the same module shows the same status across all documents that include module tables.
- **SC-006**: The Roadmap includes the MVP May 1, 2026 target with at least 3 categories: Complete, MVP Required, Post-MVP.
- **SC-007**: The Developer Onboarding Guide contains all 9 required sections and provides a viable path from zero to running environment.
- **SC-008**: The ADR document contains at least 14 entries (per ADR Seed List in US-7), each with all 6 required fields (Date, Status, Context, Decision, Alternatives, Consequences).
- **SC-009**: Every document has an accurate `Last Updated` date in its header or metadata section.
