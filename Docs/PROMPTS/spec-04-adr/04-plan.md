# Spec 04: Architecture Decision Records -- Plan Context

## Overview

**Target deliverable**: `Docs/Project Blueprint/Architecture Decision Records (ADR).md` (NEW file)
**Type**: Blueprint document (architectural reference, not code)
**Spec reference**: `specs/004-acopio-adr/spec.md`

This plan guides the creation of the ADR document from scratch. The output is a
~800-1200 line Markdown file with 35 ADR entries organized into 8 categories, a
navigable index table, and a decision dependency graph.

The ADR document is the **INSTITUTIONAL MEMORY** of the project -- the "why"
behind every significant architectural choice. It consolidates rationale scattered
across Vision v1.0, PRD v1.0, Data Model v1.0, the Constitution, and spec-03
research decisions (D-001 through D-007) into a single, navigable reference.

This is a NEW document. There is no existing ADR file to preserve or replace.

---

## Content Guidelines

### Tone & Voice

- **Rationale-driven reference document** -- not a narrative, not a tutorial
- Each ADR is self-contained: a reader understands the decision without leaving the entry
- Context sections explain the PROBLEM or NEED, not the solution (decision does that)
- Consequences state both POSITIVES and NEGATIVES honestly -- no sales pitch
- Alternatives Considered sections treat rejected options fairly, with specific rejection rationale
- Cross-references use exact section numbers: "Vision v1.0 Section 2.3", "Constitution Principle VII"
- No hedging: no "TBD", "possibly", "might consider" -- every ADR is either Accepted or not included

### Audience

- **Primary**: Developers and AI agents modifying the codebase (need to understand constraints before editing)
- **Secondary**: Technical architect evaluating future decision changes (needs original trade-off analysis)
- **Tertiary**: Product owner understanding architectural constraints on feature roadmap
- **Quaternary**: New team members onboarding to the project architecture

### Language

- English is the primary language
- Spanish canonical domain terms used inline when referencing grain-specific concepts: romaneo, merma, campaña, acopiador, liquidación, fijación, pizarra, canje
- First occurrence of each Spanish term includes English in parentheses
- Technology names used freely (unlike the spec, which was technology-agnostic -- the ADR document IS about technology choices)

### Level of Detail

- **Context**: 2-4 sentences explaining the problem or need that prompted the decision
- **Decision**: 1-3 sentences stating the chosen approach clearly and declaratively
- **Consequences**: 2-4 bullet points each for positive and negative outcomes
- **Alternatives**: At least 1 rejected alternative per ADR, with 1-2 sentence rejection rationale
- **Cross-References**: Exact upstream source(s) with section numbers
- No code examples in ADRs (this is a design rationale document, not a cookbook)

### ADR Entry Template

Every ADR MUST follow this exact structure:

```markdown
### ADR-NNN: Title

**Status**: Accepted | **Date**: YYYY-MM-DD

**Context**: [2-4 sentences: the problem, need, or constraint that prompted this decision]

**Decision**: [1-3 sentences: what was decided, stated declaratively]

**Consequences**:
- (+) [Positive consequence 1]
- (+) [Positive consequence 2]
- (-) [Negative consequence 1]
- (-) [Negative consequence 2]

**Alternatives Considered**:
- [Alternative A] -- Rejected because [specific rationale]
- [Alternative B] -- Rejected because [specific rationale] (optional, if multiple)

**Cross-References**: [Upstream document, specific section]
```

---

## Existing Content: Preserve vs. Replace

### No existing ADR document

This is a completely new file. No content exists at `Docs/Project Blueprint/Architecture Decision Records (ADR).md`.

### Source Material to Consolidate

The following sources contain scattered architectural decisions that must be formalized as ADRs:

| Source | Location | ADR Content |
|--------|----------|-------------|
| Constitution | `.specify/memory/constitution.md` | Principles I-XI: data model, multi-tenant, encryption, auth, fiscal, offline, queries, security, testing, JWT |
| Vision v1.0 | `Docs/Project Blueprint/Product Vision & Scope.md` | §2.2 Vertical Commitment, §2.3 Ironclad Principles (6 principles) |
| PRD v1.0 | `Docs/Project Blueprint/PRD.md` | §3.1 Module Architecture, §4.1-4.8 Module Specs (implicit arch decisions) |
| Data Model v1.0 | `Docs/Project Blueprint/Data Model & Domain Model.md` | §2 Ironclad Principles P1-P5, §3 ERD (entity classification), §12 AI-Ready |
| Spec-03 Research | `specs/003-acopio-data-model/research.md` | D-001 through D-007 domain decisions |
| Feature Branches | 001-025 commit history | Implicit technology choices (Rust/PyO3, Next.js, etc.) |

---

## Research Inputs

### RAG Queries (run BEFORE writing each section)

```bash
.venv/bin/python scripts/qdrant/qdrant_search.py -q "QUERY" -l 5
```

| ADR Category | RAG Queries |
|-------------|-------------|
| Infrastructure (§4) | "PostgreSQL RLS row level security multi tenant acopio" |
| Data Architecture (§5) | "dual inventory grain discrete SKU continuous", "tolerance tables regulatory Camara Arbitral versioning" |
| Grain Domain (§6) | "merma calculation formula sequential zarandeo secado", "romaneo data fields ERP capture weight quality" |
| Security (§7) | "AES 256 GCM encryption blind index HMAC", "JWT RS256 algorithm whitelist claims" |
| Fiscal (§8) | "WSLPG WSCPE WSAA architecture integration pattern", "CAEA offline fiscal invoice batch harvest" |
| Offline & Sync (§9) | "offline first sync conflict resolution grain operations" |
| Performance (§10) | "weighbridge scale integration protocol RS232 Modbus TCP" |
| AI/ML (§11) | "AI ready data architecture grain ERP training features" |

### Must-Read Project Files (via serena MCP)

Read ONLY the specific sections needed per ADR:

| File | Sections to Read |
|------|-----------------|
| `.specify/memory/constitution.md` | ALL 11 principles (I-XI) -- primary source for §4, §7 |
| `Docs/Project Blueprint/Product Vision & Scope.md` | §2.2, §2.3 only |
| `Docs/Project Blueprint/PRD.md` | §3.1, §4.1 (offline), §4.4 (dual ledger), §4.5 (WSLPG), §5.1-§5.2 (sync) |
| `Docs/Project Blueprint/Data Model & Domain Model.md` | §2 (P1-P5), §3 (ERD entity classification), §12 (AI-Ready) |
| `specs/003-acopio-data-model/research.md` | Domain Decisions D-001 through D-007 (ALL) |

---

## Section-by-Section Writing Plan

### Section 1: Document Metadata

**Effort**: Small
**Source**: New (no existing content)
**Action**:
- Create metadata table: Title, Version (1.0), Date, Owner, Status
- Add scope statement: "Captures architectural decisions from Vision v1.0, PRD v1.0, Data Model v1.0, and Constitution"
- Add upstream document references with version numbers

**RAG queries**: None needed

---

### Section 2: ADR Index

**Effort**: Medium (built LAST, after all ADRs written)
**Source**: Derived from completed ADR entries
**Action**:
- Create master index table with columns: ID, Title, Category, Status, Date
- Entries sorted by category, then by ADR number
- Each row links to the ADR heading via Markdown anchor (e.g., `[ADR-001](#adr-001-postgresql-181-as-primary-database)`)
- Minimum 35 rows (one per ADR)
- Add category subtotals

**Checkpoint**: Verify every ADR in §4-§11 has a corresponding row. Count ≥ 30.

---

### Section 3: How to Read This Document

**Effort**: Small
**Source**: New
**Action**:
- §3.1: ADR Format Template -- show the exact template structure used
- §3.2: Status Lifecycle -- explain Proposed → Accepted → Superseded → Deprecated with brief meaning per state
- §3.3: Cross-Reference Convention -- explain how to read "Vision v1.0 Section 2.3" and how to find upstream docs
- §3.4: Supersession Rules -- when/how to create a new ADR that supersedes an existing one (reference edge case from spec.md)

---

### Section 4: Infrastructure Decisions (ADR-001 through ADR-005)

**Effort**: Medium
**Primary sources**: Constitution I, II, III; Vision §2.3; Data Model §2 P1, P2

#### ADR-001: PostgreSQL 18.1 as Primary Database
- **Context source**: Constitution I ("The database is the last line of defense")
- **Key points**: Engine-enforced integrity, CHECK constraints, DECIMAL precision, RLS capability
- **Rejected alternative**: MySQL (no native RLS), SQLite (no concurrent multi-tenant)
- **Cross-ref**: Constitution Principle I, Data Model P1

#### ADR-002: UUID v4 as Primary Key Strategy
- **Context source**: Data Model §1 ("ID Strategy: UUID v4 auto-generated")
- **Key points**: No sequential enumeration (security), distributed generation (offline-first), no collision risk across branches
- **Rejected alternative**: Auto-increment integer (sequential enumeration attack, sync conflicts between offline branches)
- **Cross-ref**: Data Model §1 Metadata, Constitution VII (offline-first)

#### ADR-003: Modular Monolith via Django Apps (Not Microservices)
- **Context source**: Constitution III
- **Key points**: Clear module boundaries, independent testing, future service extraction possible
- **Rejected alternative**: Microservices from day one -- rejected for SMB team size, operational complexity, premature distribution
- **Cross-ref**: Constitution Principle III

#### ADR-004: Shared Database / Shared Schema Multi-Tenancy
- **Context source**: Data Model §1 ("Tenancy: Shared Database, Shared Schema, Hardened RLS")
- **Key points**: Single database instance, RLS enforces isolation, lower operational cost for SMB SaaS
- **Rejected alternative**: Schema-per-tenant (migration complexity, connection pooling overhead); Database-per-tenant (cost per tenant)
- **Cross-ref**: Constitution Principle II, Data Model §1

#### ADR-005: Three-Layer Tenant Isolation (ORM + RLS + IDOR)
- **Context source**: Constitution II, V
- **Key points**: Layer 1 ORM (TenantBoundManager), Layer 2 DB (PostgreSQL RLS), Layer 3 Validation (IDOR checks)
- **Rejected alternative**: ORM-only isolation -- rejected because single-point bypass via raw SQL or ORM bug
- **Cross-ref**: Constitution Principles II and V, Data Model P2

---

### Section 5: Data Architecture Decisions (ADR-006 through ADR-013)

**Effort**: Large (8 ADRs, most require reading multiple sources)
**Primary sources**: Data Model P1-P5, Constitution I, spec-03 research D-004/D-005/D-006/D-007

#### ADR-006: Ironclad Principles Lineage and Reconciliation
- **Context**: Three principle sets exist (Constitution I-XI, Vision 6 principles, Data Model P1-P5) -- reconcile overlap
- **Key points**: Constitution is the foundational layer; Vision adds strategic framing (offline-first, regulatory automation); Data Model extends with P4 (ML First) and P5 (AI-Ready)
- **Cross-ref**: Constitution I-XI, Vision §2.3, Data Model §2

#### ADR-007: DECIMAL(17,3) for Weights/Money, DECIMAL(5,2) for Percentages
- **Source**: Constitution I, Data Model P1
- **Key points**: FLOAT/DOUBLE prohibited (zero exceptions); display = 2 decimal places
- **Rejected alternative**: FLOAT -- rejected for rounding errors in financial calculations
- **Cross-ref**: Constitution Principle I, Data Model P1

#### ADR-008: Append-Only Ledger for Financial Immutability
- **Source**: Data Model P3
- **Key points**: StockMovement, Comprobante, GrainMovement, AccountMovement, MermaCalculation are append-only; errors corrected via contra-entries
- **Rejected alternative**: Soft-delete with audit log -- rejected because it allows mutation (UPDATE) which breaks forensic traceability
- **Cross-ref**: Data Model P3, Constitution I

#### ADR-009: Dual Inventory Architecture (Grain Continuous vs Discrete SKU)
- **Source**: 04-specify.md FR-008, Data Model §7 vs §5.6
- **Key points**: Grain = continuous kg-based ledger (GrainLot + GrainMovement); Agronomia inputs = discrete SKU (Product + StockMovement)
- **RAG query**: "dual inventory grain discrete SKU continuous"
- **Rejected alternative**: Single unified inventory model -- rejected because grain is measured in continuous kg (not discrete units), requires campaign segregation, and has different lifecycle (no expiration but has quality degradation)
- **Cross-ref**: Data Model §5.6, §7; PRD §4.3, §4.7

#### ADR-010: Global vs Per-Tenant Entity Classification
- **Source**: spec-03 research D-004, D-006
- **Key points**: GLOBAL (no tenant FK, no RLS): GrainType, ToleranceTable, MermaTable -- regulatory data shared by all tenants. PER-TENANT: CampanaConfig, Romaneo, all operational entities
- **Rejected alternative**: Per-tenant tolerance tables (tenant overrides) -- rejected because tolerance tables are legally mandated by Camara Arbitral, divergence = legal/commercial dispute risk
- **Cross-ref**: spec-03 research D-004, D-006; Data Model §5.1, §5.2

#### ADR-011: Campaign-Year Segregation Pattern
- **Source**: Data Model §5.1 (CampanaConfig), PRD §4.3
- **Key points**: "YYYY/YY" format (7 chars), April-March cycle, composite key (plant_id, grain_code, campaign_id) per RG 3593, per-tenant config
- **Rejected alternative**: Calendar-year segregation -- rejected because Argentine harvest campaigns span two calendar years
- **Cross-ref**: PRD §4.3, Data Model §5.1; RAG "campaign year management grain segregation"

#### ADR-012: ON DELETE Behavior -- RESTRICT Default with CASCADE/SET_NULL Exceptions
- **Source**: spec-03 research D-007, Constitution I
- **Key points**: Default RESTRICT (PROTECT). Exceptions: CASCADE for 1:1 satellites (CPE, QualityAnalysis, MermaCalculation → Romaneo); SET_NULL for nullable assignments (weighbridge_device, storage_unit, grain_lot on Romaneo)
- **Cross-ref**: spec-03 research D-007, Constitution Principle I, Data Model P1

#### ADR-013: Posicion Consolidada as Derived View (Not Stored)
- **Source**: spec-03 research D-005
- **Key points**: Cross-plant consolidated view computed on-demand from per-plant ProducerAccount balances; no stored aggregate
- **Rejected alternative**: Materialized view or stored aggregate -- rejected for consistency risk (aggregate diverges from source); deferred to implementation optimization if query profiling shows need
- **Cross-ref**: spec-03 research D-005; PRD §4.4 (posicion consolidada)

---

### Section 6: Grain Domain Decisions (ADR-014 through ADR-020)

**Effort**: Large (7 ADRs, domain-heavy, RAG-dependent)
**Primary sources**: spec-03 research D-001 through D-003, 04-specify.md

#### ADR-014: MermaTable Scope -- Zarandeo Only, Constants on GrainType
- **Source**: spec-03 research D-001
- **Key points**: MermaTable = versioned zarandeo thresholds only; manipuleo + volatil = fixed constants on GrainType (never change)
- **RAG query**: "merma calculation formula sequential zarandeo secado"
- **Cross-ref**: spec-03 research D-001

#### ADR-015: QualityParameter Inline on QualityAnalysis (Not Separate Entity)
- **Source**: spec-03 research D-002
- **Key points**: 9 fixed quality parameters defined inline; grain-type conditionality at application layer
- **Cross-ref**: spec-03 research D-002

#### ADR-016: WeighbridgeDevice as Separate Entity
- **Source**: spec-03 research D-003
- **Key points**: Physical asset with serial number, calibration history; multi-scale branches; regulatory audit traceability
- **Cross-ref**: spec-03 research D-003

#### ADR-017: Grade Fields on Romaneo (Not QualityAnalysis)
- **Source**: 04-specify.md Design Override 1 (from 03-implement.md)
- **Key points**: grado_asignado + bonificacion_rebaja_pct on Romaneo (not QualityAnalysis); for oleaginosas grado_asignado=0
- **Cross-ref**: Data Model §5.3 (Romaneo field table)

#### ADR-018: Per-Step Merma kg Not Stored (Derived from Intermediates)
- **Source**: 04-specify.md Design Override 2 (from 03-implement.md)
- **Key points**: Only peso_post_* intermediates + _pct inputs stored; zarandeo_kg/secado_kg/etc. derivable
- **Cross-ref**: Data Model §5.5 (MermaCalculation)

#### ADR-019: Single Form 1116-C per Grain Type (WSLPG Constraint)
- **Source**: 04-specify.md FR-018, WSLPG technical constraint
- **Key points**: codGrano at XML root level forces one liquidacion per grain type; software must generate separate payloads
- **RAG query**: "WSLPG Form 1116-C XML field types lengths"
- **Cross-ref**: Data Model §8.3; PRD §4.5

#### ADR-020: Own Grain vs Third-Party Grain Accounting Separation
- **Source**: RAG "own grain third party grain accounting balance sheet"
- **Key points**: Own grain = 1.3.XX Bienes de cambio (balance-sheet asset); third-party = 8.1.XX Cuentas de orden (off-balance-sheet); tracked via is_own_grain field on GrainLot
- **Cross-ref**: Data Model §5.6; RAG research 7.1

---

### Section 7: Security Decisions (ADR-021 through ADR-024)

**Effort**: Medium
**Primary sources**: Constitution IV, V, XI; Vision §2.3.4

#### ADR-021: JWT RS256 with Custom Tenant/Branch Claims
- **Source**: Constitution V, XI
- **Key points**: RS256 (asymmetric); custom claims: tenant_id, branch_id, email, full_name; algorithm whitelist enforced
- **Rejected alternative**: HS256 (symmetric) -- rejected because key compromise affects all tenants
- **Cross-ref**: Constitution V, XI

#### ADR-022: AES-256-GCM Field-Level Encryption with HMAC Blind Index
- **Source**: Constitution IV
- **Key points**: Application-level encryption for PII; blind indexing for searchable encrypted fields; master keys in Secret Manager
- **Rejected alternative**: Database-level TDE -- rejected because it doesn't protect against application-layer breaches
- **Cross-ref**: Constitution Principle IV

#### ADR-023: Argon2 Password Hashing (Not bcrypt)
- **Source**: Constitution V
- **Key points**: Memory-hard, GPU/ASIC resistant; via argon2-cffi
- **Rejected alternative**: bcrypt -- rejected for lower GPU resistance compared to Argon2
- **Cross-ref**: Constitution Principle V

#### ADR-024: SSRF Validation Pipeline (Rust)
- **Source**: Feature branch 022
- **Key points**: URL safety validation + resolved IP check; 831 lines, 308 tests; Rust for regex performance on adversarial inputs
- **Cross-ref**: Feature branch 022-ssrf-validation-pipeline

---

### Section 8: Fiscal Integration Decisions (ADR-025 through ADR-027)

**Effort**: Medium
**Primary sources**: Constitution VI; PRD §4.5, §4.6

#### ADR-025: ARCA Web Service Architecture (WSAA -> WSLPG + WSCPE + WSFEv1)
- **Source**: Constitution VI, PRD §4.5, §4.6
- **Key points**: WSAA for auth (TRA + CMS); WSFEv1 for standard invoicing (CAE); WSLPG for grain liquidaciones; WSCPE for CPE/CTG lifecycle; per-service certificate management
- **RAG query**: "WSLPG WSCPE WSAA architecture integration pattern"
- **Cross-ref**: Constitution Principle VI; PRD §4.5, §4.6

#### ADR-026: CAEA for Offline Fiscal Operations During Harvest
- **Source**: PRD §4.6 (ARCA), feature branch 024
- **Key points**: CAEA = batch pre-authorized codes for quincenas; enables offline invoice issuance during harvest; complementary to per-invoice CAE
- **Rejected alternative**: CAE-only with store-and-forward -- rejected because ARCA requires authorization BEFORE invoice issuance for legal validity; deferred CAE = legally invalid document
- **Cross-ref**: PRD §4.6; feature branch 024-rust-arca-batch

#### ADR-027: SISA-Tier Retention Calculation at LPG Filing Time
- **Source**: PRD §4.5
- **Key points**: Retention rates determined by SISA Estado (1/2/3) at filing time; SISA verification is a BLOCKING GATE before WSLPG filing
- **Cross-ref**: PRD §4.5 (LIQUIDACIONES); RG 5689/2025

---

### Section 9: Offline & Sync Decisions (ADR-028 through ADR-030)

**Effort**: Medium
**Primary sources**: Constitution VII; PRD §4.1 (offline behavior)

#### ADR-028: Offline-First as Base Architecture (Not Fallback)
- **Source**: Vision §2.3.1, Constitution VII
- **Key points**: System assumes network unreliable; every truck reception completes locally; sync is secondary non-blocking process
- **Rejected alternative**: Online-first with offline fallback -- rejected because rural Argentine acopios have intermittent connectivity; "fallback" implies degraded experience
- **RAG query**: "offline first sync conflict resolution grain operations"
- **Cross-ref**: Vision §2.3.1; Constitution Principle VII

#### ADR-029: Conflict Resolution Taxonomy (5 Strategies by Data Type)
- **Source**: Constitution VII
- **Key points**: server_wins (configuration), last_write_wins (inventory), additive (transactions), most_complete_wins (customer/producer data), server_assigns_final (document numbering)
- **Cross-ref**: Constitution Principle VII

#### ADR-030: Store-and-Forward Queue for ARCA Web Service Calls
- **Source**: PRD §4.1 (romaneo offline behavior)
- **Key points**: CPE confirmation calls (confirmarArriboCPE, descargadoDestinoCPE, confirmacionDefinitivaCPEAutomotor) queued locally; transmitted when connectivity restores
- **Cross-ref**: PRD §4.1 (RECEPCION offline behavior)

---

### Section 10: Performance Decisions (ADR-031 through ADR-032)

**Effort**: Medium
**Primary sources**: Feature branches 017-025; PRD §4.1 (weighbridge)

#### ADR-031: Rust/PyO3 Acceleration Boundary (When Rust, When Python)
- **Source**: Feature branches 017-025 (9 Rust modules)
- **Key points**: Move to Rust when: (a) latency-sensitive hot path (>1000 calls/sec), (b) GIL contention in batch processing, (c) CPU-bound computation (crypto, regex, merma), (d) adversarial input validation (SSRF). Stay in Python when: (a) ORM/database operations, (b) business orchestration logic, (c) API endpoint handlers, (d) one-time operations.
- **Rejected alternative**: Pure Python everywhere -- rejected for measured performance gaps (2.1x-8.7x slowdowns on hot paths); Python-only Rust -- rejected for pure Rust server, which would lose Django ecosystem benefits
- **Evidence**: Crypto 8.7x, IVA 4.4x, CUIT 3.1x, observability 2.6x, stock 2.1x (measured benchmarks from feature branches 018-025)
- **Cross-ref**: Feature branches 017-025; CLAUDE.md Active Technologies

#### ADR-032: Weighbridge Integration Architecture (RS-232 / Modbus / TCP Bridge)
- **Source**: PRD §4.1, RAG research 3.1
- **Key points**: Primary = Modbus RTU (Sipel Orion) or command/response (Systel); Fallback = continuous ASCII stream (GaMa A12); Network = KYASERV RS232-Ethernet bridge for LAN access
- **RAG query**: "weighbridge scale integration protocol RS232 Modbus TCP"
- **Cross-ref**: PRD §4.1 (weighbridge auto-capture); RAG research 3.1

---

### Section 11: AI/ML Readiness Decisions (ADR-033 through ADR-035)

**Effort**: Medium
**Primary sources**: Data Model P4, P5, §12; Vision §2.3.6

#### ADR-033: AI-Ready Data Architecture (4-Layer Strategy)
- **Source**: Data Model §12, P4, P5
- **Key points**: Layer 1 (operational data), Layer 2 (provenance metadata), Layer 3 (temporal context), Layer 4 (derived features); no post-hoc data migration needed
- **Cross-ref**: Data Model §12, P4 "Machine Learning First", P5 "AI-Ready Data Architecture"

#### ADR-034: Provenance Fields on All Grain Domain Models
- **Source**: Data Model P5
- **Key points**: created_at, updated_at, created_by, device_id on all grain entities; enables behavioral analytics and fraud detection baselines
- **Cross-ref**: Data Model P5

#### ADR-035: Measurement-Timestamp Pairing for Behavioral Analytics
- **Source**: Data Model P5, spec-03 NF-002
- **Key points**: 6 named timestamps per romaneo; each measurement field paired with temporal context; enables arrival-to-departure cycle time analysis and throughput optimization
- **Cross-ref**: Data Model P5, §5.3 (Romaneo timestamps)

---

### Section 12: Appendix -- Decision Dependency Graph

**Effort**: Small
**Source**: Derived from completed ADRs
**Action**:
- Create Mermaid `graph TD` showing which ADRs depend on or constrain others
- Key dependencies:
  - ADR-001 (PostgreSQL) → ADR-004 (shared schema) → ADR-005 (RLS)
  - ADR-008 (append-only) → ADR-012 (ON DELETE exceptions)
  - ADR-028 (offline-first) → ADR-002 (UUID), ADR-026 (CAEA), ADR-029 (conflict resolution), ADR-030 (store-and-forward)
  - ADR-006 (Ironclad lineage) → ADR-007 (DECIMAL), ADR-008 (append-only), ADR-033 (AI-ready)
  - ADR-009 (dual inventory) → ADR-010 (global vs tenant), ADR-011 (campaign segregation)

---

## Research-to-Section Mapping

| Research Source / RAG Query | Target ADR Section |
|---------------------------|--------------------|
| Constitution Principles I-XI | §4 (Infrastructure), §7 (Security), §9 (Offline) |
| Vision v1.0 §2.3 Ironclad Principles | §4 (ADR-001), §9 (ADR-028), §11 (ADR-033) |
| PRD v1.0 §4.1 RECEPCION | §9 (ADR-028 offline), §10 (ADR-032 weighbridge) |
| PRD v1.0 §4.4 CUENTAS | §5 (ADR-013 posicion consolidada) |
| PRD v1.0 §4.5 LIQUIDACIONES | §8 (ADR-025, ADR-027) |
| Data Model v1.0 §2 Ironclad P1-P5 | §5 (ADR-006 lineage, ADR-007, ADR-008) |
| Data Model v1.0 §12 AI-Ready | §11 (ADR-033, ADR-034, ADR-035) |
| spec-03 research D-001 | §6 ADR-014 (MermaTable scope) |
| spec-03 research D-002 | §6 ADR-015 (QualityParameter inline) |
| spec-03 research D-003 | §6 ADR-016 (WeighbridgeDevice entity) |
| spec-03 research D-004 | §5 ADR-010 (global entities) |
| spec-03 research D-005 | §5 ADR-013 (posicion consolidada) |
| spec-03 research D-006 | §5 ADR-010 (GrainType global) |
| spec-03 research D-007 | §5 ADR-012 (ON DELETE exceptions) |
| "PostgreSQL RLS multi tenant" | §4 ADR-004, ADR-005 |
| "dual inventory grain discrete SKU" | §5 ADR-009 |
| "merma calculation formula sequential" | §6 ADR-014, ADR-018 |
| "WSLPG WSCPE WSAA architecture" | §8 ADR-025, §6 ADR-019 |
| "CAEA offline fiscal invoice batch" | §8 ADR-026 |
| "offline first sync conflict resolution" | §9 ADR-028, ADR-029 |
| "weighbridge scale integration RS232" | §10 ADR-032 |
| "AI ready data architecture grain ERP" | §11 ADR-033, ADR-034 |
| "own grain third party accounting" | §6 ADR-020 |

---

## Checkpoint Gates

### Gate 1 -- After §1-§3 (Metadata + Index Placeholder + How to Read)

- [ ] §1 Metadata table contains Version 1.0, Date, Owner, Status
- [ ] §2 Index table has placeholder rows for all 35 ADRs (populated later)
- [ ] §3 ADR Format Template matches the template defined in Content Guidelines above
- [ ] §3 Status Lifecycle explains all 4 states: Proposed, Accepted, Superseded, Deprecated
- [ ] §3 Cross-Reference Convention uses exact format: "Document vX.Y Section Z.Z"

### Gate 2 -- After §4-§5 (Infrastructure + Data Architecture -- 13 ADRs)

- [ ] All 5 Infrastructure ADRs (001-005) written with complete template fields
- [ ] All 8 Data Architecture ADRs (006-013) written with complete template fields
- [ ] Constitution Principles I, II, III, V cross-referenced from at least one ADR in §4
- [ ] ADR-006 (Ironclad lineage) reconciles all three principle sets (Constitution, Vision, Data Model)
- [ ] ADR-010 explicitly names all GLOBAL entities: GrainType, ToleranceTable, MermaTable
- [ ] ADR-012 lists all CASCADE exceptions (CPE, QualityAnalysis, MermaCalculation) and SET_NULL fields
- [ ] Every ADR in §4-§5 has at least 1 rejected alternative with rationale

### Gate 3 -- After §6-§8 (Grain Domain + Security + Fiscal -- 14 ADRs)

- [ ] All 7 Grain Domain ADRs (014-020) correspond to spec-03 decisions D-001 through D-007 and design overrides
- [ ] All 4 Security ADRs (021-024) cover auth, encryption, password hashing, and SSRF
- [ ] All 3 Fiscal ADRs (025-027) cover ARCA architecture, CAEA, and SISA retention
- [ ] ADR-019 explicitly states the WSLPG single-grain-type constraint
- [ ] ADR-026 explains why CAE-only + store-and-forward is legally invalid (authorization must precede issuance)
- [ ] Constitution Principles IV, V, VI, XI cross-referenced from at least one ADR in §7-§8
- [ ] Every ADR in §6-§8 has at least 1 rejected alternative with rationale

### Gate 4 -- After §9-§11 (Offline + Performance + AI/ML -- 8 ADRs)

- [ ] All 3 Offline ADRs (028-030) cover offline-first, conflict taxonomy, store-and-forward
- [ ] Both Performance ADRs (031-032) cover Rust boundary and weighbridge
- [ ] All 3 AI/ML ADRs (033-035) cover 4-layer strategy, provenance, timestamps
- [ ] ADR-029 lists all 5 conflict strategies with per-data-type mapping
- [ ] ADR-031 includes specific criteria for Rust vs Python with measured benchmarks
- [ ] ADR-032 includes protocol fallback chain (Modbus → ASCII stream → TCP bridge)
- [ ] Constitution Principles VII, VIII cross-referenced from at least one ADR in §9-§10
- [ ] Every ADR in §9-§11 has at least 1 rejected alternative with rationale

### Gate 5 -- Final (Index + Dependency Graph + Cross-Check)

- [ ] §2 ADR Index table fully populated with all 35 ADR entries and working Markdown anchors
- [ ] §12 Dependency graph renders in Mermaid without syntax errors
- [ ] Total ADR count ≥ 30 (count heading lines matching `### ADR-NNN:`)
- [ ] All 11 Constitution principles (I-XI) are traceable: scan for each principle by number and confirm ≥1 ADR references it
- [ ] All 7 spec-03 domain decisions (D-001 through D-007) are captured: cross-check research.md decisions against §6 ADRs
- [ ] No ADR is missing any template field: title, status, date, context, decision, consequences, alternatives, cross-references
- [ ] No "TBD", "TODO", "FIXME" strings in the document
- [ ] All Mermaid diagrams render (dependency graph in §12)

---

## Done Criteria

1. File `Docs/Project Blueprint/Architecture Decision Records (ADR).md` created and saved as v1.0
2. ADR count ≥ 30 entries (target: 35) spanning all 8 categories
3. ADR index table (§2) contains one row per ADR with working Markdown anchor links
4. All 11 Constitution principles (I through XI) traced to at least 1 ADR
5. All 7 spec-03 domain decisions (D-001 through D-007) captured as individual ADRs
6. Every ADR has complete template fields: title, status, date, context, decision, consequences (+/-), alternatives (≥1 rejected), cross-references
7. Ironclad Principles reconciliation (ADR-006) explains the relationship between Constitution I-XI, Vision 6 principles, and Data Model P1-P5
8. Rust/PyO3 boundary (ADR-031) includes specific decision criteria with measured benchmark evidence
9. Conflict resolution taxonomy (ADR-029) maps all 5 strategies to specific data types
10. CAEA decision (ADR-026) explains legal constraint on authorization timing
11. Mermaid decision dependency graph (§12) renders without syntax errors
12. Zero hedging language: no "TBD", "under review", "to be determined", "possibly" in any ADR entry
