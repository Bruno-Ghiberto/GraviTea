# Tasks: Architecture Decision Records (ADR)

**Input**: Design documents from `/specs/004-acopio-adr/`
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, quickstart.md ✅
**Target deliverable**: `Docs/Project Blueprint/Architecture Decision Records (ADR).md`

**Organization**: Tasks grouped by user story (US1–US4). All writing references `research.md` for pre-extracted source content — no additional context-switching needed.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can be written in parallel (independent ADR entry, no blocking dependency)
- **[Story]**: Which user story this task primarily serves
- Source for every writing task: `specs/004-acopio-adr/research.md` + `specs/004-acopio-adr/quickstart.md`

---

## Phase 1: Setup

**Purpose**: Create the target file; confirm all source references are reachable.

- [X] T001 Create `Docs/Project Blueprint/Architecture Decision Records (ADR).md` with a blank header (version 1.0 placeholder)
- [X] T002 Confirm research.md sections §4–§11 are readable and ADR extracts match source documents (spot-check 3 ADRs against originals in `specs/003-acopio-data-model/research.md` and `.specify/memory/constitution.md`)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Document skeleton and navigation infrastructure that every user story depends on.

**⚠️ CRITICAL**: Phases 3–6 require the §1 metadata block and §3 format guide to be present first. Phase 6 requires §12 and §2 to be complete.

- [X] T003 Write §1 Document Metadata in `Docs/Project Blueprint/Architecture Decision Records (ADR).md` — include table: Title, Version 1.0, Date 2026-03-17, Owner, Upstream Documents (Vision v1.0 / PRD v1.0 / Data Model v1.0 / Constitution), Status Accepted
- [X] T004 Write §3.1 ADR Format Template in `Docs/Project Blueprint/Architecture Decision Records (ADR).md` — show the exact 7-field template (title, status, date, context, decision, consequences +/-, alternatives, cross-references) using a fictional example
- [X] T005 [P] Write §3.2 Status Lifecycle in `Docs/Project Blueprint/Architecture Decision Records (ADR).md` — define 4 states: Proposed, Accepted, Superseded, Deprecated with 1-sentence meaning each; state all entries in this document are Accepted
- [X] T006 [P] Write §3.3 Cross-Reference Convention in `Docs/Project Blueprint/Architecture Decision Records (ADR).md` — explain format "Document vX.Y Section Z.Z"; list where to find each upstream doc in repo
- [X] T007 Write §3.4 Supersession Rules in `Docs/Project Blueprint/Architecture Decision Records (ADR).md` — explain: new ADR created with status Proposed referencing original; original updated to Superseded with forward reference; both coexist until new ADR accepted (covers edge case from spec.md)
- [X] T008 Add §2 ADR Index placeholder to `Docs/Project Blueprint/Architecture Decision Records (ADR).md` — create table with columns (ID, Title, Category, Status, Date) and 35 placeholder rows labeled TBD — this section is completed in T047

**Checkpoint**: Skeleton complete (§1, §2 placeholder, §3). User story phases can now begin.

---

## Phase 3: User Story 1 — Developer Lookup (Priority: P1) 🎯 MVP

**Goal**: A developer or AI agent can find the rationale, constraints, and rejected alternatives for any Infrastructure, Data Architecture, or Grain Domain decision without consulting any other document.

**Independent Test**: Select ADR-008 (append-only ledger), ADR-010 (global entities), and ADR-018 (merma per-step not stored). Verify each entry is self-contained: context explains the problem, decision states the choice, consequences include both +/-, alternatives include ≥1 rejected option with specific rationale, cross-references use exact section format.

**Acceptance Scenario Coverage**: T009–T028 cover US1-AS1 (ADR-008 append-only ledger) and US1-AS2 (ADR-018 merma per-step not stored). US1-AS3 (ADR-031 Rust/PyO3 acceleration boundary) is covered in Phase 5 T041 — full US1 satisfaction requires Phases 1–3 + Phase 5.

### §4 Infrastructure (ADR-001–005) — 5 ADRs

Source: `specs/004-acopio-adr/research.md` §4

- [X] T009 [P] [US1] Write ADR-001: PostgreSQL 18.1 as Primary Database in `Docs/Project Blueprint/Architecture Decision Records (ADR).md` — context: engine-enforced integrity; decision: PostgreSQL 18.1 as the foundation; rejected: MySQL (no native RLS), SQLite (no concurrent multi-tenant); cross-ref: Constitution Principle I, Data Model §1
- [X] T010 [P] [US1] Write ADR-002: UUID v4 as Primary Key Strategy in `Docs/Project Blueprint/Architecture Decision Records (ADR).md` — context: offline-first requires distributed ID generation; decision: UUID v4 auto-generated; rejected: auto-increment integer (sequential enumeration + sync conflicts); cross-ref: Data Model §1 Metadata, Constitution Principle VII
- [X] T011 [P] [US1] Write ADR-003: Modular Monolith via Django Apps in `Docs/Project Blueprint/Architecture Decision Records (ADR).md` — context: SMB team size, clear module boundaries; decision: modular monolith; rejected: microservices from day one (operational complexity); cross-ref: Constitution Principle III
- [X] T012 [US1] Write ADR-004: Shared Database / Shared Schema Multi-Tenancy in `Docs/Project Blueprint/Architecture Decision Records (ADR).md` — context: cost efficiency for SMB SaaS; decision: single database, RLS enforcement; rejected: schema-per-tenant (migration complexity), database-per-tenant (cost per tenant); cross-ref: Constitution Principle II, Data Model §1
- [X] T013 [US1] Write ADR-005: Three-Layer Tenant Isolation (ORM + RLS + IDOR) in `Docs/Project Blueprint/Architecture Decision Records (ADR).md` — context: single-point failure risk; decision: Layer 1 ORM + Layer 2 RLS + Layer 3 IDOR validation; rejected: ORM-only (raw SQL bypass); cross-ref: Constitution Principles II and V, Data Model §4.9

### §5 Data Architecture (ADR-006–013) — 8 ADRs

Source: `specs/004-acopio-adr/research.md` §5

- [X] T014 [P] [US1] Write ADR-006: Ironclad Principles Lineage and Reconciliation in `Docs/Project Blueprint/Architecture Decision Records (ADR).md` — context: three independent principle sets exist (Constitution I–XI, Vision 6 principles, Data Model P1–P5); decision: Constitution is foundational, Vision adds strategic framing, Data Model extends with P4/P5; cross-ref: Constitution I–XI, Vision v1.0 Section 2.3, Data Model v1.0 Section 2.1
- [X] T015 [P] [US1] Write ADR-007: DECIMAL(17,3) for Weights/Money, DECIMAL(5,2) for Percentages in `Docs/Project Blueprint/Architecture Decision Records (ADR).md` — include critical domain fact: using wrong value (Hf vs Humedad Base) = ~168 kg error per 30-tonne truck; rejected: FLOAT (rounding errors in financial calculations); cross-ref: Constitution Principle I, Data Model v1.0 P1
- [X] T016 [P] [US1] Write ADR-008: Append-Only Ledger for Financial Immutability in `Docs/Project Blueprint/Architecture Decision Records (ADR).md` — list all affected entities: StockMovement, Comprobante, GrainMovement, AccountMovement, MermaCalculation; rejected: soft-delete with audit log (allows mutation); cross-ref: Data Model v1.0 P3, Vision v1.0 Section 2.3
- [X] T017 [P] [US1] Write ADR-009: Dual Inventory Architecture (Grain vs Discrete SKU) in `Docs/Project Blueprint/Architecture Decision Records (ADR).md` — grain = GrainLot + GrainMovement (kg-based); agronomia inputs = Product + StockMovement (unit-based); rejected: single unified inventory model; cross-ref: Data Model v1.0 Sections 5.6 and §7, PRD v1.0 Sections 4.3 and 4.7
- [X] T018 [P] [US1] Write ADR-010: Global vs Per-Tenant Entity Classification in `Docs/Project Blueprint/Architecture Decision Records (ADR).md` — explicitly name all GLOBAL entities: GrainType, ToleranceTable, MermaTable, BusinessTemplate; rationale: regulatory mandates; rejected: per-tenant tolerance overrides (legal/commercial dispute risk); cross-ref: spec-03 research Decisions D-004 and D-006, Data Model v1.0 Sections 5.1 and 5.2
- [X] T019 [P] [US1] Write ADR-011: Campaign-Year Segregation Pattern in `Docs/Project Blueprint/Architecture Decision Records (ADR).md` — YYYY/YY format, April–March cycle, composite key (plant_id, grain_code, campaign_id) per RG 3593; WSLPG uses 4-digit format (2425); document all three interaction types: storage (grain segregated by campaign in silos), accounting (grain sub-ledger in ProducerAccount is campaign-scoped), fiscal (WSLPG `campania` field uses 4-digit format); rejected: calendar-year segregation (harvest spans two calendar years); cross-ref: PRD v1.0 Sections 4.3 (storage), 4.4 (accounting), 4.5 (fiscal), Data Model v1.0 Section 5.1
- [X] T020 [US1] Write ADR-012: ON DELETE Behavior — RESTRICT Default with CASCADE/SET_NULL Exceptions in `Docs/Project Blueprint/Architecture Decision Records (ADR).md` — list all CASCADE exceptions (CPE, QualityAnalysis, MermaCalculation → Romaneo) and all SET_NULL fields (weighbridge_device, storage_unit, grain_lot on Romaneo); rejected: RESTRICT on all (makes draft deletion impossible); cross-ref: spec-03 research Decision D-007, Constitution Principle I
- [X] T021 [US1] Write ADR-013: Posición Consolidada as Derived View (Not Stored) in `Docs/Project Blueprint/Architecture Decision Records (ADR).md` — context: consistency risk of stored aggregate; decision: computed on-demand from per-plant ProducerAccount balances; rejected: materialized view (deferred to optimization if profiling shows need); cross-ref: spec-03 research Decision D-005, PRD v1.0 Section 4.4

### §6 Grain Domain (ADR-014–020) — 7 ADRs

Source: `specs/004-acopio-adr/research.md` §6

- [X] T022 [P] [US1] Write ADR-014: MermaTable Scope — Zarandeo Only, Constants on GrainType in `Docs/Project Blueprint/Architecture Decision Records (ADR).md` — include fixed constants table (manipuleo/volatil per grain); rejected: full MermaTable with all 4 params (manipuleo/volatil never change, unnecessary versioning); cross-ref: spec-03 research Decision D-001
- [X] T023 [P] [US1] Write ADR-015: QualityParameter Inline on QualityAnalysis (Not Separate Entity) in `Docs/Project Blueprint/Architecture Decision Records (ADR).md` — list all 9 fixed parameters; grain-type conditionality at application layer; rejected: standalone QualityParameter entity (over-engineering for fixed set); cross-ref: spec-03 research Decision D-002
- [X] T024 [P] [US1] Write ADR-016: WeighbridgeDevice as Separate Entity in `Docs/Project Blueprint/Architecture Decision Records (ADR).md` — rationale: accumulates calibration history, enables multi-scale branches, regulatory audit traceability; rejected: FK to Branch (no device traceability), FK to StorageUnit (wrong entity type); cross-ref: spec-03 research Decision D-003
- [X] T025 [P] [US1] Write ADR-017: Grade Fields on Romaneo (Not QualityAnalysis) in `Docs/Project Blueprint/Architecture Decision Records (ADR).md` — grado_asignado + bonificacion_rebaja_pct on Romaneo; for oleaginosas grado_asignado=0; rationale: grade is the commercial outcome of quality analysis; cross-ref: Data Model v1.0 Section 5.3
- [X] T026 [P] [US1] Write ADR-018: Per-Step Merma kg Not Stored (Derived from Intermediates) in `Docs/Project Blueprint/Architecture Decision Records (ADR).md` — only peso_post_* intermediates + input percentages stored; step-kg derivable from consecutive intermediates; rejected: storing step-kg (redundant + consistency risk); cross-ref: Data Model v1.0 Section 5.5
- [X] T027 [P] [US1] Write ADR-019: Single Form 1116-C per Grain Type (WSLPG Constraint) in `Docs/Project Blueprint/Architecture Decision Records (ADR).md` — codGrano at XML root level forces one liquidación per grain type; software must split multi-grain payloads; cross-ref: PRD v1.0 Section 4.5, Data Model v1.0 Section 8.3
- [X] T028 [P] [US1] Write ADR-020: Own Grain vs Third-Party Grain Accounting Separation in `Docs/Project Blueprint/Architecture Decision Records (ADR).md` — own = 1.3.XX Bienes de cambio (balance-sheet); third-party = 8.1.XX Cuentas de orden (off-balance-sheet); tracked via GrainLot.is_own_grain; cross-ref: Data Model v1.0 Section 5.6
- [X] T029 [US1] Run Gate 2 checkpoint on `Docs/Project Blueprint/Architecture Decision Records (ADR).md` — verify: all 13 ADRs (§4–§5) have complete template fields; Constitution Principles I, II, III each referenced from ≥1 ADR; ADR-010 explicitly names all GLOBAL entities; ADR-012 lists all CASCADE + SET_NULL exceptions; every ADR has ≥1 rejected alternative

**Checkpoint**: §4–§6 complete (20 ADRs). US1 primary acceptance scenarios satisfied (ADR-008 append-only, ADR-018 merma not stored). Gate 2 passed.

---

## Phase 4: User Story 2 — Architect Supersession Evaluation (Priority: P2)

**Goal**: An architect can evaluate whether ADR-021–ADR-027 (security and fiscal decisions) should be superseded by reading the original trade-off analysis as a baseline. The §3.4 Supersession Rules established in Phase 2 provides the process.

**Independent Test**: Select ADR-026 (CAEA for offline fiscal). Verify the context explains the legal constraint (authorization must precede issuance), the decision explains CAEA vs CAE-only, and the alternatives section explains why store-and-forward CAE is legally invalid. This is the exact information an architect needs to evaluate supersession if ARCA changes offline authorization rules.

### §7 Security Decisions (ADR-021–024) — 4 ADRs

Source: `specs/004-acopio-adr/research.md` §7

- [X] T030 [P] [US2] Write ADR-021: JWT RS256 with Custom Tenant/Branch Claims in `Docs/Project Blueprint/Architecture Decision Records (ADR).md` — RS256 (asymmetric, 4096-bit); custom claims: tenant_id, branch_id, email, full_name; access 15min / refresh 7 days; rejected: HS256 (symmetric — key compromise affects all tenants); cross-ref: Constitution Principles V and XI
- [X] T031 [P] [US2] Write ADR-022: AES-256-GCM Field-Level Encryption with HMAC-SHA256 Blind Index in `Docs/Project Blueprint/Architecture Decision Records (ADR).md` — application-level for PII; master keys in GCP Secret Manager; Rust-accelerated (8.7x); rejected: database-level TDE (does not protect against application-layer breaches); cross-ref: Constitution Principle IV
- [X] T032 [P] [US2] Write ADR-023: Argon2 Password Hashing (Not bcrypt) in `Docs/Project Blueprint/Architecture Decision Records (ADR).md` — memory-hard, GPU/ASIC resistant via argon2-cffi; rejected: bcrypt (lower GPU resistance); cross-ref: Constitution Principle V
- [X] T033 [P] [US2] Write ADR-024: SSRF Validation Pipeline (Rust) in `Docs/Project Blueprint/Architecture Decision Records (ADR).md` — validate_url_safety + check_resolved_ip; 831 lines, 308 tests; Rust for adversarial input regex (ReDoS protection); cross-ref: Feature branch 022-ssrf-validation-pipeline

### §8 Fiscal Integration Decisions (ADR-025–027) — 3 ADRs

Source: `specs/004-acopio-adr/research.md` §8

- [X] T034 [P] [US2] Write ADR-025: ARCA Web Service Architecture (WSAA → WSLPG + WSCPE + WSFEv1) in `Docs/Project Blueprint/Architecture Decision Records (ADR).md` — WSAA for auth (TRA + CMS); WSFEv1 for standard CAE; WSLPG for grain liquidaciones; WSCPE for CPE/CTG lifecycle; per-service certificate management; cross-ref: Constitution Principle VI, PRD v1.0 Sections 4.5 and 4.6
- [X] T035 [US2] Write ADR-026: CAEA for Offline Fiscal Operations During Harvest in `Docs/Project Blueprint/Architecture Decision Records (ADR).md` — CAEA = batch pre-authorized codes for quincenas; enables offline invoice issuance; MUST explicitly state: ARCA requires authorization BEFORE issuance for legal validity; deferred CAE = legally invalid document; rejected: CAE-only + store-and-forward (legally invalid at issuance time); cross-ref: PRD v1.0 Section 4.6, Feature branch 024-rust-arca-batch
- [X] T036 [US2] Write ADR-027: SISA-Tier Retention Calculation at LPG Filing Time in `Docs/Project Blueprint/Architecture Decision Records (ADR).md` — retention rates determined by SISA Estado (1/2/3) at filing time; SISA verification is a BLOCKING GATE before WSLPG filing; include IVA rate table (Estado 1→5%, 2→8%, 3→10.5%, unregistered→16%); cross-ref: PRD v1.0 Section 4.5, RG 5689/2025
- [X] T037 [US2] Run Gate 3 checkpoint on `Docs/Project Blueprint/Architecture Decision Records (ADR).md` — verify: all 7 Grain Domain ADRs (014–020) complete with D-001–D-007 mapped; all 4 Security ADRs (021–024) cover auth/encryption/password/SSRF; all 3 Fiscal ADRs (025–027); ADR-019 states single-grain WSLPG constraint; ADR-026 explains legal authorization timing; Constitution Principles IV, V, VI, XI each referenced; every ADR has ≥1 rejected alternative

**Checkpoint**: §7–§8 complete (7 ADRs, total 27 ADRs written). Gate 3 passed.

---

## Phase 5: User Story 3 — Product Owner Reviews Constraints (Priority: P3)

**Goal**: The product owner can navigate to §9 (offline decisions) and §10 (performance decisions) and understand the product-facing consequences — specifically: what offline-first enables and constrains, why Rust is used, and what the weighbridge protocol stack means for hardware decisions.

**Independent Test**: Select ADR-028 (offline-first as base) and ADR-031 (Rust/PyO3 boundary). Verify: ADR-028 consequences section states product implications clearly (every truck reception completes locally regardless of connectivity). ADR-031 consequences section explains the tradeoff of Rust maintenance cost vs. performance gain. A non-technical PO can understand the business impact without reading code.

### §9 Offline & Sync Decisions (ADR-028–030) — 3 ADRs

Source: `specs/004-acopio-adr/research.md` §9

- [X] T038 [P] [US3] Write ADR-028: Offline-First as Base Architecture (Not Fallback) in `Docs/Project Blueprint/Architecture Decision Records (ADR).md` — system assumes network unreliable; every truck reception completes locally; sync is secondary non-blocking; include market evidence (44% of operators report "regular" connectivity, INTA/ENACOM 2021); rejected: online-first with offline fallback ("fallback" = degraded experience for primary use case); cross-ref: Vision v1.0 Section 2.3, Constitution Principle VII
- [X] T039 [US3] Write ADR-029: Conflict Resolution Taxonomy (5 Strategies by Data Type) in `Docs/Project Blueprint/Architecture Decision Records (ADR).md` — list all 5 strategies with per-data-type mapping: configuration→server_wins, inventory→last_write_wins, transactions→additive, customer/producer data→most_complete_wins, document numbering→server_assigns_final; Rust implementation in feature 023; cross-ref: Constitution Principle VII
- [X] T040 [US3] Write ADR-030: Store-and-Forward Queue for ARCA Web Service Calls in `Docs/Project Blueprint/Architecture Decision Records (ADR).md` — CPE confirmation calls (confirmarArriboCPE, descargadoDestinoCPE, confirmacionDefinitivaCPEAutomotor) queued locally; 5-day CPE validity window; cross-ref: PRD v1.0 Section 4.1

### §10 Performance Decisions (ADR-031–032) — 2 ADRs

Source: `specs/004-acopio-adr/research.md` §10

- [X] T041 [P] [US3] Write ADR-031: Rust/PyO3 Acceleration Boundary (When Rust, When Python) in `Docs/Project Blueprint/Architecture Decision Records (ADR).md` — include decision criteria (latency-sensitive >1000 calls/sec, GIL contention, CPU-bound, adversarial input); include measured benchmark table (crypto 8.7x, IVA 4.4x, CUIT 3.1x, observability 2.6x, stock 2.1x); stay-Python criteria (ORM, orchestration, API handlers, one-off); rejected: pure Python everywhere (measured gaps), pure Rust server (loses Django ecosystem); cross-ref: Feature branches 017–025, CLAUDE.md Active Technologies
- [X] T042 [P] [US3] Write ADR-032: Weighbridge Integration Architecture (RS-232 / Modbus / TCP Bridge) in `Docs/Project Blueprint/Architecture Decision Records (ADR).md` — primary: Modbus RTU (Sipel Orion) or command/response (Systel); fallback: continuous ASCII stream (GaMa A12); network: KYASERV RS232-Ethernet bridge for LAN access; cross-ref: PRD v1.0 Section 4.1
- [X] T043 [US3] Run Gate 4 checkpoint on `Docs/Project Blueprint/Architecture Decision Records (ADR).md` — verify: all 3 Offline ADRs (028–030) complete; both Performance ADRs (031–032) complete; ADR-029 lists all 5 strategies with data-type mapping; ADR-031 includes specific decision criteria + measured benchmark table; ADR-032 includes protocol fallback chain; Constitution Principles VII and VIII each referenced; every ADR has ≥1 rejected alternative

**Checkpoint**: §9–§10 complete (5 ADRs, total 32 ADRs written). Gate 4 passed.

---

## Phase 6: User Story 4 — New Team Member Onboarding (Priority: P3)

**Goal**: A new team member can use the ADR index to navigate to any decision, understand the 8-category structure, and see how architectural decisions relate to each other via the dependency graph. The AI/ML roadmap ADRs explain the long-term trajectory without requiring reading of spec-01 through spec-03.

**Independent Test**: Give the complete ADR document to someone unfamiliar with the project. They should be able to: (a) click any index anchor link and land on the correct ADR heading, (b) answer "what is the conflict resolution strategy for inventory data?" within 30 seconds using the index, (c) identify from the dependency graph that ADR-028 (offline-first) constrains ADR-026 (CAEA) and ADR-029 (conflict resolution).

### §11 AI/ML Readiness Decisions (ADR-033–035) — 3 ADRs

Source: `specs/004-acopio-adr/research.md` §11

- [X] T044 [P] [US4] Write ADR-033: AI-Ready Data Architecture (4-Layer Strategy) in `Docs/Project Blueprint/Architecture Decision Records (ADR).md` — Layer 1 Operational, Layer 2 Behavioural, Layer 3 Quality History, Layer 4 Physical State (IoT); no post-hoc data reconstruction needed; rejected: post-hoc data structuring (requires data archaeology, ML delayed by months); cross-ref: Data Model v1.0 Section 12.1, P4 and P5, Vision v1.0 Section 2.3
- [X] T045 [P] [US4] Write ADR-034: Provenance Fields on All Grain Domain Models in `Docs/Project Blueprint/Architecture Decision Records (ADR).md` — created_at, updated_at, created_by, device_id on all grain entities; enables behavioral analytics and fraud detection baselines; cross-ref: Data Model v1.0 P5 and Section 12.3
- [X] T046 [P] [US4] Write ADR-035: Measurement-Timestamp Pairing for Behavioral Analytics in `Docs/Project Blueprint/Architecture Decision Records (ADR).md` — 6 named timestamps per romaneo (ts_entrada, ts_pesada_bruta, ts_calado, ts_analisis, ts_descarga, ts_tara); each measurement paired with temporal context; enables arrival-to-departure cycle time analysis and weighbridge fraud detection; cross-ref: Data Model v1.0 P5 and Section 5.3

### §12 Decision Dependency Graph

- [X] T047 [US4] Write §12 Decision Dependency Graph in `Docs/Project Blueprint/Architecture Decision Records (ADR).md` — create Mermaid `graph TD` using the starter from `specs/004-acopio-adr/quickstart.md` Section 5; key dependency chains: ADR-001→ADR-004→ADR-005; ADR-008→ADR-012; ADR-028→ADR-002/ADR-026/ADR-029/ADR-030; ADR-006→ADR-007/ADR-008/ADR-033; ADR-009→ADR-010/ADR-011; ADR-021→ADR-005; ADR-025→ADR-026/ADR-027

### §2 ADR Index (Final Population)

- [X] T048 [US4] Populate §2 ADR Index table in `Docs/Project Blueprint/Architecture Decision Records (ADR).md` — replace all 35 placeholder rows with: ID (linked anchor, format `[ADR-001](#adr-001-postgresql-181-as-primary-database)`), Title, Category, Status (Accepted), Date (2026-03-17); verify all 35 Markdown anchor links resolve to headings

**Checkpoint**: §11 complete (3 ADRs, total 35 ADRs written). §12 and §2 fully populated. US4 acceptance scenarios satisfied (index links work, dependency graph renders).

---

## Final Phase: Polish & Cross-Cutting Concerns

**Purpose**: Verification gates + quality checks that apply across all sections.

- [X] T049 Run Gate 5 checkpoint on `Docs/Project Blueprint/Architecture Decision Records (ADR).md` — count heading lines matching `### ADR-NNN:` pattern; confirm total ≥ 30 (target: 35)
- [X] T050 [P] Verify Constitution principle coverage in `Docs/Project Blueprint/Architecture Decision Records (ADR).md` — search document for each of Principles I through XI; confirm each appears in ≥1 ADR's Cross-References field; record which ADR covers each (use traceability map in `specs/004-acopio-adr/research.md`)
- [X] T051 [P] Verify spec-03 domain decision coverage in `Docs/Project Blueprint/Architecture Decision Records (ADR).md` — confirm D-001 through D-007 each appear in ≥1 ADR; spot-check D-007 (CASCADE exceptions) maps to ADR-012
- [X] T052 [P] Grep for hedging language in `Docs/Project Blueprint/Architecture Decision Records (ADR).md` — search for: "TBD", "TODO", "FIXME", "possibly", "might consider", "under review", "to be determined"; all must return 0 matches
- [X] T053 Verify §12 Mermaid dependency graph in `Docs/Project Blueprint/Architecture Decision Records (ADR).md` — paste graph code into mermaid.live or equivalent renderer; confirm no syntax errors; all referenced ADR node IDs match actual heading anchors
- [X] T054 Complete done criteria checklist from `specs/004-acopio-adr/quickstart.md` — mark all 12 items; document is complete only when all 12 pass

---

## Dependencies

```
Phase 1 (T001–T002)
  → Phase 2 (T003–T008) — skeleton required
    → Phase 3 (T009–T029) — foundational §3 required before writing any ADR
    → Phase 4 (T030–T037) — independent of Phase 3 content (parallel if team available)
    → Phase 5 (T038–T043) — independent of Phases 3–4 (parallel)
      → Phase 6 T047 (§12 Dependency Graph) — must reference ADR IDs from Phases 3–5
      → Phase 6 T048 (§2 Index) — must reference ADR IDs from Phases 3–6
        → Final Phase (T049–T054) — requires all ADRs + §12 + §2 complete
```

**Parallelizable groups within a phase** (all marked [P]):
- Phase 3: T009–T015 (§4 + §5 first 5 ADRs) can be written simultaneously; T022–T028 (§6) can be written simultaneously
- Phase 4: T030–T034 (§7 + ADR-025) can be written simultaneously
- Phase 5: T038 and T041–T042 can be written simultaneously
- Phase 6: T044–T046 (§11) can be written simultaneously

---

## Implementation Strategy

**MVP Scope = Phase 3 (US1)**: Phase 3 alone delivers the primary use case (developer lookup). A document with §1, §3, and §4–§6 (20 ADRs) satisfies US1 completely.

**Incremental Delivery**:
1. Phases 1–2 + Phase 3 → MVP (US1 satisfied, 20 ADRs)
2. + Phase 4 → Architect supersession baseline (US2 satisfied, 27 ADRs)
3. + Phase 5 → PO constraint visibility (US3 satisfied, 32 ADRs)
4. + Phase 6 + Final → Full document (US4 + polish, 35 ADRs, all gates)

**For single-author sequential writing**: Follow the task order numerically T001→T054. Each task provides the exact ADR ID, source reference (research.md section), and required content checklist.

---

## Summary

| Phase | Stories | Tasks | ADRs Written | Parallelizable |
|-------|---------|-------|-------------|----------------|
| 1 Setup | — | 2 | 0 | — |
| 2 Foundational | — | 6 | 0 | T005, T006 |
| 3 US1 Developer Lookup (P1) | US1 | 21 | 20 | 17 of 21 |
| 4 US2 Architect Supersession (P2) | US2 | 8 | 7 | 5 of 8 |
| 5 US3 PO Constraints (P3) | US3 | 6 | 5 | 4 of 6 |
| 6 US4 Onboarding (P3) | US4 | 5 | 3 | 3 of 5 |
| Final Polish | — | 6 | 0 | 3 of 6 |
| **Total** | | **54** | **35** | **32 of 54** |
