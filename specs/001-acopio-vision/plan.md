# Implementation Plan: Acopio de Granos Product Vision & Scope

**Branch**: `001-acopio-vision` | **Date**: 2026-03-15 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `specs/001-acopio-vision/spec.md`
**Plan context**: `Docs/PROMPTS/spec-01-vision/01-plan.md` (section-by-section writing guide)

## Summary

Rewrite `Docs/Project Blueprint/Product Vision & Scope.md` from a generic horizontal ERP (v0.4)
to a fully committed acopio de granos vertical SaaS vision document (v1.0). The deliverable is
a ~600-800 line Markdown file with 11 sections, 6 Mermaid diagrams, 11 competitor profiles,
5 user personas, a 4-phase roadmap, and all market data cited to research sources.

This is a **single-author blueprint document task** — no code is written, no agent teams needed.
The output is a strategic document that becomes the NORTH STAR for all downstream specs.

## Technical Context

**Language/Version**: Markdown (with Mermaid diagram extensions)
**Primary Dependencies**: RAG pipeline (`.venv/bin/python scripts/qdrant/qdrant_search.py`), existing research corpus in Qdrant `acopio_research` collection
**Storage**: File system — single file replacement: `Docs/Project Blueprint/Product Vision & Scope.md`
**Testing**: Manual validation against 15 acceptance criteria in spec.md + 7 checkpoint gates in 01-plan.md
**Target Platform**: GitHub-flavored Markdown renderer (Mermaid diagrams must render in GFM)
**Project Type**: Blueprint document (strategic vision document — not software)
**Performance Goals**: Document must be self-contained and readable in < 30 minutes by target audiences
**Constraints**: All Mermaid diagrams must render correctly; all market claims must cite [Research X.Y]; zero generic retail language
**Scale/Scope**: 11 sections, 6+ Mermaid diagrams, 11 competitor profiles, 5 personas, ~600-800 lines

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

The constitution (`constitution.md`) governs backend code development. This task produces a
**strategic document**, not code. Constitution principles I-XIV are not directly applicable.

**Relevant constitution alignment points** (document must describe these correctly):
- **Principle I (Ironclad Data Model)**: Document's module scope section must reflect the append-only ledger pattern for grain movements — described as an architectural differentiator, not implemented here
- **Principle II (Multi-Tenant RLS)**: Document must accurately describe PostgreSQL RLS as a technical differentiator for multi-plant acopio isolation
- **Principle III (Modular Django Architecture)**: Module map in Section 4.1 must be consistent with existing `apps/` structure; new `apps/acopio/` and `apps/cuentas/` are the Approach B additions
- **Principle VII (Offline-First)**: Document must lead with offline-first as primary competitive moat (consistent with Principle VII's rationale)
- **Principle X (TDD)**: Document's AI roadmap is Phase 3-4 future, not MVP — consistent with current implementation state

**No constitution violations.** Document writing does not introduce code that could violate principles.

**Complexity Tracking**: N/A — no architectural complexity additions.

## Project Structure

### Documentation (this feature)

```text
specs/001-acopio-vision/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output — compiled domain facts per section
├── data-model.md        # Phase 1 output — document content model (sections, entities, relationships)
├── contracts/           # Phase 1 output — document interface contracts (section specs)
│   └── document-structure.md
├── quickstart.md        # Phase 1 output — execution guide for writing the document
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source (the deliverable)

```text
Docs/Project Blueprint/
└── Product Vision & Scope.md   # TARGET: replace v0.4 → v1.0 (in-place rewrite)
```

**Supporting references (read-only):**
```text
Docs/Project Blueprint/
└── Descripción General del Producto.md   # Module map authority (read, don't edit)
Docs/PROMPTS/spec-01-vision/
├── 01-specify.md                          # Context prompt with RAG-verified domain facts
└── 01-plan.md                             # Section-by-section writing guide
```

**Structure Decision**: Single Markdown file replacement. No new directories created in the project (only within `specs/001-acopio-vision/` for planning artifacts). The deliverable is an in-place rewrite of the existing v0.4 document.

## Execution Approach

This is a **single-author document writing task** with the following workflow:

1. **Phase 0** (research.md): Compile all domain facts per section from RAG-verified data
2. **Phase 1** (data-model.md + contracts/): Define the document content model and section contracts
3. **Phase 1** (quickstart.md): Write the execution guide for producing the document
4. **Writing execution** (not part of speckit.plan): Author rewrites the document section by section following the quickstart guide and 7 checkpoint gates from `01-plan.md`

**Single-author execution**: No agent orchestration, no tmux, no parallel agent teams.
The author reads research.md → follows quickstart.md → validates against contracts/document-structure.md.
