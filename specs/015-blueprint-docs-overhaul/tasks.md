# Tasks: 015 Blueprint Documentation Overhaul

**Input**: Design documents from `specs/015-blueprint-docs-overhaul/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, quickstart.md
**Tests**: Not applicable — documentation-only feature. Validation is cross-reference and consistency checking.

**Organization**: Tasks are grouped by execution phase aligned with the 3-agent team architecture. User story tags ([US1]-[US10]) indicate which spec user stories each task satisfies. Cross-cutting stories (US1 Module Status, US2 Quality Metrics, US9 Cross-References) are satisfied across multiple phases.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story(ies) this task satisfies
- Exact file paths included in descriptions

## Path Conventions

- **Deliverables**: `Docs/Project Blueprint/*.md`
- **Intermediate output**: `claudedocs/015-codebase-facts.md`
- **Spec files**: `specs/015-blueprint-docs-overhaul/`
- **Agent instructions**: `Docs/Temp-prompting/015/instruction-plan.md`

---

## Phase 1: Setup

**Purpose**: Branch verification and workspace preparation
**Agent**: LEAD (orchestrator)

- [X] T001 Verify branch is `015-blueprint-docs-overhaul` and working tree is clean via `git status`
- [X] T002 Verify `scripts/run-tests-external.sh` exists and is executable
- [X] T003 Verify all 9 existing blueprint docs exist in `Docs/Project Blueprint/`
- [X] T004 Verify `claudedocs/` directory exists (create if needed)

---

## Phase 2: Codebase Facts Research (BLOCKS Phase 3 & 4)

**Purpose**: Extract all factual data from codebase into a structured reference document
**Agent**: RESEARCHER (`general-purpose`, worktree)

**Goal**: Produce `claudedocs/015-codebase-facts.md` with 8 sections that serve as the single source of truth for all 12 document updates.

**Independent Test**: Facts doc contains all 8 sections with no placeholders or "TBD" values (except GCP items explicitly marked TBD per spec).

### Section 1: Module Status

- [X] T005 [US1] Read all Django models in `backend/apps/auth/` and document model names, view count, URL count, test count, status, capabilities
- [X] T006 [P] [US1] Read all Django models in `backend/apps/core/` and document model names, view count, URL count, test count, status, capabilities
- [X] T007 [P] [US1] Read all Django models in `backend/apps/inventario/` and document model names, view count, URL count, test count, status, capabilities
- [X] T008 [P] [US1] Read all Django models in `backend/apps/ventas/` and document model names, view count, URL count, test count, status, capabilities
- [X] T009 [P] [US1] Read all Django models in `backend/apps/facturacion/` and document model names, view count, URL count, test count, status, capabilities
- [X] T010 [P] [US1] Read all Django models in `backend/apps/sync/` and document model names, view count, URL count, test count, status, capabilities

### Section 2: Verified Metrics

- [X] T011 [US2] Run `scripts/run-tests-external.sh -n 015-metrics tests/` and read `Docs/Tests/015-metrics.summary` for pass/fail/coverage
- [X] T012 [P] [US2] Count total API endpoints from all 6 YAML files in `api/openapi/` (paths x methods)
- [X] T013 [P] [US2] Count frontend stats from `frontend/`: routes, TypeScript files, components

### Section 3: Entity Inventory

- [X] T014 [US4] For each Django model across all apps, document: model name, app, file path, fields with types and constraints, FK relationships, special patterns (TenantBoundModel, immutable, encrypted)

### Section 4: Feature Completion Map

- [X] T015 [US5] Extract from `git log` all feature branches 001-014 with: branch name, what it delivered, Django apps affected, completion date

### Section 5: Docker Compose Inventory

- [X] T016 [US8] Read `docker-compose.yml` and document: all services with images, profiles, port mappings, health checks, volumes

### Section 6: OpenAPI Endpoint Summary

- [X] T017 [US3] For each YAML in `api/openapi/`: document file name, module, endpoint count (paths x methods), list of paths grouped by resource

### Section 7: ADR Raw Material

- [X] T018 [US7] For each of the 14 ADR seed topics (spec US-7), identify: code/config evidence, file paths demonstrating the pattern, any visible alternatives

### Section 8: Existing Document State

- [X] T019 [US1] [US2] Read all 9 existing blueprint docs in `Docs/Project Blueprint/` and document: current version/date, language (EN/ES), module status entries, metrics cited, key sections with accuracy assessment

### Assembly

- [X] T020 Assemble all sections (T005-T019) into `claudedocs/015-codebase-facts.md` following the 8-section template in `Docs/Temp-prompting/015/instruction-plan.md`

**Checkpoint**: `015-codebase-facts.md` complete with all 8 sections. No placeholders. Phase 3 & 4 can now begin in parallel.

---

## Phase 3: Technical Core Documents (WRITER-A)

**Purpose**: Update/create 6 technical documents using facts from Phase 2
**Agent**: WRITER-A (`technical-writer`, worktree)
**Input**: `specs/015-blueprint-docs-overhaul/spec.md` + `claudedocs/015-codebase-facts.md`
**Depends on**: Phase 2 complete

**Goal**: All 6 technical documents accurate and internally consistent.

**Independent Test**: Each document's per-document checklist (instruction-plan.md lines 161-201) fully satisfied.

### Doc 1: Data Model & Domain Model

- [X] T021 [US4] Read current `Docs/Project Blueprint/Data Model & Domain Model.md` and identify all gaps vs Facts Section 3 (Entity Inventory)
- [X] T022 [US4] Add Facturacion entities (Comprobante, ComprobanteItem, ArCaCredential, PuntoDeVenta, CAEA) with fields and relationships from Facts Section 3 to `Docs/Project Blueprint/Data Model & Domain Model.md`
- [X] T023 [P] [US4] Add Ventas entities (Order, OrderItem, Payment, Customer) with fields and relationships from Facts Section 3 to `Docs/Project Blueprint/Data Model & Domain Model.md`
- [X] T024 [P] [US4] Add Tenant Customization entities (TenantFieldDefinition, TenantModuleConfig, BusinessTemplate) with note that BusinessTemplate is system-wide to `Docs/Project Blueprint/Data Model & Domain Model.md`
- [X] T025 [US4] Create Mermaid ERD diagrams covering all modules with FK relationships in `Docs/Project Blueprint/Data Model & Domain Model.md`, replacing any existing ASCII diagrams
- [X] T026 [US4] Update version from 0.1, set `Last Updated: 2026-02-21` in `Docs/Project Blueprint/Data Model & Domain Model.md`

### Doc 2: REST API Design

- [X] T027 [US3] Read current `Docs/Project Blueprint/REST API Design.md` and identify all gaps vs Facts Section 6 (OpenAPI Summary)
- [X] T028 [US3] Change status from "En Diseno" to "Active", add reference to `api/openapi/*.yaml` as authoritative source in `Docs/Project Blueprint/REST API Design.md`
- [X] T029 [US3] Add endpoint coverage per module from Facts Section 6 with path listings to `Docs/Project Blueprint/REST API Design.md`
- [X] T030 [US3] Add Facturacion/ARCA endpoint documentation and Problem+JSON (RFC 9457) error format examples to `Docs/Project Blueprint/REST API Design.md`
- [X] T031 [US3] Set `Last Updated: 2026-02-21` in `Docs/Project Blueprint/REST API Design.md`

### Doc 3: Low-Level Design

- [X] T032 [US1] [US2] Read current `Docs/Project Blueprint/Low-Level Design (LLD).md` and identify gaps in module status and metrics
- [X] T033 [US1] [US2] Update module status table and all metrics from Facts Sections 1 and 2 in `Docs/Project Blueprint/Low-Level Design (LLD).md`
- [X] T034 [US1] Update observability section to reflect consolidated `docker-compose.yml` and add tenant customization layer in `Docs/Project Blueprint/Low-Level Design (LLD).md`
- [X] T035 [US2] Set `Last Updated: 2026-02-21` in `Docs/Project Blueprint/Low-Level Design (LLD).md`

### Doc 4: Development Workflow

- [X] T036 [US2] Read current `Docs/Project Blueprint/Development Workflow.md` and identify outdated metrics and missing workflows
- [X] T037 [US2] Update test count and coverage from Facts Section 2 in `Docs/Project Blueprint/Development Workflow.md`
- [X] T038 [US2] Add external test runner (`scripts/run-tests-external.sh`) documentation and speckit workflow (specify -> plan -> tasks -> implement) to `Docs/Project Blueprint/Development Workflow.md`
- [X] T039 [US2] Add feature branch naming convention documentation, set `Last Updated: 2026-02-21` in `Docs/Project Blueprint/Development Workflow.md`

### Doc 5: Architecture Decision Records (NEW)

- [X] T040 [US7] Create `Docs/Project Blueprint/Architecture Decision Records (ADR).md` with document header, purpose section, and ADR format template (Date, Status, Context, Decision, Alternatives, Consequences)
- [X] T041 [US7] Write ADR-001 through ADR-005 (Web-first dev, Django monolith, Defense-in-Depth, RS256 JWT, Immutable ledger) using Facts Section 7 for evidence in `Docs/Project Blueprint/Architecture Decision Records (ADR).md`
- [X] T042 [P] [US7] Write ADR-006 through ADR-010 (AES-256-GCM, Argon2, JSONB customization, Problem+JSON, Docker consolidation) using Facts Section 7 for evidence in `Docs/Project Blueprint/Architecture Decision Records (ADR).md`
- [X] T043 [P] [US7] Write ADR-011 through ADR-014 (Offline-first sync, Spec-driven dev, External test runner, AI agent skills) using Facts Section 7 for evidence in `Docs/Project Blueprint/Architecture Decision Records (ADR).md`
- [X] T044 [US7] Set `Last Updated: 2026-02-21` in `Docs/Project Blueprint/Architecture Decision Records (ADR).md`

### Doc 6: Deployment & Infrastructure Guide (NEW)

- [X] T045 [US8] Create `Docs/Project Blueprint/Deployment & Infrastructure Guide.md` with document header and 3-section structure (Local Development, Production Target, Migration Path)
- [X] T046 [US8] Write Local Development section matching Facts Section 5 (Docker Compose services, profiles, ports, healthchecks) in `Docs/Project Blueprint/Deployment & Infrastructure Guide.md`
- [X] T047 [US8] Write Production Target section with Docker-to-GCP service mapping table, known gaps from spec 011 analysis, TBD items clearly marked in `Docs/Project Blueprint/Deployment & Infrastructure Guide.md`
- [X] T048 [US8] Write Migration Path section listing known considerations and marking unstudied items as "TBD — requires further analysis" in `Docs/Project Blueprint/Deployment & Infrastructure Guide.md`
- [X] T049 [US8] Set `Last Updated: 2026-02-21` in `Docs/Project Blueprint/Deployment & Infrastructure Guide.md`

**Checkpoint**: WRITER-A complete. 6 documents updated/created. All per-document checklists satisfied.

---

## Phase 4: Strategic & Onboarding Documents (WRITER-B) [PARALLEL with Phase 3]

**Purpose**: Update/create 6 strategic documents using facts from Phase 2
**Agent**: WRITER-B (`technical-writer`, worktree)
**Input**: `specs/015-blueprint-docs-overhaul/spec.md` + `claudedocs/015-codebase-facts.md`
**Depends on**: Phase 2 complete (runs in PARALLEL with Phase 3)

**Goal**: All 6 strategic documents accurate and internally consistent.

**Independent Test**: Each document's per-document checklist (instruction-plan.md lines 202-242) fully satisfied.

### Doc 7: Product Vision & Scope

- [X] T050 [US1] [US2] Read current `Docs/Project Blueprint/Product Vision & Scope.md` and identify all stale module status and metrics
- [X] T051 [US1] Update module status table from Facts Section 1, ensuring VENTAS and ARCA show "Complete" in `Docs/Project Blueprint/Product Vision & Scope.md`
- [X] T052 [US2] Update all metrics from Facts Section 2 in `Docs/Project Blueprint/Product Vision & Scope.md`
- [X] T053 [US5] Add MVP target May 1, 2026 and list features 001-014 with summaries from Facts Section 4 in `Docs/Project Blueprint/Product Vision & Scope.md`
- [X] T054 [US1] Set `Last Updated: 2026-02-21` in `Docs/Project Blueprint/Product Vision & Scope.md`

### Doc 8: High-Level Design

- [X] T055 [US10] Read current `Docs/Project Blueprint/High-Level Design (HLD).md` and identify dual-environment gaps and missing components
- [X] T056 [US10] Convert architecture diagram to Mermaid showing both Docker Compose current (labeled "Current") and planned GCP (labeled "Planned") in `Docs/Project Blueprint/High-Level Design (HLD).md`
- [X] T057 [US10] Add Next.js 16 as current dev frontend and Electron as planned production frontend with clear labels in `Docs/Project Blueprint/High-Level Design (HLD).md`
- [X] T058 [US1] Add tenant customization layer and update observability stack description in `Docs/Project Blueprint/High-Level Design (HLD).md`
- [X] T059 [US1] Update module status table from Facts Section 1, set `Last Updated: 2026-02-21` in `Docs/Project Blueprint/High-Level Design (HLD).md`

### Doc 9: Product Requirements Document

- [X] T060 [US10] Read current `Docs/Project Blueprint/PRD.md` and identify areas describing Electron as current rather than planned
- [X] T061 [US10] Update to distinguish Next.js (implemented, current dev) from Electron (planned, production target) in `Docs/Project Blueprint/PRD.md`
- [X] T062 [US10] Clarify offline-first capability: current state (backend sync endpoints ready) vs planned state (Electron + SQLite) in `Docs/Project Blueprint/PRD.md`
- [X] T063 [US1] Update module capabilities to reflect actual implementation from Facts Section 1, set `Last Updated: 2026-02-21` in `Docs/Project Blueprint/PRD.md`

### Doc 10: Software Requirements Specification

- [X] T064 [US10] Read current `Docs/Project Blueprint/Software Requirements Specification (SRS).md` and identify design constraints that need dual-environment update
- [X] T065 [US10] Update design constraints: Electron = production constraint, Next.js = development implementation in `Docs/Project Blueprint/Software Requirements Specification (SRS).md`
- [X] T066 [US10] Update requirements to distinguish implemented reality from planned targets (labeled) in `Docs/Project Blueprint/Software Requirements Specification (SRS).md`
- [X] T067 [US1] Set `Last Updated: 2026-02-21` in `Docs/Project Blueprint/Software Requirements Specification (SRS).md`

### Doc 11: Project Roadmap

- [X] T068 [US5] Read current `Docs/Project Blueprint/Roadmap.md` and identify the original timeline that needs replacement
- [X] T069 [US5] Add MVP May 1, 2026 target with features 001-014 showing completion dates from Facts Section 4 in `Docs/Project Blueprint/Roadmap.md`
- [X] T070 [US5] Categorize remaining items as "MVP Required" (COMPRAS, REPORTES, Electron, GCP, CI/CD) or "Post-MVP" in `Docs/Project Blueprint/Roadmap.md`
- [X] T071 [US5] Set `Last Updated: 2026-02-21` in `Docs/Project Blueprint/Roadmap.md`

### Doc 12: Developer Onboarding Guide (NEW)

- [X] T072 [US6] Create `Docs/Project Blueprint/Developer Onboarding Guide.md` with document header and 9-section structure per spec US-6
- [X] T073 [US6] Write Architecture Overview section with system diagram (Mermaid) and module summary in `Docs/Project Blueprint/Developer Onboarding Guide.md`
- [X] T074 [US6] Write Environment Setup section: Docker Compose only (`docker compose up`, `seed_all`, verify tests pass via `docker compose exec web pytest`) in `Docs/Project Blueprint/Developer Onboarding Guide.md`
- [X] T075 [US6] Write Module Map section with status from Facts Section 1 and directory structure from actual project layout in `Docs/Project Blueprint/Developer Onboarding Guide.md`
- [X] T076 [US6] Write Spec-Driven Development section (speckit workflow: specify -> plan -> tasks -> implement) in `Docs/Project Blueprint/Developer Onboarding Guide.md`
- [X] T077 [US6] Write Key Conventions section (TenantBoundModel, immutable ledger, Problem+JSON, Mermaid diagrams) in `Docs/Project Blueprint/Developer Onboarding Guide.md`
- [X] T078 [US6] Write Running Tests section (Docker exec pytest, test markers, external test runner for agents) in `Docs/Project Blueprint/Developer Onboarding Guide.md`
- [X] T079 [US6] Write Feature Status Dashboard and AI Agent Context sections (CLAUDE.md, skills, Serena memories) in `Docs/Project Blueprint/Developer Onboarding Guide.md`
- [X] T080 [US6] Set `Last Updated: 2026-02-21` in `Docs/Project Blueprint/Developer Onboarding Guide.md`

**Checkpoint**: WRITER-B complete. 6 documents updated/created. All per-document checklists satisfied.

---

## Phase 5: Cross-Reference Validation & Polish

**Purpose**: Verify consistency across all 12 documents and fix any discrepancies
**Agent**: LEAD (orchestrator, main session)
**Depends on**: Phase 3 AND Phase 4 complete

### Validation

- [X] T081 [US9] Read module status tables from all 12 documents and verify identical status per module across all docs
- [X] T082 [US9] Grep all 12 documents for test counts, coverage percentages, and endpoint counts — verify same numbers everywhere
- [X] T083 [US9] Find all "see", "refer to", "as described in" cross-references across all 12 docs and verify each destination section exists and is accurate
- [X] T084 [US9] Verify all Mermaid diagram code blocks use valid syntax (check for common errors: missing arrows, unclosed brackets)
- [X] T085 [US9] Verify every document has `Last Updated: 2026-02-21` in its header
- [X] T086 [US9] Verify no document changed language (compare EN/ES from Facts Section 8 against final docs)

### Fixes

- [X] T087 [US9] Fix any module status inconsistencies found in T081 (update docs to match Facts Section 1)
- [X] T088 [US9] Fix any metric inconsistencies found in T082 (update docs to match Facts Section 2)
- [X] T089 [US9] Fix any broken cross-references found in T083 (update source or destination doc)

### Commit

- [ ] T090 Stage all updated and new documents in `Docs/Project Blueprint/` and `claudedocs/015-codebase-facts.md` for commit

**Checkpoint**: All 12 documents consistent, cross-referenced, and ready for commit.

---

## Dependencies & Execution Order

### Phase Dependencies

```text
Phase 1 (Setup)          → No dependencies, starts immediately
Phase 2 (Research)        → Depends on Phase 1, BLOCKS Phases 3 & 4
Phase 3 (WRITER-A)        → Depends on Phase 2 complete
Phase 4 (WRITER-B)        → Depends on Phase 2 complete, PARALLEL with Phase 3
Phase 5 (Validation)      → Depends on Phase 3 AND Phase 4 complete
```

### User Story to Task Mapping

| User Story | Priority | Primary Tasks | Phase |
|---|---|---|---|
| US1 - Module Status | P1 | T005-T010, T019, T033-T034, T051, T058-T059, T063, T067, T081 | 2, 3, 4, 5 |
| US2 - Quality Metrics | P1 | T011-T013, T019, T033, T037, T052, T082 | 2, 3, 4, 5 |
| US3 - REST API Docs | P1 | T017, T027-T031 | 2, 3 |
| US4 - Data Model | P1 | T014, T021-T026 | 2, 3 |
| US5 - Roadmap | P2 | T015, T053, T068-T071 | 2, 4 |
| US6 - Onboarding | P2 | T072-T080 | 4 |
| US7 - ADR | P2 | T018, T040-T044 | 2, 3 |
| US8 - Deployment Guide | P3 | T016, T045-T049 | 2, 3 |
| US9 - Cross-References | P3 | T081-T089 | 5 |
| US10 - Dual-Environment | P2 | T055-T062, T064-T066 | 4 |

### Within Each Phase

- **Phase 2**: T005-T010 parallelizable (different apps), T011-T013 parallelizable, T014-T019 sequential within sections, T020 depends on all
- **Phase 3**: Sequential within each document (read → update → set date), documents can be done in any order
- **Phase 4**: Sequential within each document, documents can be done in any order
- **Phase 5**: T081-T086 parallelizable (different checks), T087-T089 depend on corresponding checks, T090 depends on all fixes

### Parallel Opportunities

```text
Phase 2 parallelism:
  T005 ║ T006 ║ T007 ║ T008 ║ T009 ║ T010  (6 Django apps)
  T011 ║ T012 ║ T013  (metrics, endpoints, frontend)

Phase 3 ║ Phase 4 parallelism:
  WRITER-A (T021-T049) ║ WRITER-B (T050-T080)

Phase 5 parallelism:
  T081 ║ T082 ║ T083 ║ T084 ║ T085 ║ T086  (6 validation checks)
```

---

## Implementation Strategy

### MVP First (P1 User Stories)

1. Complete Phase 1: Setup (T001-T004)
2. Complete Phase 2: Research (T005-T020) — RESEARCHER agent
3. Complete Phase 3 + 4: Writing (T021-T080) — WRITER-A ║ WRITER-B
4. **At minimum, P1 docs are accurate**: Data Model, REST API, LLD, Workflow, Product Vision, HLD
5. Complete Phase 5: Validation (T081-T090)

### Incremental Delivery

Phase 2 produces the facts doc — this alone has value as a codebase reference.
Phase 3 + 4 produce 12 documents — each is independently useful once written.
Phase 5 ensures cross-document consistency — critical before commit.

### Agent Team Strategy

```text
LEAD:         Phase 1 (setup) → spawn RESEARCHER
RESEARCHER:   Phase 2 (facts extraction) → signal complete
LEAD:         spawn WRITER-A + WRITER-B in parallel
WRITER-A:     Phase 3 (6 technical docs) → signal complete
WRITER-B:     Phase 4 (6 strategic docs) → signal complete
LEAD:         Phase 5 (validation + fixes) → commit
```

---

## Notes

- [P] tasks = different files or resources, no dependencies on incomplete tasks
- [Story] labels map to spec user stories (US1-US10) for traceability
- US1 (Module Status) and US2 (Quality Metrics) are cross-cutting — satisfied incrementally across phases
- US9 (Cross-References) is exclusively Phase 5 — requires all docs complete
- Writers must NOT read codebase directly — use only `015-codebase-facts.md`
- All metrics must be exact copies from Facts Section 2 — no rounding or recalculation
- Mermaid format only for all diagrams — convert any existing ASCII
- Preserve document language (EN or ES) — do not translate
