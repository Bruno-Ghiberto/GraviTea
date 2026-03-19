---

description: "Task list for Acopio de Granos Product Vision & Scope document rewrite"

---

# Tasks: Acopio de Granos Product Vision & Scope

**Input**: Design documents from `specs/001-acopio-vision/`
**Target file**: `Docs/Project Blueprint/Product Vision & Scope.md` (in-place rewrite v0.4 → v1.0)
**Prerequisites**: plan.md ✅ | spec.md ✅ | research.md ✅ | data-model.md ✅ | contracts/ ✅ | quickstart.md ✅

**Project type**: Blueprint document — single-author writing task. No code, no tests, no agent teams.
**Tests**: N/A — validation is run via manual checklist in `contracts/document-structure.md` and `quickstart.md`

**Primary data source**: `specs/001-acopio-vision/research.md` (all facts RAG-verified)
**Section contracts**: `specs/001-acopio-vision/contracts/document-structure.md`
**Writing guide**: `specs/001-acopio-vision/quickstart.md`

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (independent section/diagram, no blocking dependencies)
- **[Story]**: Which user story this task enables (US1-US5)
- All writes target `Docs/Project Blueprint/Product Vision & Scope.md` unless noted

---

## Phase 1: Setup

**Purpose**: Pre-writing preparation — read source materials, back up v0.4, create v1.0 shell.

- [X] T001 Read and internalize `specs/001-acopio-vision/quickstart.md` (pre-writing setup — 15 min)
- [X] T002 [P] Read `Docs/Project Blueprint/Descripción General del Producto.md` — extract exact module names (8 modules in Spanish) for S4 module map
- [X] T003 [P] Read `Docs/Project Blueprint/Product Vision & Scope.md` v0.4 — extract Implementation Progress table (lines 13-28) and Feature Branch History table (001-025) verbatim to clipboard/scratch
- [X] T004 Create `Docs/Project Blueprint/Product Vision & Scope.v0.4.backup.md` — copy full v0.4 content verbatim (safety backup before in-place rewrite)
- [X] T005 Replace header of `Docs/Project Blueprint/Product Vision & Scope.md` with v1.0 stub: Version 1.0, Date 2026-03-15, Status "Vision Document — Committed" — leaves all other content intact until section rewrites

**Checkpoint**: v0.4 backup exists; v1.0 header is in place; all source material read.

---

## Phase 2: Foundational — Section 3 Market Context

**Purpose**: Market data foundation that all other sections depend on. MUST complete before US1-US5 phases.

**⚠️ CRITICAL**: S2, S4, S5, S6, S7, S8, S9 all cite or build from S3 facts. Write S3 first.

**Independent Test**: Read S3 alone — a product owner must be able to answer: (a) How many acopiadores exist nationally? (b) What is AGIS's client count? (c) What are the top 3 pain points? (d) Where is GRAVITEA positioned vs competitors?

- [X] T006 Write Section 3.1 Market Sizing in target file — TAM (~1,259 enterprises, ~2,458 plants), SAM (~1,073 private, ~1,622 plants), SOM (Córdoba 81 + Santa Fe 58 members), all figures citing [Research 6.1]. Source: `research.md §3.1 Market Sizing`
- [X] T007 Create Mermaid competitive positioning quadrant diagram for Section 3.2 in target file — axes: Desktop-only → Cloud-native (X) vs Generic → Acopio-depth (Y); GRAVITEA alone in upper-right quadrant; plot Algoritmo, AGIS, Physis, AgroAcopio, Finnegans GO Granos, Versat. Source: `research.md §3.2`, contract: `contracts/document-structure.md §S3-CONTRACT`
- [X] T008 Write 11 competitor profiles for Section 3.2 in target file — individual cards/rows for all 11 entries (8 desktop specialists + 3 cloud generalists). **CRITICAL**: AGIS = "2,000+ acopio clients" [Research 4.2], NOT "3,000+". Source: `research.md §3.2` competitor tables
- [X] T009 Add government mandatory systems callout box to Section 3.2 in target file — SIO Granos, SISA/Registro Sistémico (RG 5689/2025), BolsaTech — labeled "must integrate, not compete"
- [X] T010 Write 4-tier market segmentation for Section 3.2 in target file — large/medium/small-generic/small-manual with % ranges per tier. Source: `research.md §3.2 Market segmentation`
- [X] T011 Write 6 pain points for Section 3.3 in target file — include all regulatory citations (RG 3419/2012, RG 5689/2025, RG 5821/2026). **CRITICAL connectivity nuance**: write "brief outages during peak harvest halt CTG/SISA operations" — plants are in towns, NOT "40.2% have no internet" framing. Source: `research.md §3.4 Pain Points`
- [X] T012 Write technology adoption stats for Section 3.3 in target file — 92% apps, 65% digital platforms, 62.1M smartphone connections, buying behavior (April-June switching window, $150-500 budget). Source: `research.md §3.4 Technology adoption + Buying behavior`

**Checkpoint Gate 1** (from `quickstart.md`):
- [X] T013 Run Gate 1 validation — verify: TAM/SAM/SOM present with [Research 6.1]; Mermaid quadrant renders in GitHub preview; AGIS shows "2,000+" not "3,000+"; government systems box labeled "mandatory" or "must integrate"; connectivity nuance is present

---

## Phase 3: User Story 1 — Developer Aligns Feature Work to Acopio Strategy (Priority: P1) 🎯

**Goal**: Developer reads the document and can (a) identify the target market, (b) locate any feature in the phased roadmap, (c) identify which persona benefits from that feature, (d) confirm acopio commitment is unambiguous — all without consulting any other document.

**Independent Test**: A developer unfamiliar with the project can answer — "Which phase does grain quality analysis belong to?" (Phase 1 MVP), "Which persona uses the balanza daily?" (Balancero/Recibidor), "Is this still a horizontal ERP?" (No — zero generic retail language found).

- [X] T014 Write Section 2 Strategic Purpose — vision statement ("Empower independent Argentine grain operators..."), vertical commitment declaration (declarative, no hedging), 6 Ironclad principles (copy 4 from v0.4 + add "Regulatory Automation" + "AI-Ready Data Architecture"). Source: `research.md §S2`, contract: `contracts/document-structure.md §S2-CONTRACT`
- [X] T015 [P] [US1] Create Mermaid module map diagram for Section 4.1 in target file — 8 modules with exact Spanish names from Descripción General del Producto.md (RECEPCIÓN, ALMACENAMIENTO, CALIDAD, CUENTAS CORRIENTES, LIQUIDACIONES, FACTURACIÓN, AGRONOMÍA, CANJE) showing directional relationships. Contract: `contracts/document-structure.md §S4-CONTRACT`
- [X] T016 [P] [US1] Create Mermaid core operational flow diagram for Section 4.2 in target file — Romaneo-to-Position loop: Llegada CPE/CTG → Peso Bruto → Calado y Muestreo → Análisis Lab → Cálculo Merma → Peso Neto Conforme → Boleta de Romaneo → [Silo Assignment + Producer Account Credit] → [Liquidación 1116-C | Canje por Insumos]. Source: `research.md §S4`
- [X] T017 [US1] Write Section 4.3 MVP Scope in target file — define Phase 1 Romaneo-to-Position loop with 4 explicit sub-components: reception (CPE/CTG, peso bruto, calado), quality analysis (lab grading, tolerance tables, merma calculations), storage assignment (silo by grain type/quality/campaign), producer account credit (saldo kg + movement history). Source: `research.md §D-004`, contract: `S4-CONTRACT mvp_scope`
- [X] T018 [P] [US1] Write Section 4.4 Technical Differentiators in target file — 6 items, offline-first MUST be #1: (1) Offline-first hybrid (2) Rust acceleration 2-9x PyO3 (3) PostgreSQL RLS multi-tenancy (4) ARCA direct WSAA/WSFEv1/WSLPG (5) AI-ready data architecture (6) AES-256-GCM field encryption. Source: `research.md §S4 Technical differentiators`
- [X] T019 [P] [US1] Write Section 4.5 Dual Inventory explanation in target file — grain (activo líquido, continuous kg) vs insumos (activo contable, discrete units) — explains why new `apps/acopio/` required. Source: `research.md §S4 Dual inventory`
- [X] T020 [US1] Write Section 4.6 Out of Scope in target file — minimum 6 items: Generic POS, B2C e-commerce, Manufacturing/industrial, Field agriculture/farm management, Fleet/logistics management, Payroll/HR. Source: `research.md §S4 Out of scope`
- [X] T021 [P] [US1] Create Mermaid phased roadmap diagram for Section 4.7 in target file — 4 phases: Phase 1 (Romaneo + Position), Phase 2 (Liquidaciones + WSLPG), Phase 3 (Canje + Agronomía), Phase 4 (AI). Use `timeline` or `gantt` Mermaid syntax. Contract: `S4-CONTRACT phased_roadmap`
- [X] T022 [US1] Write Section 5 User Personas in target file — (a) Mermaid hierarchy diagram showing persona→module relationships; (b) 5 individual persona cards (Dueño/Gerente, Balancero/Recibidor, Laboratorista, Administrador/Contable, Contador Rural), each with: role, primary JTBD, key pain, tech comfort; (c) ICP definition. Source: `research.md §S5`, contract: `contracts/document-structure.md §S5-CONTRACT`

**Checkpoint Gate 2 + 3** (from `quickstart.md`):
- [X] T023 Run Gates 2 & 3 validation — verify: (Gate 2) vision statement contains "acopiadores de granos" + "offline-first" + "regulatory compliance"; 6 Ironclad principles including 2 new ones; zero hedging language. (Gate 3) 8 modules exact names; offline-first is differentiator #1; Phase 4 = AI not Phase 1; all Mermaid diagrams render.
- [X] T024 [US1] Run DL-001 check — `grep -i "hardware store\|beverage distributor\|cashier\|under evaluation"` target file → expected zero matches

**Checkpoint**: US1 complete — developer can align feature work to acopio strategy using this document alone.

---

## Phase 4: User Story 2 — Product Owner Makes Scope Decisions (Priority: P2)

**Goal**: Product owner can use market data + value proposition canvas to resolve prioritization debates (e.g., "weighbridge integration before canje module?") without re-reading raw research.

**Independent Test**: Present scope trade-off "Should we build weighbridge integration before canje module?" — document must provide sufficient market data + pain point severity + competitive gap to make an informed decision.

- [X] T025 [US2] Write Section 6 Value Proposition Canvas in target file — structured table (or Mermaid) mapping 6 pain-to-gain pairs: (1) Regulatory burden → Automatic filings; (2) Tax withholding complexity → Instant retenciones calculations + SICORE output; (3) Inventory reconciliation → Real-time grain position; (4) Producer account disputes → Transparent grading via tolerance tables; (5) Manual entry during harvest → Weighbridge integration + offline romaneo; (6) Internet outages halting CTG → CAEA hybrid mode. Source: `research.md §S3 + S4`, contract: `contracts/document-structure.md §S6-CONTRACT`
- [X] T026 [US2] Verify S3 serves product owner scope decisions — run the 4-question test from `quickstart.md §S3 Independent Test`: (a) How many acopiadores exist nationally? (b) What is AGIS's client count? (c) What are the top 3 pain points? (d) Where is GRAVITEA positioned vs competitors? All 4 answers must be findable in S3 alone. If any answer is missing or requires reading another section, add the missing content to the relevant S3 subsection in the target file. Pass condition: all 4 questions answerable from S3 text only.

**Checkpoint Gate 4** (from `quickstart.md`):
- [X] T027 Run Gate 4 validation — verify: 5 personas present; no generic roles; each persona has JTBD + pain + tech comfort; ICP definition is domain-specific (also validates T022 from Phase 3)
- [X] T028 Run Gate 5 validation — verify: 6 pain-gain pairs in S6; "CAEA" appears in connectivity row; "IVA" or "retenciones" appears in tax row; all gains reference specific product capabilities (not vague "better software")

**Checkpoint**: US2 complete — product owner can evaluate feature prioritization using market data in this document.

---

## Phase 5: User Story 3 — GTM Team Plans Sales Strategy (Priority: P3)

**Goal**: GTM team can produce a 90-day sales action plan (target accounts, channel tactics, event calendar, pricing proposals) using only this document.

**Independent Test**: GTM member creates a 90-day plan with: specific channel actions (contador outreach via FACPCE seminars), event attendance dates (A Todo Trigo May 2026), pricing proposals ($90/seat disruption math), geographic targeting (Villa María) — without consulting any other document.

- [X] T029 [P] [US3] Write Section 7.1 Contador Rural Channel in target file — free portal mechanics (real-time transactions, automated books, multi-client dashboard, one-click exports); "Invitar a tu contador" referral flow; 5-15 acopio clients per estudio (20-50 total agricultural); FACPCE RT22/RT41 + CPCE Córdoba event targeting; Xubio/Colppy model reference. Source: `research.md §S7-8 Contador rural channel`
- [X] T030 [P] [US3] Write Section 7.2 Geographic Beachhead in target file — Villa María → Córdoba → Pampas with D-005 rationale (Sociedad de Acopiadores de Córdoba, 81 Federación members, founder network). **CRITICAL**: acknowledge AGIS is also HQ'd in Villa María — name both the opportunity (dissatisfied AGIS clients) and the risk (deep local AGIS relationships). Source: `research.md §D-005`
- [X] T031 [P] [US3] Write Section 7.3 Trade Events table in target file — Tier 1: A Todo Trigo (May 2026, Mar del Plata), Sociedad de Acopiadores de Córdoba, Federación de Acopiadores. Tier 2: Grano SAC/Expo Poscosecha (November, Rosario), ExpoAgro, AgroActiva. Source: `research.md §S7-8 Trade events`
- [X] T032 [US3] Write Section 7.4 Switching Strategy in target file — April-June window (post-soybean harvest, lowest operational intensity); migration tools from AGIS/Physis/Excel formats; ACA Jóvenes network targeting for generational transition. Source: `research.md §S7-8 Switching strategy`
- [X] T033 [US3] Write Section 8 Pricing Strategy in target file — (a) pricing model: $90/seat/month + $75/seat annual + free contador portal; (b) disruption math: 2 users × $90 = $180/month vs incumbent $500-800/establishment (must show arithmetic); (c) USD-indexing rationale (grain in USD, ARS devaluation protection); (d) competitive comparison table including Versat USD 200-640/month reference. Source: `research.md §S7-8 Pricing`, contract: `contracts/document-structure.md §S8-CONTRACT`

**Checkpoint Gate 6** (from `quickstart.md`):
- [X] T034 Run Gate 6 validation — verify: "Invitar a tu contador" verbatim present; "5-15 acopio clients per estudio" present; Villa María named first with AGIS risk acknowledged; A Todo Trigo has "May 2026" and "Mar del Plata"; April-June switching window with "post-soybean harvest"; both $90 and $75 present; 2 users = $180 vs $500+ disruption math shown.

**Checkpoint**: US3 complete — GTM team can create 90-day sales action plan from this document alone.

---

## Phase 6: User Story 4 — Investor Evaluates Market Opportunity (Priority: P4)

**Goal**: Investor or advisor reads the document and can articulate: market size, why incumbents are vulnerable, pricing model, and 4-phase roadmap from MVP to AI-differentiated platform.

**Independent Test**: Someone unfamiliar with the project reads the document and correctly states (a) market size (b) why incumbents are vulnerable (legacy stacks VB6, Odoo 13) (c) pricing model ($90/seat disruption) (d) 4-phase roadmap.

- [X] T035 [P] [US4] Write Section 9 AI Differentiation Roadmap in target file — (a) framing paragraph: "Platform built in Phases 1-3 captures structured data enabling Phase 4 ML without migration — this is Ironclad Principle 6 in action"; (b) 7-capability table with model architectures and expected outcomes; (c) all capabilities explicitly Phase 3 or 4. Cite [Research 9.1]. Source: `research.md §S9`, contract: `contracts/document-structure.md §S9-CONTRACT`
- [X] T036 [P] [US4] Write Section 10 Success Metrics in target file — 3 categories: Operational (harvest > 10 trucks/hour vs manual 4-6/hour, sync < 60s, uptime 99.5%), Adoption (balancero onboarding < 1 day, active rate > 80% in 30 days), Business (stock discrepancy < 2% after 3 months vs industry 10-15%, CTG compliance > 99.5%, ARPU $360/tenant = 4 × $90). Source: `research.md §S10`, contract: `contracts/document-structure.md §S10-CONTRACT`
- [X] T037 [P] [US4] Write Section 11 Risks & Mitigation in target file — 6-row table with Severity column (High/Medium/Low): connectivity (High, offline-first), regulatory change velocity (High, modular ARCA), competitor response (Medium, first-mover), generational resistance (Medium, ACA Jóvenes), data migration barrier (High, April-June + import tools), 7-in-10 implementation failure rate (High, process-first onboarding) with [Albor Agtech] attribution. Source: `research.md §S11`, contract: `contracts/document-structure.md §S11-CONTRACT`
- [X] T038 [US4] Verify investor narrative coherence — read S3 → S4 → S8 → S9 as a mini investor pitch: market opportunity (S3) → what we're building (S4) → how we win economically (S8) → where we go with AI (S9). Fix any narrative gaps that break the investor story flow.

**Checkpoint**: US4 complete — investor can evaluate market opportunity, competitive moat, pricing, and roadmap from this document alone.

---

## Phase 7: User Story 5 — Downstream Spec Authors Trace Requirements (Priority: P5)

**Goal**: Authors of downstream specs (spec-02 PRD, spec-03 data model, spec-07 roadmap, spec-09+ implementation) can trace every requirement back to a specific element in this vision document (persona, pain point, module, or phase).

**Independent Test**: Take any downstream spec requirement (e.g., "grain quality grading") — can it be traced to (a) Laboratorista persona JTBD, (b) Pain Point #4 producer disputes, (c) MVP scope CALIDAD module, (d) Phase 1? All 4 trace points must be present.

- [X] T039 [US5] Write Section 1 Document Metadata in target file — (a) header with Version 1.0, Date 2026-03-15, Status "Vision Document — Committed"; (b) copy Implementation Progress table verbatim from v0.4 (lines 13-28); (c) copy Feature Branch History table (branches 001-025) from v0.4 and update descriptions to reflect acopio vertical context. Source: `research.md §S1`, contract: `contracts/document-structure.md §S1-CONTRACT`
- [X] T040 [US5] Verify 25 branch rows in Feature Branch History — count rows in target file Feature Branch History table → must equal exactly 25 (001-025). Fix any missing or extra rows.
- [X] T041 [US5] Verify 6 Ironclad principles in target file — confirm Section 2 has exactly 6 principles: 4 original + "Regulatory Automation" + "AI-Ready Data Architecture". Confirm principle 6 forward-references to S9 AI capabilities.
- [X] T042 [US5] Audit traceability completeness — verify that the 5 traceability pairs from spec.md US5 are all resolvable: (1) grain quality grading → Laboratorista persona + Pain #4 + MVP CALIDAD module + Phase 1; (2) AI feature → Phase 4 roadmap + Research 9.1 citation. Fix any gaps in section language that break these traces.

**Checkpoint**: US5 complete — downstream spec authors can trace every requirement to a specific vision document element.

---

## Phase 8: Polish & Cross-Cutting Validation

**Purpose**: Final quality pass, cross-section consistency, and full acceptance checklist execution.

- [X] T043 [P] Run DL-001 full-text check — `grep -i "hardware store\|beverage distributor\|cashier\|under evaluation\|retail store"` on target file → expected zero results
- [X] T044 [P] Run DL-002 citation audit — search for all quantified claims (numbers, percentages, statistics) and verify each has [Research X.Y] citation. Fix any uncited statistics.
- [X] T045 [P] Run DL-003 Mermaid validation — copy each Mermaid block into https://mermaid.live or GitHub preview; confirm all 5+ diagrams render without syntax errors. Fix any broken diagrams.
- [X] T046 Run DL-004 length check — `wc -l "Docs/Project Blueprint/Product Vision & Scope.md"` → expected 500-1000 lines. If below 500, identify content gaps; if above 1000, tighten verbose sections.
- [X] T047 Run Gate 7 validation — AI roadmap gate: all capabilities are Phase 3-4 (not MVP); "3D-CNN" + "LSTM" appear together; "MILP" appears; "SVM-Poly" appears; [Research 9.1] citation present; forward reference to AI-Ready Data Architecture principle exists.
- [X] T048 Run cross-section consistency check:
  - Module names S4 vs Descripción General del Producto.md → match exactly
  - ARPU S10 ($360) = pricing S8 (4 × $90) → consistent
  - AI features S9 ALL in Phase 3-4 per S4 roadmap → no Phase 1/2 AI
  - Connectivity nuance S3 vs S11 → same message (plants in towns, brief harvest outages)
  - Contador channel S7 → matches Contador Rural persona in S5
  - SC-005 3-axes check: for each of the 11 competitor profiles confirm that NONE occupies all 3 of: cloud-native AND offline-first AND acopio-operational-depth simultaneously. GRAVITEA must be the sole occupant of that combination.
- [X] T049 Run full Document Acceptance Checklist from `contracts/document-structure.md §Full Document Acceptance Checklist` — mark all boxes. Commit only when all gates pass.
- [X] T050 Delete backup file `Docs/Project Blueprint/Product Vision & Scope.v0.4.backup.md` after confirming v1.0 is complete and validated

---

## Dependencies & Execution Order

### Phase Dependencies

```text
Phase 1 (Setup)                — No dependencies — start immediately
Phase 2 (Foundational — S3)   — Depends on Phase 1 — BLOCKS all user story phases
Phase 3 (US1 — S2, S4, S5)   — Depends on Phase 2 (S3 facts used in S2, S4, S5)
Phase 4 (US2 — S6)            — Depends on Phase 3 (S6 synthesizes S3+S4+S5)
Phase 5 (US3 — S7, S8)        — Depends on Phase 2 (S3 market map) + Phase 3 (personas)
Phase 6 (US4 — S9, S10, S11)  — Depends on Phase 3 (S4 roadmap positions S9 as Phase 4)
Phase 7 (US5 — S1)            — Depends on ALL phases (S1 metadata stamps the complete doc)
Phase 8 (Polish)               — Depends on Phase 7 (full doc must be written before validating)
```

### User Story Dependencies

```text
US1 (P1): Can start after Phase 2 Foundational — no US dependencies
US2 (P2): Can start after Phase 3 completes (S6 needs S3+S4+S5)
US3 (P3): Can start after Phase 2 completes — parallel with US1 (S7, S8 don't depend on S2/S5)
US4 (P4): Can start after Phase 3 completes (S9 references S4 roadmap + S1 principle 6)
US5 (P5): Must be last — S1 is written after all other sections are complete
```

### Parallel Opportunities Within Phases

**Phase 3 (US1)** — within-story parallelism (all target different parts of the document):
```text
T015 Module map Mermaid      — parallel with →  T016 Operational flow Mermaid
T018 Technical differentiators — parallel with → T019 Dual inventory
T015-T020 can all be drafted as separate sections, then assembled in writing order
```

**Phase 5 (US3)**:
```text
T029 Contador channel  — parallel with → T030 Geographic beachhead
T031 Trade events      — parallel with → T029, T030
```

**Phase 6 (US4)**:
```text
T035 S9 AI roadmap   — parallel with → T036 S10 KPIs
T036 S10 KPIs        — parallel with → T037 S11 Risks
```

**Phase 8 (Polish)**:
```text
T043 DL-001 grep check — parallel with → T044 Citation audit
T045 Mermaid validation — parallel with → T043, T044
```

---

## Parallel Example: Phase 3 (US1 — Sections 2, 4, 5)

```text
All can be drafted independently (different sections of the document):
Task T015: "Create Mermaid module map diagram (8 modules, Spanish names)"
Task T016: "Create Mermaid operational flow diagram (Romaneo-to-Position loop)"
Task T018: "Write Section 4.4 Technical Differentiators (offline-first #1)"
Task T019: "Write Section 4.5 Dual Inventory explanation"
Task T021: "Create Mermaid phased roadmap (4 phases)"

Then sequentially:
Task T014: Write Section 2 Strategic Purpose (reads S3 for market validation first)
Task T017: Write Section 4.3 MVP Scope (after T015 module map is done for reference)
Task T022: Write Section 5 Personas (after T015-T021 are done for module references)
```

---

## Implementation Strategy

### MVP — User Story 1 Only (US1: Developer Alignment)

1. Complete Phase 1: Setup (T001-T005)
2. Complete Phase 2: Market Context S3 (T006-T013) — foundation
3. Complete Phase 3: US1 — Vision, Product Scope, Personas (T014-T024)
4. **STOP and VALIDATE**: Run Gate 2+3+DL-001 — developer can now align all feature work
5. Branch `001-acopio-vision` can be reviewed/merged at this point if US1 passes

### Full Document Delivery

1. Setup + Foundational (T001-T013) → Market foundation ready
2. US1 (T014-T024) → Developer alignment ✅
3. US2 (T025-T028) → Product owner scope decisions ✅
4. US3 (T029-T034) → GTM planning ✅
5. US4 (T035-T038) → Investor evaluation ✅
6. US5 (T039-T042) → Spec author traceability ✅
7. Polish (T043-T050) → All acceptance criteria pass → v1.0 ready

### Single-Author Sequential Strategy

Since this is a single-author document task, the recommended writing session order is:

**Session 1** (2 hours): T001-T013 — Setup + entire S3 (market context)
**Session 2** (2 hours): T014-T024 — S2 + S4 + S5 (vision, product, personas)
**Session 3** (1.5 hours): T025-T034 — S6 + S7 + S8 (value prop, GTM, pricing)
**Session 4** (1.5 hours): T035-T042 — S9 + S10 + S11 + S1 (AI, KPIs, risks, metadata)
**Session 5** (30 min): T043-T050 — Full validation pass

---

## Notes

- [P] tasks = can be written in any order within the phase (different document sections)
- [Story] label maps writing task to specific user story for traceability to spec.md
- No code tests — validation is manual checklist execution from `contracts/document-structure.md`
- CRITICAL data source: `specs/001-acopio-vision/research.md` — use this, NOT raw research PDFs
- All RAG queries already executed — do not re-run unless a claim needs verification
- Commit after completing each phase (not after each individual task)
- If any Mermaid diagram fails to render, try GitHub preview before assuming syntax error
