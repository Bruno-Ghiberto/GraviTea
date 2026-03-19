# Spec 04: Architecture Decision Records (ADR) -- Specification Context

## Feature Description

Create the `Docs/Project Blueprint/Architecture Decision Records (ADR).md`
document. This document captures, formalizes, and preserves the rationale
behind every significant architectural decision made during the GRAVITEA
acopio de granos pivot. It is the INSTITUTIONAL MEMORY of the project --
the "why" behind the "what" already defined in Vision (spec-01), PRD
(spec-02), and Data Model (spec-03).

ADRs prevent future developers (human or AI) from:
- Re-debating settled decisions without understanding the original trade-offs
- Accidentally violating constraints whose rationale is undocumented
- Applying patterns from other domains that contradict grain-specific realities

The document is a REFERENCE, not a specification. It does not define new
requirements -- it records and rationalizes choices already made.

## Current State (what exists)

No ADR document currently exists for the acopio vertical. Architectural
decisions are scattered across:
- Constitution (`.specify/memory/constitution.md`) -- 11 core principles
- Data Model research.md (`specs/003-acopio-data-model/research.md`) -- 7 domain decisions (D-001 through D-007)
- Vision v1.0 -- 6 Ironclad Principles (strategic framing)
- PRD v1.0 -- implicit technology and workflow choices
- Data Model v1.0 -- Ironclad Principles P1-P5 (data-layer framing)
- Feature branch history (001-025) -- implicit technology adoption decisions

This spec consolidates all of these into a single, navigable, ADR-formatted
document using a lightweight ADR template (title, status, context,
decision, consequences, alternatives).

## Research Inputs

### RAG Queries (run these FIRST -- do NOT read full research files)

```bash
.venv/bin/python scripts/qdrant/qdrant_search.py -q "QUERY" -l 5
```

Queries to run:
- "AI ready data architecture grain ERP training features"
- "dual inventory grain discrete SKU continuous"
- "offline first sync conflict resolution grain operations"
- "weighbridge scale integration protocol RS232 Modbus TCP"
- "WSLPG WSCPE WSAA architecture integration pattern"
- "own grain third party grain accounting balance sheet off balance"
- "CAEA offline fiscal invoice batch harvest"
- "Rust PyO3 acceleration hot path performance"
- "tolerance tables regulatory Camara Arbitral versioning"
- "PostgreSQL RLS row level security multi tenant"

### Source Documents (for reference -- prefer RAG results above)

Only read specific sections if RAG results are insufficient:

| Doc ID | Relevant Sections |
|--------|-------------------|
| 3.1 | Communication Protocols, Integration Recommendation |
| 4.3 | Strategic Implications for Software Vendors (offline, accountant channel) |
| 5.1 | Executive Summary, WSAA Service Name, WSLPG endpoints |
| 7.1 | 3.3 Distinguishing Own vs. Third-Party Grain |
| 9.1 | Edge Computing for Offline, AI data strategy |
| 10.1 | Open-source reference implementations |

### Must-Read Project Files

These files are the PRIMARY sources for ADR content -- read via serena MCP:

| File | Sections to Read |
|------|-----------------|
| `Docs/Project Blueprint/Product Vision & Scope.md` | 2.3 Ironclad Principles, 2.2 Vertical Commitment |
| `Docs/Project Blueprint/PRD.md` | 3.1 Module Architecture, 4.1 RECEPCION (offline), 4.4 CUENTAS (dual ledger), 4.5 LIQUIDACIONES (WSLPG), 5.1 Offline Architecture, 5.2 Sync Strategy |
| `Docs/Project Blueprint/Data Model & Domain Model.md` | 2.1 Ironclad Principles P1-P5, 3.1 Global ERD, 12 AI-Ready Architecture |
| `.specify/memory/constitution.md` | All 11 principles (I-XI) |
| `specs/003-acopio-data-model/research.md` | Domain Decisions D-001 through D-007 |

### Critical Domain Facts

- The project has 25 completed feature branches with implicit technology decisions that need formal ADR capture
- Constitution principles I-XI were written for generic ERP; the acopio pivot introduced principles P4 (ML First) and P5 (AI-Ready) in the Data Model, creating overlap that the ADR must reconcile
- Rust/PyO3 acceleration layer was added across 9 modules (018-025) -- the "when to use Rust vs Python" boundary is an architectural decision needing formalization
- Conflict resolution strategies vary by data type (server_wins, last_write_wins, additive, most_complete_wins, server_assigns_final) -- this taxonomy is an ADR
- CAEA (Codigo de Autorizacion Electronico Anticipado) enables offline fiscal operations during harvest; the choice to support CAEA alongside CAE is a significant architectural decision
- Weighbridge integration uses RS-232 as universal baseline with Modbus RTU and TCP/IP bridge as alternatives -- integration strategy is an ADR
- Global vs per-tenant entity classification (GrainType, ToleranceTable, MermaTable = global; CampanaConfig = per-tenant) is a non-obvious boundary decision
- Own grain (balance-sheet asset, 1.3.XX Bienes de cambio) vs third-party grain (off-balance-sheet, 8.1.XX Cuentas de orden) is a critical accounting architecture decision
- Single Form 1116-C per grain type (WSLPG constraint) drives the LiquidacionPrimaria model design
- PostgreSQL 18.1 was chosen over alternatives; RLS is the core multi-tenant enforcement mechanism

## Requirements

### Functional Requirements

FR-001: Capture every architectural decision from Vision v1.0, PRD v1.0, Data Model v1.0, and Constitution principles I-XI in formal ADR format
FR-002: Each ADR must contain: title, status (Accepted/Superseded/Deprecated), date, context, decision, consequences (positive + negative), alternatives considered
FR-003: Organize ADRs into logical categories: Infrastructure, Data Architecture, Security, Grain Domain, Fiscal Integration, Offline/Sync, Performance, AI/ML
FR-004: Cross-reference each ADR to the upstream document(s) where the decision was made (Vision, PRD, Data Model, Constitution)
FR-005: Document the Rust/PyO3 boundary decision -- criteria for when computation moves to Rust vs stays in Python
FR-006: Document conflict resolution taxonomy (5 strategies) with rationale per data type
FR-007: Document the global vs per-tenant entity classification boundary
FR-008: Document the dual inventory architecture (grain continuous ledger vs discrete SKU inventory)
FR-009: Document all 7 domain decisions from spec-03 research.md (D-001 through D-007) in ADR format
FR-010: Document the CAEA strategy for offline fiscal operations during harvest
FR-011: Document the weighbridge integration architecture (RS-232, Modbus RTU, TCP/IP bridge)
FR-012: Document the ARCA web service integration architecture (WSAA -> WSLPG + WSCPE + WSFEv1)
FR-013: Document the own grain vs third-party grain accounting separation
FR-014: Document the campaign-year segregation pattern and composite key strategy
FR-015: Document the UUID v4 primary key strategy and its trade-offs
FR-016: Document the modular monolith architecture decision (Django apps, not microservices)
FR-017: Document the Posicion Consolidada as derived view decision (not stored entity)
FR-018: Document the ON DELETE behavior exceptions (CASCADE for 1:1 satellites, SET_NULL for nullable assignments)
FR-019: Include a decision log table (ADR index) at the top of the document for quick navigation
FR-020: Document the Ironclad Principles lineage: Constitution (I-XI) -> Vision (6 principles) -> Data Model (P1-P5) with reconciliation of overlapping concerns

### Non-Functional Requirements

NF-001: ADR format follows Michael Nygard's lightweight ADR template adapted for this project
NF-002: Each ADR is self-contained -- readable without needing to consult the source document
NF-003: Status field enables future supersession tracking (e.g., if a decision is later reversed)
NF-004: Document must be navigable via internal Markdown anchor links from the index table
NF-005: Alternatives-considered section must include at least 1 rejected alternative per ADR with explicit rejection rationale
NF-006: Total document should aim for completeness over brevity -- this is a reference document, not a summary

## Target Document Structure

```
1. Metadata
2. ADR Index (table with ID, title, category, status, date)
3. How to Read This Document
   3.1 ADR Format Template
   3.2 Status Lifecycle (Proposed -> Accepted -> Superseded/Deprecated)
   3.3 Cross-Reference Convention
4. Infrastructure Decisions
   ADR-001: PostgreSQL 18.1 as Primary Database
   ADR-002: UUID v4 as Primary Key Strategy
   ADR-003: Modular Monolith via Django Apps (Not Microservices)
   ADR-004: Shared Database / Shared Schema Multi-Tenancy
   ADR-005: Three-Layer Tenant Isolation (ORM + RLS + IDOR)
5. Data Architecture Decisions
   ADR-006: Ironclad Principles Lineage and Reconciliation
   ADR-007: DECIMAL(17,3) for Weights/Money, DECIMAL(5,2) for Percentages
   ADR-008: Append-Only Ledger for Financial Immutability
   ADR-009: Dual Inventory Architecture (Grain Continuous vs Discrete SKU)
   ADR-010: Global vs Per-Tenant Entity Classification
   ADR-011: Campaign-Year Segregation Pattern
   ADR-012: ON DELETE Behavior: RESTRICT Default with CASCADE/SET_NULL Exceptions
   ADR-013: Posicion Consolidada as Derived View (Not Stored)
6. Grain Domain Decisions
   ADR-014: MermaTable Scope -- Zarandeo Only, Constants on GrainType
   ADR-015: QualityParameter Inline on QualityAnalysis (Not Separate Entity)
   ADR-016: WeighbridgeDevice as Separate Entity
   ADR-017: Grade Fields on Romaneo (Not QualityAnalysis)
   ADR-018: Per-Step Merma kg Not Stored (Derived from Intermediates)
   ADR-019: Single Form 1116-C per Grain Type (WSLPG Constraint)
   ADR-020: Own Grain vs Third-Party Grain Accounting Separation
7. Security Decisions
   ADR-021: JWT RS256 with Custom Tenant/Branch Claims
   ADR-022: AES-256-GCM Field-Level Encryption with HMAC Blind Index
   ADR-023: Argon2 Password Hashing (Not bcrypt)
   ADR-024: SSRF Validation Pipeline (Rust)
8. Fiscal Integration Decisions
   ADR-025: ARCA Web Service Architecture (WSAA -> WSLPG + WSCPE + WSFEv1)
   ADR-026: CAEA for Offline Fiscal Operations During Harvest
   ADR-027: SISA-Tier Retention Calculation at LPG Filing Time
9. Offline & Sync Decisions
   ADR-028: Offline-First as Base Architecture (Not Fallback)
   ADR-029: Conflict Resolution Taxonomy (5 Strategies by Data Type)
   ADR-030: Store-and-Forward Queue for ARCA Web Service Calls
10. Performance Decisions
    ADR-031: Rust/PyO3 Acceleration Boundary (When Rust, When Python)
    ADR-032: Weighbridge Integration Architecture (RS-232 / Modbus / TCP Bridge)
11. AI/ML Readiness Decisions
    ADR-033: AI-Ready Data Architecture (4-Layer Strategy)
    ADR-034: Provenance Fields on All Grain Domain Models
    ADR-035: Measurement-Timestamp Pairing for Behavioral Analytics
12. Appendix: Decision Dependency Graph
```

## Acceptance Criteria

AC-01: Every ADR has all required fields: title, status, date, context, decision, consequences, alternatives
AC-02: ADR index table at document top links to every ADR via Markdown anchors
AC-03: All 7 domain decisions from spec-03 research.md (D-001 through D-007) are captured as individual ADRs
AC-04: All 11 Constitution principles (I-XI) are traced to at least one ADR
AC-05: Rust/PyO3 boundary decision (ADR-031) includes specific criteria (e.g., "move to Rust when: latency-sensitive hot path, >1000 calls/sec, GIL contention in batch processing")
AC-06: Conflict resolution taxonomy (ADR-029) covers all 5 strategies with per-data-type mapping
AC-07: At least 30 ADRs covering all categories (Infrastructure, Data, Grain, Security, Fiscal, Offline, Performance, AI)
AC-08: Cross-references to upstream documents use specific section numbers (e.g., "Vision v1.0 Section 2.3", "PRD v1.0 Section 4.4")
AC-09: Each ADR includes at least 1 rejected alternative with explicit rationale
AC-10: Document renders correctly in Markdown with working internal anchor links

## Dependencies

- Depends on: spec-01 (Vision v1.0), spec-02 (PRD v1.0), spec-03 (Data Model v1.0)
- Blocks: spec-05 (HLD -- ADRs inform high-level design choices), spec-06 (API Design -- ADRs constrain API patterns)
- References: `.specify/memory/constitution.md`, `specs/003-acopio-data-model/research.md`
