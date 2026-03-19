# Implementation Plan: Acopio PRD Rewrite

**Branch**: `002-acopio-prd` | **Date**: 2026-03-16 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `specs/002-acopio-prd/spec.md`

> **Blueprint Spec Note**: This is a document rewrite (spec-02 of 08), not a code
> implementation. Single-author execution — no multi-agent orchestration or tmux
> sessions. The "implementation" is the in-place rewrite of
> `Docs/Project Blueprint/PRD.md` (v0.4 → v1.0).

---

## Summary

Rewrite `Docs/Project Blueprint/PRD.md` from a generic horizontal ERP PRD (v0.4,
Spanish, targeting "PyMEs minoristas") to a comprehensive **acopio de granos**
Product Requirements Document (v1.0, English + Spanish domain terms) covering
8 functional modules, 5 personas (≥ 3 user stories each), 5+ Mermaid diagrams,
operational workflows, regulatory compliance specs (CPE/CTG, WSLPG, SISA,
ARCA retentions), hardware integration, and phased delivery plan.

**Upstream**: Vision v1.0 (`Docs/Project Blueprint/Product Vision & Scope.md`) —
completed in spec-01.
**Downstream**: spec-03 (Data Model), spec-04 (ADRs), spec-07 (Roadmap), spec-08a/b/c
all derive their functional justification from this PRD.

**Key constraint**: All 19 FRs and 10 SCs from `specs/002-acopio-prd/spec.md` must be
satisfied. See `Docs/PROMPTS/spec-02-prd/02-plan.md` for section-by-section writing plan,
RAG query schedule, preserve-vs-replace table, and 7 checkpoint gates.

---

## Technical Context

**Language/Version**: Markdown (CommonMark + GitHub-flavored Mermaid); English primary;
Spanish domain terms canonical (romaneo, merma, acopiador, etc.)
**Primary Dependencies**: Qdrant RAG pipeline at `.venv/bin/python scripts/qdrant/qdrant_search.py`;
`Docs/Project Blueprint/PRD.md` v0.4 (content to preserve verbatim);
`Docs/Project Blueprint/Product Vision & Scope.md` v1.0 (cross-reference source);
`Docs/Project Blueprint/Descripción General del Producto.md` (module names authority)
**Storage**: Single file: `Docs/Project Blueprint/PRD.md` (in-place rewrite v0.4 → v1.0).
Git tracks v0.4 in history — no manual backup needed.
**Testing**: Manual validation against 7 checkpoint gates + `specs/002-acopio-prd/spec.md`
SC-001 to SC-010. Full-text searches (`grep`) used for SC-008 (zero retail language).
**Target Platform**: GitHub-flavored Markdown; rendered in VS Code Markdown Preview and GitHub.
Mermaid diagrams must render in both.
**Project Type**: Blueprint specification document (single Markdown file rewrite)
**Performance Goals**: ≥ 700 lines, ≤ 1000 lines; ≥ 5 Mermaid diagrams all error-free;
all 5 personas × ≥ 3 user stories each = ≥ 15 total with Given/When/Then ACs
**Constraints**: Satisfy all 19 FRs (spec.md); zero NEEDS CLARIFICATION; zero retail
language ("cajero", "ferretería", "PyMEs minoristas", "evaluating 4 niches");
no duplication of Vision-level strategic content
**Scale/Scope**: 10 sections, 8 modules, 5 personas, 4 phases, ≥ 5 Mermaid diagrams

---

## Constitution Check

*GATE: The PRD describes a system — constitutional compliance applies to what the PRD
specifies, not to the document itself.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Ironclad Data Model | ✅ Required | PRD must specify append-only ledger for romaneo, cuenta corriente, and silo assignment. DECIMAL for financial fields. FR-004 (dual ledger) + FR-005 (retention calculation). |
| II. Multi-Tenant Isolation (RLS) | ✅ Required | PRD must scope all entities by tenant; posición consolidada must aggregate only within same tenant. FR-004 + FR-012. |
| III. Modular Django Architecture | ✅ No violations | 8 acopio modules map to future Django apps. Constitution lists `compras`/`reportes` as future — acopio modules are additional. |
| IV. Application-Level Encryption | ✅ Inherited | Producer CUIT, financial data (cuenta corriente amounts), and ARCA certificates must be specified as AES-256-GCM encrypted. Inherited from platform encryption module. |
| V. Secure Auth & Sessions | ✅ Inherited | No auth changes. PRD reuses existing JWT RS256. |
| VI. Fiscal Compliance (ARCA) | ✅ Required | PRD must specify FACTURACIÓN reuses WSAA/WSFEv1 (branch 001) for CAE/CAEA; LIQUIDACIONES uses WSLPG. FR-005 + FR-006 + A-006. |
| VII. Offline-First | ✅ Required | PRD must specify offline operation for all Phase 1 modules; store-and-forward for CPE confirmation. FR-016 (online/offline matrix). Constitution conflict resolution: romaneo = additive, configuration = server_wins. |
| VIII. Query Optimization | ✅ N/A | Document rewrite — no queries. Future implementation specs must follow this. |
| IX. Secure Data Operations | ✅ N/A | Document rewrite. |
| X. TDD | ✅ N/A | Document rewrite — no code. Future specs derived from PRD must follow TDD. |
| XI. JWT Auth | ✅ Inherited | No changes to auth. |
| XII. Rate Limiting | ✅ Inherited | No changes. |
| XIII. Cursor-Based Pagination | ✅ N/A | Document rewrite. |
| XIV. API Documentation | ✅ N/A | Document rewrite. |

**Verdict**: No violations. No Complexity Tracking entries needed.

---

## Project Structure

### Documentation (this feature)

```text
specs/002-acopio-prd/
├── plan.md              # This file
├── research.md          # Phase 0 output — consolidated domain facts by section
├── data-model.md        # Phase 1 output — 6 core entities + supporting entities
├── quickstart.md        # Phase 1 output — PRD reading guide by persona
└── tasks.md             # Phase 2 output (NOT created by /speckit.plan)
```

### Output Artifact

```text
Docs/Project Blueprint/
└── PRD.md               # TARGET: in-place rewrite v0.4 → v1.0
                          # (single file, no new files created)
```

**Structure Decision**: Single in-place rewrite. No new directories or code files.
Git history preserves v0.4 (`git log -- "Docs/Project Blueprint/PRD.md"`).

---

## Writing Phases

> Blueprint spec writing phases replace standard coding phases.
> Each phase corresponds to a section group in the 10-section PRD v1.0 target.

### Phase W0: Setup and Scaffolding
**Before writing any section**:
1. Read `specs/002-acopio-prd/research.md` (this plan's Phase 0 output) — all domain facts
2. Read `Docs/Project Blueprint/PRD.md` v0.4 — identify verbatim-preserve blocks
3. Read `Docs/Project Blueprint/Descripción General del Producto.md` — module names authority
4. Cross-check `specs/002-acopio-prd/spec.md` clarifications (5 items in §Clarifications)

**Guard rails**:
- Never read full research PDFs (use `research.md` and RAG queries)
- When additional domain depth needed: `.venv/bin/python scripts/qdrant/qdrant_search.py -q "QUERY" -l 5`

### Phase W1: Foundation (§10 + §1-§2)
**§10 Implementation Foundation** — copy verbatim from v0.4, move to §10:
- Implementation Progress table (v0.4 §1 lines 13-24)
- Estado de Implementación (v0.4 §3.2 lines 98-120)
- ARCA integration details (§4.3)
- Sync engine (§4.4)
- Personalización (§4.5)
- Auth JWT RS256 (§4.6)
- Rust acceleration benchmarks (§5.2 NFR-PERF-05)

**§1 Metadata** — adapt from v0.4:
- Version 1.0, Status "Acopio de Granos Vertical — Active Development"
- Remove "Nota estratégica" box
- Cross-reference §10 for progress

**§2 Introduction + Glossary** — new acopio intro + adapted glossary per `research.md §2`

**Gate W1**: Implementation Foundation complete → §3.2 table verbatim matches v0.4 lines 98-120

### Phase W2: Functional Decomposition (§3)
**§3.1 Mindmap** — 8 acopio modules Mermaid (replaces generic retail)
**§3.2 Implementation Status** — VERBATIM copy from v0.4
**§3.3 Module Dependency Graph** — new Mermaid per spec.md US-5 AC-3

**Gate W2**: Both new Mermaid diagrams render; §3.2 verbatim preserved; zero generic retail terms

### Phase W3: Phase 1 Modules (§4.1–§4.4)
Write in order: RECEPCIÓN → CALIDAD → ALMACENAMIENTO → CUENTAS CORRIENTES
Use template per module: Feature List → State Machine → Data Capture → Offline Behavior → User Stories (≥ 3) → Acceptance Criteria
Use domain facts from `research.md`; fix merma formula and CPE methods precisely

**Gate W3**: State machines for RECEPCIÓN and LIQUIDACIONES render; merma formula exact; posición consolidada in §4.4

### Phase W4: Phase 2–3 Modules (§4.5–§4.8)
Write: LIQUIDACIONES → FACTURACIÓN → AGRONOMÍA → CANJE
LIQUIDACIONES: retention tables complete with all 4 tiers, both RG citations
FACTURACIÓN: reuse note for branch 001; acopio service types only

**Gate W4**: Retention tables present (IVA 5/8/10.5/16% RG 2300; Ganancias 0/2/15/30% RG 4325); blocking SISA gate specified

### Phase W5: Cross-Module Sections (§5–§7)
§5.1 Operational flow — 11-step romaneo flowchart Mermaid (largest diagram)
§5.2 "A fijar" flow — short flowchart
§5.3 Campaign transition — prose workflow
§6: CPE/CTG (with correct WSCPE methods), WSLPG, SISA blocking gate, retention tables
§7: Weighbridge RS-232 + TCP/IP + dual-scale + stability detection (no brand names)

**Gate W5**: Romaneo flow diagram 11 steps renders; CPE state machine correct WSCPE methods; §6.4 retention tables match §4.5

### Phase W6: NFRs and Phased Delivery (§8–§9)
§8.1 Per-module online/offline matrix — all 8 modules, 3-category classification
§8.2-§8.4 Performance + Security + Edge case NFRs (preserve from v0.4 + add acopio)
§9 Four phases with entry/exit criteria per Vision v1.0 phase allocation

**Gate W6**: Offline matrix covers all 8 modules; Phase 1 exit = "first real truck reception"; Phase allocations match Vision v1.0

### Phase W7: Validation
Run all 7 checkpoint gates from `02-plan.md`:
- Full-text grep: zero hits for "cajero", "cashier", "PyMEs minoristas", "ferretería"
- Count user stories ≥ 15 (5 personas × ≥ 3)
- Count Mermaid diagrams ≥ 5 (render test)
- Verify retention tables: both IVA (4 tiers) and Ganancias (4 tiers) present
- Verify §10 contains feature branch history verbatim
- Cross-check spec.md 5 clarifications are reflected in document

---

## Key Cross-References to Maintain

| Source | Target in PRD | Validation |
|--------|--------------|-----------|
| spec.md 5 clarifications | §4.4 CUENTAS CORRIENTES + §5.2 + §4.2 + §4.3 + §7 | Each clarification locatable |
| Vision v1.0 phase allocation | §9 phase boundaries | Phase 1 = RECEPCIÓN+CALIDAD+ALMACENAMIENTO+CC |
| Descripción General module names | §3.1 mindmap + §4.x headers | Exact Spanish CAPS names |
| v0.4 §3.2 | §10 Implementation Foundation | Verbatim: 19-row table |
| v0.4 §4.3–§4.6 | §10 Implementation Foundation | ARCA/Sync/Personalización/Auth |
| spec.md SC-009 | §9 phase allocation + persona names | Consistent with Vision |

---

## Phase 0 Output

See: [research.md](./research.md)

## Phase 1 Output

See: [data-model.md](./data-model.md), [quickstart.md](./quickstart.md)
