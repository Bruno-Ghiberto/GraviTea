# Implementation Plan: 015 Blueprint Documentation Overhaul

**Branch**: `015-blueprint-docs-overhaul` | **Date**: 2026-02-21 | **Spec**: `specs/015-blueprint-docs-overhaul/spec.md`
**Input**: Feature specification from `specs/015-blueprint-docs-overhaul/spec.md`

## Summary

Update 9 existing and create 3 new Project Blueprint documents to restore the documentation suite as the single source of truth for GRAVITEA-ERP (February 2026 state). Executed by a 3-agent team: RESEARCHER extracts codebase facts, two WRITER agents produce documents in parallel, LEAD validates cross-references. This is a documentation-only feature — no source code changes.

## Technical Context

**Language/Version**: N/A (documentation feature — no code changes)
**Primary Dependencies**: Existing codebase as read-only source of truth
**Storage**: Markdown files in `Docs/Project Blueprint/`
**Testing**: Cross-reference validation, metric consistency checks, Mermaid syntax verification
**Target Platform**: GitHub Markdown + Notion mirror
**Project Type**: Documentation overhaul
**Performance Goals**: N/A
**Constraints**: Preserve document language (EN/ES), preserve existing structure, Mermaid diagrams only
**Scale/Scope**: 12 documents (9 update + 3 create), ~150KB total output

## Constitution Check

*GATE: Checked against `.specify/memory/constitution.md`*

| Principle | Applicable? | Status |
|---|---|---|
| I. Ironclad Data Model | No | N/A — no schema changes |
| II. Multi-Tenant Isolation | No | N/A — no code changes |
| III. Modular Django Architecture | Read-only | PASS — RESEARCHER reads app structure, no modifications |
| IV. Application-Level Encryption | No | N/A — no code changes |
| V. Secure Authentication | No | N/A — no code changes |
| VI. Fiscal Compliance (ARCA) | Read-only | PASS — documents describe ARCA integration, no changes |
| VII. Offline-First | No | N/A — no code changes |
| VIII. Query Optimization | No | N/A — no code changes |
| IX. Secure Data Operations | No | N/A — no code changes |
| X. Test-Driven Development | No | N/A — no tests to write for docs |
| XI. JWT Authentication | No | N/A — no code changes |
| XII. Rate Limiting | No | N/A — no code changes |
| XIII. Cursor-Based Pagination | No | N/A — no code changes |
| XIV. API Documentation | Read-only | PASS — documents reference OpenAPI specs, no changes |

**Gate Result**: PASS — documentation-only feature has no constitution violations.

## Project Structure

### Documentation (this feature)

```text
specs/015-blueprint-docs-overhaul/
    plan.md              # This file
    spec.md              # Feature specification (from /speckit.specify)
    research.md          # Phase 0 output (all unknowns resolved)
    checklists/
        requirements.md  # Requirements checklist
    tasks.md             # Phase 2 output (from /speckit.tasks — NOT created here)
```

### Deliverables (repository)

```text
Docs/Project Blueprint/
    Product Vision & Scope.md                    # [UPDATE] Product Vision & Scope
    High-Level Design (HLD).md                   # [UPDATE] High-Level Design
    Low-Level Design (LLD).md                    # [UPDATE] Low-Level Design
    Data Model & Domain Model.md                 # [UPDATE] Data Model & Domain Model
    REST API Design.md                           # [UPDATE] REST API Design
    Development Workflow.md                      # [UPDATE] Development Workflow
    PRD.md                                       # [UPDATE] Product Requirements Document
    Software Requirements Specification (SRS).md # [UPDATE] Software Requirements Specification
    Roadmap.md                                   # [UPDATE] Project Roadmap
    Architecture Decision Records (ADR).md       # [CREATE] Architecture Decision Records
    Developer Onboarding Guide.md                # [CREATE] Developer Onboarding Guide
    Deployment & Infrastructure Guide.md         # [CREATE] Deployment & Infrastructure Guide

claudedocs/
    015-codebase-facts.md  # Intermediate: RESEARCHER output consumed by WRITERs
```

**Structure Decision**: No source code directories affected. All output is Markdown in `Docs/Project Blueprint/`. The intermediate facts document goes to `claudedocs/` per project convention.

## Team Architecture

### Agent Roster

| Agent | subagent_type | Isolation | Phase | Purpose |
|-------|--------------|-----------|-------|---------|
| **RESEARCHER** | `general-purpose` | worktree | 1 | Reads codebase, runs metrics, produces `015-codebase-facts.md` |
| **WRITER-A** | `technical-writer` | worktree | 2 | Updates/creates 6 technical core documents |
| **WRITER-B** | `technical-writer` | worktree | 2 | Updates/creates 6 strategic + onboarding documents |
| **LEAD** | orchestrator (main) | — | 1-3 | Task management, cross-reference validation, commit |

### Phase Dependency Graph

```text
Phase 1: RESEARCHER ──────────────────────┐
         (codebase facts extraction)       │
                                           ▼
Phase 2: WRITER-A (6 docs) ═══╗   facts ready
         WRITER-B (6 docs) ═══╝   [parallel]
                  │                    │
                  ▼                    ▼
Phase 3: LEAD validates ──────────────────┐
         (cross-refs, consistency)        │
                                          ▼
                                       Commit
```

## Phase 1: Research — Codebase Facts Extraction

**Agent**: RESEARCHER (`general-purpose`)
**Blocking**: Phase 2 cannot start until this completes
**Output**: `claudedocs/015-codebase-facts.md`

### Tasks

| ID | Task | Input | Acceptance |
|----|------|-------|------------|
| T001 | Read all Django models across `backend/apps/` | Source files | Every model listed with fields, FKs, patterns |
| T002 | Read all views/viewsets and URL patterns | Source files | Endpoint count per module |
| T003 | Run `scripts/run-tests-external.sh -n 015-metrics tests/` | Test suite | `.summary` file with pass/fail/coverage |
| T004 | Count endpoints from `api/openapi/*.yaml` | 6 YAML files | Paths × methods per module |
| T005 | Read `docker-compose.yml` for service inventory | Config file | All services, profiles, ports, healthchecks |
| T006 | Extract feature completion map from `git log` | Git history | Branches 001-014 with dates and summaries |
| T007 | Gather ADR raw material for 14 seed topics | Codebase + configs | File path evidence per ADR |
| T008 | Read all 9 existing blueprint docs for current state | `Docs/Project Blueprint/` | Version, language, metrics cited, accuracy |
| T009 | Read frontend source for stats | `frontend/` | Routes, TS files, component count |
| T010 | Assemble `015-codebase-facts.md` with 8 sections | T001-T009 output | All sections populated, no placeholders |

### Facts Document Template (8 sections)

1. **Module Status Table** — per Django app: models, views, URLs, tests, status, capabilities
2. **Verified Metrics** — test count, coverage, endpoints, frontend stats, verification date
3. **Entity Inventory** — every model with fields, types, FKs, special patterns
4. **Feature Completion Map** — branches 001-014 with dates and summaries
5. **Docker Compose Inventory** — services, profiles, ports, healthchecks, volumes
6. **OpenAPI Endpoint Summary** — per YAML: module, endpoint count, path list
7. **ADR Raw Material** — per seed topic: code evidence, file paths, alternatives
8. **Existing Document State** — per doc: version, language, current metrics, accuracy

## Phase 2: Writing — Document Production (Parallel)

**Agents**: WRITER-A + WRITER-B (`technical-writer`), running in parallel
**Blocking**: Requires Phase 1 complete (facts doc available)
**Input**: `specs/015-blueprint-docs-overhaul/spec.md` + `claudedocs/015-codebase-facts.md`

### Shared Writer Rules

1. Use ONLY `015-codebase-facts.md` for factual claims — do NOT read codebase directly
2. Copy exact numbers from Facts Section 2 for all metrics
3. Use only status terms: "Complete", "Partial (what's missing)", "Planned", "Not started"
4. All diagrams in Mermaid format; convert existing ASCII to Mermaid
5. Preserve document language (English or Spanish)
6. Preserve existing section structure; add sections, don't reorganize
7. Set `Last Updated: 2026-02-21` in every document header
8. Label all planned/future architecture as "Planned" or "Target"
9. New documents follow section structure from spec user stories (US-6, US-7, US-8)

### WRITER-A Tasks — Technical Core

| ID | Document | Action | Key Deliverables |
|----|----------|--------|-----------------|
| T011 | `Data Model & Domain Model.md` | Update | Mermaid ERDs for all modules; Facturacion, Ventas, Tenant Customization entities added; version incremented |
| T012 | `REST API Design.md` | Update | Status "Active"; OpenAPI YAMLs as authoritative source; endpoint coverage per module; Problem+JSON examples |
| T013 | `Low-Level Design (LLD).md` | Update | Metrics from facts; module status; observability; consolidated Docker Compose; tenant customization layer |
| T014 | `Development Workflow.md` | Update | Current test count/coverage; external test runner; speckit workflow; feature branch conventions |
| T015 | `Architecture Decision Records (ADR).md` | **Create** | 14 ADR entries (seed list); each with Date, Status, Context, Decision, Alternatives, Consequences |
| T016 | `Deployment & Infrastructure Guide.md` | **Create** | Docker Compose current (from facts); GCP service mapping with TBD items; migration considerations |

### WRITER-B Tasks — Strategic & Onboarding

| ID | Document | Action | Key Deliverables |
|----|----------|--------|-----------------|
| T017 | `Product Vision & Scope.md` | Update | Module status; metrics; MVP May 1 2026; features 001-014 listed; VENTAS/ARCA "Complete" |
| T018 | `High-Level Design (HLD).md` | Update | Mermaid architecture diagram; Docker current + GCP planned (labeled); Next.js + Electron dual-env; tenant customization |
| T019 | `PRD.md` — Product Requirements | Update | Dual-environment distinction; offline-first current vs planned; actual module capabilities |
| T020 | `Software Requirements Specification (SRS).md` | Update | Updated constraints (Electron=prod, Next.js=dev); implemented vs planned requirements labeled |
| T021 | `Roadmap.md` — Project Roadmap | Update | MVP May 1 2026; features 001-014 with completion dates; remaining: MVP Required vs Post-MVP |
| T022 | `Developer Onboarding Guide.md` | **Create** | 9 sections: Architecture Overview, Docker Setup, Module Map, Speckit Workflow, Conventions, Directory Structure, Running Tests, Feature Dashboard, AI Agent Context |

### Per-Document Checklists

*(Full checklists in `Docs/Temp-prompting/015/instruction-plan.md` lines 161-242)*

Each document has 4-9 checklist items the writer must verify before marking complete. The checklists are part of the writer agent prompts, not repeated here for brevity.

## Phase 3: Validation — Cross-Reference Integrity

**Agent**: LEAD (orchestrator, main session)
**Blocking**: Requires Phase 2 complete (all 12 docs written)

### Validation Tasks

| ID | Check | Method | Pass Criteria |
|----|-------|--------|--------------|
| T023 | Module status consistency | Read module tables from all docs | Same status per module across all documents |
| T024 | Metric consistency | Grep test count, coverage, endpoints across all docs | Same numbers everywhere |
| T025 | Cross-reference integrity | Find "see", "refer to" references; verify destinations | Zero broken or contradictory references |
| T026 | Mermaid syntax | Check diagram code blocks | All diagrams use valid Mermaid syntax |
| T027 | Last Updated dates | Check every doc header | All show `Last Updated: 2026-02-21` |
| T028 | Language preservation | Compare doc language before/after | No document changed language |

### Cross-Reference Matrix

| Source Doc | References To | What's Referenced |
|---|---|---|
| HLD | Data Model | Entity relationships |
| HLD | LLD | Implementation details |
| HLD | Deployment Guide | Infrastructure |
| LLD | Data Model | Schema details |
| LLD | REST API Design | Endpoint details |
| LLD | Development Workflow | Testing procedures |
| Product Vision | Roadmap | Timeline |
| Product Vision | HLD | Architecture overview |
| PRD | SRS | Requirements |
| PRD | HLD | Architecture |
| Onboarding | Development Workflow | Dev process |
| Onboarding | Deployment Guide | Environment setup |
| Onboarding | ADR | Key decisions |
| Roadmap | Product Vision | Feature scope |

## Task Summary

| Phase | Tasks | Agent | Parallel? |
|-------|-------|-------|-----------|
| Phase 1: Research | T001-T010 (10 tasks) | RESEARCHER | Sequential within phase |
| Phase 2A: Technical Writing | T011-T016 (6 tasks) | WRITER-A | Sequential within agent |
| Phase 2B: Strategic Writing | T017-T022 (6 tasks) | WRITER-B | Sequential within agent |
| Phase 3: Validation | T023-T028 (6 tasks) | LEAD | Sequential within phase |
| **Total** | **28 tasks** | **3 agents + LEAD** | **Phases 2A ║ 2B parallel** |

> **Task ID Note**: This plan uses T001-T028 for its 28 high-level tasks. The granular `tasks.md` uses T001-T090 for 90 implementation tasks. The two ID spaces are independent — when referencing task IDs, specify which document (plan or tasks.md) to avoid ambiguity.

## Constraints (from spec clarifications)

1. **Metric verification**: `scripts/run-tests-external.sh` → read `.summary` files
2. **Diagram format**: Mermaid only (convert existing ASCII)
3. **Onboarding setup**: Docker Compose only (WSL venv = AI agent workaround)
4. **GCP section**: Known mappings + gaps from spec 011; undecided = "TBD"
5. **ADR topics**: 14-entry seed list in spec US-7 (minimum)
6. **Language**: Preserve existing per document (English or Spanish)
7. **Structure**: Preserve existing section order; add, don't reorganize

## Success Criteria (from spec)

| ID | Criteria | Verification |
|----|----------|-------------|
| SC-001 | Zero "0%" or "Pending" for completed modules | Plan T023 / tasks.md T081 |
| SC-002 | 3 new documents created with all required sections | Plan T015,T016,T022 / tasks.md T040-T049,T072-T080 |
| SC-003 | All metrics match verified codebase state | Plan T024 / tasks.md T082 |
| SC-004 | Zero broken/contradictory cross-references | Plan T025 / tasks.md T083 |
| SC-005 | Same module status across all documents | Plan T023 / tasks.md T081 |
| SC-006 | Roadmap has MVP May 1 with 3 categories | Plan T021 / tasks.md T068-T071 |
| SC-007 | Onboarding Guide has all 9 required sections | Plan T022 / tasks.md T072-T080 |
| SC-008 | ADR has 14+ entries with all 6 fields | Plan T015 / tasks.md T040-T044 |
| SC-009 | Every document has accurate Last Updated date | Plan T027 / tasks.md T085 |

## Complexity Tracking

No constitution violations to justify. Documentation-only feature with no architectural complexity additions.
