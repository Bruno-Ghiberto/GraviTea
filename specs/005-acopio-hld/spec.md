# Feature Specification: High-Level Design (HLD) Document

**Feature Branch**: `005-acopio-hld`
**Created**: 2026-03-17
**Status**: Draft
**Input**: Create `Docs/Project Blueprint/High-Level Design (HLD).md` from specs 01-04 upstream documents

## Clarifications

### Session 2026-03-17

- Q: In section 5 (Component Overview), should the HLD annotate which apps are Phase 1 vs Phase 2, or present all 8 apps uniformly? → A: Present all 8 apps uniformly as intended architecture; add "(Phase 2)" inline annotation only on apps outside Phase 1 MVP scope (`apps/facturacion`, `apps/liquidaciones`).

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Developer Architecture Reference (Priority: P1)

A backend developer joining the team (or an AI implementation agent running specs 09+) reads the HLD to understand the system architecture before writing code. They need to know which Django app owns each domain entity, what external services the system integrates with, how data flows through the romaneo reception workflow, and what architectural constraints (RLS, offline-first, Rust boundaries) apply to their implementation work.

**Why this priority**: Without a clear component map and data flow diagram, every implementation agent must re-read four upstream documents and synthesise the architecture themselves. P1 because all implementation specs (09+) are blocked until this document exists.

**Independent Test**: Give a developer who has read only this document the task: "Which Django app handles CPE lifecycle calls, and what happens to those calls when the server is offline?" They should answer within 2 minutes using only this document.

**Acceptance Scenarios**:

1. **Given** a developer reads section 5 (Component Overview), **When** they look up entity `Romaneo`, **Then** they identify it belongs to `apps/acopio` and see which related entities exist (QualityAnalysis, MermaCalculation, CPE, WeighbridgeDevice).
2. **Given** a developer reads section 9.1 (Romaneo Reception Flow), **When** they follow the 10-step data flow, **Then** each step identifies the responsible component (weighbridge driver, Rust merma engine, WSCPE client) and any offline behaviour.
3. **Given** a developer reads section 4 (Container Architecture), **When** they look up the Rust extension container, **Then** they find the acceleration boundary criteria and the benchmark table showing which operations are Rust-accelerated.
4. **Given** a developer reads section 8 (Offline-First Architecture), **When** they look up CPE confirmation calls, **Then** they confirm these are queued via `PendingOperation` (store-and-forward) and transmitted on reconnect.

---

### User Story 2 - Architect ARCA Integration Evaluation (Priority: P2)

An architect or technical lead reads the ARCA integration section of the HLD to evaluate the feasibility and constraints of the offline fiscal strategy. They need to understand the WSAA authentication flow, why CAEA is required for offline invoice issuance, why store-and-forward CAE is legally invalid, and what the certificate management model looks like.

**Why this priority**: The ARCA integration is the highest-risk external dependency. Architects evaluating regulatory compliance or planning the fiscal implementation sprint must have the full integration architecture in one place. P2 because it informs spec-08a (ARCA Grain Integration Guide).

**Independent Test**: Select section 6 (ARCA Integration Architecture). The architect answers within 5 minutes: "Why can't we use store-and-forward CAE for offline invoicing?" and "What happens if the WSAA token expires mid-WSLPG batch?" Both answers must be in the document.

**Acceptance Scenarios**:

1. **Given** an architect reads section 6.5, **When** they look for the CAEA legal constraint, **Then** the document explicitly states CAEA codes must be obtained before the offline period begins and a deferred CAE produces a legally invalid fiscal document.
2. **Given** an architect reads section 6.2 (WSAA Auth Flow), **When** they follow the TRA → CMS → LoginCMS → TA flow, **Then** they see the 12-hour token expiry, Redis caching strategy, and the error path for token expiry mid-batch.
3. **Given** an architect reads section 6.3 (WSLPG Integration), **When** they look for the single-grain-type constraint, **Then** the document states `codGrano` is at the XML root — one submission per grain type — with SISA as a blocking gate before filing.
4. **Given** an architect reads section 6.6 (Certificate Management), **When** they look for certificate scope, **Then** the document states each ARCA service (WSLPG, WSCPE, WSFEv1) requires a separate X.509 certificate with private keys in Google Cloud Secret Manager.

---

### User Story 3 - Product Owner Deployment and Connectivity Review (Priority: P3)

A product owner or sales engineer reads the offline-first section and deployment topology to understand the product's connectivity constraints, deployment options for SMB acopiadores, and infrastructure requirements.

**Why this priority**: Offline-first is GraviTea's primary market differentiator. Product owners presenting to clients need to explain what "offline-first" means operationally, what the CAEA constraint means for harvest planning, and what infrastructure a client with 1–5 plants needs.

**Independent Test**: A product owner reads sections 8 (Offline-First) and 11 (Deployment Topology). Without any other context, they answer: "Can a client run the system on a single server?" and "What happens if the internet goes out during harvest?" within 3 minutes.

**Acceptance Scenarios**:

1. **Given** a product owner reads section 8.1, **When** they look for the connectivity baseline, **Then** the document states that 44% of operators report "regular" (not good) connectivity and offline is the base operating mode, not a degraded fallback.
2. **Given** a product owner reads section 8.6, **When** they look for the offline fiscal path, **Then** the document explains CAEA quincena codes must be obtained before the offline period and invoicing is blocked (not degraded) if CAEA codes were not obtained before connectivity loss.
3. **Given** a product owner reads section 11.2, **When** they look for production deployment options, **Then** the document describes both full-cloud and hybrid (plant server + cloud sync) topology options with no Kubernetes or microservices required for initial scale.

---

### User Story 4 - New Team Member System Onboarding (Priority: P3)

A new team member (engineer, QA, or technical PM) reads the HLD as their first introduction to the system. They need the full picture — containers, communication protocols, security model, and how the AI/ML roadmap is being prepared — without reading any of specs 01-04.

**Why this priority**: Onboarding speed directly impacts team velocity. A self-contained HLD eliminates a lengthy orientation process.

**Independent Test**: A new team member reads only the HLD. They can: (a) sketch the C4 container diagram, (b) name all 5 conflict resolution strategies and their target data types, (c) describe the 3-layer security model, (d) explain what data the system collects for Phase 4 ML features.

**Acceptance Scenarios**:

1. **Given** a new team member reads section 3 (System Context), **When** they view the C4 Level 1 diagram, **Then** they see all external actors (ARCA WSAA/WSLPG/WSCPE/WSFEv1, weighbridge device, browser client, mobile client future, operator PC) without reading any other document.
2. **Given** a new team member reads section 10 (Security Architecture), **When** they view the defense-in-depth diagram, **Then** they see 3 distinct labeled layers (ORM TenantBoundManager, PostgreSQL RLS, IDOR JWT validation) each with its specific enforcement mechanism.
3. **Given** a new team member reads section 12 (AI/ML Readiness), **When** they look at the 4-layer strategy, **Then** they can explain what data is collected today (Layers 1–3) and what the IoT anchor point (Layer 4) enables in a future phase without schema changes.

---

### Edge Cases

- What happens if the ARCA WSLPG endpoint URL changes? The HLD lists both homologation and production URLs; certificate registration differences must be noted.
- What happens when a CPE expires during an extended offline period (>5 days)? Section 8.7 defines the system response (operator alert) and required action (no automatic extension).
- What happens when CAEA quincena codes expire during an extended outage? Section 8.7 must state: invoicing blocked, no automatic workaround.
- What if a weighbridge brand not in the 3-tier stack is used? Section 7 must indicate the stack covers the known Argentine market; new brands require adding a driver.
- What if the Rust `.so` extension fails to load at Django startup? Section 4.2 must state the Python fallback activates automatically without operator intervention.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-0501**: The HLD MUST contain a C4 Level 1 system context diagram (Mermaid) showing the GraviTea system boundary and all external actors: ARCA WSAA, ARCA WSLPG, ARCA WSCPE, ARCA WSFEv1, weighbridge device, browser client, mobile client (future), and operator PC.
- **FR-0502**: The HLD MUST contain a C4 Level 2 container diagram (Mermaid) showing all major containers — Django API, PostgreSQL 18.1, Redis 7.x, Rust extension (.so), Qdrant (optional) — with labeled communication protocols on every connection arrow.
- **FR-0503**: The HLD MUST document the complete ARCA integration architecture: WSAA authentication flow (TRA → CMS → LoginCMS → TA), per-service X.509 certificate management, Redis token caching strategy, and CAEA offline mode with the legal constraint on authorization timing.
- **FR-0504**: The HLD MUST document the weighbridge integration protocol stack in three tiers: (1) Modbus RTU / ASCII command-response, (2) continuous ASCII stream fallback, (3) KYASERV RS-232-to-Ethernet bridge — per ADR-032.
- **FR-0505**: The HLD MUST document the offline-first sync architecture including store-and-forward queue mechanics, all 5 conflict resolution strategies with their target data types, and CPE validity window constraints.
- **FR-0506**: The HLD MUST document the security architecture across all 3 isolation layers (ORM TenantBoundManager, PostgreSQL RLS, IDOR/JWT validation) with a Mermaid defense-in-depth diagram showing independent enforcement at each layer.
- **FR-0507**: The HLD MUST document the Rust/PyO3 acceleration boundary including the 4 criteria for using Rust and a benchmark table showing all 7 measured speedups (feature branches 018-rust-crypto, 019-rust-fiscal-compute, and 021-rust-observability-hotpath).
- **FR-0508**: The HLD MUST include a step-by-step data flow diagram for the romaneo reception flow covering all 10 steps (arrival → gross weigh → sampling → quality analysis → merma calculation → grade assignment → unload → tare weigh → net calculation → romaneo issuance), with each step identifying the responsible component.
- **FR-0509**: The HLD MUST include a data flow diagram for the fiscal authorization flow covering both the CAE path (online, per-invoice round-trip to ARCA) and the CAEA path (offline, pre-authorized quincena batch).
- **FR-0510**: The HLD MUST document the AI/ML readiness 4-layer data architecture (Operational, Behavioural, Quality History, Physical State/IoT) per ADR-033, ADR-034, ADR-035.
- **FR-0511**: The HLD MUST include a technology decisions cross-reference table linking each HLD section to its corresponding ADR(s), covering all 8 ADR categories (Infrastructure, Data Architecture, Grain Domain, Security, Fiscal Integration, Offline & Sync, Performance, AI/ML Readiness).
- **FR-0512**: The HLD MUST document the deployment topology for both environments: (1) development via Docker Compose with all services, ports, and Rust build stage and (2) production under the single-server SMB constraint with full-cloud and hybrid options.

### Key Entities

- **HLD Document**: The output artifact — `Docs/Project Blueprint/High-Level Design (HLD).md`, version 1.0, status Accepted. Standalone — readable without consulting specs 01-04.
- **C4 Context Diagram**: Mermaid diagram showing GraviTea system boundary and all 8 external actors.
- **C4 Container Diagram**: Mermaid diagram showing 5 internal containers with labeled communication protocols.
- **Romaneo Reception Data Flow**: 10-step sequence diagram identifying responsible component at each step.
- **Fiscal Authorization Data Flow**: Branching flow diagram covering CAE path and CAEA offline path.
- **Technology Cross-Reference Table**: Table mapping HLD sections → ADR IDs → ADR titles for all 8 decision categories.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-0501**: A developer unfamiliar with the system identifies the responsible Django app for any domain entity in the Data Model within 2 minutes of reading section 5 (Component Overview).
- **SC-0502**: A reader can answer "Why is store-and-forward CAE legally invalid for offline invoicing?" within 1 minute using only section 6 (ARCA Integration Architecture).
- **SC-0503**: All 5 conflict resolution strategies and their target data types are locatable in section 8.4 within 30 seconds using the table of contents.
- **SC-0504**: The romaneo reception flow diagram covers all 10 steps in sequence with no gaps; a QA engineer can derive acceptance tests directly from the step descriptions.
- **SC-0505**: A new team member reading only this document can name all external ARCA services, the 3 tenant isolation layers, and the 4 AI/ML data layers without consulting specs 01-04.
- **SC-0506**: Zero hedging language ("TBD", "TODO", "FIXME", "possibly", "might consider") in the output document — grep returns 0 matches.
- **SC-0507**: All Mermaid diagrams render without syntax errors — C4 context, C4 container, defense-in-depth, romaneo flow, fiscal flow, production topology all produce valid output.
- **SC-0508**: Every architecture section cross-references at least one ADR using the exact "ADR-NNN" format; the Technology Cross-Reference Table covers all 8 ADR categories.

## Non-Functional Requirements

- **NF-0501**: All diagrams MUST use text-based notation (Mermaid or ASCII art) — no binary image files.
- **NF-0502**: Every architecture section MUST cross-reference the relevant ADR(s) using the exact format "ADR-NNN" with the ADR title.
- **NF-0503**: Zero hedging language — no "TBD", "TODO", "FIXME", "possibly", "might consider".
- **NF-0504**: Document metadata: version 1.0, date 2026-03-17, status Accepted, owner GraviTea Architecture Team.
- **NF-0505**: All integration flows MUST include error paths (WSAA timeout, weighbridge disconnect, CPE expiry, CAEA quincena expiry).
- **NF-0506**: All protocol choices MUST trace their rationale to the specific ADR — the HLD cites, not invents, architectural rationale.
- **NF-0507**: Self-contained — a new engineer reading only this document understands external integrations, containers, core data flows, and architectural constraints.

## Scope

### In Scope

- C4 Level 1 and Level 2 diagrams (system context and container)
- Component overview for all 8 Django apps
- Complete ARCA integration architecture (WSAA, WSLPG, WSCPE, WSFEv1, CAEA, SISA)
- Weighbridge integration 3-tier protocol stack with error paths
- Offline-first architecture: sync protocol, conflict resolution (5 strategies), store-and-forward queue
- Security architecture: 3-layer defense-in-depth, field encryption, key management
- Rust/PyO3 acceleration boundary with benchmark evidence (7 modules)
- Data flow diagrams: romaneo reception (10 steps), fiscal authorization (CAE + CAEA paths), sync flow
- Deployment topology: Docker Compose dev environment and production SMB single-server options
- AI/ML readiness 4-layer data architecture
- Technology decisions cross-reference table (all 8 ADR categories)

### Out of Scope

- Database ERD and entity field details (spec-03, Data Model & Domain Model)
- Individual ADR rationale text (spec-04, ADR document)
- REST API endpoint specifications (spec-06)
- Detailed ARCA SOAP XML schemas and example payloads (spec-08a)
- Phase 4 ML model implementation details (referenced informatively only)
- Frontend architecture (not yet defined)

## Dependencies and Assumptions

### Upstream Dependencies

- **spec-03** complete: `Docs/Project Blueprint/Data Model & Domain Model.md` v1.0 — entity names, RLS approach, Ironclad Principles P1–P5.
- **spec-04** complete: `Docs/Project Blueprint/Architecture Decision Records (ADR).md` v1.0 — all 35 ADRs. The HLD cites these; it does not restate rationale.

### Downstream Dependents

- **spec-06** (REST API Design) — API patterns constrained by container architecture and security layers here.
- **spec-08a** (ARCA Grain Integration Guide) — Section 6 of HLD is the architectural overview spec-08a expands.
- **spec-09 through spec-12** (all implementation specs) — implementation agents reference HLD for app/layer context.

### Assumptions

- Django app naming: `apps/core`, `apps/auth`, `apps/acopio`, `apps/cuentas`, `apps/facturacion`, `apps/liquidaciones`, `apps/sync`, `apps/core/observability` — consistent with PRD module decomposition. `apps/liquidaciones` is treated as a distinct app from `apps/facturacion` per PRD §3.1. Section 5 of the HLD presents all 8 apps uniformly as the intended architecture, with inline "(Phase 2)" annotations on apps outside Phase 1 MVP scope: `apps/facturacion` (electronic invoicing, Wave 6) and `apps/liquidaciones` (WSLPG + SISA gate, spec-14). Phase 1 apps (specs 09–12): `apps/core`, `apps/auth`, `apps/acopio`, `apps/cuentas`, `apps/sync`, `apps/core/observability`.
- The 10-step romaneo reception flow is the canonical representation; PRD's 11-step breakdown treats silo assignment as a sub-step of romaneo issuance.
- Production cloud provider is GCP (Cloud Run + Cloud SQL Enterprise Plus), consistent with Google Cloud Secret Manager references in the ADR document.
- Qdrant is an optional container — required for dev/RAG workflows, optional for Phase 1 and Phase 2 production deployments.
