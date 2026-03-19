# Tasks: Acopio ERP Roadmap

**Input**: Design documents from `/specs/007-acopio-roadmap/`
**Prerequisites**: plan.md ✅ spec.md ✅ research.md ✅ contracts/acceptance-gates.md ✅ quickstart.md ✅
**Deliverable**: `Docs/Project Blueprint/Roadmap.md` v1.0
**Type**: Blueprint document writing (no code, no tests)

**Organization**: Tasks grouped by user story for independent writing and verification.
**Note on §3 ordering**: US3 (Strategic Context) is written before US1's §5 due to document
structure constraints — §3 must precede §5 in the output file. Priority labelling reflects
spec importance; writing order follows plan.md execution sequence.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (independent content, no dependency on incomplete prior task)
- **[Story]**: Which user story this task belongs to (US1=P1, US2=P2, US3=P2, US4=P3)

---

## Phase 1: Setup

**Purpose**: Verify all inputs are available and conventions are understood before writing.

- [x] T001 Verify all 6 input blueprint docs exist at v1.0: `Docs/Project Blueprint/Product Vision & Scope.md`, `PRD.md`, `Data Model & Domain Model.md`, `Architecture Decision Records (ADR).md`, `High-Level Design (HLD).md`, `REST API Design.md`
- [x] T002 Read §1 metadata block from `Docs/Project Blueprint/REST API Design.md` (or HLD) to confirm the exact blockquote format and changelog table format used by the blueprint series
- [x] T003 Confirm `Docs/Project Blueprint/Roadmap.md` does not yet exist (or is empty) — do not overwrite without reading first

**Checkpoint**: All 6 input docs confirmed v1.0. Output path clear. Convention understood.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Write §1 metadata (always first in every blueprint doc) and run all RAG
queries needed for the writing phases. No user story work starts until these are done.

**⚠️ CRITICAL**: §1 MUST be written first (document header). All RAG queries MUST complete
before writing §3 and §9.

- [x] T004 Write `§1 Document Metadata` in `Docs/Project Blueprint/Roadmap.md`: blockquote header (Version 1.0, Status: Draft, Date: today, Depends on: spec-01 through spec-06), one-paragraph scope statement, and changelog table (single row v1.0)
- [x] T005 [P] Run RAG query for §3.1–§3.2: `.venv/bin/python scripts/qdrant/qdrant_search.py -q "acopio software market AGIS competitors VB6 switching costs" -l 5` — save key facts to working notes
- [x] T006 [P] Run RAG query for §3.3–§3.4: `.venv/bin/python scripts/qdrant/qdrant_search.py -q "acopiador pain points TAM market sizing geographic distribution" -l 5` — save key figures to working notes
- [x] T007 [P] Run RAG query for §9.1–§9.2: `.venv/bin/python scripts/qdrant/qdrant_search.py -q "contador rural accountant channel distribution GTM acopiador" -l 5` — save channel strategy facts
- [x] T008 [P] Run RAG query for §9.5 and §7.1: `.venv/bin/python scripts/qdrant/qdrant_search.py -q "Expoagro Agroactiva grain trade events AI ML grain storage predictive" -l 5` — save trade events + AI features

**Checkpoint**: §1 written. RAG results available. Ready to begin user story sections.

---

## Phase 3: User Story 3 — Strategic Context (Priority: P2)

**⚠️ Written before US1 (despite lower priority) because §3 precedes §5 in document structure.**

**Goal**: §3 Strategic Context complete — an advisor unfamiliar with the project can read
§3 alone and answer: TAM, main competitor weakness, regulatory moat, and switching window.

**Independent Test**: Read §3 only (skip all other sections) and answer the four advisor
questions without consulting any other document. All four answers must be findable in §3.

### Implementation for User Story 3

- [x] T009 [US3] Write `§3.1 Market Opportunity` in `Docs/Project Blueprint/Roadmap.md`: ~1,073 private acopio companies, ~1,622 plants; Pampas concentration (Buenos Aires, Córdoba, Santa Fe); budget USD 150–500/month SMB, USD 500–2,000 medium; TAM estimate ~800 SMBs × ~$300/month avg = ~$2.9M ARR (labelled "(estimated)")
- [x] T010 [P] [US3] Write `§3.2 Competitive Positioning` in `Docs/Project Blueprint/Roadmap.md`: AGIS (AmericaGIS, 2,000+ clients, VB6/.NET, desktop-only — no web/mobile for acopio); Algoritmo S.A. (Silohub web integration, most dangerous direct competitor); Agrobit (SAP partner, enterprise only, not SMB threat); GraviTea gap: cloud-native + offline-first + ARCA velocity
- [x] T011 [P] [US3] Write `§3.3 Regulatory Tailwind` in `Docs/Project Blueprint/Roadmap.md`: RG 5689/2025 + RG 5821/2026 add real-time ARCA compliance; compliance velocity = ongoing moat (first vendor to ship compliant update wins trust); CPE/WSCPE already in Phase 1 (romaneo async queue per ADR-027); WSLPG Phase 2
- [x] T012 [P] [US3] Write `§3.4 Window of Opportunity` in `Docs/Project Blueprint/Roadmap.md`: post-soybean harvest April–June = only low-friction switching window; missing it = 12-month delay; generational shift (younger operators, ACA Jóvenes = early adopters); cloud-native entrants have 5–8 year window before AGIS modernises
- [x] T013 [US3] Gate G1 check: `grep -c "Version 1.0" "Docs/Project Blueprint/Roadmap.md"` must return ≥ 2

**Checkpoint**: §3 complete. Advisor can brief in <10 min. G1 passes.

---

## Phase 4: User Story 1 — Phase 1 Execution Plan (Priority: P1) 🎯 MVP

**Goal**: §4 + §5 + §8 Gantt complete — a team member can read these three sections and
know exactly what to build, in what order, and what "done" means for Phase 1 go-live.

**Independent Test**: A team member who has not read any prior spec reads §4 + §5 only,
then names all four MVP specs, their dependency order, and all five go-live criteria —
without consulting any other document.

### Implementation for User Story 1

- [x] T014 [US1] Write `§4 Product Phases Overview` in `Docs/Project Blueprint/Roadmap.md`: 1-paragraph narrative introducing 3-phase model; summary table with columns Phase | Name | Specs | Entry Criteria | Exit/Trigger — 3 rows (Phase 1: specs 09-12, go-live trigger; Phase 2: specs 13-16, ≥5 customers + ≥60 days + ≥100 romaneos; Phase 3: AI/ML, ≥20 customers + ≥10,000 romaneos)
- [x] T015 [US1] Write `§5.1 Phase 1 Scope` in `Docs/Project Blueprint/Roadmap.md`: 4-row table — spec-09 (Grain Reference → `apps/acopio/` models + fixtures), spec-10 (Romaneo Core → `apps/acopio/` + `rust/gravitea-core/src/merma.rs`), spec-11 (Storage & Position → `apps/acopio/` storage), spec-12 (Producer Accounts → `apps/cuentas/` + encrypted CUIT + blind index)
- [x] T016 [US1] Write `§5.2 Critical Path` in `Docs/Project Blueprint/Roadmap.md`: spec-09 MUST complete before spec-10 (GrainType FK); spec-10 MUST complete before spec-11 (storage refs romaneo); spec-11 and spec-12 CAN run in parallel once spec-10 merges; note that spec-10 (Romaneo Core) is the serial bottleneck (7-week estimate per research.md R2)
- [x] T017 [P] [US1] Write `§5.3 Deliverables Table` in `Docs/Project Blueprint/Roadmap.md`: columns Spec | Module path | Django models | Rust modules | Phase 1 REST endpoints (count from spec-06 REST API Design §13 Phase 1 rows)
- [x] T018 [US1] Write `§5.4 Go-Live Definition of Done` in `Docs/Project Blueprint/Roadmap.md`: binary checklist (every item pass/fail) — ≥5 items including: all 4 spec PRs merged to main; ≥1 romaneo end-to-end (truck in → stored → account updated); CPE lifecycle tested against ARCA test environment; offline sync tested (romaneo created offline, synced when connected); ≥1 paying customer has completed ≥1 romaneo in production
- [x] T019 [US1] Write `§5.5 Target Timeline` in `Docs/Project Blueprint/Roadmap.md`: T+ week offsets (not absolute calendar dates): T+0 spec-09 start; T+3 spec-09 merged; T+10 spec-10 merged; T+10→T+15 spec-11 ∥ spec-12 parallel; T+15→T+16 integration + ARCA test + data migration; T+16 Phase 1 go-live. Note: T+ = working weeks, 2 devs
- [x] T020 [US1] Gate G2 check: manually verify §5.4 DoD checklist has ≥5 binary (pass/fail) items with no subjective wording
- [x] T021 [US1] Write `§8 Mermaid Gantt diagram` in `Docs/Project Blueprint/Roadmap.md`: ` ```mermaid gantt ` block showing spec-09 through Phase 3 trigger gate using T+N notation (see 07-plan.md §8 for pre-written skeleton)
- [x] T022 [US1] Gate G3/G5 check: `grep -c '```mermaid' "Docs/Project Blueprint/Roadmap.md"` ≥ 1 (will add second diagram in T028); `grep -c "spec-09\|spec-10\|spec-11\|spec-12"` ≥ 8

**Checkpoint**: §4 + §5 + §8 Gantt complete. US1 independently testable. G2 passes.

---

## Phase 5: User Story 4 — Phase Boundary Enforcement (Priority: P3)

**Goal**: §6 + §7 complete — a team member can consult these sections and get a binary
answer to "can we start Phase 2/3 now?" from the trigger conditions.

**Independent Test**: Read §6 alone; ask "can we start WSLPG now?" — the Phase 2 trigger
conditions must give a clear binary answer without any ambiguity.

### Implementation for User Story 4

- [x] T023 [US4] Write `§6.1 Phase 2 Scope` in `Docs/Project Blueprint/Roadmap.md`: 4-spec table (spec-13 Agronomia Adaptation → extends existing modules; spec-14 WSLPG Integration → `apps/facturacion/wslpg/`; spec-15 Reports → `apps/reportes/`; spec-16 Canje → `apps/acopio/canje/`)
- [x] T024 [US4] Write `§6.2 Phase 2 Trigger Conditions` in `Docs/Project Blueprint/Roadmap.md`: ALL THREE required — (1) ≥5 paying customers; (2) Phase 1 production-stable ≥60 calendar days, no P1/P2 bugs open; (3) ≥100 romaneos processed in production. Explicit note: "Starting any spec-13+ work before this trigger is out of scope"
- [x] T025 [P] [US4] Write `§6.3 Phase 2 Deliverables Table` in `Docs/Project Blueprint/Roadmap.md`: same format as §5.3
- [x] T026 [US4] Write `§6.4 WSLPG Integration Notes` in `Docs/Project Blueprint/Roadmap.md`: SOAP service (WSLPG v1.22+); XML complexity; pyafipws reference implementation; effort estimate 4–6 weeks for spec-14; critical distinction: WSCPE = Phase 1 (CPE = grain transport certificate); WSLPG = Phase 2 (liquidación primaria = settlement, Form 1116 B/C); reference ADR-025 (WSAA hub-and-spoke)
- [x] T027 [P] [US4] Write `§7.1–§7.4 Phase 3 Intelligence & Scale` in `Docs/Project Blueprint/Roadmap.md`: §7.1 AI/ML candidates (predictive merma → price signals → anomaly detection → NLQ queries); §7.2 multi-tenant growth (white-label, cooperative chains, accountant portal expansion); §7.3 data readiness prerequisites (ADR-033 event log, ADR-034 ML scoring table, ADR-035 AI query patterns — all from Phase 1); §7.4 Phase 3 trigger (≥20 customers + ≥10,000 romaneos + AI pipeline reviewed)
- [x] T028 [US4] Complete `§8` by adding the spec dependency graph diagram in `Docs/Project Blueprint/Roadmap.md`: ` ```mermaid graph TD ` block showing spec-01 → spec-02 → spec-03 → spec-09 → spec-10 → spec-11/12 → GoLive → spec-13/14 → spec-15/16 (see 07-plan.md §8 for pre-written skeleton)
- [x] T029 [US4] Gate G3 final check: `grep -c '```mermaid' "Docs/Project Blueprint/Roadmap.md"` must return ≥ 2

**Checkpoint**: §6 + §7 + §8 complete. US4 independently testable. All Mermaid diagrams present.

---

## Phase 6: User Story 2 — Go-to-Market Calendar (Priority: P2)

**Goal**: §9 complete — a non-technical co-founder reads §9 alone and derives a 3-step
quarterly action plan (Q1 enrol contadores → Q2 convert → Q3 onboard) without any other doc.

**Independent Test**: A founder reads §9 alone, then states: (a) primary channel name,
(b) which months to begin outreach, (c) what to say when a prospect says "my data is in AGIS",
(d) 3 industry events by name.

### Implementation for User Story 2

- [x] T030 [US2] Write `§9.1 Contador Rural Flywheel` in `Docs/Project Blueprint/Roadmap.md`: rural accountant is dual decision-maker with owner; estudio serves 5–10 acopio/cooperative clients = 10× multiplier; distribution flywheel: free portal → time saved → recommends to clients; target: 10 enrolled contadores BEFORE public launch; accountant portal requirements (multi-client dashboard, vencimientos, SICORE/IVA exports)
- [x] T031 [US2] Write `§9.2 Sales Motion Timeline` in `Docs/Project Blueprint/Roadmap.md`: seasonal calendar — Jan–Mar pre-harvest (pipeline building via contadores); Apr–Jun post-soybean harvest PRIMARY conversion window (low-friction switching); Jul–Sep off-season (onboarding, case studies); Oct–Dec pre-summer (renewals, upsell, second-wave conversions)
- [x] T032 [P] [US2] Write `§9.3 Pricing Tiers` in `Docs/Project Blueprint/Roadmap.md`: SMB USD 199–499/month (1 branch, ≤5 users); Medium USD 499–999/month (2–5 branches, ≤20 users); note: "Exact pricing validated post customer discovery; ranges are directional only"
- [x] T033 [P] [US2] Write `§9.4 Migration Playbook` in `Docs/Project Blueprint/Roadmap.md`: AGIS uses SQL Server — structured import from AGIS CSV export or Excel (.xlsx); ≤2 hours from upload to first romaneo target; fiscal record continuity (10-year Argentine regulatory requirement → read-only archive view)
- [x] T034 [US2] Write `§9.5 Trade Events Calendar` in `Docs/Project Blueprint/Roadmap.md`: Expoagro (San Nicolás, Buenos Aires, March — 100k+ attendees); Agroactiva (Armstrong, Santa Fe, June — Córdoba/Santa Fe belt); CONINAGRO assembly (annual, cooperative network); BCCBA events (Bolsa de Cereales de Córdoba, regional pizarra price events)
- [x] T035 [US2] Gate G4/G6/G7 check: `grep -ic "contador" "Docs/Project Blueprint/Roadmap.md"` ≥ 4; `grep -ic "post-harvest\|abril\|june\|switching window" "Docs/Project Blueprint/Roadmap.md"` ≥ 2

**Checkpoint**: §9 complete. US2 independently testable. G4/G6/G7 pass.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Complete the remaining sections (§10, §11, §12, §2) and run all 12 acceptance
gates. §2 Executive Summary is written LAST as a synthesis of all prior sections.

- [x] T036 [P] Write `§10 Risk Register` in `Docs/Project Blueprint/Roadmap.md`: table only (no narrative) — ≥8 rows with columns `# | Risk | Probability | Impact | Mitigation` — mandatory risks per spec FR-005: R1 ARCA regulation change; R2 ARCA SOAP instability; R3 offline sync edge case; R4 data migration friction; R5 2-dev capacity (spec-10 bottleneck); R6 competitor response (Algoritmo web product); R7 contador channel slow; R8 post-harvest window missed
- [x] T037 [P] Write `§11 Success Metrics & KPIs` in `Docs/Project Blueprint/Roadmap.md`: table with ≥6 rows — columns `KPI | Target | Measurement Method | Phase` — mandatory KPIs: ≥1 paying customer by Phase 1 go-live; ≥50 romaneos in first 60 days; ≤2h onboarding time; ≥5 customers before Phase 2 trigger; ≤16 working weeks Phase 1 build; ≥10 contador enrollments pre-launch. All targets numeric.
- [x] T038 Write `§12 Team & Resource Requirements` in `Docs/Project Blueprint/Roadmap.md`: §12.1 two-developer model (Dev 1 = backend/domain: spec-09/10/11; Dev 2 = fullstack/integration: spec-12 + ARCA tests); parallel tracks (spec-11 ∥ spec-12); serial bottleneck (spec-10); §12.2 external dependencies (ARCA homologación env, WSAA cert, weighbridge test data, contador network); §12.3 tooling (all from HLD — no new infrastructure)
- [x] T039 Write `§2 Executive Summary` in `Docs/Project Blueprint/Roadmap.md` LAST: 3–4 paragraphs synthesising all other sections — (1) what GraviTea is; (2) why now (AGIS gap + regulatory velocity + switching window + generational shift); (3) execution plan in 3 sentences (Phase 1 T+16 weeks, Phase 2 triggered by ≥5 customers, Phase 3 AI after ≥20 customers); (4) GTM (contador flywheel, April–June window); add key facts blockquote (TAM, go-live, competitor, channel, window)
- [x] T040 Constitution cross-check on `Docs/Project Blueprint/Roadmap.md`: verify (a) WSCPE = Phase 1 / WSLPG = Phase 2 distinction is clear; (b) module paths are `apps/acopio/` and `apps/cuentas/` (not `apps/grain/` or other); (c) offline-first described as Phase 1 requirement not future feature; (d) append-only ledgers (AccountMovement, GrainMovement) — PATCH/DELETE not implied
- [x] T041 Gate G5/G8 check: `grep -c "| R[0-9]" "Docs/Project Blueprint/Roadmap.md"` ≥ 8 (risk rows); `grep -ci "KPI\|paying customer\|romaneo\|onboarding" "Docs/Project Blueprint/Roadmap.md"` ≥ 6
- [x] T042 Run all 12 acceptance gates from `specs/007-acopio-roadmap/quickstart.md` — all must PASS before proceeding
- [x] T043 Update `specs/007-acopio-roadmap/spec.md` status field from `Draft` to `Complete`
- [x] T044 Save Serena memory `session-2026-03-17-spec07-roadmap-complete` with: deliverable path, gate results (12/12 PASS), line count, key decisions (R1-R7 from research.md)

**Checkpoint**: All 12 gates PASS. Document complete. Memory saved.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 completion — BLOCKS all writing
- **US3 Strategic Context (Phase 3)**: Depends on Phase 2 (needs RAG results from T005/T006)
- **US1 Phase 1 Plan (Phase 4)**: Depends on Phase 2 (RAG complete) — §5 can begin after §3 is written (for document structure coherence, though content is independent)
- **US4 Phase Boundaries (Phase 5)**: Depends on Phase 4 (§6-§7 reference Phase 1 scope from §5)
- **US2 GTM (Phase 6)**: Depends on Phase 2 (needs RAG from T007/T008) — content independent of §5
- **Polish (Phase 7)**: Depends on Phases 3-6 complete — §2 executive summary requires all sections exist

### User Story Dependencies

- **US1 (P1)**: Depends on Foundation (Phase 2) complete and §3 written (document ordering)
- **US2 (P2)**: Depends on Foundation (Phase 2) complete — content independent of US1/US3/US4
- **US3 (P2)**: Depends on Foundation (Phase 2) complete — content independent of other stories
- **US4 (P3)**: Depends on US1 §5 (Phase 4) complete — §6 references Phase 1 scope

### Within Each Phase

- RAG queries (T005-T008) run in parallel before writing
- Independent subsections within a section marked [P] can be written simultaneously
- Each section completed and verified before moving to the next

### Parallel Opportunities

- T005, T006, T007, T008: All RAG queries run in parallel in Phase 2
- T010, T011, T012 (§3 subsections): All can be written in parallel
- T017 (§5.3 table) can be written in parallel while T016 (§5.2 text) is being written
- T025, T027 (§6.3 table and §7 sections): Can be written in parallel
- T032, T033 (§9.3 pricing and §9.4 migration): Can be written in parallel
- T036 (§10 risks) and T037 (§11 KPIs): Can be written in parallel

---

## Parallel Writing Example: US3 (Strategic Context §3)

```text
# All subsections of §3 can be written in parallel:
Task: "Write §3.2 Competitive Positioning (T010)"  → uses RAG results from T005
Task: "Write §3.3 Regulatory Tailwind (T011)"      → uses RAG results from T005
Task: "Write §3.4 Window of Opportunity (T012)"    → uses RAG results from T006
# Then merge into document and gate-check (T013)
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001-T003)
2. Complete Phase 2: Foundational (T004-T008) — CRITICAL
3. Complete Phase 3: US3 Strategic Context (T009-T013) — prerequisite for US1 section ordering
4. Complete Phase 4: US1 Phase 1 Plan (T014-T022) — §4 + §5 + §8 Gantt
5. **STOP and validate**: Can a team member read §3-§5 alone and make Phase 1 execution decisions?
6. If YES → MVP document increment delivered

### Incremental Delivery

1. Foundation + US3 → §3 strategic context ready (advisor can be briefed)
2. + US1 → §4 + §5 + §8 Gantt ready (Phase 1 can begin)
3. + US4 → §6 + §7 + §8 dep graph ready (Phase 2/3 scope locked)
4. + US2 → §9 GTM ready (sales campaign can launch)
5. + Polish → Full document v1.0 (all 12 gates pass)

### Single-Writer Strategy

Since this is written by one person (Bruno), all phases are sequential:
Complete Phase 1 → Phase 2 → Phase 3 → Phase 4 → Phase 5 → Phase 6 → Phase 7
Writing order matches 07-plan.md execution sequence.

---

## Notes

- [P] tasks within a phase can be drafted simultaneously in different editor panes
- Every section must match the §N heading convention from prior blueprint docs
- Use T+ week offsets in all timeline references — never absolute calendar dates in §5-§8
- Seasonal GTM dates (April–June) in §9 are calendar-fixed by nature — acceptable exception
- After T042 (all 12 gates pass), the document is final — no further edits needed
- Commit message: `docs: add Roadmap.md v1.0 (spec-07)`
