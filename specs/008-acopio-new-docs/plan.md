# Implementation Plan: Acopio New Blueprint Documents (08a/08b/08c)

**Branch**: `008-acopio-new-docs` | **Date**: 2026-03-18 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/008-acopio-new-docs/spec.md`

## Summary

Produce three Markdown blueprint documents that complete the GraviTea Acopio ERP design suite before implementation specs (09-12) begin. **08a** is the ARCA grain web service integration guide expanding HLD §6 to endpoint-level detail. **08b** is the AI/ML feature roadmap expanding HLD §12 with model architecture and training data strategy. **08c** is the formal SRS replacing the stale retail-vertical version with acopio-specific shall-statements and a traceability matrix.

This is a **blueprint spec** (01-08 tier): deliverables are Markdown documents, not code. Single-author writing mode — no tmux agent teams, no Django migrations, no test suites.

## Technical Context

**Language/Version**: Markdown (GitHub-Flavored Markdown with Mermaid diagrams)
**Primary Dependencies**: Upstream blueprints (PRD v1.0, HLD v1.0, Data Model v1.0, ADR v1.0, REST API Design v1.0, Roadmap v1.0)
**Storage**: N/A — static Markdown files in `Docs/Project Blueprint/`
**Testing**: Grep-based acceptance criteria validation (automated gate checks)
**Target Platform**: Documentation (consumed by developers, QA, architects)
**Project Type**: Blueprint documentation
**Performance Goals**: N/A
**Constraints**: No implementation code (FR-031); zero TBD/TODO markers (FR-028); consistent terminology (FR-029)
**Scale/Scope**: 3 documents, ~11 sections each, estimated 300-500 lines per document

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Ironclad Data Model | N/A | Blueprint documents, not schema changes. 08c references Data Model spec-03 but does not alter it. |
| II. Multi-Tenant Isolation | N/A | No code produced. 08c formalizes tenant isolation as SRS-SE02. |
| III. Modular Django Architecture | PASS | 08c maps SRS requirements to existing module structure (acopio, cuentas). |
| IV. Application-Level Encryption | N/A | 08c formalizes as SRS-SE03. |
| V. Secure Authentication | N/A | 08c formalizes as SRS-SE01/SE04/SE06. |
| VI. Fiscal Compliance (ARCA) | PASS | 08a directly supports this — documents the full ARCA integration architecture. |
| VII. Offline-First | PASS | 08a documents CAEA offline path and store-and-forward queue (ADR-030). |
| X. Test-Driven Development | N/A | No code to test. Gate checks serve as the "test suite" for documents. |

**Result**: PASS — no violations. No complexity tracking needed.

## Project Structure

### Documentation (this feature)

```text
specs/008-acopio-new-docs/
├── spec.md              # Feature specification (done)
├── plan.md              # This file
├── research.md          # Phase 0: RAG query results + upstream analysis
├── data-model.md        # Phase 1: Document structure definitions
├── quickstart.md        # Phase 1: Writing kickoff guide
├── checklists/
│   └── requirements.md  # Spec quality checklist (done)
└── tasks.md             # Phase 2: Task breakdown (created by /speckit.tasks)
```

### Deliverables (repository root)

```text
Docs/Project Blueprint/
├── ARCA Grain Integration Guide.md          # 08a — NEW file
├── AI-ML Feature Roadmap.md                 # 08b — NEW file
└── Software Requirements Specification (SRS).md  # 08c — OVERWRITE stale file
```

**Structure Decision**: All three deliverables are Markdown files in the existing `Docs/Project Blueprint/` directory. No new directories needed. 08c overwrites the stale retail-vertical SRS.

## Complexity Tracking

> No constitution violations — table not needed.

---

## Phase 0: Research

### Research Tasks

All domain facts are already consolidated in `Docs/PROMPTS/spec-08-new-docs/08-specify.md` (Critical Domain Facts section) and validated via RAG during `/sc:design` and `/sc:improve`. The RAG results are cached at `Docs/RAG_results/spec08/`.

| Research Task | Source | Status |
|---------------|--------|--------|
| WSAA auth flow (TRA, LoginCMS, Token+Sign) | RAG `arca_dev_guides` + HLD §6 + 08-specify.md | Resolved |
| WSLPG endpoints and XML fields | RAG `acopio_research` (5.1) + newly ingested `arca_dev_guides` (manual_wslpg_1.24.pdf) | Resolved |
| WSCPE lifecycle and method catalog | RAG `acopio_research` (1.2) + newly ingested `arca_dev_guides` (manual-wscpe.pdf) | Resolved |
| WSCPE method name discrepancy | RAG result: HLD says `descargadoDestinoCPE`, ARCA WSDL says `confirmarDescargaCPE` | Flagged — resolve during 08a writing against WSCPE manual |
| CAEA offline legal constraint | HLD §6 + 08-specify.md | Resolved |
| Homologation URLs (WSCPE, WSFEv1) | Newly ingested ARCA docs in Qdrant `arca_dev_guides` / `arca_api_specs` | Available for query |
| SISA retention tiers | RAG `acopio_research` (1.4) + 08-specify.md | Resolved |
| AI/ML model candidates | Roadmap §7.1 + RAG `acopio_research` (9.1) | Resolved |
| Phase model alignment (3-phase vs 4-phase) | Roadmap is authoritative: 3-phase model | Resolved |
| Weighbridge RS-232/Modbus protocols | RAG `acopio_research` (3.1) + 08-specify.md | Resolved |
| Romaneo workflow steps | RAG `acopio_research` (2.1) | Resolved |
| pyafipws and open-source ARCA libraries | RAG `acopio_research` (10.1, 5.1) | Resolved |

**NEEDS CLARIFICATION**: None — all research tasks resolved during `/sc:design` and `/sc:improve`.

### RAG Collections Available

| Collection | Contents | Status |
|------------|----------|--------|
| `acopio_research` | 20+ grain industry research docs (weighbridge, quality, WSLPG, WSCPE, AI/ML, operations) | Active |
| `arca_api_specs` | 8 ARCA technical specs (WSAA, WSFEv1, WSMTXCA, WSBFEV1, WSSEG, padron, SIRE) | Freshly ingested |
| `arca_dev_guides` | 14 ARCA developer manuals (WSAA, WSLPG, WSCPE, WSCDC, SIRE, WSFEv1, WSFEX, etc.) | Freshly ingested |
| `arca_setup_certs` | 8 certificate/environment setup docs | Freshly ingested |

**Query pattern**: `.venv/bin/python scripts/qdrant/qdrant_search.py -q 'QUERY' -l 5`

---

## Phase 1: Design

### Document Structure Definitions

Each deliverable follows the target structure defined in `Docs/PROMPTS/spec-08-new-docs/08-specify.md` (Target Document Structures section) and elaborated in `Docs/PROMPTS/spec-08-new-docs/08-plan.md` (Section-by-Section Writing Plans).

#### 08a — ARCA Grain Integration Guide (11 sections)

| § | Section | Effort | Primary Source | Key Deliverable |
|---|---------|--------|----------------|-----------------|
| 1 | Document Metadata | Small | HLD/Roadmap §1 pattern | Version header, changelog, upstream refs |
| 2 | ARCA Service Overview | Medium | HLD §6, RAG `arca_api_specs` | Hub-spoke Mermaid diagram, service catalog table with URLs |
| 3 | WSAA Authentication | Large | RAG `arca_dev_guides` (WSAA manual), HLD §3.2 | TRA→CMS→LoginCMS sequence diagram, Token+Sign caching, error handling |
| 4 | WSLPG — Grain Settlement | Large | RAG `acopio_research` (5.1), `arca_dev_guides` (WSLPG v1.24) | XML field reference, codGrano constraint, SISA gate, retention tiers table |
| 5 | WSCPE — CPE Lifecycle | Large | RAG `acopio_research` (1.2), `arca_dev_guides` (WSCPE manual) | State machine Mermaid, full method catalog, discrepancy resolution |
| 6 | WSFEv1/CAEA | Medium | HLD §3.2, ADR-026 | CAE/CAEA paths, CAEA legal warning callout, Rust 024 reference |
| 7 | Certificate Management | Medium | ADR-025, RAG `arca_dev_guides` | Per-service cert requirement, Secret Manager, rotation procedure |
| 8 | Homologation Testing | Medium | RAG `arca_dev_guides`, research 5.1 | URLs table, test CUITs, per-service checklist |
| 9 | Open-Source References | Small | RAG `acopio_research` (10.1, 5.1) | pyafipws assessment, adaptation caveats |
| 10 | ADR Cross-Reference | Small | ADR v1.0 | 7 ADR citations table (ADR-019, 025-030) |
| 11 | Glossary | Small | PRD §2.1 (avoid duplicating) | ARCA-specific terms only |

**Mermaid diagrams required**: ≥ 3 (hub-spoke §2, WSAA sequence §3, CPE state machine §5)
**Tables required**: ≥ 5 (service catalog, retention tiers, error handling, test checklist, ADR cross-ref)

#### 08c — Software Requirements Specification (12 sections)

| § | Section | Effort | Primary Source | Key Deliverable |
|---|---------|--------|----------------|-----------------|
| 1 | Document Metadata | Small | HLD/Roadmap §1 pattern | Version header, note: complete rewrite replacing stale retail SRS |
| 2 | Introduction | Small | 08-specify.md FR-08C01 | SRS-PPNN ID scheme, MoSCoW classification, scope statement |
| 3 | System Overview | Small | HLD §3, PRD | C4 Level 1 reference (not duplicated), user roles, system boundaries |
| 4 | Functional Requirements — Phase 1 | **Large** | PRD §4.1-§4.4, REST API v1.0, RAG `acopio_research` (2.1, 8.3) | ≥20 SRS-RE/CA/AL/CC IDs, ≥30 shall-statements |
| 5 | Functional Requirements — Phase 2 (Deferred) | Small | PRD §4.5-§4.8, Roadmap §5 | SRS-LQ/FA/AG/CJ stubs with "Deferred" status |
| 6 | External Interface Requirements | **Large** | 08a (cross-ref), RAG `acopio_research` (3.1, 3.2) | ARCA SOAP, weighbridge RS-232/Modbus/ASCII/KYASERV, REST API |
| 7 | Performance Requirements | Small | PRD §8 | SRS-PF01-05: <500ms API, <30s sync, <5min romaneo, concurrency |
| 8 | Security Requirements | Small | PRD §8, HLD security, Constitution | SRS-SE01-06: JWT RS256, RLS, AES-256-GCM, Argon2, SSRF, rate limit |
| 9 | Data Requirements | Small | Data Model v1.0, ADR-012 | SRS-DA01-04: entities, DECIMAL(17,3), ON DELETE, campaign segregation |
| 10 | Traceability Matrix | **Large** | PRD §4, SRS §4 requirements, REST API v1.0 | PRD→SRS→spec→API→test marker, zero empty cells in Must rows |
| 11 | Constraints and Assumptions | Small | Roadmap §2-§3, PRD §6 | Regulatory, hardware, team size, offline assumptions |
| 12 | Appendix: Requirement ID Namespace | Small | 08-specify.md FR-08C01 | Complete PP code table with reserved ranges |

**Shall-statements required**: ≥ 30
**SRS-XX IDs required**: ≥ 20 for Phase 1 + ≥ 4 for Phase 2 stubs

#### 08b — AI/ML Feature Roadmap (11 sections)

| § | Section | Effort | Primary Source | Key Deliverable |
|---|---------|--------|----------------|-----------------|
| 1 | Document Metadata | Small | HLD/Roadmap §1 pattern | Version header, upstream refs |
| 2 | Strategic Context | Small | Roadmap §3.2, Product Vision | Competitive differentiation, data advantage |
| 3 | 4-Layer Data Architecture | **Large** | ADR-033/034/035, Data Model v1.0 | Layer descriptions with field refs, Mermaid data architecture diagram |
| 4 | ML Model Catalog | **Large** | Roadmap §7.1, HLD §12, RAG `acopio_research` (9.1) | P3-Q1 through P3-Q4 + HLD informative + deferred CV |
| 5 | Feature Engineering Strategy | Medium | Data Model v1.0, RAG `acopio_research` (9.1) | Raw field→feature mappings, temporal windows, cross-entity joins |
| 6 | Training Data Collection Plan | Medium | Roadmap §7.4 | Minimum thresholds: 10k romaneos, 1 campana, 3 operators |
| 7 | Delivery Sequence | Medium | Roadmap §7.1/§7.4 | **3-phase model** (not 4-phase), triggers, Mermaid dependency graph |
| 8 | IoT Integration Roadmap | Medium | 08-specify.md FR-08B06 | Sensors, protocols (LoRaWAN/Modbus TCP/MQTT), data pipeline |
| 9 | Vector Search and NLQ Strategy | Small | 08-specify.md FR-08B07 | Qdrant dev vs prod, NLQ feasibility |
| 10 | Infrastructure Requirements | Small | HLD §12 | GPU requirements (minimal), inference latency targets |
| 11 | ADR Cross-Reference | Small | ADR v1.0 | 3 ADR citations (ADR-033, 034, 035) |

**Critical constraint**: MUST use Roadmap's 3-phase model — ML is Phase 3, not Phase 4 (SC-007).
**Mermaid diagrams required**: ≥ 2 (data architecture, delivery sequence)

### Writing Order and Checkpoint Gates

```text
┌──────────────────────────────────────┐
│  08a: ARCA Grain Integration Guide   │
│  (11 sections, 3 Large)              │
├──────────────────────────────────────┤
│  GATE 1: grep validation             │
│  ✓ ARCA services ≥40  ✓ Mermaid ≥3  │
│  ✓ fwshomo.afip ≥1    ✓ ADRs ≥7     │
│  ✓ TBD/TODO = 0                      │
└──────────┬───────────────────────────┘
           │
┌──────────▼───────────────────────────┐
│  08c: Software Requirements Spec     │
│  (12 sections, 3 Large)              │
├──────────────────────────────────────┤
│  GATE 2: grep validation             │
│  ✓ SRS-RE/CA/AL/CC ≥20  ✓ shall ≥30 │
│  ✓ baud/Modbus/RS-232 ≥5            │
│  ✓ TBD/TODO = 0                      │
└──────────┬───────────────────────────┘
           │
┌──────────▼───────────────────────────┐
│  08b: AI/ML Feature Roadmap          │
│  (11 sections, 2 Large)              │
├──────────────────────────────────────┤
│  GATE 3: grep validation             │
│  ✓ ML models ≥4    ✓ Layers ≥8      │
│  ✓ ADR-033/034/035 ≥3               │
│  ✓ TBD/TODO = 0                      │
└──────────────────────────────────────┘
```

### Content Guidelines (Summary)

- **Tone**: Technical but accessible — same register as HLD and Roadmap
- **Language**: English with Spanish domain terms retained (romaneo, merma, liquidacion, etc.)
- **Rule**: Expand upstream blueprints — never copy-paste from them
- **ADR format**: Always "ADR-NNN (Title)" — e.g., "ADR-025 (ARCA Web Service Architecture)"
- **Warning callouts**: `> **WARNING**: text` for critical legal/compliance constraints
- **No code**: No Python/SQL/shell. Mermaid, XML summaries, config tables allowed.
- **No TBD**: State constraints explicitly instead of writing TBD/TODO/placeholder

Full content guidelines in `Docs/PROMPTS/spec-08-new-docs/08-plan.md` §7.

### Research-to-Section Mapping (Summary)

Full 28-row mapping table in `Docs/PROMPTS/spec-08-new-docs/08-plan.md` §6. Key feeds:

| Source Category | Feeds Into |
|----------------|------------|
| RAG `arca_api_specs` + `arca_dev_guides` | 08a §2-§8 (all ARCA service sections) |
| RAG `acopio_research` (1.x, 5.1, 8.x, 10.1) | 08a §4-§5 (WSLPG, WSCPE), §9 (open-source refs) |
| RAG `acopio_research` (9.1) | 08b §2-§8 (all AI/ML sections) |
| RAG `acopio_research` (2.1, 2.2, 3.1, 3.2, 8.3) | 08c §4 (Phase 1 requirements), §6 (interfaces) |
| HLD v1.0 | 08a §2-§8 (expanded), 08b §3-§4 (expanded), 08c §3 (referenced) |
| PRD v1.0 | 08c §4-§5 (formalized into shall-statements), §7-§8 (NFRs) |
| Data Model v1.0 | 08b §3/§5 (field refs), 08c §9 (data requirements) |
| REST API Design v1.0 | 08c §4 (endpoint column), §6.3, §10 (traceability matrix) |
| ADR v1.0 | 08a §10 (7 ADRs), 08b §11 (3 ADRs), 08c §8-§9 (security/data ADRs) |

### Done Criteria

- [ ] `Docs/Project Blueprint/ARCA Grain Integration Guide.md` exists (08a)
- [ ] `Docs/Project Blueprint/AI-ML Feature Roadmap.md` exists (08b)
- [ ] `Docs/Project Blueprint/Software Requirements Specification (SRS).md` contains acopio content (08c)
- [ ] Gate 1 passes (08a: ARCA ≥40, Mermaid ≥3, fwshomo ≥1, ADRs ≥7, TBD=0)
- [ ] Gate 2 passes (08c: SRS-IDs ≥20, shall ≥30, hardware ≥5, TBD=0)
- [ ] Gate 3 passes (08b: ML models ≥4, layers ≥8, ADRs ≥3, TBD=0)
- [ ] FR-001 through FR-031 satisfied
- [ ] SC-001 through SC-007 verifiable
- [ ] Zero TBD/TODO/placeholder across all three documents
- [ ] Terminology consistent with Data Model and PRD glossary
- [ ] All Mermaid diagrams render correctly
- [ ] All cross-document references point to correct section numbers
