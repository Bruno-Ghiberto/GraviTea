# Implementation Plan: High-Level Design (HLD) Document

**Branch**: `005-acopio-hld` | **Date**: 2026-03-17 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `specs/005-acopio-hld/spec.md`

## Summary

Write `Docs/Project Blueprint/High-Level Design (HLD).md` — a single, diagram-driven architecture
reference document (target: 1,500–2,500 lines) that synthesises the four upstream blueprint
documents (Vision v1.0, PRD v1.0, Data Model v1.0, ADR v1.0) into one self-contained reference.
The output is a Markdown document with ≥6 Mermaid diagrams, ≥40 headings, 13 top-level sections,
and zero hedging language. No new architectural decisions are invented — all content derives from
the 35 ADRs already captured in spec-04.

**Deliverable path**: `Docs/Project Blueprint/High-Level Design (HLD).md`
**Context file**: `Docs/PROMPTS/spec-05-hld/05-plan.md` — section-by-section writing guide with
Mermaid starter skeletons, domain facts, and checkpoint gates.

---

## Technical Context

**Language/Version**: N/A — document writing task (Markdown + Mermaid notation)
**Primary Dependencies**: `Docs/Project Blueprint/Architecture Decision Records (ADR).md` (35 ADRs), `Docs/Project Blueprint/Data Model & Domain Model.md` v1.0, `Docs/Project Blueprint/PRD.md` v1.0, `Docs/Project Blueprint/Product Vision & Scope.md` v1.0
**Storage**: N/A — output is a plain Markdown file; no database interaction
**Testing**: grep-based checkpoint verification (see research.md § Checkpoint Gates)
**Target Platform**: Markdown file on disk; renders in GitHub, MkDocs, or any CommonMark renderer
**Project Type**: Blueprint documentation (spec-05 in the 01-08 blueprint range)
**Performance Goals**: Document must be complete, self-contained, and renderable; no timing requirement
**Constraints**: Zero hedging language; ≥6 Mermaid diagrams; ≥40 headings; all 35 ADRs cited via "ADR-NNN" format; 13 sections matching spec.md FR-0501–FR-0512
**Scale/Scope**: Single Markdown document; estimated 1,500–2,500 lines; 7 diagrams; ≈40 ADR cross-references

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

This is a blueprint documentation task. The constitution governs code implementation; the HLD
document must accurately *describe* the architecture that embodies each principle. No code is
written in this spec. Constitution compliance is verified by confirming the HLD accurately
represents each applicable principle.

| Principle | Applicability | HLD Section | Compliance Check |
|-----------|--------------|-------------|-----------------|
| I — Ironclad Data Model | Informative | §5.1 (apps/core), §5.3 (apps/acopio), §10 (Security) | HLD must mention `DECIMAL(17,3)`, `ON DELETE RESTRICT`, append-only ledger |
| II — Multi-Tenant Isolation | CRITICAL | §10 (Security Architecture) | HLD must describe all 3 layers: TenantBoundManager, PostgreSQL RLS with `SET LOCAL`, IDOR/JWT validation |
| III — Modular Django Architecture | Informative | §5 (Component Overview) | HLD must cover all 8 apps with correct `apps/` naming; Phase 2 annotation applied |
| IV — Application-Level Encryption | Informative | §10.5–10.6 | HLD must name AES-256-GCM, HMAC-SHA256 blind index, Google Cloud Secret Manager |
| V — Secure Authentication | Informative | §10.4 | HLD must name JWT RS256, 4096-bit RSA key, 15-min/7-day token lifetimes, algorithm whitelist |
| VI — Fiscal Compliance (ARCA) | CRITICAL | §6 (ARCA Integration) | HLD must include WSAA TRA→CMS→LoginCMS→TA flow and CAEA legal constraint sentence |
| VII — Offline-First | CRITICAL | §8 (Offline-First Architecture) | HLD must list all 5 conflict resolution strategies with exact strategy names |
| VIII — Query Optimization | N/A | — | Not relevant to architecture documentation |
| IX — Secure Data Operations | Informative | §10 | Described via TenantBoundManager and IDOR validation layer |
| X — TDD | N/A | — | QA and testing concerns not part of HLD scope |
| XI — JWT Authentication | Informative | §10.4 | RS256 algorithm whitelist, custom claims (tenant_id, branch_id) |

**GATE STATUS**: PASS — no constitution violations. The three critical principles (II, VI, VII) are
fully covered by the spec's FR-0503, FR-0505, FR-0506 requirements with explicit acceptance
criteria.

---

## Project Structure

### Documentation (this feature)

```text
specs/005-acopio-hld/
├── spec.md               # Feature specification (completed — speckit.specify)
├── checklists/
│   └── requirements.md   # Specification quality checklist (all 17 items PASS)
├── plan.md               # This file (speckit.plan output)
├── research.md           # Phase 0 output — writing guide, key domain facts
├── quickstart.md         # Phase 1 output — acceptance verification guide
└── tasks.md              # Phase 2 output (speckit.tasks — NOT created by speckit.plan)
```

### Source Output (deliverable)

```text
Docs/Project Blueprint/
├── High-Level Design (HLD).md     ← PRIMARY OUTPUT of this feature
├── Architecture Decision Records (ADR).md   (upstream — spec-04, do not modify)
├── Data Model & Domain Model.md             (upstream — spec-03, do not modify)
├── PRD.md                                   (upstream — spec-02, do not modify)
└── Product Vision & Scope.md               (upstream — spec-01, do not modify)
```

**Structure Decision**: Single-file output. This is a blueprint documentation spec — no code
structure is required. The deliverable is one Markdown file written section by section following
the 14-step writing order documented in `Docs/PROMPTS/spec-05-hld/05-plan.md`.

### No data-model.md

**Rationale**: This spec writes a document, not code. The entities described in the HLD derive
directly from `Docs/Project Blueprint/Data Model & Domain Model.md` v1.0 (spec-03). Reproducing
entity definitions here would duplicate spec-03.

### No contracts/

**Rationale**: The HLD is an internal architecture reference document. It exposes no API surfaces,
no web service contracts, and no interface definitions. The REST API specification is deferred to
spec-06.

---

## Complexity Tracking

No constitution violations; no complexity justifications required.

---

## Writing Technology

| Tool | Role |
|------|------|
| Markdown | Primary document format |
| Mermaid (`graph TD`, `sequenceDiagram`, `flowchart TD`) | All 7 architecture diagrams |
| ADR document (spec-04) | Authoritative source for all 35 ADRs |
| Data Model document (spec-03) | Entity-to-app mapping for §5 |
| PRD (spec-02) | Romaneo workflow steps for §9.1 |
| `Docs/PROMPTS/spec-05-hld/05-plan.md` | Section-by-section writing guide |

---

## Writing Order

Write sections in this order (minimises context switching between source docs):

| Step | Section | Source Focus |
|------|---------|-------------|
| 1 | §1 Document Metadata | spec.md metadata fields |
| 2 | §2 System Overview | spec.md Scope section |
| 3 | §13 skeleton | ADR document §3.1 index (8 categories) |
| 4 | §3 System Context C4 L1 | ADR-001–003, ADR-025 |
| 5 | §4 Container Architecture C4 L2 | ADR-001–004, ADR-031, CLAUDE.md |
| 6 | §5 Component Overview | Data Model §3.1 ERD, PRD §3.1 |
| 7 | §6 ARCA Integration | ADR-025–027, CPE/WSLPG domain facts |
| 8 | §7 Weighbridge Integration | ADR-032, weighbridge domain facts |
| 9 | §8 Offline-First Architecture | ADR-028–030, conflict resolution table |
| 10 | §9 Data Flow Diagrams | PRD §4.1, romaneo 10-step mapping |
| 11 | §10 Security Architecture | ADR-005, ADR-021–024 |
| 12 | §11 Deployment Topology | ADR-003–004, Docker Compose service list |
| 13 | §12 AI/ML Readiness | ADR-033–035 |
| 14 | §13 complete | Fill in ADR IDs from all content sections |

---

## Phase 0: Research Summary

**Status**: All NEEDS CLARIFICATION resolved in spec.md `## Clarifications` session.

No outstanding unknowns. See `research.md` for the complete writing reference guide, including:
- Domain terminology definitions for all Argentine fiscal/grain terms
- Verbatim constraint sentences that must appear word-for-word
- Diagram rendering notes and Mermaid syntax guidance
- Checkpoint gate commands

---

## Phase 1: Design Artifacts

**research.md**: ✅ Writing reference guide (domain facts, verbatim constraints, key decisions)
**quickstart.md**: ✅ Acceptance verification guide (how to validate the completed HLD)
**data-model.md**: ⊘ Skipped — no entities to define (document writing task; derives from spec-03)
**contracts/**: ⊘ Skipped — no API surfaces to specify (document writing task)

---

## Checkpoint Gates

Run these checks after each writing phase. Full gate commands in `Docs/PROMPTS/spec-05-hld/05-plan.md §8`.

### Gate 1 — Metadata + Context (after §§1–3)
```bash
grep "Version 1.0" "Docs/Project Blueprint/High-Level Design (HLD).md"  # ≥1 match
grep -c "^### ADR-" "Docs/Project Blueprint/High-Level Design (HLD).md"  # 0 matches (HLD cites, not reproduces)
```

### Gate 2 — Containers + Components + ARCA (after §§4–6)
```bash
grep "CAEA codes MUST be obtained before" "Docs/Project Blueprint/High-Level Design (HLD).md"  # 1 match
grep "8\.7×\|8\.8×\|4\.4×" "Docs/Project Blueprint/High-Level Design (HLD).md"            # 3 matches
grep "Phase 2" "Docs/Project Blueprint/High-Level Design (HLD).md"                          # ≥2 matches
```

### Gate 3 — Weighbridge + Offline + Data Flows (after §§7–9)
```bash
grep "server_wins\|last_write_wins\|additive\|most_complete_wins\|server_assigns_final" \
  "Docs/Project Blueprint/High-Level Design (HLD).md"  # 5 matches
grep "44%" "Docs/Project Blueprint/High-Level Design (HLD).md"  # ≥1 match
grep "KYASERV" "Docs/Project Blueprint/High-Level Design (HLD).md"  # ≥1 match
```

### Gate 4 — Security + Deployment + AI/ML (after §§10–12)
```bash
grep "SET LOCAL app.current_tenant_id" "Docs/Project Blueprint/High-Level Design (HLD).md"  # ≥1 match
grep ":8000\|:5432\|:6379" "Docs/Project Blueprint/High-Level Design (HLD).md"              # ≥3 matches
grep "environment_sensor_id" "Docs/Project Blueprint/High-Level Design (HLD).md"            # ≥1 match
```

### Gate 5 — Final (all sections complete)
```bash
grep -i "TBD\|TODO\|FIXME\|possibly\|might consider" "Docs/Project Blueprint/High-Level Design (HLD).md"
# Expected: 0 matches (empty output)
grep -c "^## \|^### " "Docs/Project Blueprint/High-Level Design (HLD).md"
# Expected: ≥ 40
grep -c '```mermaid' "Docs/Project Blueprint/High-Level Design (HLD).md"
# Expected: ≥ 6
```

---

## Done Criteria

The task is complete when ALL of these are satisfied:

- [ ] `Docs/Project Blueprint/High-Level Design (HLD).md` created and non-empty
- [ ] §1 metadata: Version 1.0, Date 2026-03-17, Status Accepted, Owner GraviTea Architecture Team
- [ ] C4 Level 1 diagram renders — all 8 external actors present
- [ ] C4 Level 2 diagram renders — 5 containers with labeled protocol arrows
- [ ] §5: all 8 apps; `apps/facturacion` and `apps/liquidaciones` annotated "(Phase 2)"
- [ ] §6.5: CAEA legal constraint sentence present verbatim
- [ ] §9.1: romaneo flow exactly 10 steps, responsible component at each step
- [ ] §8.4: all 5 conflict resolution strategies with target data types
- [ ] §4.4: Rust benchmark table — all 7 speedup values using × symbol
- [ ] §13: technology cross-reference table covers all 8 ADR categories
- [ ] Zero hedging language (grep Gate 5)
- [ ] ≥6 Mermaid diagrams (grep Gate 5)
